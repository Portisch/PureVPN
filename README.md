PureVPN VPN For Kodi/XBMC Player
===============================

PureVPN VPN enables you to stream torrents anonymously on Kodi/XBMC player, and bypass ISP throttling or different authorities spying on your online activities.

Fast P2P Optimized Servers
=============================  

PureVPN have the fastest P2P optimized servers to give you the ultimate torrenting experience. 


Zero Log Policy
===================

With a zero-log policy, you can access any global channel without having the fear that someone is spying and tracking your online activities all the time. 


250+ Servers in 144 locations
===============================

PureVPN VPN has servers in 144 locations around the world. So, you can easily select the locations and servers internally in your Kodi/XBMC player easily without having to exit Kodi. 

 
Split Tunneling Feature
============================

Split Tunneling lets you split and prioritize your data traffic. You can route your official data through VPN tunnel, and less important stuff without the cover of VPN.
 

------------------------------------------------------------------------


More about the PureVPN VPN Kodi/XBMC Player Add-on
==================================================

This add-on is a combination of program add-on and service.  It allows the configuration and switching between different VPN profiles/locations.  It will reconnect to a VPN on boot and then maintain the VPN connection based on the add-ons being used.  It's primary function is to avoid having to mess with VPNs once everything is set up.

It was most definitely inspired by wanting to improve on the excellent VPN for OPENELEC. It relies on the openvpn to do the network stuff.

To use this add-on, first set up a connection to a VPN provider and then validate with at least one profile.  The first of these is the primary VPN which will be used to reconnect at boot.

Using the Add-on Filter, identify which add-ons will use which VPN and which add-ons will not use a VPN at all.  As the add-on is selected, the VPN will automatically switch to the correct profile.  When an add-on is used that doesn't have a filter, the previous VPN profile to any filtering will be reverted to.  When configuring the filters, you must restart the service (on the Settings/Monitor tab) to start using the changes.

Multiple VPNs can be selected for a single add-on.  What this means is that when you switch to an add-on, if you have a current VPN which is one of the multiple VPNs identified then that VPN will continue to be used.  If your current VPN is not one of the multiple VPNs identified, then it'll select the lowest number VPN.

Other VPN profiles can be used via the VPN Manager for OpenELEC add-on in the Program section.

Additionally, primary VPN profiles can be cycled through either using the add-on menu, or at any time, a button on the remote.  On pressing the button the first time, the current VPN state will be displayed.  Subsequent presses will cycle around the available connections (and optionally disconnect).

After a short period (~10 seconds), the VPN last displayed will be connected.  If you don't want this to happen, cycle back to the current connected VPN.  If the network is active during a switch any traffic will likely be disrupted

To set up the cycle funtion, there's a remote.xml file within the add-on zip which shows how to map the cycle function onto a key. You can use the Keymap Editor add-on to create an xml file within the userdata directory (/storage/.kodi/userdata/keymaps) and edit it to contain the RunScript command show in remote.xml.

Finally, there's a bunch of other options to turn some of the behavior described on and off.  Everything is defaulted to sensible behavior.

We also have added a speed test into the option menu, just for fun...has nothing to do with VPNs though! But you can check your internet connection speed before and after connecting to PureVPN. 
