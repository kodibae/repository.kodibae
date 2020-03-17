# -*- coding: UTF-8 -*-
"""
    Modified for Jen Template integration 2018.07.08
"""

"""
 weblogin
 by Anarchintosh @ xbmcforums
 Copyleft (GNU GPL v3) 2011 onwards

 this example is configured for Fantasti.cc login
 See for the full guide please visit:
 http://forum.xbmc.org/showthread.php?p=772597#post772597


 USAGE:
 in your default.py put:

 import weblogin
 logged_in = weblogin.doLogin('a-path-to-save-the-cookie-to','the-username','the-password')

 logged_in will then be either True or False depending on whether the login was successful.
"""

import __builtin__
import cookielib
import os
import re
import time
import urllib,urllib2
import koding,xbmcaddon


def check_login(source,username):
    """ search for the string in the html, without caring about upper or lower case """
    if re.search(login_verified,source,re.IGNORECASE):
        return True
    else:
        return False


def verify_login(cookiepath, username, password):
    """ check if user has supplied only a folder path, or a full path """
    if not os.path.isfile(cookiepath):
        """ if the user supplied only a folder path, append on to the end of the path a filename. """
        cookiepath = os.path.join(cookiepath, 'cookies.lwp')
        
    """ delete any old version of the cookie file """
    try:
        os.remove(cookiepath)
    except:
        pass

    if username and password:
        """ first check to see if a current session is active """
        addon_id = xbmcaddon.Addon().getAddonInfo('id')
        ownAddon = xbmcaddon.Addon(id=addon_id)
        expiration = ownAddon.getSetting('WEBLOGIN_EXPIRES_AT')
        if time.time() < expiration and len(expiration) > 1:
            return True
        """ the header used to pretend you are a browser """
        user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'

        """ build the form data necessary for the login """
        login_data = urllib.urlencode({user_var:username, pwd_var:password})

        """ build the request we will make """
        req = urllib2.Request(login_url, login_data)
        req.add_header('User-Agent',user_agent)

        """ initiate the cookielib class """
        cj = cookielib.LWPCookieJar()

        """ install cookielib into the url opener, so that cookies are handled """
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        """ do the login and get the response """
        response = opener.open(req)
        source = response.read()
        response.close()

        """ check the received html for a string that will tell us if the user is logged in """
        """ pass the username, which can be used to do this. """
        login = check_login(source,username)

        """ if login suceeded, save the cookiejar """
        if login == True:
            cj.save(cookiepath)

        """ return whether we are logged in or not """
        return login
    else:
        return False
