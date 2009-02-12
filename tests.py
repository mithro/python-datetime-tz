#!/usr/bin/python2.4
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Disable the protected method member warning as we are trying to test them!
# Disable the bad name warnings as tests need to start with test in lowercase.
# Disable the exception does nothing, as we want to test exceptions.
# Disable the missing docstrings as test methods are 'self documenting'.
# Disable the override inbuilt, because that is exactly what we want to do.
# pylint: disable-msg=W0212,C6409,C6111,W0622,W0704

"""Tests for the datetime_tz module."""

__author__ = "tansell@google.com (Tim Ansell)"

import datetime
import os
import StringIO
import unittest
import warnings

import datetime_tz
import pytz


class MockMe(object):
  """Simple class to handle saving/restoring of mocked values."""

  def __init__(self):
    self.mocked = {}

  # pylint: disable-msg=W0613,W0122
  def __call__(self, tomock, mockwith):
    if tomock not in self.mocked:
      self.mocked[tomock] = eval(tomock)
    exec("%s = mockwith" % tomock)

  # pylint: disable-msg=W0612,W0122
  def tearDown(self):
    for tomock, tounmock in self.mocked.iteritems():
      exec("%s = tounmock" % tomock)


class TestLocalTimezoneDetection(unittest.TestCase):

  def setUp(self):
    # Ignore warnings in datetime_tz as we are going to forcably generate them.
    warnings.filterwarnings("ignore", module="datetime_tz")
    self.mocked = MockMe()

  def tearDown(self):
    self.mocked.tearDown()

  def testEnvironMethod(self):
    # Test when TZ exists
    os.environ["TZ"] = "UTC"
    tzinfo = datetime_tz._detect_timezone_environ()
    self.assertEqual(pytz.utc, tzinfo)

    # Test when TZ is an invalid option
    os.environ["TZ"] = "Invalid-Timezone"
    tzinfo = datetime_tz._detect_timezone_environ()
    self.assertEqual(None, tzinfo)

  def testEtcTimezoneMethod(self):
    def os_path_exists_fake(filename, os_path_exists=os.path.exists):
      if filename == "/etc/timezone":
        return True
      return os_path_exists(filename)
    self.mocked("os.path.exists", os_path_exists_fake)

    # Check that when /etc/timezone is a valid input
    def timezone_valid_fake(filename, file=open):
      if filename == "/etc/timezone":
        return StringIO.StringIO("Australia/Sydney")
      return file(filename)

    self.mocked("__builtins__.file", timezone_valid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(pytz.timezone("Australia/Sydney").zone, tzinfo.zone)

    # Check that when /etc/timezone is invalid timezone
    def timezone_invalid_fake(filename, file=open):
      if filename == "/etc/timezone":
        return StringIO.StringIO("Invalid-Timezone")
      return file(filename)

    self.mocked("__builtins__.file", timezone_invalid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(None, tzinfo)

    # Check that when /etc/timezone is random "binary" data
    def timezone_binary_fake(filename, file=open):
      if filename == "/etc/timezone":
        return StringIO.StringIO("\0\r\n\t\0\r\r\n\0")
      return file(filename)

    self.mocked("__builtins__.file", timezone_binary_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(None, tzinfo)

  def testEtcLocaltimeMethod(self):
    def os_path_exists_fake(filename, os_path_exists=os.path.exists):
      if filename == "/etc/localtime":
        return True
      return os_path_exists(filename)
    self.mocked("os.path.exists", os_path_exists_fake)

    def localtime_valid_fake(filename, file=file):
      if filename == "/etc/localtime":
        return file("test_localtime_sydney")
      return file(filename)
    self.mocked("__builtins__.file", localtime_valid_fake)

    # Test the single matches case
    self.mocked("pytz.all_timezones", [pytz.timezone("Australia/Sydney")])

    r = datetime_tz._detect_timezone_etc_localtime()

    self.assertEqual(r, pytz.timezone("Australia/Sydney"))

    # Test the multiple matches case
    self.mocked("pytz.all_timezones", [pytz.timezone("Australia/Sydney"),
                                       pytz.timezone("Australia/Sydney")])

    r = datetime_tz._detect_timezone_etc_localtime()

    self.assertNotEqual(r, pytz.timezone("Australia/Sydney"))

  def testPHPMethod(self):
    # FIXME: Actually test this method sometime in the future.
    pass


class TestDatetimeTZ(unittest.TestCase):

  def testCreation(self):
    # Creation with string timezone
    d1 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo="UTC")
    self.assert_(isinstance(d1, datetime_tz.datetime_tz))

    # Creation with tzinfo object
    d2 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo=pytz.utc)
    self.assert_(isinstance(d2, datetime_tz.datetime_tz))

    # Creation from a datetime_tz object
    d3 = datetime_tz.datetime_tz(d1)
    self.assert_(isinstance(d3, datetime_tz.datetime_tz))
    self.assertEqual(d1.tzinfo, d3.tzinfo)

    # Creation from a datetime object
    d4 = datetime.datetime.now()
    d4 = pytz.timezone("Australia/Sydney").localize(d4)
    d5 = datetime_tz.datetime_tz(d4)
    self.assert_(isinstance(d3, datetime_tz.datetime_tz))
    self.assertEqual(d4.tzinfo, d5.tzinfo)

    # Creation from a naive datetime object
    d6 = datetime.datetime.now()
    try:
      d7 = datetime_tz.datetime_tz(d6)
      self.assert_(False)
    except TypeError:
      pass

    d7 = datetime_tz.datetime_tz(d6, "Australia/Sydney")
    self.assert_(isinstance(d7, datetime_tz.datetime_tz))
    self.assertEqual(d7.tzinfo, pytz.timezone("Australia/Sydney"))

  def testOperations(self):
    dadd = datetime_tz.datetime_tz.now() + datetime.timedelta(days=1)

    dradd = datetime_tz.datetime_tz.now()
    dradd += datetime.timedelta(days=1)

    dsub = datetime_tz.datetime_tz.now() - datetime.timedelta(days=1)

    drsub = datetime_tz.datetime_tz.now()
    drsub -= datetime.timedelta(days=1)

    dreplace = datetime_tz.datetime_tz.now()
    dreplace = dreplace.replace(day=1)

    self.assert_(isinstance(dadd, datetime_tz.datetime_tz))
    self.assert_(isinstance(dsub, datetime_tz.datetime_tz))
    self.assert_(isinstance(dradd, datetime_tz.datetime_tz))
    self.assert_(isinstance(drsub, datetime_tz.datetime_tz))
    self.assert_(isinstance(dreplace, datetime_tz.datetime_tz))

    # Make sure the wrapped functions still look like the original functions
    self.assertEqual(dreplace.replace.__name__,
                     datetime.datetime.replace.__name__)
    self.assertEqual(dreplace.replace.__doc__,
                     datetime.datetime.replace.__doc__)

    try:
      dreplace = datetime_tz.datetime_tz.now()
      dreplace = dreplace.replace(days=1)

      self.assert_(False)

    except TypeError:
      pass

  def testUtcFromTimestamp(self):
    datetime_tz.localtz_set("Australia/Sydney")

    for timestamp in 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.utcfromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo, pytz.utc)
      self.assertEqual(d.totimestamp(), timestamp)

  def testFromTimestamp(self):
    datetime_tz.localtz_set("Australia/Sydney")

    for timestamp in 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.fromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo.zone, pytz.timezone("Australia/Sydney").zone)
      self.assertEqual(d.totimestamp(), timestamp)

  def testUtcNow(self):
    datetime_tz.localtz_set("Australia/Sydney")

    d = datetime_tz.datetime_tz.utcnow()

    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo, pytz.utc)

  def testNow(self):
    datetime_tz.localtz_set("Australia/Sydney")

    d = datetime_tz.datetime_tz.now()

    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, pytz.timezone("Australia/Sydney").zone)

  def testFromOrdinal(self):
    try:
      d = datetime_tz.datetime_tz.fromordinal(1)
      str(d)
      self.assert_(False)
    except SyntaxError:
      pass

if __name__ == "__main__":
  unittest.main()
