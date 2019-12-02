#!/usr/bin/python
# -*- coding: utf-8 -*-

import os 
import urllib
import urllib2
import json
import re
import xbmc
import xbmcgui
import xbmcaddon

from libs.platform import getAddonPath
from libs.utility import debugTrace

addon = xbmcaddon.Addon("service.purevpn.monitor")
vpn_provider = addon.getSetting("vpn_provider")

# Getting country code form the country selected
def getCountryId(countrY):
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    vpn_provider = addon.getSetting("vpn_provider")
    fname = str(getAddonPath(True, vpn_provider + "/countriesList.json"))
    debugTrace(fname)
    with open(fname, 'r') as fp:
        return_list = json.load(fp)
    
    for key,value in return_list.items():
        arr = [',',')','(']
        for character in arr:
            if character in value:
                value = value.replace(character, '')
        return_list[key] = value
    try:
    	countrY_iD = return_list.keys()[return_list.values().index(str(countrY))]
    	debugTrace(countrY_iD)
    	
    except:
	countrY_iD = '254'
    return countrY_iD


# Making a call to speedtest api for getting the fastest server acc. to the detils provided
def callToSTApi(protO_iD, vpn_username, countrY_iD):

    #urL = 'https://api.atom.purevpn.com/speedtestbeta/v1/getServersWithoutPsk'
    #urL = 'https://api.atom.purevpn.com/speedtest/v2/getServersWithoutPsk'
    urL = 'https://atomapi.com/speedtest/v2/getServersWithoutPsk'
    valueS = {'iCountryId': countrY_iD,
              'iResellerId': '1',
              'iProtocolNumber1': protO_iD,
              'iMcs' : '1',
              'sDeviceType': 'android',
              'sUsername': vpn_username}
 
    headeR = {'User-Agent': 'kodi-http-client', 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json', 'X-Psk': 'utNJGncZCcbFVf3Okvr4'}
    try: 
        datA = urllib.urlencode(valueS)
        requesT = urllib2.Request(urL, datA, headeR)
        responsE = urllib2.urlopen(requesT)
        raW_responsE = responsE.read()
        jsoN_responsE = json.loads(raW_responsE)
    except:
        jsoN_responsE = 'null'
    return jsoN_responsE


# Extracting the useful information from the response get from speedtest api
def stDetails(jsoN_responsE):
     
     returN_lisT = {}
     checK = 1

     if 'header' in jsoN_responsE:
         st_resp_code = int(jsoN_responsE['header']['code'])
         st_resp_msg = str(jsoN_responsE['header']['message'])
         if int(jsoN_responsE['header']['code']) == checK:
             for key in jsoN_responsE:
                 mp_event = 'kodi_connecting'
                 if key == 'body':
                     if 'servers' in jsoN_responsE[key]:
                         jsoN_responsE_serveR = jsoN_responsE[key]['servers']
                         for item in jsoN_responsE_serveR:
                             for key2 in item:
                                 if key2 == 'host':
                                     returN_lisT[key2] = item[key2]
                                 elif key2 == 'acknowledgement_server':
                                     returN_lisT[key2] = item[key2]
                                 elif key2 == 'protocol_no':
                                     returN_lisT[key2] = item[key2]
                                 elif key2 == 'server_type':
                                     returN_lisT[key2] = item[key2]
                                 elif key2 == 'configuration':
                                     returN_lisT[key2] = item[key2]
         
         # Working for if username and other details are valid it will return  a server in resp1 and type in resp2         
             response1 = str(returN_lisT['host'])
             response2 = str(returN_lisT['server_type'])
             response3 = str(returN_lisT['configuration'])
         
         # Else it will set the credentials for error message
         else:
             response1 = 'Error Connecting to PureVPN'
             response2 = st_resp_msg
             response3 = 'null'

         debugTrace('Response 1 ' + response1)
         debugTrace('Response 2 ' + response2)
         debugTrace('Resposne 3 ' + response3)

     return st_resp_code, response1, response2, response3

   
# Creating a custom config file for speedtest returned server         
def createCustomFile(sT_confiG, ovpn_connection, sT_dnS_patH, protO_typE, protO_nuM, vpn_provider, sT_dnS_adD, sT_dnS_typE):
    pathToAuthFile = str(getAddonPath(True, vpn_provider + "/pass.txt"))
    pathToDnsPatch = str(getAddonPath(True, vpn_provider + "/dnsLeak.py"))

    with open (sT_dnS_patH, 'w') as config_file:
        config_file.write(sT_confiG + '\nauth-user-pass ' + pathToAuthFile)
        config_file.write("\nup '/bin/bash -c \"python " + pathToDnsPatch + '"\'' + "\ndown '/bin/bash -c \"python " + pathToDnsPatch + '"\'')
