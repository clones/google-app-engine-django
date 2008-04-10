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

"""Tests that the db module correctly initialises the API stubs."""


import unittest

from django.db import connection
from django.db.backends.appengine.base import DatabaseWrapper

from appengine_django import appid
from appengine_django.db import base


class DatastoreTest(unittest.TestCase):
  """Tests that the datastore stubs have been correctly setup."""

  def testDjangoDBConnection(self):
    """Tests that the Django DB connection is using our replacement."""
    self.assert_(isinstance(connection, DatabaseWrapper))

  def testDjangoDBConnectionStubs(self):
    """Tests that members required by Django 0.97 are stubbed."""
    self.assert_(hasattr(connection, "features"))
    self.assert_(hasattr(connection, "ops"))

  def testDjangoDBErroClasses(self):
    """Tests that the error classes required by Django 0.97 are stubbed."""
    self.assert_(hasattr(base, "DatabaseError"))
    self.assert_(hasattr(base, "IntegrityError"))

  def testDatastorePath(self):
    """Tests that the datastore path contains the app name."""
    d_path, h_path = base.get_datastore_paths()
    self.assertNotEqual(-1, d_path.find("django_%s" % appid))
    self.assertNotEqual(-1, h_path.find("django_%s" % appid))

  def testTestDatastorePath(self):
    """Tests that the test datastore is using the in-memory datastore."""
    td_path, th_path = base.get_test_datastore_paths()
    self.assert_(td_path is None)
    self.assert_(th_path is None)
