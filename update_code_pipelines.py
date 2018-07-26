#!/usr/bin/python
"""
This script updates code pipelines with branch information passed as an argument
"""

__author__ = "Nasir Ahmed"
__version__ = "1.0"

import re
import json
import pprint
import os.path
import crayons
import argparse
import ConfigParser
import boto3

parser = argparse.ArgumentParser(description='Code Pipeline Update Script')
parser.add_argument('-p', action='store', help='Boto3 profile: default, dev, qa, prod')
parser.add_argument('-u', action='store', help='Branch: release/x.xx or master')
parser.add_argument('-v', action='version', version='1.0')

args = parser.parse_args()


""" Read AWS Credentials
Get users' home dir """
home_path = os.path.expanduser('~')
""" relative AWS creds location note the leading '/' is required for this implementation """
cred_file = '/.aws/credentials'
""" combine both to get path to our credentials """
cfg_file = home_path + cred_file
config = ConfigParser.ConfigParser()
config.readfp(open(cfg_file))

if args.p is not None:
    env = args.p
else:
    env = 'qa'

""" read values from a section """
aws_access_key_id = config.get(env, 'aws_access_key_id')
aws_secret_access_key = config.get(env, 'aws_secret_access_key')
aws_session_token = config.get(env, 'aws_session_token')

out_dir = './cpl_data/'

REGIONS = ['us-east-1']

def get_pipelines(run):
    code_pipeline = boto3.client('codepipeline', aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key, aws_session_token = aws_session_token)
    pipelines = code_pipeline.list_pipelines()
    i = 0
    p = {}
    for k, v in pipelines.items():
        while i < len(v):
            if re.findall(r'pipelineTest',v[i]['name'],re.IGNORECASE):
                response = code_pipeline.get_pipeline(name=v[i]['name'])
                if response['pipeline']['stages'][0]['actions'][0]['actionTypeId']['provider'] == 'GitHub':
                    print crayons.white('Pipeline: ') + crayons.yellow(response['pipeline']['name'])
                    print crayons.white('Branch: ') + crayons.white(response['pipeline']['stages'][0]['actions'][0]['configuration']['Branch'])
                    p_name = out_dir + str(response['pipeline']['name']) + '.json'
                    print crayons.white('File: ') + crayons.yellow(p_name)
                    #del response['pipeline']['name']['artifactStore']
                    if run == 'first':
                        with open(p_name, 'w') as outfile:
                            json.dump(response['pipeline'], outfile)
                            p.update({response['pipeline']['name']:p_name})
                    elif run == 'second':
                        print crayons.white('Pipeline: ') + crayons.yellow(response['pipeline']['name'])
                        print crayons.white('Branch: ') + crayons.white(response['pipeline']['stages'][0]['actions'][0]['configuration']['Branch'])
                        
                pprint.pprint(response)
                #j = json.dumps(response['pipeline'],sort_keys=True, indent=4, separators=(',', ': '))
            i += 1
                #exit(1)
    return p

def update_code_pipeline(p, args):
    code_pipeline = boto3.client('codepipeline', aws_access_key_id = aws_access_key_id, aws_secret_access_key = aws_secret_access_key, aws_session_token = aws_session_token)
    pipelines = code_pipeline.list_pipelines()
    #pprint.pprint(p)
    print crayons.red('\nUpdate Branch To: %s' % str(args.u))
    msg = 'Do you want to continue?'
    yes_no = raw_input("%s (Y/n) " % msg) == 'Y'
    if yes_no:
        for p, f in p.items():
            with open(f, 'r') as jsonFile:
                data = json.load(jsonFile)
                orig_b = data['stages'][0]['actions'][0]['configuration']['Branch']
                data['stages'][0]['actions'][0]['configuration']['Branch'] = args.u
            with open(f, 'w') as jsonFile:
                json.dump(data, jsonFile)
        up = code_pipeline.update_pipeline(f)
        print crayons.red('Branch Updated To: %s' % str(args.u))
        get_pipelines(run='second')

if __name__ == '__main__':
    for REGION in REGIONS:
        print crayons.white('#####################')
        print crayons.white('UPDATE CODE PIPELINES')
        print crayons.white('#####################') + '\n'
        print crayons.white('REGION: %s' % REGION.upper()) + '\n'
        p = get_pipelines(run='first')
        if args.u is not None:
            update_code_pipeline(p, args)
