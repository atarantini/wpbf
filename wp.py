#!/usr/bin/env python
#
# wpbf WordPress tools
#
# Copyright 2011 Andres Tarantini (atarantini@gmail.com)
#
# This file is part of wpbf.
#
# wpbf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wpbf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with wpbf.  If not, see <http://www.gnu.org/licenses/>.

import urllib, urllib2, re

def request(url, params, proxy):
	"""
	Request an URL with a given parameters and proxy
	"""
        request = urllib2.Request(url)
        request.add_header("User-agent", "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1")
        if proxy:
            proxy_handler = urllib2.ProxyHandler({'http': proxy})
            opener = urllib2.build_opener(proxy_handler)
        else:
            opener = urllib2.build_opener()
        return opener.open(request, urllib.urlencode(params)).read()

def login(url, username, password, proxy):
        """
        Try to login into WordPress and see in the returned data contains login errors

        url - Login form URL
        username - Wordpress username
        password - Password for the supplied username
        proxy - HTTP proxy URL
        """
        data = request(url, [('log', username), ('pwd', password)], proxy)
        if "ERROR" in data or "Error" in data or "login_error" in data:
            return False
        else:
            return True

def check_username(url, username, proxy):
        """
        Try to login into WordPress and check in the returned data contains username errors

        url - Login form URL
        username - Wordpress username
        proxy - HTTP proxy URL
        """
        data = request(url, [('log', username), ('pwd', 'check_username')], proxy)
        if "ERROR" in data or "Error" in data or "login_error" in data:
            if "usuario es incorrecto" in data or "Invalid username" in data:
                return False
            else:
                return True
        else:
            return True

def find_username(url, proxy):
    data =  request(url, [], proxy)

    username = None

    match = re.search('(<!-- by (.*?) -->)', data, re.IGNORECASE)       # busco <!-- by AUTHOR -->
    if match:
        username = match.group()[8:-4]

    if username is None:
        match = re.search('View all posts by (.*)"', data, re.IGNORECASE)       # busco View all posts by AUTHOR
        if match:
            username = match.group()[18:-1]

    if username is None:
        match = re.search('<a href="'+wp_base_url+'author/(.*)" ', data, re.IGNORECASE)
        if match:
            username = match.group()[len(wp_base_url)+16:-2]

    if username is None or len(username) < 1:
        logger.info("Can't find username")
        error = True
        return False
    else:
        username = username.strip().replace("/","")
        return username
