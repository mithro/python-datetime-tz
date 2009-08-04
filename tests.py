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
        filename = os.path.join(os.path.dirname(__file__),
                                "test_localtime_sydney")
        return file(filename)
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
    # Create with the local timezone
    datetime_tz.localtz_set(pytz.utc)
    d0 = datetime_tz.datetime_tz(2008, 10, 1)
    self.assert_(isinstance(d0, datetime_tz.datetime_tz))
    self.assertEqual(d0.tzinfo, pytz.utc)

    # Creation with string timezone
    d1 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo="UTC")
    self.assert_(isinstance(d1, datetime_tz.datetime_tz))
    self.assertEqual(d1.tzinfo, pytz.utc)

    # Creation with tzinfo object
    d2 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo=pytz.utc)
    self.assert_(isinstance(d2, datetime_tz.datetime_tz))
    self.assertEqual(d1.tzinfo, pytz.utc)

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

    d7 = datetime_tz.datetime_tz(d6, "US/Pacific")
    self.assert_(isinstance(d7, datetime_tz.datetime_tz))
    self.assertEqual(d7.tzinfo, pytz.timezone("US/Pacific"))

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

    try:
      import functools
      # Make sure the wrapped functions still look like the original functions
      self.assertEqual(dreplace.replace.__name__,
                       datetime.datetime.replace.__name__)
      self.assertEqual(dreplace.replace.__doc__,
                       datetime.datetime.replace.__doc__)
    except ImportError:
      pass

    try:
      dreplace = datetime_tz.datetime_tz.now()
      dreplace = dreplace.replace(days=1)

      self.assert_(False)

    except TypeError:
      pass

  def testUtcFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.utcfromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo, pytz.utc)
      self.assertEqual(d.totimestamp(), timestamp)

  def testFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.fromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo.zone, pytz.timezone("US/Pacific").zone)
      self.assertEqual(d.totimestamp(), timestamp)

  def testUtcNow(self):
    datetime_tz.localtz_set("US/Pacific")

    d = datetime_tz.datetime_tz.utcnow()

    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo, pytz.utc)

  def testAsDate(self):
    d = datetime_tz.datetime_tz.now()

    self.assert_(isinstance(d, datetime.date))

  def testConvert(self):
    d = datetime_tz.datetime_tz(2009, 5, 1, 16, 12, 10)

    d_datetime = d.asdatetime()
    self.assert_(isinstance(d_datetime, datetime.datetime))
    self.assert_(not isinstance(d_datetime, datetime_tz.datetime_tz))
    self.assertEqual(d_datetime, datetime.datetime(2009, 5, 1, 16, 12, 10))

    d_date = d.asdate()
    self.assert_(isinstance(d_date, datetime.date))
    self.assert_(not isinstance(d_date, datetime.datetime))
    self.assertEqual(d_date, datetime.date(2009, 5, 1))

  def testNow(self):
    datetime_tz.localtz_set("US/Pacific")

    d = datetime_tz.datetime_tz.now()

    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, pytz.timezone("US/Pacific").zone)

    tz = pytz.timezone("Australia/Sydney")
    d = datetime_tz.datetime_tz.now(tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)


  def testFromOrdinal(self):
    try:
      datetime_tz.datetime_tz.fromordinal(1)
      self.assert_(False)
    except SyntaxError:
      pass

  def testSmartParse(self):
    datetime_tz.localtz_set("Australia/Sydney")

    tz = pytz.timezone("US/Pacific")
    now = datetime_tz.datetime_tz(2008, 12, 5, tzinfo=tz)
    tommorrow = now+datetime.timedelta(days=1)

    mocked = MockMe()

    @staticmethod
    def now_fake(tzinfo):
      if tz is tzinfo:
        return now
      else:
        assert False
    mocked("datetime_tz.datetime_tz.now", now_fake)

    d = datetime_tz.datetime_tz.smartparse("now", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("today", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertEqual(d.tzinfo.zone, tz.zone)

    # test that it's not case sensitive
    d = datetime_tz.datetime_tz.smartparse("ToDay", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("NOW", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("yesterday", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("tommorrow", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, tommorrow)
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("a second ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1 second ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 seconds ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1 minute ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(minutes=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 minutes ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(minutes=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1 hour ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 hours ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 days ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 days 5 hours ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2, hours=5))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 days and a hour ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2, hours=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("4 daYs AND A SECond aGO", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=4, seconds=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1 day and a hour ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1d 2h ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    # FIXME: These below should actually test the equivalence
    d = datetime_tz.datetime_tz.smartparse("start of today", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("start of tommorrow", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d,
        tommorrow.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("start of yesterday", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of today", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of tommorrow", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d,
        tommorrow.replace(hour=23, minute=59, second=59, microsecond=999999))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of yesterday", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    # FIXME: These above should actually test the equivalence

    mocked.tearDown()

    toparse = datetime_tz.datetime_tz(2008, 12, 5)
    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y/%m/%d"))
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y-%m-%d"))
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y%m%d"))
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(
        toparse.strftime("start of %d, %B %Y"))
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d,
        toparse.replace(hour=0,minute=0,second=0,microsecond=0))

    toparse = datetime_tz.datetime_tz(2008, 12, 5, tzinfo=tz)
    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y/%m/%d"), tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y-%m-%d"), tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y%m%d"), tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(
        toparse.strftime("start of %d, %B %Y"), tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    self.assertEqual(d,
        toparse.replace(hour=0,minute=0,second=0,microsecond=0))


class TestIterate(unittest.TestCase):
  def testBetween(self):
    iterate = datetime_tz.iterate

    tz = pytz.utc
    start = datetime_tz.datetime_tz.smartparse("2008/05/12 11:45", tz)
    end = datetime_tz.datetime_tz.smartparse("2008/05/16 11:46", tz)

    result = []
    for dt in iterate.between(start, datetime_tz.timedelta(days=1), end):
      result.append(dt.strftime("%Y/%m/%d %H:%M"))

    self.assertEqual(result, ["2008/05/12 11:45", "2008/05/13 11:45",
                              "2008/05/14 11:45", "2008/05/15 11:45",
                              "2008/05/16 11:45"])

    start = datetime_tz.datetime_tz.smartparse("2008/05/12 11:45", tz)
    end = datetime_tz.datetime_tz.smartparse("2008/05/16 11:45", tz)

    result = []
    for dt in iterate.between(start, datetime_tz.timedelta(days=1), end):
      result.append(dt.strftime("%Y/%m/%d %H:%M"))

    self.assertEqual(result, ["2008/05/12 11:45", "2008/05/13 11:45",
                              "2008/05/14 11:45", "2008/05/15 11:45"])

  def testDays(self):
    iterate = datetime_tz.iterate

    tz = pytz.utc
    start = datetime_tz.datetime_tz.smartparse("2008/05/12 11:45", tz)
    end = datetime_tz.datetime_tz.smartparse("2008/05/16 11:46", tz)

    result = []
    for dt in iterate.days(start, end):
      result.append(dt.strftime("%Y/%m/%d %H:%M"))

    self.assertEqual(result, ["2008/05/12 11:45", "2008/05/13 11:45",
                              "2008/05/14 11:45", "2008/05/15 11:45",
                              "2008/05/16 11:45"])

    start = datetime_tz.datetime_tz.smartparse("2008/05/12 11:45", tz)
    end = datetime_tz.datetime_tz.smartparse("2008/05/16 11:45", tz)

    result = []
    for dt in iterate.days(start, end):
      result.append(dt.strftime("%Y/%m/%d %H:%M"))

    self.assertEqual(result, ["2008/05/12 11:45", "2008/05/13 11:45",
                              "2008/05/14 11:45", "2008/05/15 11:45"])


if __name__ == "__main__":
  unittest.main()
