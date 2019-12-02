#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import urllib2
import os
import urllib
import xbmcaddon
import xbmcvfs
import urllib
import xbmc
import re
import xbmcgui
import xbmc
import json


from libs.common import getAddonPath
from libs.utility import debugTrace
from libs.vpnproviders import removeGeneratedFiles

# Initializing some required variables
addon = xbmcaddon.Addon("service.purevpn.monitor")
version = addon.getAddonInfo('version')
vpn_provider = addon.getSetting("vpn_provider")
timestr = time.strftime('%W')
flag = 5

def updatePureResolver():
    resolverPath = str(getAddonPath(True, vpn_provider + "/dnsLeak.py"))
    dirPath = str(getAddonPath(True, vpn_provider))
    with open (resolverPath,'r') as f_old:
        read = f_old.readlines()
    with open (resolverPath, 'w') as f_new:
        for line in read:
            if 'purevpnPath=' in line:
                f_new.write('purevpnPath=' + '"' + dirPath + '"\n')
            else:
                f_new.write(line)

    f_old.close()
    f_new.close()

def checkLatestFailover():
    # Checking for latest failover LOCATIONS.txt file
    rawLoc = str(getAddonPath(True, vpn_provider + "/rawLocations.txt"))
    Locations = str(getAddonPath(True, vpn_provider + "/LOCATIONS.txt"))
    url = 'https://s3.amazonaws.com/purevpn-dialer-assets/kodi/app/LOCATION.json'

    resp = urllib2.urlopen(url, timeout = 3)
    data = json.load(resp)
    data1 = data.values()
    with open(rawLoc, 'w') as file:
        if type(data1)==list:
            file.write(str(data1)+ "\n")

    if os.path.exists(Locations):
        os.remove(Locations)

    delete_list = ["[[u'", " u'", "'", ", [u", "[","crt]","]"]

    fin = open(rawLoc)
    fout = open(Locations, "w+")
    fout.seek(0)
    for line in fin:
        for word in delete_list:
            if word == "crt]":
                line = line.replace(word,"crt\n")
            line = line.replace(word, "")
        
        fout.write(line[:-1])
    fin.close()
    fout.close()
    os.remove(rawLoc)

def checkLatestCountries():   
    #url = 'https://api.atom.purevpn.com/inventory/v1/getCountries/1?iResellerId=1'
    url = "https://atomapi.com/inventory/v1/getCountries/1"
    req = urllib2.Request(url,headers={'User-Agent' : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30" , "Content-Type": "application/x-www-form-urlencoded", "X-Psk": "utNJGncZCcbFVf3Okvr4"})
    try:
        resp = urllib2.urlopen(req, timeout = 4)
        html = resp.read()
        data = json.loads(html)
        return_list = {}
        if 'body' in data:
            print 'yes'
            #with open ('hello.json', 'w') as countries_list:
            if 'countries' in data['body']:
                data_body_countries = data['body']['countries']
                for item in data_body_countries:

                    return_list[item['id']] = item['name']

        fname = str(getAddonPath(True, vpn_provider + "/countriesList.json"))
        with open (fname, 'w') as fp:
            json.dump(return_list, fp, indent=4)
    
    except Exception as e:
        print e

# The function will check for the latest version if available on website
def checkLatestVersion():
    debugTrace('Current version is ' + version)   
    global flag
    #url = "https://s3.amazonaws.com/purevpn-dialer-assets/linux/app/version.json"
    url = "https://s3.amazonaws.com/purevpn-dialer-assets/kodi/app/version.json"
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    
    req = urllib2.Request(url,headers={'User-Agent' : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30" , "Content-Type": "application/x-www-form-urlencoded"})

    try:
        response = urllib2.urlopen(req, timeout = 2)
        html = response.read()
        data = json.loads(html)
        for key in data:
            my_string = data[key]

        debugTrace('Version Available for download is ' + my_string)
        if version == my_string:
            debugTrace('no update available')
            flag = 0
        else:
            debugTrace('update available')
            flag = 1
    except:
        pass


# Will create a file with current version and time checker (day number)
def createUpdateChecker():
    global flag
    fname = str(getAddonPath(True, vpn_provider + "/updatechecker.txt"))
    if os.path.isfile(fname):
        with open(fname, 'r+') as file:
            i = file.read()
            if i != timestr:
                try:
                    removeGeneratedFiles()
                    debugTrace("Removed")
                except Exception as e:
                    print str(e) + ' on removing old ovpn files'

                try:
                    updatePureResolver()
                    debugTrace("Resolver Updated")
                except Exception as e:
                    print str(e) + ' on updating resolver'

                try:
                    checkLatestFailover()
                    debugTrace("Failover Checked")
                except Exception as e:
                    print str(e) + ' on checking failover'

                try:
                    checkLatestCountries()
                    debugTrace("Countries List Updated")
                except Exception as e:
                    print str(e) + ' on updating counties list'
               
                try:
                    checkLatestVersion()
                    debugTrace("Latest Addon version checked")
                except Exception as e:
                    print str(e) + ' on checking latest version'
               
                file.seek(0)
                file.truncate()
                file.write(timestr)
               
                debugTrace('file overwritten')

            else:
                debugTrace('No need to check now')
              
                file.close()
           
    else:
        try:
            removeGeneratedFiles()
            debugTrace("Removed")
        except Exception as e:
            print str(e) + ' on removing old ovpn files'
        
        try:
            updatePureResolver()
            debugTrace("Resolver Updated")
        except Exception as e:
            print str(e) + ' on updating resolver'

        try:
            checkLatestFailover()
            debugTrace("Failover Checked")
        except Exception as e:
            print str(e) + ' on checking failover'

        try:
            checkLatestCountries()
            debugTrace("Countries List Updated")
        except Exception as e:
            print str(e) + ' on updating counties list'

        try:
            checkLatestVersion()
            debugTrace("Latest Addon version checked")
        except Exception as e:
            print str(e) + ' on checking latest version'

        with open(fname, 'w') as file:
            file.write(timestr)
            file.close()
      
        debugTrace('file created and written')
        

    if flag == 1:
        debugTrace('yes')
      
        return True
    else:
        debugTrace('no')
      
        return False

createUpdateChecker()
