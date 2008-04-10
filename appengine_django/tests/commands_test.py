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

"""
Tests that the manage.py commands execute correctly.

These tests only verify that the commands execute and exit with a success code.
They are intended to catch import exceptions and similar problems, it is left
up to tests in other modules to verify that the functionality of each command
works correctly.
"""


import os
import signal
import subprocess
import tempfile
import time
import unittest

from django.db.models import get_models

from google.appengine.ext import db
from appengine_django.models import BaseModel
from appengine_django.models import ModelManager
from appengine_django.models import ModelOptions
from appengine_django.models import RegistrationTestModel


class CommandsTest(unittest.TestCase):
  """Unit tests for the manage.py commands."""

  # How many seconds to wait for a command to exit.
  COMMAND_TIMEOUT = 10

  def runCommand(self, command, args=None, int_after=None, input=None):
    """Helper to run the specified command in a child process.

    Args:
      command: The name of the command to run.
      args: List of command arguments to run the command with.
      int_after: If set to a positive integer, SIGINT will be sent to the
        running child process after this many seconds to cause an exit. This
        should be less than the COMMAND_TIMEOUT value (10 seconds).
      input: A string to write to stdin when the command starts. stdin is
        closed after the string is written.

    Raises:
      This function does not return anything but will raise assertion errors if
      the command does not exit successfully.
    """
    if not args:
      args = []
    start = time.time()
    int_sent = False
    fd, tempname = tempfile.mkstemp()
    infd = fd
    if input:
      infd = subprocess.PIPE

    child = subprocess.Popen(["./manage.py", command] + args, stdin=infd,
                             stdout=fd, stderr=fd, cwd=os.getcwdu())
    if input:
      child.stdin.write(input)
      child.stdin.close()

    while 1:
      rc = child.poll()
      if rc is not None:
        # Child has exited.
        break
      elapsed = time.time() - start
      if int_after and int_after > 0 and elapsed > int_after and not int_sent:
        # Sent SIGINT as requested, give child time to exit cleanly.
        os.kill(child.pid, signal.SIGINT)
        start = time.time()
        int_sent = True
        continue
      if elapsed < self.COMMAND_TIMEOUT:
        continue
      # Command is over time, kill and exit loop.
      os.kill(child.pid, signal.SIGKILL)
      time.sleep(2)  # Give time for the signal to be received.
      break

    # Check child return code
    os.close(fd)
    self.assertEquals(0, rc,
                      "%s did not return successfully (rc: %d): Output in %s" %
                      (command, rc, tempname))
    os.unlink(tempname)

  def testDiffSettings(self):
    """Tests the diffsettings command."""
    self.runCommand("diffsettings")

  def testDumpData(self):
    """Tests the dumpdata command."""
    self.runCommand("dumpdata")

  def testFlush(self):
    """Tests the flush command."""
    self.runCommand("flush")

  def testLoadData(self):
    """Tests the loaddata command."""
    self.runCommand("loaddata")

  def testLoadData(self):
    """Tests the loaddata command."""
    self.runCommand("loaddata")

  def testReset(self):
    """Tests the reste command."""
    self.runCommand("reset", ["appengine_django"])

  def testRunserver(self):
    """Tests the runserver command."""
    self.runCommand("runserver", int_after=2.0)

  def testShell(self):
    """Tests the shell command."""
    self.runCommand("shell", input="exit")
