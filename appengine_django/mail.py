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
This module replaces the Django mail implementation with a version that sends
email via the mail API provided by Google App Engine.

Multipart / HTML email is not yet supported.
"""

import logging

from django.core import mail
from django.conf import settings

from google.appengine.api import mail as gmail

try:
  # Django >= 0.97
  from django.core.mail import SMTPConnection
except ImportError:
  # Django = 0.96
  SMTPConnection = object


class GoogleSMTPConnection(SMTPConnection):
  def __init__(self, host=None, port=None, username=None, password=None,
               use_tls=None, fail_silently=False):
    if (host):
      logging.warn("'host' parameter is ignored when running "
                   "in Google App Engine")
    if (port):
      logging.warn("'port' parameter is ignored when running in "
                   "Google App Engine")
    if (username):
      logging.warn("'username' parameter is ignored when running "
                   "in Google App Engine")
    if (password):
      logging.warn("'password' parameter is ignored when running "
                   "in Google App Engine")
    self.use_tls = (use_tls is not None) and use_tls or settings.EMAIL_USE_TLS
    self.fail_silently = fail_silently
    self.connection = None

  def open(self):
    self.connection = True

  def close(self):
    pass

  def _send(self, email_message):
    """A helper method that does the actual sending."""
    if not email_message.to:
      return False
    try:
      if (isinstance(email_message,gmail.EmailMessage)):
        e = message
      elif (isinstance(email_message,mail.EmailMessage)):
        e = gmail.EmailMessage(sender=email_message.from_email,
                               to=email_message.to,
                               subject=email_message.subject,
                               body=email_message.body)
        if email_message.bcc:
            e.bcc = list(email_message.bcc)
        #TODO - add support for html messages and attachments...
      e.send()
    except:
      if not self.fail_silently:
          raise
      return False
    return True


#Remove this when 0.96 support is no longer needed.
def send_mass_mail(datatuple, fail_silently=False, auth_user=None,
                   auth_password=None):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.

    This implementation for Google App Engine ignores the auth_user and
    auth_password setting, as these are not needed when using App Engine's
    default mail API.
    """
    if auth_user:
        logging.warning("auth_user parameter is ignored when running in "
                        "Google App Engine")
    if auth_password:
        logging.warning("auth_password parameter is ignored when running in "
                        "Google App Engine")
    num_sent = 0
    for subject, message, from_email, recipient_list in datatuple:
        if not recipient_list:
            continue
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        try:
          gmail.send_mail(sender=from_email,
                          to=', '.join(recipient_list),
                          subject=subject,
                          body=message)
          num_sent += 1
        except:
          if not fail_silently:
            raise
    return num_sent


def mail_admins(subject, message, fail_silently=False):
    """Sends a message to the admins, as defined by the ADMINS setting."""
    _mail_group(settings.ADMINS, subject, message, fail_silently)


def mail_managers(subject, message, fail_silently=False):
    """Sends a message to the managers, as defined by the MANAGERS setting."""
    _mail_group(settings.MANAGERS, subject, message, fail_silently)


def _mail_group(group, subject, message, fail_silently=False):
    """Sends a message to an administrative group."""
    if group:
      mail.send_mail(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                     settings.SERVER_EMAIL, [a[1] for a in group],
                     fail_silently)
      return
    # If the group had no recipients defined, default to the App Engine admins.
    try:
      gmail.send_mail_to_admins(settings.SERVER_EMAIL,
                                settings.EMAIL_SUBJECT_PREFIX + subject,
                                message)
    except:
      if not fail_silently:
        raise
