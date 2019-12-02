#!/usr/bin/python

import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import datetime
import math

from libs.Mixpanel import Mixpanel
from libs.platform import getAddonPath

mp_token = Mixpanel('0f2e8ba3e39bda1226054ba0b84c7146')
addon = xbmcaddon.Addon("service.purevpn.monitor")
version = addon.getAddonInfo('version')
clientId = ''
timestr = ''

# Getting client id from a file created which will be used in every mixpanel event call as a distinct id.
def getClientId():
    global clientId
    vpn_provider = addon.getSetting("vpn_provider")
    if os.path.isfile(getAddonPath(True, vpn_provider + "/loginDetails.txt")):
        with open(getAddonPath(True, vpn_provider + "/loginDetails.txt"), 'r') as fx:
            lines = fx.readlines()
            if lines[2]:
                clientId = lines[2]
            else:
                clientId = 'Not valid'

# Setting Time for Mixpanel Events.
def setTime():
    global timestr
    # Current Time of system
    currentTime = time.time()
    # Working aroung to trim the time w.r.t to our requirements.
    step1 = currentTime/86400
    step2 = math.floor(step1)
    #Time in required format
    timestr = step2* 86400

# Event defined for connected state
def mp_connected(state1, state, vpn_username, countrY, protO_typE, sT_dnS_adD, country, ii):
    global clientId, timestr
    getClientId()
    setTime()
    mp_event = 'kodi_connected'
  
    if state1 == 1:
        status = 'True'
    else: 
        status = 'False'
    
    try:
        mp_token.track(clientId, mp_event, {'username': vpn_username,
                                            'device_type': 'kodi',
                                            'selected_location': countrY,
                                            'selected_protocol': protO_typE,
                                            'st_server': sT_dnS_adD,
                                            'assigned_location': country,
                                            'st_status' : status,
                                            'st_time_to_connect': ii,
                                            'addon_version': version,
                                            'time': timestr})
   
    except Exception as e:
        print str(e) + ' on ' + mp_event
   
# Event defined for utc state
def mp_utc(vpn_username, countrY, protO_typE, dialog_message):
    global clientId, timestr
    getClientId()
    setTime()
    mp_event = 'kodi_utc'
 
    try:
        mp_token.track(clientId, mp_event, {'username': vpn_username,
                                            'device_type': 'kodi',
                                            'selected_location': countrY,
                                            'selected_protocol': protO_typE,
                                            'reason_utc': dialog_message,
                                            'addon_version': version,
                                            'time': timestr})

    except Exception as e:
        print str(e) + ' on ' + mp_event

# Event defined for disconnected state
def mp_disconnected(vpn_username, country):
    global clientId, timestr
    getClientId()
    setTime()
    mp_event = 'kodi_disconnected'
 
    try:
        mp_token.track(clientId, mp_event, {'username': vpn_username,
                                            'device_type': 'kodi',
                                            'source_location': country,
                                            'addon_version': version,
                                            'time': timestr})

    except Exception as e:
        print str(e) + ' on ' + mp_event

# Event defined for Autoconnect/ Connection after split tunneling.
def mp_autoConnect(vpn_username, protO_typE, countrY):
    global clientId, timestr
    getClientId()
    setTime()
    mp_event = 'kodi_connected'
   
    try:
        mp_token.track(clientId, mp_event, {'username': vpn_username,
                                            'last_connected_protcol': protO_typE,
                                            'last_connected_location': countrY,
                                            'device_type': 'kodi',
                                            'addon_version': version,
                                            'time': timestr})
    except Exception as e:
        print str(e) + ' on ' + mp_event

def mp_limitExceed(vpn_username):
    global clientId, timestr
    getClientId()
    setTime()
    mp_event = 'VPNApp_MultiLoginExceeded'
    
    try:
        mp_token.track(clientId, mp_event, {'username': vpn_username,
                                            'App_DeviceType': 'kodi',
                                            'Version': version,
                                            'time': timestr})
    except Exception as e:
        print str(e) + ' on ' + mp_event
