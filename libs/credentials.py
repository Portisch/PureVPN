#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import shutil
import re
import xbmc
import xbmcaddon

from libs.common import getIconPath
from libs.utility import debugTrace
from libs.platform import getPlatform, platforms

# If defaults is pressed, no need to change username and password in the settings panel.

def defCred():
    addon = xbmcaddon.Addon("service.purevpn.monitor")
    fd = open(getIconPath()+"settings.xml", 'r')
    if fd: 
        debugTrace("Opening settings.xml")
        fd2 = open(getIconPath()+"settings.xml.bak", 'w')
        vpn_username = addon.getSetting("vpn_username")
        vpn_password = addon.getSetting("vpn_password")
        sudo_password = addon.getSetting("sudo_password")

        # Searching for the lines having username and password in settings.xml and keeping the lines unchanged.
        for line in fd:
            if "id=\"vpn_username\"" in line:
                line = "        <setting label=\"32004\" type=\"text\" id=\"vpn_username\" default=\"" +  vpn_username + "\"/>\n"
            elif "id=\"vpn_password\"" in line:
                line = "        <setting label=\"32005\" type=\"text\" id=\"vpn_password\" option=\"hidden\" default=\"" +  vpn_password + "\"/>\n"
            elif "id=\"sudo_password\"" in line:
                if getPlatform() == platforms.LINUX:
                    line = "        <setting label=\"32030\" type=\"text\" id=\"sudo_password\" option=\"hidden\" default=\"" +  sudo_password + "\"/>\n"
            fd2.write(line)
        fd2.close()
        fd.close()
        #os.remove(getIconPath()+"settings.xml")
        shutil.copy(getIconPath()+"settings.xml.bak", getIconPath()+"settings.xml")
    else:
        debugTrace("Error opening settings.xml")

defCred()
