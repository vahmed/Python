#!/usr/bin/python

import sys
import pexpect
from pexpect import pxssh

def cvs():
    
    VS_PROMPT="Selection#: "
    CLI_PROMPT="% "
    RST_PROMPT=" confirm \[n\] "
    
    user = ''
    host = ''
    passwd = ''

    s = pxssh.pxssh()
    #s.logfile_read = open("cvs.log", "w")
    s.logfile_read = sys.stdout
    s.login(host,user,passwd)
    s.sendline('/usr/lib/NetScout/rtm/bin/localconsole')
    s.expect(VS_PROMPT)
    s.sendline('15')
    s.expect(VS_PROMPT)
    s.sendline('15')
    s.expect(VS_PROMPT)
    s.sendline('99')
    s.expect(VS_PROMPT)
    s.sendline('11')
    s.expect(CLI_PROMPT)
    s.sendline('set asi 3 conv on')
    s.expect(CLI_PROMPT)
    s.sendline('set tsa auto')
    s.expect(CLI_PROMPT)
    s.sendline('set tsa commit')
    s.expect(RST_PROMPT)
    s.sendline('y')
    s.prompt()
    s.logout()

    return None

if __name__ == '__main__':
    cvs()
