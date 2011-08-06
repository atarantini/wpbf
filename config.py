#
# wpbf config file
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
#
wordlist = "wordlist.txt"
plugins_list = "plugins.txt"
script_path = "wp-login.php"
url = "http://localhost/wordpress/wp-login.php"
threads = 5
proxy = None

# users
username = "admin"
eu_gap_tolerance = 3

# keywords
min_keyword_len = 3
min_frequency = 3
ignore_with = ['&', ';', '<', '>', '(', ')', '}', '{', '=', '#', ':', '.', '_', '/', '\\']
