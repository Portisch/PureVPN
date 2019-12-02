#!/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import xbmcaddon
import xbmcvfs
import xbmcgui
import xbmc 
import shutil
import json
import urllib
import urllib2
import os

from libs.platform import getAddonPath
from libs.utility import debugTrace

flag = ''
status = ''
clientId = 1
vpn_username = ''
vpn_password = ''
addon = xbmcaddon.Addon("service.purevpn.monitor")
vpn_provider = addon.getSetting("vpn_provider")


def createDetailsFile():
    global flag, status, clientId, vpn_provider
   
    # Creating a file for user's verification status and clientId
    fname1 = getAddonPath(True, vpn_provider + "/loginDetails.txt")
    if os.path.isfile(fname1):
        os.remove(fname1)
     
    with open(fname1,'w') as file4:
        file4.write(str(flag) + '\n' + str(status) + '\n' + str(clientId))
        file4.close()

    debugTrace('File containing cliendId created')

def throwCall():
    global flag, status, clientId, vpn_username, vpn_password

    # Calling api to verify credentials and to get clientId
    url = "https://api.dialertoserver.com/user/login.json?api_key=pvpnUserPrd"
    values = {"sUsername": vpn_username,"sPassword": vpn_password,'sDeviceType': 'android','sDeviceId': '1', 'iResellerId': '1'}
    header = {'content-type': 'application/x-www-form-urlencoded', 'X-Psk': 'utNJGncZCcbFVf3Okvr4'}
    debugTrace('Making a call to api for credentials verification and getting client id')
    data = urllib.urlencode(values)
    request = urllib2.Request(url, data, header)
    response = urllib2.urlopen(request)
    result = response.read()
    resp_json = json.loads(result)

    if resp_json['header']['code'] == '0':
        clientId = resp_json['body']['client_id']
        if resp_json['body']['status'] != "":
            status = resp_json['body']['status']
            flag = 'uta'
            stack = '1'
        else:
            status = resp_json['header']['message']
            flag = 'auth'
            stack = '2'
    else:
        clientId = ''
        status = resp_json['header']['message']
        flag = 'uta'
        stack = '3'
    
def createUnPass():
    global status, lag, clientId, vpn_username, vpn_password, vpn_provider, addon
    digests = []

    # The function will check if there is any diffrence between the usernames before and after by comparing the hash files before and after.
    # If there is a diffrence it will forward to check credentials. if no diffrence will discontinue.

    # Will create a file with username and password.
    fname2 = getAddonPath(True, vpn_provider + "/tempauth.txt")
    with open (fname2, 'w') as file:
        vpn_username = addon.getSetting("vpn_username")
        vpn_password = addon.getSetting("vpn_password")
        file.write(vpn_username +'\n' + vpn_password)
        file.close()
    
    # Will check for the older file having username and password and will compare the two files using their hashes.    
    fname3 = getAddonPath(True, vpn_provider + "/auth.txt")    
    if os.path.isfile(fname3):
        for filename in [fname2, fname3]:
            hasher = hashlib.md5()
            with open(filename, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
                a = hasher.hexdigest()
                digests.append(a)

        # If hashes are diffrent will replace the older file with new one and throw a call to get the clientId for latest credential else do nothing
        if(digests[0] == digests[1]) == False:
            debugTrace('Hashes are diffrent')
            shutil.copy2(fname2, fname3)
            throwCall()
            createDetailsFile()

    # If first use, and cant find old file (auth1) then will not compare and will continue with call to get the clientId for latest credentials
    else:
        shutil.copy2(fname2, fname3)
        throwCall()
        createDetailsFile()
    # Remove temporary created auth file i.e. tempauth
    if os.path.isfile(fname2):
        os.remove(fname2) 
