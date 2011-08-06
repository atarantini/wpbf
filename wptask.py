"""
wpbf is a WordPress BruteForce script to remotely test password strength of the WordPress blogging software

Copyright 2011 Andres Tarantini (atarantini@gmail.com)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from wplib import Wp

class WpTask():
    """Base task class"""
    def run(self):
        pass

class WpTaskStop(Exception):
    """Stop all tasks"""
    def __str__(self):
        return 'Stop all tasks!'

class WpTaskFingerprint(Wp, WpTask):
    """Perform WordPress fingerprint and, is positive, log the results"""
    def run(self):
        self.logger.info("WordPress version: %s", self.fingerprint())

class WpTaskLogin(Wp, WpTask):
    """Perform WordPress login. If login is positive, will return true or false otherwise.

    Note that username and password must be set invoking setUsername and setPassword methods.
    """
    _username = ""
    _password = ""

    def setUsername(self, username):
        self._username = username

    def setPassword(self, password):
        self._password = password

    def run(self):
        if self.login(self._username, self._password):
            # username and password found: log data and stop all tasks
            self.logger.info("Password '%s' found for username '%s' on %s", self._password, self._username, self.get_login_url())
            raise WpTaskStop

class WpTaskPluginCheck(Wp, WpTask):
    """Check if a plugin exists

    Note that plugin name must be set invoking setPluginName method. TODO: Refactor this!
    """
    _plugin = ""

    def setPluginName(self, plugin):
        self._plugin = plugin

    def run(self):
        if self.check_plugin(self._plugin):
            self.logger.info("Plugin '%s' was found", self._plugin)
