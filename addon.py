#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2016 Zomboided
#    modified Copyright (C) 2016 PureVPNLtd
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
#    This module displays the VPN Manager for OpenVPN menu options

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import os
import time
import urllib2
import urllib

from libs.common import settingsValidated, getIPInfo, isVPNConnected, getVPNProfile, getVPNProfileFriendly
from libs.common import getFriendlyProfileList, connectVPN, disconnectVPN,disconnectVPN2, setVPNState, requestVPNCycle, getFilteredProfileList
from libs.common import getAddonPath, isVPNMonitorRunning, setVPNMonitorState, getVPNMonitorState, wizard
from libs.common import getIconPath, updateService
from libs.platform import getPlatform, platforms, getPlatformString
from libs.utility import debugTrace, errorTrace, infoTrace
from libs.vpnproviders import getProfileList, genovpnFiles
from libs.ganalytics import sendGoogleAnalyticsPageView
from libs.update import createUpdateChecker
from libs.credentials import defCred
from libs.checkUnPass import createUnPass

debugTrace("-- Entered addon.py " + sys.argv[0] + " " + sys.argv[1] + " " + sys.argv[2] + " --")

# Set the addon name for use in the dialogs
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo("name")

# Get the arguments passed in
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = sys.argv[2].split("?", )
action = ""
params = ""
# If an argument has been passed in, the first character will be a ?, so the first list element is empty
inc = 0
for token in args:
    if inc == 1 : action = token
    if inc > 1 : params = params + token
    inc = inc + 1  

# Don't seem to need to do this on *nix platforms as the filename will be different
if getPlatform() == platforms.WINDOWS: params = params.replace("/", "\\")

debugTrace("Parsed arguments to action=" + action + " params=" + params)

    
def topLevel():
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    # Build the top level menu with URL callbacks to this plugin
    
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    vpn_provider = addon.getSetting("vpn_provider")
    
    debugTrace("Displaying the top level menu")
    try:
        url = base_url + "?disconnect"
        if getVPNProfileFriendly() != "":
            li = xbmcgui.ListItem("[COLOR ffff0000]Disconnect[/COLOR]", iconImage=getIconPath()+"unlocked.png")
    
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    except:
        pass

    url = base_url + "?display"
    li = xbmcgui.ListItem("Display VPN status", iconImage=getIconPath()+"display.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    url = base_url + "?list"
    if getVPNProfileFriendly() == "":
        li = xbmcgui.ListItem("Connect to Country", iconImage=getIconPath()+"locked.png")
    else:
        li = xbmcgui.ListItem("Change Country", iconImage=getIconPath()+"locked.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    url = base_url + "?switch"
    if isVPNMonitorRunning():
        li = xbmcgui.ListItem("Stop Split tunneling", iconImage=getIconPath()+"paused.png")
    else:
        li = xbmcgui.ListItem("Play Split tunneling", iconImage=getIconPath()+"play.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
   
    url = base_url + "?settings"
    li = xbmcgui.ListItem("Add-on Settings", iconImage=getIconPath()+"settings.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)

    if createUpdateChecker():
        addonname = 'PureVPN'
        response  = "PureVPN's Kodi Add-on has a new update. Please download the update from www.purevpn.com/kodi-addon"
        xbmcgui.Dialog().ok(addonname, response)

    if addon.getSetting("vpn_system_menu_item") == "true":
        url = base_url + "?system"
        li = xbmcgui.ListItem("Display enhanced information", iconImage=getIconPath()+"enhanced.png")
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    
    xbmcplugin.endOfDirectory(addon_handle)
    updateService()
    createUnPass()
    
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    return


def listSystem():
    lines = []
    site, ip, country, isp = getIPInfo(addon)
    lines.append("[B][COLOR ff0099ff]Connection[/COLOR][/B]")
    if isVPNConnected():
        lines.append("Connected using profile " + getVPNProfileFriendly())
        lines.append("VPN provider is " + addon.getSetting("vpn_provider"))
    else:
        lines.append("Not connected to a VPN")
    lines.append("Connection location is " + country)
    lines.append("External IP address is " + ip)
    lines.append("Service Provider is " + isp)
    lines.append("Location sourced from " + site)
    lines.append("[B][COLOR ff0099ff]Network[/COLOR][/B]")
    lines.append("IP address is " + xbmc.getInfoLabel("Network.IPAddress"))
    lines.append("Gateway is " + xbmc.getInfoLabel("Network.GatewayAddress"))
    lines.append("Subnet mask is " + xbmc.getInfoLabel("Network.SubnetMask"))
    lines.append("Primary DNS is " + xbmc.getInfoLabel("Network.DNS1Address"))
    lines.append("Secondary DNS is " + xbmc.getInfoLabel("Network.DNS2Address"))
    lines.append("[B][COLOR ff0099ff]PureVPN monitor[/COLOR][/B]")
    lines.append("PureVPN monitor verison is " + addon.getAddonInfo("version"))
    lines.append("PureVPN monitor behaviour is " + getPlatformString())
    if isVPNMonitorRunning():
        lines.append("PureVPN monitor add-on split tunneling is playing")
    else:
        lines.append("PureVPN monitor add-on split tunneling is stopped")
    lines.append("[B][COLOR ff0099ff]System[/COLOR][/B]")
    lines.append("Kodi build version is " + xbmc.getInfoLabel("System.BuildVersion"))
    lines.append("System name is " + xbmc.getInfoLabel("System.FriendlyName"))
    lines.append("System date is " + xbmc.getInfoLabel("System.Date"))
    lines.append("System time is " + xbmc.getInfoLabel("System.Time"))
    lines.append("Platform is " + sys.platform)
    lines.append("Free memory is " + xbmc.getInfoLabel("System.FreeMemory"))
    lines.append("Disk is " + xbmc.getInfoLabel("System.TotalSpace") + ", " + xbmc.getInfoLabel("System.UsedSpace"))
    
    for line in lines:
        url = base_url + "?back"
        li = xbmcgui.ListItem(line, iconImage=getIconPath()+"enhanced.png")
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)
    return


def back():
    xbmc.executebuiltin("Action(ParentDir)")
    return
    

def displayStatus():
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    _, ip, country, isp = getIPInfo(addon)
    if isVPNConnected():
        debugTrace("VPN is connected, displaying the connection info")
        xbmcgui.Dialog().ok(addon_name, "Connected to PureVPN in " + country + ".\nUsing profile " + getVPNProfileFriendly() + ".\nIP address is " + ip + ".")
    else:
        debugTrace("VPN is not connected, displaying the connection info")
        xbmcgui.Dialog().ok(addon_name, "Not connected to PureVPN.\nNetwork location is " + country + ".\nIP address is " + ip + ".")
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    return

    
def listConnections():
   
    # We should have a VPN set up by now, but don't list if we haven't.
    vpn_provider = addon.getSetting("vpn_provider")
    debugTrace("Listing the connections available for " + vpn_provider)
    if vpn_provider != "":
        # Get the list of connections and add them to the directory
        all_connections = getProfileList(vpn_provider)
        ovpn_connections = getFilteredProfileList(all_connections, addon.getSetting("vpn_protocol"), None)
        connections = getFriendlyProfileList(vpn_provider, ovpn_connections)
        inc = 0
        for connection in ovpn_connections:
            url = base_url + "?change?" + ovpn_connections[inc]
            conn_text = ""
            conn_primary = ""

            if getVPNProfileFriendly() == connections[inc] and isVPNConnected(): 
                conn_text = "[COLOR ff00ff00]" + connections[inc] + conn_primary + " (Connected)[/COLOR]"
                icon = getIconPath()+"connected.png"
            else:
                conn_text = connections[inc] + conn_primary
                icon = getIconPath()+"locked.png"                
            li = xbmcgui.ListItem(conn_text, iconImage=icon)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
            inc = inc + 1
    xbmcplugin.endOfDirectory(addon_handle)            
    return

    
def disconnect():
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    # Disconnect or display status if already disconnected
    debugTrace("Disconnect selected from connections menu")
    if isVPNConnected():
        disconnectVPN()
        setVPNState("off")
    #else:
    #    displayStatus()
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    return
    
    
def changeConnection():
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    # Connect, or display status if we're already using selected VPN profile
    debugTrace("Changing connection to " + params + " from " + getVPNProfile() + ", connected:" + str(isVPNConnected()))
    if isVPNConnected() and params == getVPNProfile():
        displayStatus()
    else: 
        disconnectVPN2()       
        connectVPN("1", params)
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    return


def cycleConnection():
    # Cycle through the connections
    debugTrace("Cycling through available connections")
    requestVPNCycle()
    return
    

def switchService():
    debugTrace("Switching monitor state, current state is " + getVPNMonitorState())
    if isVPNMonitorRunning():
        setVPNMonitorState("Stopped")
        addon.setSetting("monitor_stopped", "true")
        infoTrace("addon.py", "VPN monitor service stopped")
    else:
        setVPNMonitorState("Started")
        addon.setSetting("monitor_stopped", "false")
        infoTrace("addon.py", "VPN monitor service restarted")
    xbmc.executebuiltin('Container.Refresh')
    return
    

def update():
    
    addon_name = 'PureVPN'
    debugTrace('Update Available')
    xbmcgui.Dialog().ok(addon_name, "PureVPN's Kodi Add-on has a new update. Please download the update from www.purevpn.com/kodi-repo")
       

if action == "display": 
    # Display the network status
    displayStatus()
elif action == "system":
    listSystem()
elif action == "back" : 
    back()
elif action == "update" :
    update()
    #listSystem()
elif not settingsValidated(addon) and action != "":
    if not action =="settings": xbmcgui.Dialog().ok(addon_name, "Please set username and password first.  You can do this using the VPN Configuration tab within the Settings dialog.")
    defCred()
    xbmc.executebuiltin("Addon.OpenSettings(service.purevpn.monitor)")
else:
    # User wants to see settings, list connections or they've selected to change something.  
    # If it's none of these things, we're at the top level and just need to show the menu
    if action == "settings" :
        debugTrace("Opening settings")
        defCred()
        xbmc.executebuiltin("Addon.OpenSettings(service.purevpn.monitor)")    
        sendGoogleAnalyticsPageView("/kodiVPNSetting", addon)
    elif action == "list" :
        if genovpnFiles("PureVPN") == True:
            listConnections()
            sendGoogleAnalyticsPageView("/kodiVPNListConnection", addon)
    elif action == "disconnect" : disconnect()
    elif action == "change" : changeConnection()
    elif action == "cycle" : cycleConnection()
    elif action == "switch" : switchService()
   
    else:
        topLevel()
        sendGoogleAnalyticsPageView("/kodiVPNMainScreen", addon)
sys.argv[1] = int(sys.argv[1])
if sys.argv[1] <3:
    xbmc.executebuiltin('Container.Refresh')
debugTrace("-- Exit addon.py --")
