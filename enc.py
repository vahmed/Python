#!/usr/bin/python 
#
# Generate encrypted string
#
import base64
import getpass
import codecs
from simplecrypt import encrypt, decrypt

data = getpass.getpass('Data to encrypt:')
passphrase = getpass.getpass('Passphrase:')

def enc(data,passphrase):
    ciphertext = encrypt(passphrase, data)
    ciphertext = base64.b64encode(ciphertext)
    hex_passphrase = codecs.encode(passphrase, 'hex')
    print 'Data: ', ciphertext
    print 'Passphrase: ', hex_passphrase
    return ciphertext

if __name__ == '__main__':
    encr = enc(data,passphrase)
