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

"""Support for integrating a Django project with the appengine infrastructure.

This works with both Django 0.96 (via much monkey patching) and Django
0.97.pre1.

This module enables you to use the Django manage.py utility and *some* of it's
subcommands. View the help of manage.py for exact details.

Additionally this module takes care of initialising the datastore (and a test
datastore) so that the Django test infrastructure can be used for your
appengine project.

To use this module add the following two lines to your main.py and manage.py
scripts at the end of your imports:
  from appengine_django import InstallAppengineHelperForDjango
  InstallAppengineHelperForDjango()

If you would like to use a version of Django other than that provided by the
system all you need to do is include it in a directory just above this helper,
eg:
  appengine_django/__init__.py        -  This file
  django/...                          - your private copy of Django.
"""

import logging
import os
import sys


DIR_PATH = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(DIR_PATH)

# Add this project to the start of sys path to enable direct imports.
sys.path = [PARENT_DIR,] + sys.path

# Try to import the appengine code from the system path.
try:
  from google.appengine.api import apiproxy_stub_map
except ImportError, e:
  # Not on the system path. Build a list of alternative paths where it may be.
  # First look within the project for a local copy, then look for where the Mac
  # OS SDK installs it.
  paths = [os.path.join(PARENT_DIR, '.google_appengine'),
           os.path.join(PARENT_DIR, 'google_appengine'),
           '/usr/local/google_appengine']
  # Then if on windows, look for where the Windows SDK installed it.
  for path in os.environ.get('PATH', '').split(';'):
    path = path.rstrip('\\')
    if path.endswith('google_appengine'):
      paths.append(path)
  try:
    from win32com.shell import shell
    from win32com.shell import shellcon
    id_list = shell.SHGetSpecialFolderLocation(
        0, shellcon.CSIDL_PROGRAM_FILES)
    program_files = shell.SHGetPathFromIDList(id_list)
    paths.append(os.path.join(program_files, 'Google',
                              'google_appengine'))
  except ImportError, e:
    # Not windows.
    pass
  # Loop through all possible paths and look for the SDK dir.
  SDK_PATH = None
  for sdk_path in paths:
    if os.path.exists(sdk_path):
      SDK_PATH = sdk_path
      break
  if SDK_PATH is None:
    # The SDK could not be found in any known location.
    sys.stderr.write("The Google App Engine SDK could not be found!\n")
    sys.stderr.write("See README for installation instructions.\n")
    sys.exit(1)
  if SDK_PATH == os.path.join(PARENT_DIR, 'google_appengine'):
    logging.warn('Loading the SDK from the \'google_appengine\' subdirectory '
                 'is now deprecated!')
    logging.warn('Please move the SDK to a subdirectory named '
                 '\'.google_appengine\' instead.')
    logging.warn('See README for further details.')
  # Add the SDK and the libraries within it to the system path.
  EXTRA_PATHS = [
      SDK_PATH,
      os.path.join(SDK_PATH, 'lib', 'django'),
      os.path.join(SDK_PATH, 'lib', 'webob'),
      os.path.join(SDK_PATH, 'lib', 'yaml', 'lib'),
  ]
  # Add SDK paths at the start of sys.path, but after the local directory which
  # was added to the start of sys.path on line 50 above. The local directory
  # must come first to allow the local imports to override the SDK and
  # site-packages directories.
  sys.path = sys.path[0:1] + EXTRA_PATHS + sys.path[1:]
  from google.appengine.api import apiproxy_stub_map


# Remove the standard version of Django if a local copy has been provided.
if os.path.exists(os.path.join(PARENT_DIR, 'django')):
  for k in [k for k in sys.modules if k.startswith('django')]:
    del sys.modules[k]

from django import VERSION
from django.conf import settings


# Flags made available this module
appid = None
appconfig = None
have_appserver = False

# Hide everything other than the flags above and the install function.
__all__ = ("appid", "appconfig", "have_appserver",
           "InstallAppengineHelperForDjango")


INCOMPATIBLE_COMMANDS = ["adminindex", "createcachetable", "dbshell",
                         "inspectdb", "runfcgi", "syncdb", "validate"]


def LoadAppengineEnvironment():
  """Loads the appengine environment.

  Returns:
    This function has no return value, but it sets the following parameters on
    this package:
    - appid: The name of the application as read from the config file.
    - appconfig: The appserver configuration dictionary for the application, as
      read from the config file.
    - have_appserver: Boolean parameter which is True if the code is being run
        from within the appserver environment.
  """
  global appid, appconfig, have_appserver

  # Load the application configuration.
  try:
    from google.appengine.tools import dev_appserver
    appconfig, unused_matcher = dev_appserver.LoadAppConfig(".", {})
    appid = appconfig.application
  except ImportError:
    # Running under the real appserver.
    appconfig = {}
    appid = "unknown"

  # Detect if we are running under an appserver.
  have_appserver = False
  stub = apiproxy_stub_map.apiproxy.GetStub("datastore_v3")
  if stub:
    have_appserver = True
  logging.debug("Loading application '%s' %s an appserver" %
                (appid, have_appserver and "with" or "without"))


def InstallAppengineDatabaseBackend():
  """Installs the appengine database backend into Django.

  The appengine database lives in the db/ subdirectory of this package, but is
  known as "appengine" to Django. This function installs the module where
  Django expects to find its database backends.
  """
  from appengine_django import db
  sys.modules['django.db.backends.appengine'] = db
  PatchTestDBCreationFunctions()
  logging.debug("Installed appengine database backend")


def PatchTestDBCreationFunctions():
  """Installs the functions that create/remove the test database.

  Only required for Django 0.96. Django 0.97 finds these functions in the
  backend and uses them automatically. Also skipped if running under an
  appserver.
  """
  if VERSION >= (0, 97, None) or have_appserver:
    return
  from django.test import utils
  from appengine_django.db import creation
  utils.create_test_db = creation.create_test_db
  utils.destroy_test_db = creation.destroy_test_db
  logging.debug("Installed test database create/destroy functions")


def InstallGoogleMemcache():
  """Installs the Google memcache into Django.

  By default django tries to import standard memcache module.
  Because appengine memcache is API compatible with Python memcache module,
  we can trick Django to think it is installed and to use it.
  
  Now you can use CACHE_BACKEND = 'memcached://' in settings.py. IP address
  and port number are not required.
  """
  from google.appengine.api import memcache
  sys.modules['memcache'] = memcache
  logging.debug("Installed App Engine memcache backend")


def InstallDjangoModuleReplacements():
  """Replaces internal Django modules with App Engine compatible versions."""

  # Replace the session module with a partial replacement overlay using
  # __path__ so that portions not replaced will fall through to the original
  # implementation. 
  try:
    from django.contrib import sessions
    orig_path = sessions.__path__[0]
    sessions.__path__.insert(0, os.path.join(DIR_PATH, 'sessions'))
    from django.contrib.sessions import backends
    backends.__path__.append(os.path.join(orig_path, 'backends'))
  except ImportError:
    logging.debug("No Django session support available")

  # Replace incompatible dispatchers.
  import django.core.signals
  import django.db
  import django.dispatch.dispatcher

  # Rollback occurs automatically on Google App Engine. Disable the Django
  # rollback handler.
  try:
    django.dispatch.dispatcher.disconnect(
        django.db._rollback_on_exception,
        django.core.signals.got_request_exception)
  except django.dispatch.errors.DispatcherKeyError, e:
    logging.debug("Django rollback handler appears to be already disabled.")


def PatchDjangoSerializationModules():
  """Monkey patches the Django serialization modules.

  The standard Django serialization modules to not correctly handle the
  datastore models provided by this package. This method installs replacements
  for selected modules and methods to give Django the capability to correctly
  serialize and deserialize datastore models.
  """
  # These can't be imported until InstallAppengineDatabaseBackend has run.
  from django.core.serializers import python
  from appengine_django.serializer.python import Deserializer
  if not hasattr(settings, "SERIALIZATION_MODULES"):
    settings.SERIALIZATION_MODULES = {}
  base_module = "appengine_django"
  settings.SERIALIZATION_MODULES["xml"] = "%s.serializer.xml" % base_module
  python.Deserializer = Deserializer
  PatchDeserializedObjectClass()
  DisableModelValidation()
  logging.debug("Installed appengine json and python serialization modules")


def PatchDeserializedObjectClass():
  """Patches the DeserializedObject class.

  The default implementation calls save directly on the django Model base
  class to avoid pre-save handlers. The model class provided by this package
  is not derived from the Django Model class and therefore must be called
  directly.

  Additionally we need to clear the internal _parent attribute as it may
  contain a FakeParent class that is used to deserialize instances without
  needing to load the parent instance itself. See the PythonDeserializer for
  more details.
  """
  # This can't be imported until InstallAppengineDatabaseBackend has run.
  from django.core.serializers import base
  class NewDeserializedObject(base.DeserializedObject):
    def save(self, save_m2m=True):
      self.object.save()
      self.object._parent = None
  base.DeserializedObject = NewDeserializedObject
  logging.debug("Replacement DeserializedObject class installed")

def DisableModelValidation():
  """Disables Django's model validation routines.

  The model validation is primarily concerned with validating foreign key
  references. There is no equivalent checking code for datastore References at
  this time.

  Validation needs to be disabled or serialization/deserialization will fail.
  """
  # Imports must be performed in this function as they differ between versions.
  if VERSION < (0, 97, None):
    from django.core import management
    management.get_validation_errors = lambda x, y=0: 0
  else:
    from django.core.management import validation
    validation.get_validation_errors = lambda x, y=0: 0
  logging.debug("Django SQL model validation disabled")

def CleanupDjangoSettings():
  """Removes incompatible entries from the django settings module."""

  # Ensure this module is installed as an application.
  apps = getattr(settings, "INSTALLED_APPS", ())
  found = False
  for app in apps:
    if app.endswith("appengine_django"):
      found = True
      break
  if not found:
    logging.warn("appengine_django module is not listed as an application!")
    apps += ("appengine_django",)
    setattr(settings, "INSTALLED_APPS", apps)
    logging.info("Added 'appengine_django' as an application")

  # Ensure the database backend is appropriately configured.
  dbe = getattr(settings, "DATABASE_ENGINE", "")
  if dbe != "appengine":
    settings.DATABASE_ENGINE = "appengine"
    logging.warn("DATABASE_ENGINE is not configured as 'appengine'. "
                 "Value overriden!")
  for var in ["NAME", "USER", "PASSWORD", "HOST", "PORT"]:
    val = getattr(settings, "DATABASE_%s" % var, "")
    if val:
      setattr(settings, "DATABASE_%s" % var, "")
      logging.warn("DATABASE_%s should be blank. Value overriden!")

  # Remove incompatible middleware modules.
  mw_mods = list(getattr(settings, "MIDDLEWARE_CLASSES", ()))
  disallowed_middleware_mods = (
    'django.middleware.doc.XViewMiddleware',)
  if VERSION < (0, 97, None):
      # Sessions are only supported with Django 0.97.
      disallowed_middleware_mods += (
          'django.contrib.sessions.middleware.SessionMiddleware',)
  for modname in mw_mods[:]:
    if modname in disallowed_middleware_mods:
      # Currently only the CommonMiddleware has been ported.  As other base
      # modules are converted, remove from the disallowed_middleware_mods
      # tuple.
      mw_mods.remove(modname)
      logging.warn("Middleware module '%s' is not compatible. Removed!" %
                   modname)
  setattr(settings, "MIDDLEWARE_CLASSES", tuple(mw_mods))

  # Remove incompatible application modules
  app_mods = list(getattr(settings, "INSTALLED_APPS", ()))
  disallowed_apps = (
    'django.contrib.contenttypes',
    'django.contrib.sites',)
  if VERSION < (0, 97, None):
      # Sessions are only supported with Django 0.97.
      disallowed_apps += ('django.contrib.sessions',)
  for app in app_mods[:]:
    if app in disallowed_apps:
      app_mods.remove(app)
      logging.warn("Application module '%s' is not compatible. Removed!" % app)
  setattr(settings, "INSTALLED_APPS", tuple(app_mods))

  # Remove incompatible session backends.
  session_backend = getattr(settings, "SESSION_ENGINE", "")
  if session_backend.endswith("file"):
    logging.warn("File session backend is not compatible. Overriden "
                 "to use db backend!")
    setattr(settings, "SESSION_ENGINE", "django.contrib.sessions.backends.db")


def ModifyAvailableCommands():
  """Removes incompatible commands and installs replacements where possible."""
  if have_appserver:
    # Commands are not used when running from an appserver.
    return
  from django.core import management
  if VERSION < (0, 97, None):
    RemoveCommands(management.DEFAULT_ACTION_MAPPING)
    from appengine_django.management.commands import runserver
    management.DEFAULT_ACTION_MAPPING['runserver'] = runserver.v096_command
    from appengine_django.management.commands import flush
    management.DEFAULT_ACTION_MAPPING['flush'] = flush.v096_command
    from appengine_django.management.commands import reset
    management.DEFAULT_ACTION_MAPPING['reset'] = reset.v096_command
    # startapp command for django 0.96 
    management.PROJECT_TEMPLATE_DIR = os.path.join(__path__[0], 'conf',
                                                   '%s_template')
  else:
    project_directory = os.path.join(__path__[0], "../")
    management.get_commands(project_directory=project_directory)
    # Replace startapp command which is set by previous call to get_commands().
    from appengine_django.management.commands.startapp import ProjectCommand
    management._commands['startapp'] = ProjectCommand(project_directory) 
    RemoveCommands(management._commands)
    # Django 0.97 will install the replacements automatically.
  logging.debug("Removed incompatible Django manage.py commands")


def RemoveCommands(command_dict):
  """Removes incompatible commands from the specified command dictionary."""
  for cmd in command_dict.keys():
    if cmd.startswith("sql"):
      del command_dict[cmd]
    elif cmd in INCOMPATIBLE_COMMANDS:
      del command_dict[cmd]


def InstallReplacementImpModule():
  """Install a replacement for the imp module removed by the appserver.

  This is only required for Django 0.97 which uses imp.find_module to find
  mangement modules provided by applications.
  """
  if VERSION < (0, 97, None) or not have_appserver:
    return
  modname = 'appengine_django.replacement_imp'
  imp_mod = __import__(modname, {}, [], [''])
  sys.modules['imp'] = imp_mod
  logging.debug("Installed replacement imp module")


def InstallAppengineHelperForDjango():
  """Installs and Patches all of the classes/methods required for integration.

  If the variable DEBUG_APPENGINE_DJANGO is set in the environment verbose
  logging of the actions taken will be enabled.
  """
  if os.getenv("DEBUG_APPENGINE_DJANGO"):
    logging.getLogger().setLevel(logging.DEBUG)
  else:
    logging.getLogger().setLevel(logging.INFO)
  logging.debug("Loading the Google App Engine Helper for Django...")

  # Force Django to reload its settings.
  settings._target = None

  # Must set this env var *before* importing any more of Django.
  os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

  LoadAppengineEnvironment()
  InstallReplacementImpModule()
  InstallAppengineDatabaseBackend()
  InstallModelForm()
  InstallGoogleMemcache()
  InstallDjangoModuleReplacements()
  PatchDjangoSerializationModules()
  CleanupDjangoSettings()
  ModifyAvailableCommands()
  InstallGoogleSMTPConnection()
  InstallAuthentication()

  logging.debug("Successfully loaded the Google App Engine Helper for Django.")


def InstallGoogleSMTPConnection():
  from appengine_django import mail as gmail
  from django.core import mail
  if VERSION >= (0, 97, None):
    logging.debug("Installing Google Email Adapter for Django 0.97+")
    mail.SMTPConnection = gmail.GoogleSMTPConnection
  else:
    logging.debug("Installing Google Email Adapter for Django 0.96")
    mail.send_mass_mail = gmail.send_mass_mail
  mail.mail_admins = gmail.mail_admins
  mail.mail_managers = gmail.mail_managers


def InstallAuthentication():
  try:
    from appengine_django.auth import models as helper_models
    from django.contrib.auth import models
    models.User = helper_models.User
    models.Group = helper_models.Group
    models.Permission = helper_models.Permission
    models.Message = helper_models.Message
    from django.contrib.auth import middleware as django_middleware
    from appengine_django.auth.middleware import AuthenticationMiddleware
    django_middleware.AuthenticationMiddleware = AuthenticationMiddleware
    from django.contrib.auth import decorators as django_decorators
    from appengine_django.auth.decorators import login_required
    django_decorators.login_required = login_required
    if VERSION >= (0, 97, None):
      from appengine_django.auth import tests
      from django.contrib.auth import tests as django_tests
      django_tests.PasswordResetTest = None
      django_tests.__test__ = {}
      django_tests.__doc__ = tests.__doc__
    logging.debug("Installing authentication framework")
  except ImportError:
    logging.debug("No Django authentication support available")


def InstallModelForm():
  """Replace Django ModelForm with the AppEngine ModelForm."""
  # This MUST happen as early as possible, but after any auth model patching.
  from google.appengine.ext.db import djangoforms as aeforms
  from django import newforms as forms
  forms.ModelForm = aeforms.ModelForm

  # Extend ModelForm with support for EmailProperty
  # TODO: This should be submitted to the main App Engine SDK.
  from google.appengine.ext.db import EmailProperty
  def get_form_field(self, **kwargs):
    """Return a Django form field appropriate for an email property."""
    defaults = {'form_class': forms.EmailField}
    defaults.update(kwargs)
    return super(EmailProperty, self).get_form_field(**defaults)
  EmailProperty.get_form_field = get_form_field
