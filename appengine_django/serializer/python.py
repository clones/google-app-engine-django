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
A Python "serializer", based on the default Django python serializer.

The only customisation is in the deserialization process which needs to take
special care to resolve the name and parent attributes of the key for each
entity and also recreate the keys for any references appropriately.
"""


from django.conf import settings
from django.core.serializers import base
from django.core.serializers import python
from django.db import models

from google.appengine.api import datastore_types
from google.appengine.ext import db

try:
  from django.utils.encoding import smart_unicode
except ImportError:
  import datetime
  import types
  from django.utils.functional import Promise

  def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    non_strings = (types.NoneType, int, long, datetime.datetime, datetime.date,
                   datetime.time, float)
    if strings_only and isinstance(s, non_strings):
      return s
    if not isinstance(s, basestring,):
      if hasattr(s, '__unicode__'):
        s = unicode(s)
      else:
        s = unicode(str(s), encoding, errors)
    elif not isinstance(s, unicode):
      # Note: We use .decode() here, instead of unicode(s, encoding,
      # errors), so that if s is a SafeString, it ends up being a
      # SafeUnicode at the end.
      s = s.decode(encoding, errors)
    return s

  def smart_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
      # The input is the result of a gettext_lazy() call.
      return s
    return force_unicode(s, encoding, strings_only, errors)

Serializer = python.Serializer

def Deserializer(object_list, **options):
  """Deserialize simple Python objects back into Model instances.

  It's expected that you pass the Python objects themselves (instead of a
  stream or a string) to the constructor
  """
  models.get_apps()
  for d in object_list:
    # Look up the model and starting build a dict of data for it.
    Model = python._get_model(d["model"])
    data = {}
    key = db.Key(d["pk"])
    if key.name():
      data["key_name"] = key.name()
    if key.parent():
      parent = db.get(key.parent())
      if not parent:
        raise base.DeserializationError(
            "Cannot load entity '%s'. Parent '%s' cannot be found" %
            (key, key.parent()))
      data["parent"] = parent
    m2m_data = {}

    # Handle each field
    for (field_name, field_value) in d["fields"].iteritems():
      if isinstance(field_value, str):
        field_value = smart_unicode(
            field_value, options.get("encoding",
                                     settings.DEFAULT_CHARSET),
            strings_only=True)
      field = Model.properties()[field_name]

      if isinstance(field, db.Reference):
        # Resolve foreign key references.
        if isinstance(field_value, list):
          # field contains a from_path sequence
          data[field.name] = db.Key.from_path(*field_value)
        elif isinstance(field_value, basestring):
          if field_value.find("from_path") != -1:
            # field encoded in repr(key) format
            data[field.name] = eval(field_value)
          else:
            # field encoded a str(key) format
            data[field.name] = db.Key(field_value)
        else:
          raise base.DeserializationError(u"Invalid reference value: '%s'" %
                                          field_value)
        if not data[field.name].name():
          raise base.DeserializationError(u"Cannot load Reference with "
                                          "unnamed key: '%s'" % field_value)
      else:
        data[field.name] = field.validate(field_value)
    yield base.DeserializedObject(Model(**data), m2m_data)
