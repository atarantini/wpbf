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
import threading

from wplib import Wp

class WpbfWorker(threading.Thread):
    """Handle threads that consume the tasks queue"""
    def __init__(self, task_queue):
        threading.Thread.__init__(self)
        self._queue = task_queue

    def run(self):
        while self._queue.qsize() > 0:
            try:
                task = self._queue.get()
                task.run()
                self._queue.task_done()
            except WpTaskStop:
                self._queue.queue.clear()

class WpTask():
    """Base task class"""

    _task_queue = False
    _requeue = False

    def run(self):
        pass

    def stop_all_tasks(self):
        raise WpTaskStop

    def requeue(self):
        """Requeue a task"""
        if self._requeue and self._keywords.has_key('task_queue'):
            self._task_queue = self._keywords['task_queue']
            self._task_queue.put(self)
            self._requeue = False
            return True
        return False

class WpTaskStop(Exception):
    """Clear tasks queue"""
    def __str__(self):
        return 'Stop all tasks!'

class WpTaskFingerprint(Wp, WpTask):
    """Perform WordPress fingerprint and. If positive, log the results"""
    def run(self):
        version = self.fingerprint()
        if version:
            self.logger.info("WordPress version: %s", self.fingerprint())

        server_path = self.find_server_path()
        if server_path:
            self.logger.info("WordPress path in server: %s", self.find_server_path())

class WpTaskLogin(Wp, WpTask):
    """
    Perform WordPress login. If login is positive, will log the username and password combination

    username -- string representing a username
    password -- string representing a password
    """
    def run(self):
        if self._keywords.has_key('username') and self._keywords.has_key('password') and self.login(self._keywords['username'], self._keywords['password']):
            # username and password found: log data and stop all tasks
            self.logger.info("Password '%s' found for username '%s' on %s", self._keywords['password'], self._keywords['username'], self.get_login_url())
            if self._keywords.has_key('dontstop') and self._keywords['dontstop'] is False:
                self.stop_all_tasks()

class WpTaskPluginCheck(Wp, WpTask):
    """
    Check if a plugin exists. If not 404 error is found and request is completed, the
    plugin name will be logged

    name -- string representing the plugin name/directory
    """
    def run(self):
        if self._keywords.has_key('name') and self.check_plugin(self._keywords['name']):
            self.logger.info("Plugin '%s' was found", self._keywords['name'])
            plugin_doc_url = self.check_plugin_documentation(self._keywords['name'])
            if plugin_doc_url:
                plugin_version = self.find_plugin_version(plugin_doc_url)
                if plugin_version is not False:
                    self.logger.info("Plugin '%s' version: %s (more info @ %s)", self._keywords['name'], plugin_version, plugin_doc_url)
                else:
                    self.logger.info("Additional plugin documentation for '%s' can be found @ %s", self._keywords['name'], plugin_doc_url)
