#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys

from appengine_django.db.base import get_datastore_paths

try:
  from django.core.management.base import BaseCommand
except ImportError:
  # Fake BaseCommand out so imports on django 0.96 don't fail.
  BaseCommand = object


def start_dev_appserver():
  """Starts the appengine dev_appserver program for the Django project.

  The appserver is run with default parameters. If you need to pass any special
  parameters to the dev_appserver you will have to invoke it manually.
  """
  from google.appengine.tools import dev_appserver_main
  progname = sys.argv[0]
  args = []
  # hack __main__ so --help in dev_appserver_main works OK.
  sys.modules['__main__'] = dev_appserver_main
  # Set bind ip/port if specified.
  if len(sys.argv) > 2:
    addrport = sys.argv[2]
    try:
      addr, port = addrport.split(":")
    except ValueError:
      addr, port = None, addrport
    if not port.isdigit():
      print "Error: '%s' is not a valid port number." % port
      sys.exit(1)
  else:
    addr, port = None, None
  if addr:
    args.extend(["--address", addr])
  if port:
    args.extend(["--port", port])
  # Pass the application specific datastore location to the server.
  p = get_datastore_paths()
  args.extend(["--datastore_path", p[0], "--history_path", p[1]])
  # Append the current working directory to the arguments.
  dev_appserver_main.main([progname] + args + [os.getcwdu()])


# Django 0.96 integration.
def v096_command(*args):
  """Runs the appengine development appserver for the current project.

  Note: This command does not start the standard django server. The
  dev_appserver is run with its default arguments.
  """
  # This wrapper function is used instead of passing start_dev_appserver
  # directly to Django because Django 0.96 wants to read it's docstring and
  # args attribute for commandline help.
  start_dev_appserver()
v096_command.args = "[optional port number, or ipaddr:port]"


# Django 0.97 integration.
class Command(BaseCommand):
    """Overrides the default Django 0.97 runserver command.

    Instead of starting the default Django development server this command
    fires up a copy of the full fledged appengine dev_appserver that emulates
    the live environment your application will be deployed to.
    """
    help = 'Runs a copy of the appengine development server.'
    args = '[optional port number, or ipaddr:port]'

    def run_from_argv(self, argv):
      start_dev_appserver()
