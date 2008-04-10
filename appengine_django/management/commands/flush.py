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

import logging
import os
import sys

try:
  from django.core.management.base import BaseCommand
except ImportError:
  # Fake BaseCommand out so imports on django 0.96 don't fail.
  BaseCommand = object


# Django 0.96 integration.
def v096_command(*args):
  """Clears the current datastore and loads the initial fixture data. """
  # This wrapper function is used instead of passing the real function directly
  # to Django because Django 0.96 wants to read its docstring and args
  # attribute for commandline help.
  from django.db import connection
  connection.flush()
  from django.core.management import load_data
  load_data(['initial_data'])
v096_command.args = ""


# Django 0.97 integration.
class Command(BaseCommand):
    """Overrides the default Django 0.97 flush command.
    """
    help = 'Clears the current datastore and loads the initial fixture data.'

    def run_from_argv(self, argv):
      from django.db import connection
      connection.flush()
      from django.core.management import call_command
      call_command('loaddata', 'initial_data')

    def handle(self, *args, **kwargs):
      self.run_from_argv(None)
