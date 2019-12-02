#!/usr/bin/python
# -*- coding: utf-8 -*-
#    
#    KODI PureVPN Addon by ahlat :)
#    Copyright (C) 2016 Zomboided
#    modified Copyright (C) 2016 PureVPNLtd
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    Shared code fragments used by the VPN Manager for OpenVPN add-on.

import xbmcaddon
import xbmcvfs
import shutil
import json
import urllib
import xbmc
import os
import re
import urllib2
import xbmcgui
import xbmc
import glob
import sys
import xbmcgui
import ssl
from libs.platform import getVPNLogFilePath, fakeConnection, isVPNTaskRunning, stopVPN, startVPN, getAddonPath, getSeparator, getUserDataPath
from libs.platform import getVPNConnectionStatus, connection_status, getPlatform, platforms, writeVPNLog, checkVPNInstall, checkVPNCommand
from libs.utility import debugTrace, infoTrace, errorTrace, ifDebug
from libs.vpnproviders import getVPNLocation, getRegexPattern, getProfileList, provider_display, usesUserKeys, usesSingleKey, gotKeys
from libs.vpnproviders import ovpnFilesAvailable, fixOVPNFiles, getLocationFiles, removeGeneratedFiles, copyKeyAndCert, genovpnFiles
from libs.vpnproviders import usesPassAuth, cleanPassFiles
from libs.ipinfo import getIPInfoFrom, getIPSources
from libs.ganalytics import getIP2Location, sendGoogleAnalytics, sendGoogleAnalyticsConnectedCountry
from libs.Mixpanel import Mixpanel
from libs.stserver import getCountryId, callToSTApi, stDetails, createCustomFile
from libs.mp import mp_connected, mp_disconnected, mp_utc, mp_autoConnect, mp_limitExceed 


def getIconPath():
    return getAddonPath(True, "/resources/")    
    

def getFilteredProfileList(ovpn_connections, filter, addon):
    # Filter out the profiles that we're not using
    
    # Filter based on protocol type
    if "TCP" in filter:
        filterTCP = "(TCP"
    else:
        filterTCP = "()"
    if "UDP" in filter:
        filterUDP = "(UDP"
    else:
        filterUDP = "()"

    # Filter out connections already in use.  If we don't wanna filter
    # the primary connections, just pass 'None' in as the addon
    used = []
    if not addon == None:        
        i = 1
        # Adjust the 11 below to change conn_max
        while i < 11:
            s = addon.getSetting(str(i) + "_vpn_validated")
            if not s == "" : used.append(s)
            i = i + 1
        
    connections = []
    for connection in ovpn_connections:
        if filterTCP in connection or filterUDP in connection:
            if not connection in used:
                connections.append(connection)                 
    return connections

    
def getFriendlyProfileList(vpn_provider, ovpn_connections):
    # Munge a ovpn full path name is something more friendly
    
    connections = []
    regex_str = getRegexPattern(vpn_provider)
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Produce a compiled pattern and interate around the list of connections
    pattern = re.compile(regex_str)
    for connection in ovpn_connections:
        connections.append(pattern.search(connection).group(1))        
    return connections
    

def getFriendlyProfileName(vpn_provider, ovpn_connection):
    # Make the VPN profile names more readable to the user to select from
    regex_str = getRegexPattern(vpn_provider)
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Return friendly version of string
    match = re.search(regex_str, ovpn_connection)
    return match.group(1)
    

def getIPInfo(addon):
    # Based this code on a routine in the VPN for OPENELEC plugin
    # Generate request to find out where this IP is based
    # Return ip info source, ip, location, isp
    source = addon.getSetting("ip_info_source")
    if not source in getIPSources():
        addon.setSetting("ip_info_source", getIPSources()[0])
        source == getIPSources()[0]

    debugTrace("Getting IP info from " + source)
    retry = 0
    while retry < 3:
        ip, country, region, city, isp = getIPInfoFrom(source)
 	debugTrace(str(ip) + str(country) + str(region) + str(city) + str(isp))
        if ip == "no info":
            debugTrace("No location information was returned for IP using " + source)
            # Got a response but couldn't format it.  No point retrying
            return source, "no info", "unknown", "unknown"
        elif ip == "error":
            errorTrace("common.py", "Something bad happened when trying to get a response from iplocation.net " + isp)
            # Didn't get a valid response so want to retry three times in case service was busy
            if retry == 2 : return source + " (not available)", "unknown", "unknown", "unknown"
            xbmc.sleep(1500)
	    disconnectVPN2()            
        else:
	    
            # Worked, exit loop
            break
        retry = retry + 1
        
    location = ""
    if not (region == "-" or region == "Not Available"): location = region
    if not (country == "-" or country == "Not Available"):
        if not location == "": location = location + ", "
        location = location + country

    return source, ip, location, isp

    
def resetVPNConfig(addon, starting):    
    # Reset all of the connection config options
    i = starting
    # Adjust 11 below if changing number of conn_max
    while i < 11:
        addon.setSetting(str(i) + "_vpn_validated", "")
        addon.setSetting(str(i) + "_vpn_validated_friendly", "")
        i = i + 1
    
    
def settingsValidated(addon):
    if addon.getSetting("vpn_username") == "" and addon.getSetting("vpn_password") == "": return False
    return True


def stopVPNConnection():
    # Kill the running VPN task and reset the current VPN window properties
    setVPNProfile("")
    setVPNProfileFriendly("")
    debugTrace("Stopping VPN")

    # End any existing openvpn process
    waiting = True
    while waiting:
        # Send the kill command to end the openvpn process
        stopVPN()
    
        # Wait half a second just to make sure the process has time to die
        xbmc.sleep(500)

        # See if the openvpn process is still alive
        waiting = isVPNConnected()
            
    setVPNState("stopped")
    return



def startVPNConnection(vpn_profile):  
   
    # Initializing some variables required
    ovpn_connection = vpn_profile     
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    vpn_username = addon.getSetting("vpn_username")
    vpn_provider = addon.getSetting("vpn_provider")

    # Extacting last connected country and protocol
    splitted = vpn_profile.split("PureVPN/",1)[1]
    countrY, protocoL = splitted.split('(')
    protocoL = protocoL.split('.')[0]
    debugTrace('Last connected country was: ' + countrY)
    debugTrace('Last connected protocol was: ' + protocoL)

    # Setting up protocol from the info extracted
    if protocoL == 'UDP)':
        protO_nuM = ' 53'
        protO_typE = 'udp'
        protO_iD = 9
    elif protocoL == 'TCP)':
        protO_nuM = ' 80'
        protO_typE = 'tcp'
        protO_iD = 8

    # Function call for fetching country code
    countrY = countrY[:-1]
    countrY_iD = getCountryId(countrY)
    debugTrace('Country code: ' + countrY_iD)

    # Function call to make a speedtest request
    jsoN_responsE = callToSTApi(protO_iD, vpn_username, countrY_iD) 
    debugTrace('Speedtest Response: ' + str(jsoN_responsE))

    # Function call to extract details from the speedtest response
    st_resp_code, response1, response2, response3 = stDetails(jsoN_responsE)
    debugTrace('Response Code is: ' + str(st_resp_code))

    # Handling if wrong or expired username is used 
    if st_resp_code != 1:
        addonname = 'PureVPN'
        xbmcgui.Dialog().ok(addonname, response1, response2)
        sys.exit()
    
    # if username is valid, setting up the variables for w.r.t speedtest response
    else:
        sT_dnS_adD = response1
        sT_dnS_typE = response2
        sT_confiG = response3
    debugTrace('Server address from speedtest response: ' + sT_dnS_adD)
 
    # Creating a custom config file from speedtest response
    sT_dnS_patH = str(getAddonPath(True, vpn_provider + "/custom.ovpn"))
    debugTrace('Path for custom config file is: ' + sT_dnS_patH)

    createCustomFile(sT_confiG, ovpn_connection, sT_dnS_patH, protO_typE, protO_nuM, vpn_provider, sT_dnS_adD, sT_dnS_typE)
    vpn_profile = sT_dnS_patH 
    debugTrace('Config file created for speedtest connection: ' + vpn_profile)
    
    # Starting VPN Connection
    startVPN(vpn_profile)

    debugTrace("Waiting for VPN to connect")
    debugTrace('Making Connection using' + vpn_profile)
    i = 0
    loop_max = 77
    if fakeConnection(): loop_max = 2

    while i <= loop_max:
        xbmc.sleep(2000)
        state = getVPNConnectionStatus()
        if not state == connection_status.UNKNOWN: break
        i = i + 2

    if fakeConnection(): state = connection_status.CONNECTED

    if state == connection_status.CONNECTED:
        setVPNProfile(getVPNRequestedProfile())
        setVPNProfileFriendly(getVPNRequestedProfileFriendly())
        setVPNState("started")
        debugTrace("VPN connection to " + getVPNProfile() + " successful")
        addon = xbmcaddon.Addon("service.purevpn.monitor")
        vpn_username = addon.getSetting("vpn_username")
        _, ip, country, isp = getIPInfo(addon)
        # Mixpanel Event for AutoConnect / After SplitTunneling
        mp_autoConnect(vpn_username, protO_typE, countrY)
        debugTrace('Mixpanel Event successfully reported')

    return state

def isVPNConnected():
    # Return True if the VPN task is still running, or the VPN connection is still active
    # Return False if the VPN task is no longer running and the connection is not active
    
    # If there's no profile, then we're not connected (or should reconnect...)
    if getVPNProfile() == "" : return False
    
    # Make a call to the platform routine to detect if the VPN task is running
    return isVPNTaskRunning()
    
    
def setVPNLastConnectedProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_Profile_Name", profile_name)
    return

    
def getVPNLastConnectedProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Last_Profile_Name")

    
def setVPNLastConnectedProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNLastConnectedProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Last_Profile_Friendly_Name")       
    
    
def setVPNRequestedProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Profile_Name", profile_name)
    return

    
def getVPNRequestedProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Profile_Name")

    
def setVPNRequestedProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNRequestedProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Profile_Friendly_Name")    


def setVPNProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Profile_Name", profile_name)
    return

    
def getVPNProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Name")

    
def setVPNProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Friendly_Name")    


def setConnectionErrorCount(count):
    # Return the number of times a connection retry has failed
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connection_Errors", str(count))


def getConnectionErrorCount():
    # Return the number of times a connection retry has failed
    err = xbmcgui.Window(10000).getProperty("VPN_Manager_Connection_Errors")
    if err == "": return 0
    return int(xbmcgui.Window(10000).getProperty("VPN_Manager_Connection_Errors"))

    
def setVPNState(state):
	# Store current state - "off" (deliberately), "stopped", "started", "" (at boot) or "unknown" (error)
    xbmcgui.Window(10000).setProperty("VPN_Manager_VPN_State", state)
    return

    
def getVPNState():
	# Store current state
    return xbmcgui.Window(10000).getProperty("VPN_Manager_VPN_State")
    
    
def startService():
    # Routine for config to call to request that service starts.  Can time out if there's no response
    # Check to see if service is not already running (shouldn't be...)
    if not xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    
    debugTrace("Requesting service restarts")
    # Update start property and wait for service to respond or timeout
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "start")
    for i in range (0, 30):
        xbmc.sleep(1000)
        if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "started": return True
    # No response in 30 seconds, service is probably dead
    errorTrace("common.py", "Couldn't communicate with VPN monitor service, didn't acknowledge a start")
    return False

    
def ackStart():
    # Routine for service to call to acknowledge service has started
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "started")

    
def startRequested():
    # Service routine should call this to wait for permission to restart.  
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "start": return True
    return False

    
def stopService():
    # Routine for config to call to request service stops and waits until that happens
    # Check to see if the service has stopped previously
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    
    debugTrace("Requesting service stops")
    # Update start property and wait for service to respond or timeout
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "stop")
    for i in range (0, 30):
        xbmc.sleep(1000)
        if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    # Haven't had a response in 30 seconds which is badness
    errorTrace("common.py", "Couldn't communicate with VPN monitor service, didn't acknowledge a stop")
    return False

    
def stopRequested():
    # Routine for service to call in order to determine whether to stop
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stop": return True
    return False
    
    
def ackStop():    
    # Routine for service to call to acknowledge service has stopped
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "stopped")

    
def updateService():
    # Set a windows property to tell the background service to update using the latest config data
    debugTrace("Update service requested")
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Update", "update")

    
def ackUpdate():
    # Acknowledge that the update has been received
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Update", "updated")


def forceCycleLock():
    # Loop until we get the lock, or have waited for 10 seconds
    i = 0
    while i < 10 and not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "":
        xbmc.sleep(1000)
        i = i + 1
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "Forced Locked")
    
    
def getCycleLock():
    # If the lock is forced, don't wait, just return (ie don't queue)
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "Forced Locked" : return False
    # If there's already a queue on the lock, don't wait, just return
    if not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock_Queued") == "" : return False
    # Loop until we get the lock or time out after 5 seconds
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock_Queued", "Queued")
    i = 0
    while i < 5 and not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "":
        xbmc.sleep(1000)
        i = i + 1
    # Free the queue so another call can wait on it
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock_Queued", "")   
    # Return false if a forced lock happened whilst we were queuing
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "Forced Locked" : return False
    # Return false if the lock wasn't obtained because of a time out
    if i == 5 : return False 
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "Locked")
    return True

    
def freeCycleLock():
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "")
    
    
def updateServiceRequested():
    # Check to see if an update is requred
    return (xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Update") == "update")

    
def requestVPNCycle():
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    addon_name = addon.getAddonInfo("name")

    # Don't cycle if we can't get a lock
    if getCycleLock():
    
        # Don't cycle if there's nothing been set up to cycle around
        if settingsValidated(addon):
        
            debugTrace("Got cycle lock in requestVPNCycle")
        
            if addon.getSetting("allow_cycle_ 	debugTrace(str(ip) + str(country) + str(region) + str(city) + str(isp))disconnect") == "true":
                allow_disconnect = True
            else:
                allow_disconnect = False

            # Preload the cycle variable if this is the first time through
            if getVPNCycle() == "":
                if getVPNProfile() == "":
                    setVPNCycle("Disconnect")
                else:
                    setVPNCycle(getVPNProfile())
            else:
                # Build the list of profiles to cycle through
                profiles=[]
                found_current = False
                if allow_disconnect or ((not allow_disconnect) and getVPNProfile() == ""):
                    profiles.append("Disconnect")
                    if getVPNProfile() == "": found_current = True
                i=1
                # Adjust the 11 below to change conn_max
                while i<11:
                    next_profile = addon.getSetting(str(i)+"_vpn_validated")
                    if not next_profile == "":
                        profiles.append(next_profile)
                        if next_profile == getVPNProfile() : 
                            found_current = True
                    i=i+1
                if not found_current:
                    profiles.append(getVPNProfile())
                      
                # Work out where in the cycle we are and move to the next one
                current_profile = 0
                for profile in profiles:
                    current_profile = current_profile + 1
                    if getVPNCycle() == profile:            
                        if current_profile > (len(profiles)-1):
                            setVPNCycle(profiles[0])
                        else:
                            setVPNCycle(profiles[current_profile])
                        break
              
            # Display a notification message
            icon = getIconPath()+"locked.png"
            if getVPNCycle() == "Disconnect":
                if getVPNProfile() == "":
                    dialog_message = "Not connected"
                    icon = getIconPath()+"disconnected.png"
                else:
                    dialog_message = "Disconnect?"
                    icon = getIconPath()+"unlocked.png"
            else:
                if getVPNProfile() == getVPNCycle():
                    dialog_message = "Connected to " + getFriendlyProfileName(addon.getSetting("vpn_provider_validated"), getVPNCycle())
                    icon = getIconPath()+"connected.png"
                else:
                    dialog_message = "Connect to " + getFriendlyProfileName(addon.getSetting("vpn_provider_validated"), getVPNCycle()) + "?"
            
            debugTrace("Cycle request is " + dialog_message)
            xbmcgui.Dialog().notification(addon_name, dialog_message , icon, 3000, False)
        else:
            xbmcgui.Dialog().notification(addon_name, "VPN is not set up and authenticated.", xbmcgui.NOTIFICATION_ERROR, 10000, True)

        freeCycleLock()
        
    
def getVPNCycle():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Cycle")

    
def setVPNCycle(profile):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Cycle", profile)

    
def clearVPNCycle():
    setVPNCycle("")


def isVPNMonitorRunning():
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State") == "Started":
        return True
    else:
        return False
    
    
def setVPNMonitorState(state):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Monitor_State", state)
    
    
def getVPNMonitorState():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State")


def resetVPNConnections(addon):
    # Reset all connection information so the user is forced to revalidate everything
    infoTrace("resetVPN.py", "Resetting all validated VPN settings and disconnected existing VPN connections")
    
    forceCycleLock()
    
    resetVPNConfig(addon, 1)
    # Remove any last connect settings
    setVPNLastConnectedProfile("")
    setVPNLastConnectedProfileFriendly("")
        
    # Removal any password files that were created (they'll get recreated if needed)
    debugTrace("Deleting all pass.txt files")
    cleanPassFiles()
    
    # No need to stop/start monitor, just need to let it know that things have changed.
    # Because this is a reset of the VPN, the monitor should just work out it has no good connections
    updateService()
    debugTrace("Stopping any active VPN connections")
    stopVPNConnection()
    
    freeCycleLock()
    
    xbmcgui.Dialog().notification(addon.getAddonInfo("name"), "Not connected", getIconPath()+"disconnected.png", 5000, False)
    
    
def disconnectVPN():
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    addon_name = addon.getAddonInfo("name")

    debugTrace("Disconnecting the VPN")
    
    forceCycleLock()
    
    # Show a progress box before executing stop
    progress = xbmcgui.DialogProgress()
    progress_title = "Disconnecting from VPN."
    progress.create(addon_name,progress_title)
    
    # Stop the monitor service
    progress_message = "Stopping VPN monitor."
    progress.update(1, progress_title, progress_message)
    if not stopService():
        progress.close()
        # Display error in an ok dialog, user will need to do something...
        errorTrace("common.py", "VPN monitor service is not running, can't stop VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and reboot.")
        freeCycleLock()
        return
    
    xbmc.sleep(500)
    
    progress_message = "Stopping any active VPN connection."
    progress.update(1, progress_title, progress_message)
    
    # Kill the VPN connection if the user hasn't gotten bored waiting
    if not progress.iscanceled():
        stopVPNConnection()
        xbmc.sleep(500)    
        progress_message = "Not connected to VPN, restarting VPN monitor"
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNState("off")
    else:
        progress_message = "Disconnect cancelled, restarting VPN monitor"
        
    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has stopped")
        dialog_message = "Error, Service not running.\nCheck log and reboot."        
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(500)
        progress.close()
    
        # Update screen and display result in an ok dialog
        xbmc.executebuiltin('Container.Refresh')
        
        
        _, ip, country, isp = getIPInfo(addon)  
             
        #dialog_message = "Not connected to VPN.\nNetwork location is " + country + ".\nIP address is " + ip
            
        infoTrace("common.py", "Not connected to the VPN")

    freeCycleLock()
    vpn_username = addon.getSetting('vpn_username')
    #xbmcgui.Dialog().ok(addon_name, dialog_message)
   
    # Mixpanel event on Disconnect
    mp_disconnected(vpn_username, country)
    debugTrace('Mixpanel Event successfully reported')

def disconnectVPN2():
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    addon_name = addon.getAddonInfo("name")

    debugTrace("Disconnecting the VPN")

    forceCycleLock()


    # Stop the monitor service
    if not stopService():
        # Display error in an ok dialog, user will need to do something...
        errorTrace("common.py", "VPN monitor service is not running, can't stop VPN")
        #xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and reboot.")
        freeCycleLock()
        return

    xbmc.sleep(500)

    # Kill the VPN connection if the user hasn't gotten bored waiting
    stopVPNConnection()
    xbmc.sleep(500)
    setVPNLastConnectedProfile("")
    setVPNLastConnectedProfileFriendly("")
    setVPNState("off")

    # Restart service
    if not startService():
        errorTrace("common.py", "VPN monitor service is not running, VPN has stopped")
    else:
        # Close out the final progress dialog
        xbmc.sleep(500)

        # Update screen and display result in an ok dialog
        xbmc.executebuiltin('Container.Refresh')

    freeCycleLock()
    vpn_username = addon.getSetting('vpn_username')

    
def getCredentialsPath(addon):
    return getAddonPath(True, getVPNLocation(addon.getSetting("vpn_provider"))+"/pass.txt")
    
    
def writeCredentials(addon): 
   
    # Write the credentials file        
    try:
        credentials_path = getCredentialsPath(addon)
        debugTrace("Writing VPN credentials file to " + credentials_path)
        credentials = open(credentials_path,'w')
        credentials.truncate()
        credentials.close()
        credentials = open(credentials_path,'a')
        credentials.write(addon.getSetting("vpn_username")+"\n")
        credentials.write(addon.getSetting("vpn_password")+"\n")
        credentials.close()
    except:
        errorTrace("common.py", "Couldn't create credentials file " + credentials_path)
        return False
    xbmc.sleep(500)
    return True
    

def wizard():
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    addon_name = addon.getAddonInfo("name")    

    # Indicate the wizard has been run, regardless of if it is to avoid asking again
    addon.setSetting("vpn_wizard_run", "true")
    
    # Wizard or settings?
    if xbmcgui.Dialog().yesno(addon_name, "No primary VPN connection has been set up.  Would you like to do this using the set up wizard or using the Settings dialog?", "", "", "Settings", "Wizard"):
        
        # Select the VPN provider
        vpn = xbmcgui.Dialog().select("Select your VPN provider.", provider_display)
        vpn_provider = provider_display[vpn]

        # Get the username and password
        vpn_username = ""
        vpn_password = ""
        vpn_username = xbmcgui.Dialog().input("Enter your " + vpn_provider + " username.", type=xbmcgui.INPUT_ALPHANUM)
        if not vpn_username == "":
            vpn_password = xbmcgui.Dialog().input("Enter your " + vpn_provider + " password.", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
        
        # Try and connect if we've gotten all the data
        if not vpn_password == "":
            addon.setSetting("vpn_provider", vpn_provider)
            addon.setSetting("vpn_username", vpn_username)
            addon.setSetting("vpn_password", vpn_password)
            connectVPN("1", vpn_provider)
            # Need to reinitialise addon here for some reason...
            addon = xbmcaddon.Addon("service.purevpn.monitor")
            if settingsValidated(addon):
                xbmcgui.Dialog().ok(addon_name, "Successfully connected to " + vpn_provider + ".  Use the Settings dialog to add additional VPN connections.  You can also define add-on split tunneling to dynamically change the VPN connection being used.")
            else:
                xbmcgui.Dialog().ok(addon_name, "Could not connect to " + vpn_provider + ".  Use the Settings dialog to correct any issues and try connecting again.")
            
        else:
            xbmcgui.Dialog().ok(addon_name, "You need to enter both a VPN username and password to connect.")

            
def removeUsedConnections(addon, connection_order, connections):
    # Filter out any used connections from the list given
    # Don't filter anything if it's not one of the primary connection
    if connection_order == "0": return connections
    unused = []
    for connection in connections:
        i = 1
        found = False
        # Adjust 11 below if changing number of conn_max
        while i < 11:
            if connection == addon.getSetting(str(i) + "_vpn_validated_friendly"):
                found = True
            i = i + 1
        if not found : unused.append(connection)
    return unused

            
def connectVPN(connection_order, vpn_profile):

    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    addon_name = addon.getAddonInfo("name")
    #countryCode = getIP2Location()
    
    # If we've not arrived here though the addon (because we've used the add-on setting
    # on the option menu), we want to surpress running the wizard as there's no need.
    addon.setSetting("vpn_wizard_run", "true")

    # Check openvpn installed and runs
    if not addon.getSetting("checked_openvpn") == "true":        
        if checkVPNInstall(addon): addon.setSetting("checked_openvpn", "true")
        else: return

    if not addon.getSetting("ran_openvpn") == "true":
        stopVPN()    
        if checkVPNCommand(addon): addon.setSetting("ran_openvpn", "true")
        else: return
    
    # The VPN protocol can be blank if this is a new run and the wizard is being used.
    # Force it to UDP as that's the most optimal and let them change in the settings.
    vpn_protocol = addon.getSetting("vpn_protocol")
    if vpn_protocol == "":
        addon.setSetting("vpn_protocol", "UDP")
        vpn_protocol = "UDP"
    
    # Do some stuff to set up text used in dialog windows
    
    state = ""
    
    forceCycleLock()
    
    # Display a progress dialog box (put this on the screen quickly before doing other stuff)
    progress = xbmcgui.DialogProgress()
    progress_title = "PureVPN Status:"
    progress.create(addon_name,progress_title) 

    debugTrace(progress_title)
        
    # Stop the monitor service
    progress_message = "Stopping VPN monitor."
    progress.update(1, progress_title, progress_message)
    if not stopService():
        progress.close()
        # Display error result in an ok dialog
        errorTrace("common.py", "VPN monitor service is not running, can't start VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and re-enable.")
        return

    if not progress.iscanceled():
        progress_message = "VPN monitor stopped."
        debugTrace(progress_message)
        progress.update(5, progress_title, progress_message)
        xbmc.sleep(500)
        
    # Stop any active VPN connection
    if not progress.iscanceled():
        progress_message = "Stopping any active VPN connection."    
        progress.update(6, progress_title, progress_message)
        stopVPNConnection()

    if not progress.iscanceled():
        progress_message = "Not connected to VPN."
        progress.update(10, progress_title, progress_message)
        xbmc.sleep(500)
        
    # Install the VPN provider    
    existing_connection = ""
    if not progress.iscanceled():
    
        vpn_provider = addon.getSetting("vpn_provider")

        # Reset the username/password if it's not being used
        if not usesPassAuth(vpn_provider):
            addon.setSetting("vpn_username", "")
            addon.setSetting("vpn_password", "")  
                
        vpn_username = addon.getSetting("vpn_username")
        vpn_password = addon.getSetting("vpn_password")
        
        # Reset the setting indicating we've a good configuration for just this connection
        existing_connection = addon.getSetting(connection_order + "_vpn_validated")
        addon.setSetting(connection_order + "_vpn_validated", "")
        addon.setSetting(connection_order + "_vpn_validated_friendly", "")
        last_provider = addon.getSetting("vpn_provider_validated")
        last_credentials = addon.getSetting("vpn_username_validated") + " " + addon.getSetting("vpn_password_validated")
        if last_provider == "" : last_provider = "?"
        
        # Provider or credentials we've used previously have changed so we need to reset all validated connections
        vpn_credentials = vpn_username + " " + vpn_password
        if not last_provider == vpn_provider:
            last_credentials = "?"
        if not last_credentials == vpn_credentials:
            debugTrace("Credentials have changed since last time lthrough so need to revalidate")
            resetVPNConfig(addon, 1)   
    
    # Generate or fix the OVPN files if we've not done this previously
    provider_gen = True
    if not progress.iscanceled():
        progress_message = "Setting up VPN provider " + vpn_provider + "."
        progress.update(11, progress_title, progress_message)
        provider_gen = genovpnFiles(vpn_provider)

    if provider_gen:
        if not progress.iscanceled():
            progress_message = "Connecting to " + vpn_provider
            progress.update(15, progress_title, progress_message)
            xbmc.sleep(500)
                            
        # Set up user credentials file
        if not progress.iscanceled() and usesPassAuth(vpn_provider):
            credentials_path = getCredentialsPath(addon)
            debugTrace("Attempting to use the credentials in " + credentials_path)
            if (not last_credentials == vpn_credentials) or (not xbmcvfs.exists(credentials_path)) or (not settingsValidated(addon)):
                progress_message = "Configuring authentication settings for user " + vpn_username + "."
                progress.update(16, progress_title, progress_message)
                provider_gen = writeCredentials(addon)

    got_keys = True
    keys_copied = True
    cancel_attempt = False
    cancel_clear = False
    if provider_gen:
        ovpn_name = ""
        if not progress.iscanceled():
            if usesPassAuth(vpn_provider):
                progress_message = "Using authentication settings for user " + vpn_username + "."
            else:
                progress_message = "User authentication not used with " + vpn_provider + "."
            progress.update(19, progress_title, progress_message)
            xbmc.sleep(500)

        # Display the list of connections
        if not progress.iscanceled():
            ovpn_name = getFriendlyProfileName(vpn_provider, vpn_profile)
            ovpn_connection = vpn_profile

        if not progress.iscanceled() and not ovpn_name == "":
            # Fetch the key from the user if one is needed
            if usesUserKeys(getVPNLocation(vpn_provider)):                
                # If a key already exists, skip asking for it
                if not (gotKeys(getVPNLocation(vpn_provider), ovpn_name)):
                    # Stick out a helpful message if this is first time through
                    if not gotKeys(getVPNLocation(vpn_provider), ""):
                        xbmcgui.Dialog().ok(addon_name, vpn_provider + " provides unique key and certificate files to authenticate, typically called [I]client.key and client.crt[/I] or [I]user.key and user.crt[/I].  Make these files available on an accessable drive or USB key.")                
                    # Get the last directory browsed to avoid starting from the top
                    start_dir = xbmcgui.Window(10000).getProperty("VPN_Manager_User_Directory")
                    if usesSingleKey(getVPNLocation(vpn_provider)): select_title = "Select the user key file to use for all connections"
                    else: select_title = "Select the user key file to use for this individual connection"
                    key_file = xbmcgui.Dialog().browse(1, select_title, "files", ".key", False, False, start_dir, False)
                    if key_file.endswith(".key"):
                        start_dir = os.path.dirname(key_file) + getSeparator()
                        if usesSingleKey(getVPNLocation(vpn_provider)): select_title = "Select the user certificate file to use for all connections"
                        else: select_title = "Select the user certificate file to use for this individual connection"
                        crt_file = xbmcgui.Dialog().browse(1, select_title, "files", ".crt", False, False, start_dir, False)                    
                        if crt_file.endswith(".crt"):
                            start_dir = os.path.dirname(crt_file) + getSeparator()
                            xbmcgui.Window(10000).setProperty("VPN_Manager_User_Directory", start_dir)
                            keys_copied = copyKeyAndCert(getVPNLocation(vpn_provider), ovpn_name, key_file, crt_file)
                            got_keys = keys_copied
                        else:
                            got_keys = False
                    else:
                        got_keys = False

        # Try and connect to the VPN provider using the entered credentials        
        if not progress.iscanceled() and not ovpn_name == "" and got_keys:    
            progress_message = "Connecting using profile " + ovpn_name + "."
            debugTrace(progress_message)

        # Spliting up the selected location in country name and protocol name
            countrY, protocoL = ovpn_name.split('(')
            debugTrace('Country is: ' + str(countrY))
            debugTrace('Protocol is: ' + str(protocoL))
 
        # Setting up the port, type and id according to selected protocol
            if protocoL == 'UDP)':
                protO_nuM = ' 53'
                protO_typE = 'udp'
                protO_iD = 9
            elif protocoL == 'TCP)':
                protO_nuM = ' 80'
                protO_typE = 'tcp'
                protO_iD = 8
           
            # Function call for fetching country code
            countrY = countrY[:-1]
            countrY_iD = getCountryId(countrY)
            debugTrace('Country code: ' + countrY_iD) 
           
            # Function call to make a speedtest request
            jsoN_responsE = callToSTApi(protO_iD, vpn_username, countrY_iD)
            if jsoN_responsE == 'null':
                addon_name = 'PureVPN'
                response1 = 'Error connecting to PureVPN, could not estabilish connection.\nCheck your network connectivity and retry."'
                xbmcgui.Dialog().ok(addon_name, response1)
                progress_message = 'Please Wait'
                progress.update(1, progress_title, progress_message)
                disconnectVPN2()
                sys.exit()
            else:
                pass
            debugTrace('Speedtest Response: ' + str(jsoN_responsE)) 
           
            # Function call to extract details from the speedtest response
            st_resp_code, response1, response2, response3 = stDetails(jsoN_responsE)
            debugTrace('Response Code is: ' + str(st_resp_code)) 
            
            # Handling if wrong or expired username is used
            if st_resp_code != 1:
                addonname = 'PureVPN'
                if st_resp_code == 1008:
                    additionalResponse = 'Please contact our live chat if you want to connect PureVPN on more devices.'
                    xbmcgui.Dialog().ok(addonname, response1, response2, additionalResponse)
                    # Mixpanel Event on Limit Exceed
                    mp_limitExceed(vpn_username)
                    debugTrace('Mixpanel Event successfully reported')
                else:
                    xbmcgui.Dialog().ok(addonname, response1, response2)
                sys.exit()
 
            # if username is valid, setting up the variables for w.r.t speedtest response
            else:
                sT_dnS_adD = response1
                sT_dnS_typE = response2
                sT_confiG = response3
            debugTrace('Server address from speedtest response: ' + sT_dnS_adD)
            
            # Creating a custom config file from speedtest response
            sT_dnS_patH = str(getAddonPath(True, vpn_provider + "/custom.ovpn"))
           
            debugTrace('Path for custom config file is: ' + sT_dnS_patH)
            createCustomFile(sT_confiG, ovpn_connection, sT_dnS_patH, protO_typE, protO_nuM, vpn_provider, sT_dnS_adD, sT_dnS_typE)
           
            # Assigning the custom config file path to a variable
            st_ovpn_connection = sT_dnS_patH

            # Start the connection and wait a second before starting to check the state
            startVPN(st_ovpn_connection)
            i = 0
            # Bad network takes over a minute to spot so loop for a bit longer (each loop is 2 seconds)
            loop_max_st = 10
            if fakeConnection(): loop_max_st = 2
            percent_st = 20
            while i <= loop_max_st:
                progress.update(percent_st, progress_title, progress_message)
                xbmc.sleep(2000)
                state1 = getVPNConnectionStatus()
                debugTrace('Connection state should be: 1')
                debugTrace('Connection state is: ' + str(state1))
                if not (state1 == connection_status.UNKNOWN or state1 == connection_status.TIMEOUT) : break
                elif progress.iscanceled(): break
                i = i + 1
                percent_st = percent_st + 2
                ii = str(i)          
                if os.path.exists(sT_dnS_patH):
                    os.remove(sT_dnS_patH)
 
    # Mess with the state to make it look as if we've connected to a VPN
    if fakeConnection() and not progress.iscanceled() and provider_gen and not ovpn_name == "" and got_keys:
        state1 = connection_status.CONNECTED

    # Setting up status for mixpanel if speedtest connection is successful 
    if state1 == connection_status.CONNECTED:
        st_status = 'Success'
        debugTrace('Final state for Speedtest server is: ' + str(state1))  
  
    else:
        startVPN(ovpn_connection)
        e = 0
        # Bad network takes over a minute to spot so loop for a bit longer (each loop is 2 seconds)
        loop_max_def = 15
        if fakeConnection(): loop_max_def = 2
        percent_def = 20
        while e <= loop_max_def:
            progress.update(percent_def, progress_title, progress_message)
            xbmc.sleep(2000)
            state = getVPNConnectionStatus()
            debugTrace('State for static servers is: ' + str(state))
            if not (state == connection_status.UNKNOWN or state == connection_status.TIMEOUT) : break
            elif progress.iscanceled(): break
            e = e + 1
            percent_def = percent_def + 2
        if fakeConnection() and not progress.iscanceled() and provider_gen and not ovpn_name == "" and got_keys:
            state = connection_status.CONNECTED

        if state == connection_status.CONNECTED:
            st_status = 'fail'
            ii = 'null'
      
    # Determine what happened during the connection attempt        
    if state1 == connection_status.CONNECTED or state == connection_status.CONNECTED:
        mp_event = 'kodi_connected'
        # Success, VPN connected! Display an updated progress window whilst we work out where we're connected to
        progress_message = "Connection Established."
        progress.update(97, progress_title, progress_message)
        # Set the final message to indicate success
        progress_message = "Connection Established."
        _, ip, country, isp = getIPInfo(addon)
        dialog_message = "Connected to PureVPN in " + country + ".\nIP address is " + ip
        infoTrace("common.py", dialog_message)

           
        if ifDebug(): writeVPNLog()
        # Store that setup has been validated and the credentials used
        setVPNProfile(ovpn_connection)
        setVPNProfileFriendly(ovpn_name)
        
        addon.setSetting("vpn_provider_validated", vpn_provider)
        addon.setSetting("vpn_username_validated", vpn_username)
        addon.setSetting("vpn_password_validated", vpn_password)
        addon.setSetting(connection_order + "_vpn_validated", ovpn_connection)
        addon.setSetting(connection_order + "_vpn_validated_friendly", ovpn_name)
        
        setVPNState("started")
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setConnectionErrorCount(0)
        # Indicate to the service that it should update its settings
        updateService()
       # sendGoogleAnalytics(vpn_username, countryCode)
        sendGoogleAnalyticsConnectedCountry(vpn_username)
       
        # Mixpanel Event on Connection Created
        mp_connected(state1, state, vpn_username, countrY, protO_typE, sT_dnS_adD, country, ii)
        debugTrace('Mixpanel Event successfully reported')
        
    elif progress.iscanceled() or cancel_attempt:
        # User pressed cancel.  Don't change any of the settings as we've no idea how far we got
        # down the path of installing the VPN, configuring the credentials or selecting the connection
        # We're assuming here that if the VPN or user ID has been changed, then the connections are invalid
        # already.  If the cancel happens during the connection validation, we can just use the existing one.
        # Set the final message to indicate user cancelled operation
        progress_message = "Cancelling connection attempt, restarting VPN monitor."
        progress.update(97, progress_title, progress_message)
        # Set the final message to indicate cancellation
        progress_message = "Cancelling connection attempt, VPN monitor restarted."
        # Restore the previous connection info 
        dialog_message = "Cancelled connection attempt.\n"
        
        if not isVPNConnected():
            if cancel_clear:
                dialog_message = dialog_message + "This connection has been removed from the list of valid connections."
            else:
                dialog_message = dialog_message + "This connection has not been validated."
            resetVPNConfig(addon, int(connection_order))
        
        # Don't know how far we got, if we were trying to connect and then got cancelled,
        # there might still be an instance of openvpn running we need to kill
        stopVPN()
    else:
        # An error occurred, The current connection is already invalidated.  The VPN credentials might 
        # be ok, but if they need re-entering, the user must update them which will force a reset.  
        progress_message = "Error connecting to VPN, restarting VPN monitor."
        progress.update(97, progress_title, progress_message)
        xbmc.sleep(500)
        # Set the final message to show an error occurred
        progress_message = "Error connecting to VPN, VPN monitor restarted."
        # First set of errors happened prior to trying to connect
        if not provider_gen:
            dialog_message = "Error creating OVPN or credentials file for provider.\nCheck log to determine cause of failure."
        elif not got_keys:
            if not keys_copied:
                dialog_message = "Failed to copy supplied user key and cert files.\nCheck log and retry."
            else:
                dialog_message = "User key and certificate files are required, but were not provided.  Locate the files and try again."
        elif ovpn_name == "":
            dialog_message = "No unused VPN profiles were available for " + vpn_protocol + " protocol.\nChange VPN provider settings."
        else:
            # This second set of errors happened because we tried to connect and failed
            if state == connection_status.AUTH_FAILED: 
                dialog_message = "Error connecting to PureVPN, authentication failed.\nCheck your username and password."
                credentials_path = getCredentialsPath(addon)
                addon.setSetting("vpn_username_validated", "")
                addon.setSetting("vpn_password_validated", "")
            elif state == connection_status.NETWORK_FAILED: 
                dialog_message = "Error connecting to PureVPN, could not estabilish connection.\nCheck your username, password and network connectivity and retry."
            elif state == connection_status.TIMEOUT:
                dialog_message = "Error connecting to PureVPN, connection has timed out.\nTry using a different VPN profile or retry."
            else:
                dialog_message = "Error connecting to PureVPN, something unexpected happened.\nRetry to check openvpn operation and then check log."
                addon.setSetting("ran_openvpn", "false")
            
            # Output what when wrong with the VPN to the log
            writeVPNLog()

        resetVPNConfig(addon, int(connection_order))
        
        errorTrace("common.py", dialog_message)

        # The VPN might be having a spaz still so we want to ensure it's stopped
        stopVPN()
 
        # Mixpanel Event on utc
        if state != connection_status.AUTH_FAILED:
            mp_utc(vpn_username, countrY, protO_typE, dialog_message)
            debugTrace('Mixpanel Event successfully reported')
        
    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has started")
        dialog_message = "Error, Service not running.\nCheck log and reboot."     
  
   
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(500)
        progress.close()
    
    freeCycleLock()

    # Display connection result in an ok dialog
    xbmcgui.Dialog().ok(progress_title, dialog_message)
    
    # Refresh the screen if this is not being done on settings screen
    xbmc.executebuiltin('Container.Refresh')
    

  
