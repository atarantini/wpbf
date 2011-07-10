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
from random import randint
from urlparse import urljoin, urlparse

class Wp:
    """Perform variuos actions (login, username check/enumeration, keyword search) in a WordPress Blog."""

    _cache = {}

    def request(self, url, params, proxy=None, cache=False):
	"""Request an URL with a given parameters and proxy

	url    -- URL to request
	params -- dictionary with POST variables
	proxy  -- URL for an HTTP proxy
	cache  -- True if you want request to be cached and get a cached version of the request
	"""
	if cache and self._cache.has_key(url):
	    return self._cache[url]

	request = urllib2.Request(url)
	request.add_header("User-agent", "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1")
	if proxy:
	    proxy_handler = urllib2.ProxyHandler({'http': proxy})
	    opener = urllib2.build_opener(proxy_handler)
	else:
	    opener = urllib2.build_opener()
	response = opener.open(request, urllib.urlencode(params)).read()

	if cache:
	    self._cache[url] = response

	return response

    def rm_duplicates(self, seq):
	"""Remove duplicates from a list

	This Function have been made by Dave Kirby and taken from site http://www.peterbe.com/plog/uniqifiers-benchmark
	"""
	seen = set()
	return [x for x in seq if x not in seen and not seen.add(x)]

    def login(self, url, username, password, proxy):
	"""Try to login into WordPress and see in the returned data contains login errors

	url      -- Login form URL
	username -- Wordpress username
	password -- Password for the supplied username
	proxy    -- HTTP proxy URL
	"""
	data = self.request(url, [('log', username), ('pwd', password)], proxy)
	if "ERROR" in data or "Error" in data or "login_error" in data:
	    return False
	else:
	    return True

    def check_username(self, url, username, proxy):
	"""Try to login into WordPress and check in the returned data contains username errors

	url      -- Login form URL
	username -- Wordpress username
	proxy    -- URL of an HTTP proxy
	"""
	data = self.request(url, [('log', username), ('pwd', str(randint(1, 9999)))], proxy)
	if "ERROR" in data or "Error" in data or "login_error" in data:
	    if "usuario es incorrecto" in data or "Invalid username" in data:
		return False
	    else:
		return True
	else:
	    return True

    def find_username(self, url, proxy):
	"""Try to find a suitable username searching for common strings used in templates that refers to authors of blog posts

	url   -- Any URL in the blog that can contain author references
	proxy -- URL of a HTTP proxy
	"""
	data =  self.request(url, [], proxy)
	username = None

	match = re.search('(<!-- by (.*?) -->)', data, re.IGNORECASE)       # search "<!-- by {AUTHOR} -->"
	if match:
	    username = match.group()[8:-4]

	if username is None:
	    match = re.search('View all posts by (.*)"', data, re.IGNORECASE)       # search "View all posts by {AUTHOR}"
	    if match:
		username = match.group()[18:-1]

	if username is None:
	    match = re.search('<a href="'+urljoin(url, ".")+'author/(.*)" ', data, re.IGNORECASE)	    # search "author/{AUTHOR}
	    if match:
		username = match.group()[len(url)+16:-2]

	if username is None or len(username) < 1:
	    return False
	else:
	    username = username.strip().replace("/","")
	    return username

    def enumerate_usernames(self, base_url, gap_tolerance=0, proxy=None):
	"""Enumerate usernames

	Enumerate usernames using TALSOFT-2011-0526 advisory (http://seclists.org/fulldisclosure/2011/May/493) present in
	WordPress > 3.2-beta2, or try to match from title of the user's archive page

	base_url      -- Base URL of the WordPress blog
	gap_tolerance -- Tolerance for user ID gaps in the sequence (this gaps are present when users are deleted and new users created)
	proxy         -- URL of a HTTP proxy
	"""
	uid = 0
	usernames = []
	gaps = 0
	title_cache = ""
	redirect = False
	while True:
	    try:
		uid = uid + 1
		url = base_url.rstrip("/")+"/?author="+str(uid)
		request = urllib2.Request(url)
		request.add_header("User-agent", "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1")
		if proxy:
		    proxy_handler = urllib2.ProxyHandler({"http": proxy})
		    opener = urllib2.build_opener(proxy_handler)
		else:
		    opener = urllib2.build_opener()
		response = opener.open(request)
		data = response.read()
		self._cache[url] = data	    # save response in cache
		parsed_response_url = urlparse(response.geturl())
		response_path = parsed_response_url.path
		if 'author' in response_path:
		    # A redirect was made and the username is exposed
		    usernames.append(response_path.split("/")[-2])
		    redirect = True
		    gaps = 0
		elif parsed_response_url.geturl() == url and redirect is False:
		    # There was no redirection but the user ID seems to exists so we will try to
		    # find the username as the first word in the title
		    title_search = re.search("<title>(.*)</title>", data, re.IGNORECASE)
		    if title_search:
			title =  title_search.group(1)
			# If the title is the same than the last user ID requested, there are no new users
			if title == title_cache:
			    break
			else:
			    title_cache = title
			    usernames.append(title.split()[0])
			    gaps = 0
		else:
		    break
	    except urllib2.HTTPError:
		gaps = gaps + 1
		if gaps > gap_tolerance:
		    break

	return [user for user in usernames if self.check_username(base_url+"/wp-login.php", user, proxy)]

    def find_keywords_in_url(self, url, proxy=None, min_keyword_len=3, min_frequency=2, ignore_with=[]):
	"""Try to find relevant keywords within the given URL, usually this keywords will be used added to the wordlist

	url             -- Any URL in the blog that can contain author references
	proxy           -- URL of a HTTP proxy
	min_keyword_len -- Filter keywords that doesn't have this minimum length
	min_frequency   -- Filter keywords number of times than a keyword appears within the content
	ignore_with     -- Ignore words that contains any characters in this list
	"""
	data =  self.request(url, [], proxy, True)
	keywords = []

	# get keywords from title
	title = re.search('<title>.*</title>', data, re.IGNORECASE).group()
	[keywords.insert(0,kw.lower()) for kw in title[7:-8].split(" ")][:-1]

	# get keywords from url content
	[keywords.append(k.strip()) for k in self.get_keywords(re.sub("<.*?>", "", data), min_keyword_len, min_frequency)]

	# filter keywords
	keywords = self.rm_duplicates([k.lower().strip().strip(",").strip("?").strip('"') for k in keywords if len(k) > min_keyword_len])    # min leght
	if len(ignore_with) > 0:	# ignore keywords with certain characters
	    for keyword in keywords[:]:
		for i in ignore_with:
		    if i in keyword:
			keywords.remove(keyword)
			break

	return keywords

    def get_keywords(self, data, min_keyword_len=3, min_frequency=2):
	"""Get relevant keywords from text

	data	        -- Input text to be indexed
	min_keyword_len -- Filter keywords that doesn't have this minimum length
	min_frequency	-- Filter keywords by the number of times than a keyword appear
	"""
	words = [w for w in data.split() if len(w) > min_keyword_len]
	keywords = {}
	for word in words:
	    if word in keywords:
		keywords[word] += 1
	    else:
		keywords[word] = 1

	for keyword, frequency in keywords.copy().iteritems():
	    if frequency < min_frequency:
		del keywords[keyword]

	return [k for k, v in keywords.iteritems()]
