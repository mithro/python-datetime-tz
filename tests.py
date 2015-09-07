#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 et sts=2 ai:
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
#

# Disable the protected method member warning as we are trying to test them!
# pylint: disable=protected-access

# Disable the bad name warnings as tests need to start with test in lowercase.
# pylint: disable=invalid-name

# Disable the exception does nothing, as we want to test exceptions.
# pylint: disable=pointless-except

# Disable the missing docstrings as test methods are 'self documenting'.
# pylint: disable=missing-docstring

# Disable the override inbuilt, because that is exactly what we want to do.
# pylint: disable=redefined-builtin

# Disable complaints about not using datelibe.CreateDatetime
# pylint: disable=g-tzinfo-datetime

"""Tests for the datetime_tz module."""

__author__ = "tansell@google.com (Tim Ansell)"

import copy
import ctypes
import datetime
import itertools
import os
import random
import sys
import unittest
import warnings

import dateutil
import dateutil.parser
import pytz

import datetime_tz
# To test these, we still import them
from datetime_tz import detect_windows
from datetime_tz import update_win32tz_map

try:
  # pylint: disable=g-import-not-at-top
  import win32timezone
except ImportError:
  win32timezone = None

try:
  # pylint: disable=g-import-not-at-top,unused-import
  import __builtin__ as builtins
except ImportError:
  # pylint: disable=g-import-not-at-top,unused-import
  import builtins

try:
  # pylint: disable=g-import-not-at-top
  from StringIO import StringIO
except ImportError:
  # pylint: disable=g-import-not-at-top
  from io import StringIO

try:
  xrange
except NameError:
  xrange = range


FMT = "%Y-%m-%d %H:%M:%S %Z%z"


# Older versions of pytz only have AmbiguousTimeError, while newer versions
# throw NonExistentTimeError.
if not hasattr(pytz, "NonExistentTimeError"):
  pytz.NonExistentTimeError = pytz.AmbiguousTimeError


class MockMe(object):
  """Simple class to handle saving/restoring of mocked values."""

  def __init__(self):
    self.mocked = {}

  # pylint: disable=unused-argument,exec-used,eval-used
  def __call__(self, tomock, mockwith):
    if tomock not in self.mocked:
      self.mocked[tomock] = eval(tomock)
    exec("%s = mockwith" % tomock)

  # pylint: disable=unused-variable,exec-used
  def tearDown(self):
    for tomock, tounmock in self.mocked.items():
      exec("%s = tounmock" % tomock)


if sys.platform != "win32":
  os_timestamp_limits = (-100000000, -1, 0, 1, 1233300000)
else:
  os_timestamp_limits = (0, 1, 744018)


class TestTimeZoneBase(unittest.TestCase):

  TEST_YEARS = (1950, 1994, 2019)
  TEST_MONTHS = (2, 6, 11)
  TEST_DAYS = (1, 5, 28)
  TEST_HOURS = (0, 1, 2, 3, 23)
  TEST_MINUTES = (0, 59)
  TEST_SECONDS = (0, 59)
  TEST_POINTS = list(itertools.product(
      TEST_YEARS, TEST_MONTHS, TEST_DAYS, TEST_HOURS,
      TEST_MINUTES, TEST_SECONDS))

  def assertTimezoneEqual(self, actual, expected):
    # For UTC we check actual identity
    if expected is pytz.utc:
      self.assertTrue(pytz.utc is actual)

    # For very simple timezones, we assert the timezones are equal.
    elif isinstance(expected, pytz._FixedOffset):
      self.assertEqual(expected, actual)

    # Otherwise we have to normalize the timezones to a set of given dates and
    # compare the objects.
    elif isinstance(expected, datetime.tzinfo):
      self.assertTrue(isinstance(actual, datetime.tzinfo))
      self.assertEqual(expected.zone, actual.zone)

      for args in self.TEST_POINTS:
        d = datetime.datetime(*args)

        expected_d = expected.localize(d)
        actual_d = actual.localize(d)

        self.assertEqual(expected_d, actual_d)
        self.assertEqual(expected_d.tzinfo, actual_d.tzinfo)
    else:
      raise SystemError(
          "assertTimezoneEqual doesn't deal with an expected value of %s (%r)"
          % (expected, expected))


class TestTimeZoneBaseTest(TestTimeZoneBase):

  def testAssertTimezoneCheckNumber(self):
    self.assertTrue(len(self.TEST_POINTS) < 600)

  def testAssertTimezoneEqualUTC(self):
    self.assertTimezoneEqual(pytz.utc, pytz.utc)
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.timezone("Australia/Sydney"), pytz.utc)
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.FixedOffset(300), pytz.utc)

  def testAssertTimezoneEqualFixed(self):
    self.assertTimezoneEqual(
        pytz.FixedOffset(300), pytz.FixedOffset(300))
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual,
        pytz.FixedOffset(-300), pytz.FixedOffset(300))
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual,
        pytz.FixedOffset(400), pytz.FixedOffset(300))
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual,
        pytz.timezone("Australia/Sydney"), pytz.FixedOffset(300))
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual,
        pytz.utc, pytz.FixedOffset(300))

  def testAssertTimezoneEqualOther(self):
    self.assertTimezoneEqual(
        pytz.timezone("Australia/Sydney"), pytz.timezone("Australia/Sydney"))
    self.assertTimezoneEqual(
        pytz.timezone("US/Pacific"), pytz.timezone("US/Pacific"))

    test_tzinfo = pytz.timezone("Australia/Sydney")
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.FixedOffset(-300), test_tzinfo)
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.FixedOffset(400), test_tzinfo)
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.timezone("US/Pacific"), test_tzinfo)
    self.assertRaises(
        AssertionError,
        self.assertTimezoneEqual, pytz.utc, test_tzinfo)

    # Choose 100 random unix timestamps and run them through the assert
    # function.
    random.seed(1)
    unix_ts = random.sample(xrange(0, os_timestamp_limits[-1]*2), 50)
    unix_ts.sort()

    for timezone in ("Australia/Sydney", "US/Pacific", "Europe/Minsk"):
      tzinfo = pytz.timezone(timezone)
      for ts in unix_ts:
        d = datetime_tz.datetime_tz.utcfromtimestamp(ts).astimezone(tzinfo)
        self.assertTimezoneEqual(d.tzinfo, tzinfo)


class TestLocalTimezoneDetection(TestTimeZoneBase):

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
    self.assertTimezoneEqual(tzinfo, pytz.utc)

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
    def timezone_valid_fake(filename, mode="r", open=open):
      if filename == "/etc/timezone":
        return StringIO("Australia/Sydney")
      return open(filename, mode)

    self.mocked("builtins.open", timezone_valid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertTimezoneEqual(tzinfo, pytz.timezone("Australia/Sydney"))

    # Check that when /etc/timezone is invalid timezone
    def timezone_invalid_fake(filename, mode="r", open=open):
      if filename == "/etc/timezone":
        return StringIO("Invalid-Timezone")
      return open(filename, mode)

    self.mocked("builtins.open", timezone_invalid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(None, tzinfo)

    # Check that when /etc/timezone is random "binary" data
    def timezone_binary_fake(filename, mode="r", open=open):
      if filename == "/etc/timezone":
        return StringIO("\0\r\n\t\0\r\r\n\0")
      return open(filename, mode)

    self.mocked("builtins.open", timezone_binary_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(None, tzinfo)

  def testEtcLocaltimeMethodSingleMatch(self):
    if sys.platform == "win32":
      raise self.skipTest("/etc timezone method will never work on Windows")
    test_zonedata_sydney = os.path.join(
        os.path.dirname(__file__), "test_zonedata_sydney")
    f = open(test_zonedata_sydney, "rb")
    test_tzinfo_sydney = pytz.tzfile.build_tzinfo(
        "Australia/Sydney", f)
    f.close()

    def os_path_exists_fake(filename, os_path_exists=os.path.exists):
      if filename in (
          "/etc/localtime",
          "/usr/share/zoneinfo/right/Etc/UTC",
          "/usr/share/zoneinfo/right/Australia/Sydney",
          ):
        return True
      return os_path_exists(filename)
    self.mocked("os.path.exists", os_path_exists_fake)

    os_walk = os.walk
    def os_walk_fake(dirname, *args, **kw):
      if dirname in (
          "/usr/share/zoneinfo/posix",
          ):
        return [
            (dirname, ["Etc", "Australia"], []),
            (os.path.join(dirname, "Etc"), [], ["UTC"]),
            (os.path.join(dirname, "Australia"), [], ["Sydney", "Melbourne"]),
            ]
      return os_walk(dirname, *args, **kw)
    self.mocked("os.walk", os_walk_fake)

    def localtime_valid_fake(filename, mode="r", open=open):
      if filename == "/etc/localtime":
        filename = os.path.join(os.path.dirname(__file__),
                                localtime_file)
      if filename in (
          "/usr/share/zoneinfo/posix/Australia/Melbourne",
          "/usr/share/zoneinfo/posix/Australia/Sydney",
          ):
        filename = test_zonedata_sydney

      if filename in (
          "/usr/share/zoneinfo/posix/Etc/UTC",
          ):
        filename = os.path.join(os.path.dirname(__file__),
                                "test_zonedata_utc")
      return open(filename, mode)
    self.mocked("builtins.open", localtime_valid_fake)

    self.assertEqual(
        ["Australia/Melbourne", "Australia/Sydney", "Etc/UTC"],
        list(sorted(datetime_tz._load_local_tzinfo().keys())))

    # Test the case where single match in the local database which also exists
    # in the pytz database.
    localtime_file = "test_zonedata_utc"

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertTimezoneEqual(r, pytz.timezone("Etc/UTC"))

    # Test the case where multiple matches in the local database which also
    # exist in the pytz database.
    localtime_file = "test_zonedata_sydney"

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertTimezoneEqual(r, pytz.timezone("Australia/Melbourne"))

    # Test the case where multiple matches in the local database, but only one
    # is in pytz database.
    localtime_file = "test_zonedata_sydney"
    self.mocked("pytz.all_timezones", ["Australia/Sydney"])

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertTimezoneEqual(r, pytz.timezone("Australia/Sydney"))

    # Test the no matches case
    localtime_file = "test_zonedata_sydney"
    self.mocked("pytz.all_timezones", [])

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertTimezoneEqual(r, pytz.timezone("/etc/localtime"))
    # Make sure we can still use the datetime object
    # pylint: disable=expression-not-assigned
    datetime_tz.datetime_tz.now() + datetime.timedelta(days=60)

    # Test the case where /etc/localtime doesn't match anything in the local
    # database and nothing in pytz.
    localtime_file = "test_zonedata_utc"
    self.mocked("datetime_tz._load_local_tzinfo",
                lambda: {"Australia/Sydney": test_tzinfo_sydney})
    self.mocked("pytz.all_timezones", ["Australia/Sydney"])

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertTimezoneEqual(r, pytz.timezone("/etc/localtime"))
    # Make sure we can still use the datetime object
    # pylint: disable=expression-not-assigned
    datetime_tz.datetime_tz.now() + datetime.timedelta(days=60)

    # Test the case where there is no local database, so we fall back to
    # matching pytz database
    localtime_file = "test_zonedata_sydney"
    self.mocked("datetime_tz._load_local_tzinfo", lambda: {})
    self.mocked("pytz.all_timezones", ["Australia/Sydney"])
    self.mocked("datetime_tz._tzinfome", lambda x: test_tzinfo_sydney)

    r = datetime_tz._detect_timezone_etc_localtime()
    self.assertNotEqual(r.zone, "/etc/localtime")
    self.assertTimezoneEqual(r, test_tzinfo_sydney)

  def testPHPMethod(self):
    # FIXME: Actually test this method sometime in the future.
    pass

  def testWindowsTimezones(self):
    if sys.platform == "win32":
      self.assertNotEqual(detect_windows._detect_timezone_windows(), None)

    class kernel32_old(object):

      @staticmethod
      def GetTimeZoneInformation(tzi_byref):
        tzi = tzi_byref._obj
        tzi.bias = -120
        tzi.standard_name = "South Africa Standard Time"
        tzi.standard_start = detect_windows.SYSTEMTIME_c()
        tzi.standard_start.year = 0
        tzi.standard_start.month = 0
        tzi.standard_start.day_of_week = 0
        tzi.standard_start.day = 0
        tzi.standard_start.hour = 0
        tzi.standard_start.minute = 0
        tzi.standard_start.second = 0
        tzi.standard_start.millisecond = 0
        tzi.standard_bias = 0
        tzi.daylight_name = "South Africa Daylight Time"
        tzi.daylight_bias = -60
        tzi.daylight_start.year = 0
        tzi.daylight_start.month = 0
        tzi.daylight_start.day_of_week = 0
        tzi.daylight_start.day = 0
        tzi.daylight_start.hour = 0
        tzi.daylight_start.minute = 0
        tzi.daylight_start.second = 0
        tzi.daylight_start.millisecond = 0
        return 0

    class _kernel32(kernel32_old):

      @staticmethod
      def GetDynamicTimeZoneInformation(tzi_byref):
        kernel32_old.GetTimeZoneInformation(tzi_byref)
        tzi = tzi_byref._obj
        tzi.key_name = "South Africa Standard Time"
        tzi.dynamic_daylight_time_disabled = False

    class windll(object):
      kernel32 = _kernel32

    if hasattr(ctypes, "windll"):
      self.mocked("ctypes.windll", windll)
    else:
      ctypes.windll = windll

    self.assertTimezoneEqual(
        detect_windows._detect_timezone_windows(),
        pytz.timezone("Etc/GMT-2"))

    windll.kernel32 = kernel32_old
    if win32timezone is None:
      self.assertEqual(detect_windows._detect_timezone_windows(), None)
    else:
      self.assertTimezoneEqual(
          detect_windows._detect_timezone_windows(),
          pytz.timezone("Etc/GMT-2"))

    class _win32timezone_mock(object):

      class TimeZoneInfo(object):

        @staticmethod
        def _get_indexed_time_zone_keys(*unused_args, **unused_kwargs):
          return {"South Africa Standard Time": "AUS Eastern Standard Time"}

    self.mocked("detect_windows.win32timezone", _win32timezone_mock)
    self.assertTimezoneEqual(
        detect_windows._detect_timezone_windows(),
        pytz.timezone("Australia/Sydney"))


class TestDatetimeTZ(TestTimeZoneBase):

  def setUp(self):
    # All tests are assumed to be in Australia/Sydney unless otherwise
    # specified.
    datetime_tz.localtz_set("Australia/Sydney")
    self.mocked = MockMe()

  def tearDown(self):
    self.mocked.tearDown()

  def testPeopleRants(self):
    """This test contains various things which people rant about."""

    # Tests some of the pitfuls discussed at
    # http://www.enricozini.org/2009/debian/using-python-datetime/
    ############################################################################

    # That's right, the datetime object created by a call to datetime.datetime
    # constructor now seems to think that Finland uses the ancient "Helsinki
    # Mean Time" which was obsoleted in the 1920s.
    #
    # Well not anymore!
    eurhel = pytz.timezone("Europe/Helsinki")
    a = datetime_tz.datetime_tz(2008, 6, 23, 18, 2, 31, 101025, eurhel)
    self.assertEqual(repr(a),
                     "datetime_tz(2008, 6, 23, 18, 2, 31, 101025,"
                     " tzinfo=<DstTzInfo 'Europe/Helsinki' EEST+3:00:00 DST>)")

    # Timezone-aware datetime objects have other bugs: for example, they fail to
    # compute Unix timestamps correctly. The following example shows two
    # timezone-aware objects that represent the same instant but produce two
    # different timestamps.
    #
    # Well not anymore!
    utc = pytz.timezone("UTC")
    a = datetime_tz.datetime_tz(2008, 7, 6, 5, 4, 3, tzinfo=utc)
    self.assertEqual(str(a), "2008-07-06 05:04:03+00:00")
    self.assertEqual(a.totimestamp(), 1215320643.0)
    # FIXME(tansell): %s is effected by the TZ environment value.
    # self.assertEqual(a.strftime("%s"), "1215284643")

    italy = pytz.timezone("Europe/Rome")
    b = a.astimezone(italy)
    self.assertEqual(str(b), "2008-07-06 07:04:03+02:00")
    self.assertEqual(b.totimestamp(), 1215320643.0)
    # self.assertNotEqual(b.strftime("%s"), "1215284643")

    # TODO(tansell): We still discard timezone information in strptime...
    # datetime.strptime silently throws away all timezone information. If you
    # look very closely, it even says so in its documentation

  def testCreation(self):
    # Create with the local timezone
    datetime_tz.localtz_set(pytz.utc)
    d0 = datetime_tz.datetime_tz(2008, 10, 1)
    self.assertTrue(isinstance(d0, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d0.tzinfo, pytz.utc)

    # Creation with string timezone
    d1 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo="UTC")
    self.assertTrue(isinstance(d1, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d1.tzinfo, pytz.utc)

    # Creation with tzinfo object
    d2 = datetime_tz.datetime_tz(2008, 10, 1, tzinfo=pytz.utc)
    self.assertTrue(isinstance(d2, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d1.tzinfo, pytz.utc)

    # Creation from a datetime_tz object
    d3 = datetime_tz.datetime_tz(d0)
    self.assertTrue(isinstance(d3, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d0.tzinfo, d3.tzinfo)
    self.assertEqual(d0, d3)
    self.assertFalse(d0 is d3)

    d3 = datetime_tz.datetime_tz(d1)
    self.assertTrue(isinstance(d3, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d1.tzinfo, d3.tzinfo)
    self.assertEqual(d1, d3)
    self.assertFalse(d1 is d3)

    d3 = datetime_tz.datetime_tz(d2)
    self.assertTrue(isinstance(d3, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d2.tzinfo, d3.tzinfo)
    self.assertEqual(d2, d3)
    self.assertFalse(d2 is d3)

    # Creation from an already localized datetime object
    d4 = datetime.datetime(2008, 10, 1, 10, 10)
    d4 = pytz.timezone("Australia/Sydney").localize(d4)
    d5 = datetime_tz.datetime_tz(d4)
    self.assertTrue(isinstance(d3, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d4.tzinfo, d5.tzinfo)

    # Creation from a naive datetime object not in DST
    d6 = datetime.datetime(2008, 12, 5)
    try:
      d7 = datetime_tz.datetime_tz(d6)
      self.fail("Was able to create from a naive datetime without a timezone")
    except TypeError:
      pass

    d7 = datetime_tz.datetime_tz(d6, "US/Pacific")
    self.assertTrue(isinstance(d7, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d7.tzinfo, pytz.timezone("US/Pacific"))
    self.assertEqual(d7.tzinfo._dst, datetime.timedelta(0))

    # Creation from a naive datetime object in DST
    d6 = datetime.datetime(2008, 7, 13)
    try:
      d7 = datetime_tz.datetime_tz(d6)
      self.fail("Was able to create from a naive datetime without a timezone")
    except TypeError:
      pass

    d7 = datetime_tz.datetime_tz(d6, "US/Pacific")

    self.assertTrue(isinstance(d7, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d7.tzinfo, pytz.timezone("US/Pacific"))
    self.assertEqual(d7.tzinfo._dst, datetime.timedelta(0, 3600))

  def testBadDates(self):
    # For example, 1:30am on 27th Oct 2002 happened twice in the US/Eastern
    # timezone when the clocks where put back at the end of Daylight Savings
    # Time.
    # This could be 2002-10-27 01:30:00 EDT-0400
    #            or 2002-10-27 01:30:00 EST-0500
    loc_dt = datetime.datetime(2002, 10, 27, 1, 30, 00)
    self.assertRaises(pytz.AmbiguousTimeError, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"))

    # Check we can use is_dst to disambiguate.
    loc_dt = datetime.datetime(2002, 10, 27, 1, 30, 00)

    dt2 = datetime_tz.datetime_tz(
        loc_dt, pytz.timezone("US/Eastern"), is_dst=False)
    self.assertEqual(dt2.strftime(FMT), "2002-10-27 01:30:00 EST-0500")

    dt1 = datetime_tz.datetime_tz(
        loc_dt, pytz.timezone("US/Eastern"), is_dst=True)
    self.assertEqual(dt1.strftime(FMT), "2002-10-27 01:30:00 EDT-0400")

    # Similarly, 2:30am on 7th April 2002 never happened at all in the
    # US/Eastern timezone, as the clock where put forward at 2:00am skipping the
    # entire hour.
    loc_dt = datetime.datetime(2002, 4, 7, 2, 30, 00)

    raiseme = (pytz.AmbiguousTimeError, pytz.NonExistentTimeError)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"))
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=True)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=False)

    raiseme = (pytz.AmbiguousTimeError, pytz.NonExistentTimeError)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"))
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=True)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=False)

    # But make sure the cases still work when it"s "now"
    @staticmethod
    def utcnowmockedt():
      return datetime_tz.datetime_tz(2002, 10, 27, 5, 30, tzinfo=pytz.utc)

    datetime_tz.localtz_set("US/Eastern")
    self.mocked("datetime_tz.datetime_tz.utcnow", utcnowmockedt)
    self.assertEqual(datetime_tz.datetime_tz.now().strftime(FMT),
                     "2002-10-27 01:30:00 EDT-0400")

    @staticmethod
    def utcnowmockest():
      return datetime_tz.datetime_tz(2002, 10, 27, 6, 30, tzinfo=pytz.utc)

    datetime_tz.localtz_set("US/Eastern")
    self.mocked("datetime_tz.datetime_tz.utcnow", utcnowmockest)
    self.assertEqual(datetime_tz.datetime_tz.now().strftime(FMT),
                     "2002-10-27 01:30:00 EST-0500")

  def disabledTestBadDates2(self):
    # FIXME(tansell): Make these tests pass
    raiseme = (pytz.AmbiguousTimeError, pytz.NonExistentTimeError)

    # 27th is not DST
    loc_dt = datetime.datetime(2002, 10, 27, 1, 10, 00)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=True)

    # 25th is DST
    loc_dt = datetime.datetime(2002, 10, 25, 1, 10, 00)
    self.assertRaises(raiseme, datetime_tz.datetime_tz,
                      loc_dt, pytz.timezone("US/Eastern"), is_dst=False)

  def testAroundDst(self):
    # Testing going backwards into daylight savings
    utc_dt = datetime_tz.datetime_tz(2002, 10, 27, 6, 10, 0, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-10-27 01:10:00 EST-0500")

    before = loc_dt - datetime_tz.timedelta(minutes=10)
    self.assertEqual(before.strftime(FMT), "2002-10-27 01:00:00 EST-0500")

    before = loc_dt - datetime_tz.timedelta(minutes=20)
    self.assertEqual(before.strftime(FMT), "2002-10-27 01:50:00 EDT-0400")

    after = loc_dt + datetime_tz.timedelta(minutes=10)
    self.assertEqual(after.strftime(FMT), "2002-10-27 01:20:00 EST-0500")

    # Testing going forwards out of daylight savings
    utc_dt = datetime_tz.datetime_tz(2002, 10, 27, 5, 50, 0, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-10-27 01:50:00 EDT-0400")

    after = loc_dt + datetime_tz.timedelta(minutes=10)
    self.assertEqual(after.strftime(FMT), "2002-10-27 01:00:00 EST-0500")

    after = loc_dt + datetime_tz.timedelta(minutes=20)
    self.assertEqual(after.strftime(FMT), "2002-10-27 01:10:00 EST-0500")

    before = loc_dt - datetime_tz.timedelta(minutes=10)
    self.assertEqual(before.strftime(FMT), "2002-10-27 01:40:00 EDT-0400")

    # Test going backwards out of daylight savings
    utc_dt = datetime_tz.datetime_tz(2002, 4, 7, 7, 10, 00, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-04-07 03:10:00 EDT-0400")

    before = loc_dt - datetime_tz.timedelta(minutes=10)
    self.assertEqual(before.strftime(FMT), "2002-04-07 03:00:00 EDT-0400")

    before = loc_dt - datetime_tz.timedelta(minutes=20)
    self.assertEqual(before.strftime(FMT), "2002-04-07 01:50:00 EST-0500")

    after = loc_dt + datetime_tz.timedelta(minutes=10)
    self.assertEqual(after.strftime(FMT), "2002-04-07 03:20:00 EDT-0400")

    # Test going forwards into daylight savings
    utc_dt = datetime_tz.datetime_tz(2002, 4, 7, 6, 50, 00, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-04-07 01:50:00 EST-0500")

    after = loc_dt + datetime_tz.timedelta(minutes=10)
    self.assertEqual(after.strftime(FMT), "2002-04-07 03:00:00 EDT-0400")

    after = loc_dt + datetime_tz.timedelta(minutes=20)
    self.assertEqual(after.strftime(FMT), "2002-04-07 03:10:00 EDT-0400")

    before = loc_dt - datetime_tz.timedelta(minutes=10)
    self.assertEqual(before.strftime(FMT), "2002-04-07 01:40:00 EST-0500")

  def testOperations(self):
    dadd = datetime_tz.datetime_tz.now() + datetime.timedelta(days=1)

    dradd = datetime_tz.datetime_tz.now()
    dradd += datetime.timedelta(days=1)

    dsub = datetime_tz.datetime_tz.now() - datetime.timedelta(days=1)

    drsub = datetime_tz.datetime_tz.now()
    drsub -= datetime.timedelta(days=1)

    dreplace = datetime_tz.datetime_tz.now()
    dreplace = dreplace.replace(day=1)

    self.assertTrue(isinstance(dadd, datetime_tz.datetime_tz))
    self.assertTrue(isinstance(dsub, datetime_tz.datetime_tz))
    self.assertTrue(isinstance(dradd, datetime_tz.datetime_tz))
    self.assertTrue(isinstance(drsub, datetime_tz.datetime_tz))
    self.assertTrue(isinstance(dreplace, datetime_tz.datetime_tz))

    try:
      dreplace = datetime_tz.datetime_tz.now()
      dreplace = dreplace.replace(days=1)

      self.assertTrue(False)
    except TypeError:
      pass

    try:
      dreplace.replace(tzinfo=None)

      self.fail("Was able to replace tzinfo with none!")
    except TypeError:
      pass

  def testUtcFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in os_timestamp_limits:
      d = datetime_tz.datetime_tz.utcfromtimestamp(timestamp)

      self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
      self.assertTimezoneEqual(d.tzinfo, pytz.utc)
      self.assertEqual(d.totimestamp(), timestamp)

  def testFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in os_timestamp_limits:
      d = datetime_tz.datetime_tz.fromtimestamp(timestamp)

      self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
      self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Pacific"))
      self.assertEqual(d.totimestamp(), timestamp)

      # Changing the timezone should have no effect on the timestamp produced.
      d = d.astimezone("UTC")
      self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
      self.assertTimezoneEqual(d.tzinfo, pytz.utc)
      self.assertEqual(d.totimestamp(), timestamp)

  def testUtcNow(self):
    datetime_tz.localtz_set("US/Pacific")

    d = datetime_tz.datetime_tz.utcnow()

    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, pytz.utc)

  def testAsDate(self):
    d = datetime_tz.datetime_tz.now()

    self.assertTrue(isinstance(d, datetime.date))

  def testConvert(self):
    d = datetime_tz.datetime_tz(2009, 5, 1, 16, 12, 10)

    d_datetime = d.asdatetime()
    self.assertTrue(isinstance(d_datetime, datetime.datetime))
    self.assertTrue(not isinstance(d_datetime, datetime_tz.datetime_tz))
    self.assertEqual(d_datetime, datetime.datetime(2009, 5, 1, 16, 12, 10))

    d_date = d.asdate()
    self.assertTrue(isinstance(d_date, datetime.date))
    self.assertTrue(not isinstance(d_date, datetime.datetime))
    self.assertEqual(d_date, datetime.date(2009, 5, 1))

  def testNow(self):
    datetime_tz.localtz_set("US/Pacific")

    d = datetime_tz.datetime_tz.now()

    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Pacific"))

    tz = pytz.timezone("Australia/Sydney")
    d = datetime_tz.datetime_tz.now(tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)

  def testFromOrdinal(self):
    try:
      datetime_tz.datetime_tz.fromordinal(1)
      self.fail("Was able to create a datetime_tz using fromordinal!")
    except SyntaxError:
      pass

  def testReplace(self):
    # Testing normal replace
    dt = datetime_tz.datetime_tz(
        2010, 3, 10, 17, 23, 26, 871430, "US/Pacific")

    replaced = dt.replace(hour=0, minute=0, second=0, microsecond=1)
    result = datetime_tz.datetime_tz(
        2010, 3, 10, 0, 0, 0, 1, "US/Pacific")
    self.assertEqual(result, replaced)

    replaced = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    result = datetime_tz.datetime_tz(
        2010, 3, 10, 0, 0, 0, 0, "US/Pacific")
    self.assertEqual(result, replaced)

    # Test replacing across daylight savings boundary
    dt = datetime_tz.datetime_tz(
        2010, 3, 14, 17, 23, 26, 871430, "US/Pacific")

    replaced = dt.replace(hour=0, minute=0, second=0, microsecond=1)
    result = datetime_tz.datetime_tz(
        2010, 3, 14, 0, 0, 0, 1, "US/Pacific")
    self.assertEqual(result, replaced)

    replaced = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    result = datetime_tz.datetime_tz(
        2010, 3, 14, 0, 0, 0, 0, "US/Pacific")
    self.assertEqual(result, replaced)

    # Test starting outside of DST
    utc_dt = datetime_tz.datetime_tz(2002, 10, 27, 6, 10, 0, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-10-27 01:10:00 EST-0500")

    # Since we don't start off in DST, so a replace should try and keep us out
    # of DST
    assert not loc_dt.is_dst

    replace = loc_dt.replace(hour=1)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:10:00 EST-0500")

    replace = loc_dt.replace(is_dst=False)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:10:00 EST-0500")

    replace = loc_dt.replace(minute=50, second=0, microsecond=0)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:50:00 EST-0500")

    # Unless we are also replacing the DST flag
    replace = loc_dt.replace(hour=1, is_dst=True)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:10:00 EDT-0400")

    replace = loc_dt.replace(is_dst=True)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:10:00 EDT-0400")

    replace = loc_dt.replace(minute=50, second=0, microsecond=0, is_dst=True)
    self.assertEqual(replace.strftime(FMT), "2002-10-27 01:50:00 EDT-0400")

    # But if we go too far, replace should still do the right thing
    replace = loc_dt.replace(day=26)
    self.assertEqual(replace.strftime(FMT), "2002-10-26 01:10:00 EDT-0400")

    replace = loc_dt.replace(day=28)
    self.assertEqual(replace.strftime(FMT), "2002-10-28 01:10:00 EST-0500")

    # FIXME(tansell): Make these test work.
    # self.assertRaises(pytz.NonExistentTimeError, loc_dt.replace,
    #                   day=26, is_dst=False)
    # self.assertRaises(pytz.NonExistentTimeError, loc_dt.replace,
    #                   day=28, is_dst=True)

    # Testing starting in DST
    utc_dt = datetime_tz.datetime_tz(2002, 4, 7, 7, 10, 00, tzinfo=pytz.utc)
    loc_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
    self.assertEqual(loc_dt.strftime(FMT), "2002-04-07 03:10:00 EDT-0400")

    # Since we start in DST, so a replace should try and keep us in DST.
    assert loc_dt.is_dst

    replace = loc_dt.replace(minute=0, second=0, microsecond=0)
    self.assertEqual(replace.strftime(FMT), "2002-04-07 03:00:00 EDT-0400")

    # 2:30 doesn't actually exist
    self.assertRaises(pytz.NonExistentTimeError, loc_dt.replace,
                      hour=2, minute=30, second=0, microsecond=0)

  def testSmartParse(self):
    datetime_tz.localtz_set("Australia/Sydney")

    tz = pytz.timezone("US/Pacific")
    now = datetime_tz.datetime_tz(2008, 12, 5, tzinfo=tz)
    tomorrow = now+datetime.timedelta(days=1)

    @staticmethod
    def now_fake(tzinfo):
      if tz is tzinfo:
        return now
      else:
        assert False
    self.mocked("datetime_tz.datetime_tz.now", now_fake)

    d = datetime_tz.datetime_tz.smartparse("now", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("today", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertTimezoneEqual(d.tzinfo, tz)

    # test that it's not case sensitive
    d = datetime_tz.datetime_tz.smartparse("ToDay", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("NOW", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now)
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("yesterday", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("tomorrow", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, tomorrow)
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("a second ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1 second ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 seconds ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(seconds=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1 minute ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(minutes=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 minutes ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(minutes=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1 hour ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 hours ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 days ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 days 5 hours ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2, hours=5))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 days and a hour ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=2, hours=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("4 daYs AND A SECond aGO", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=4, seconds=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1 day and a hour ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("an hour and a day ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=1))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1d 2h ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2h5m32s ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=2, minutes=5, seconds=32))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("1y 2 month ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=2))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("2 months and 3m ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        months=2, minutes=3))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("3m4months1y ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=4, minutes=3))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("3m4months and 1y ago", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=4, minutes=3))
    self.assertTimezoneEqual(d.tzinfo, tz)

    self.assertRaises(ValueError,
                      datetime_tz.datetime_tz.smartparse,
                      "5 billion years ago", tz)

    self.assertRaises(ValueError,
                      datetime_tz.datetime_tz.smartparse,
                      "5 ago", tz)

    # FIXME: These below should actually test the equivalence
    d = datetime_tz.datetime_tz.smartparse("start of today", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("start of tomorrow", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(
        d, tomorrow.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("start of yesterday", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("end of today", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("end of tomorrow", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(
        d, tomorrow.replace(
            hour=23, minute=59, second=59, microsecond=999999))
    self.assertTimezoneEqual(d.tzinfo, tz)

    d = datetime_tz.datetime_tz.smartparse("end of yesterday", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)
    # FIXME: These above should actually test the equivalence

    self.mocked.tearDown()

    # Test datetime string with timezone information,
    # also provide timezone argument
    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00-05:00", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.FixedOffset(-300))
    self.assertEqual(d, pytz.FixedOffset(-300).localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00+0800", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00+08:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.FixedOffset(480))
    self.assertEqual(d, pytz.FixedOffset(480).localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST-05:00", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))
    self.assertEqual(d, pytz.timezone("US/Eastern").localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 EST 2009", tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))
    self.assertEqual(d, pytz.timezone("US/Eastern").localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    # Test datetime string with timezone information,
    # no more timezone argument
    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00-05:00")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.FixedOffset(-300))
    self.assertEqual(d, pytz.FixedOffset(-300).localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00+0800")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00+08:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.FixedOffset(480))
    self.assertEqual(d, pytz.FixedOffset(480).localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))
    self.assertEqual(d, pytz.timezone("US/Eastern").localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST-05:00")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))
    self.assertEqual(d, pytz.timezone("US/Eastern").localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 EST 2009")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))
    self.assertEqual(d, pytz.timezone("US/Eastern").localize(
        datetime.datetime(2009, 11, 9, 23, 0, 0)))

    # UTC, nice and easy
    d = datetime_tz.datetime_tz.smartparse("Tue Jul 03 06:00:01 UTC 2010")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2010-07-03 06:00:01+00:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.utc)

    # Try Pacific standard time
    d = datetime_tz.datetime_tz.smartparse("2002-10-27 01:20:00 EST")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2002-10-27 01:20:00-05:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    d = datetime_tz.datetime_tz.smartparse("2002-10-27 01:20:00 EDT")
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2002-10-27 01:20:00-04:00")
    self.assertTimezoneEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    # Using Oslon timezones means you end up with ambigious dates.
    #   2002-10-27 01:30:00 US/Eastern
    #  could be either,
    #   2002-10-27 01:30:00 EDT-0400
    #   2002-10-27 01:30:00 EST-0500
    try:
      d = datetime_tz.datetime_tz.smartparse(
          "Tue Jul 03 06:00:01 US/Pacific 2010")
      self.assertTrue(False)
    except ValueError:
      pass

    # Make sure we get exceptions when invalid timezones are used.
    try:
      d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 Random 2009")
      self.assertTrue(False)
    except ValueError:
      pass

    try:
      d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 XXX 2009")
      self.assertTrue(False)
    except ValueError:
      pass

    ###########################################################################
    toparse = datetime_tz.datetime_tz(2008, 6, 5)
    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y/%m/%d"))
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y-%m-%d"))
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y%m%d"))
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(
        toparse.strftime("start of %d, %B %Y"))
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(
        d, toparse.replace(hour=0, minute=0, second=0, microsecond=0))

    toparse = datetime_tz.datetime_tz(2008, 12, 5, tzinfo=tz)
    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y/%m/%d"), tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y-%m-%d"), tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(toparse.strftime("%Y%m%d"), tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)
    self.assertEqual(d, toparse)

    d = datetime_tz.datetime_tz.smartparse(
        toparse.strftime("start of %d, %B %Y"), tz)
    self.assertTrue(isinstance(d, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(d.tzinfo, tz)
    self.assertEqual(
        d, toparse.replace(hour=0, minute=0, second=0, microsecond=0))

  def testLocalize(self):
    # Test naive to sydney and utc
    naive_dt = datetime.datetime(2010, 7, 11, 12, 34, 54)
    ldt = datetime_tz.localize(naive_dt)
    self.assertTrue(isinstance(ldt, datetime_tz.datetime_tz))
    self.assertEqual(ldt.year, 2010)
    self.assertEqual(ldt.month, 7)
    self.assertEqual(ldt.day, 11)
    self.assertEqual(ldt.hour, 12)
    self.assertEqual(ldt.minute, 34)
    self.assertEqual(ldt.second, 54)
    self.assertTimezoneEqual(ldt.tzinfo, pytz.timezone("Australia/Sydney"))
    datetime_tz.localtz_set("UTC")
    ldt = datetime_tz.localize(naive_dt)
    self.assertTimezoneEqual(ldt.tzinfo, pytz.UTC)

    # Test joburg to sydney
    datetime_tz.localtz_set("Australia/Sydney")
    joburg_dt = datetime_tz.datetime_tz(
        2010, 7, 11, 12, 34, 54, "Africa/Johannesburg")
    ldt = datetime_tz.localize(joburg_dt)
    self.assertTimezoneEqual(ldt.tzinfo, pytz.timezone("Australia/Sydney"))
    self.assertEqual(ldt.hour, 20)

    # Test aware datetime to datetime_tz
    utc_dt = datetime.datetime(2010, 7, 11, 12, 34, 54, tzinfo=pytz.utc)
    ldt = datetime_tz.localize(utc_dt)
    self.assertTrue(isinstance(ldt, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(ldt.tzinfo, pytz.timezone("Australia/Sydney"))
    self.assertEqual(ldt.hour, 22)

    # Test joburg not touched on no force_local
    joburg_dt = datetime.datetime(2010, 7, 11, 12, 34, 54, tzinfo=pytz.utc)
    ldt = datetime_tz.localize(joburg_dt, force_to_local=False)
    self.assertTrue(isinstance(ldt, datetime_tz.datetime_tz))
    self.assertTimezoneEqual(ldt.tzinfo, pytz.utc)
    self.assertEqual(ldt.hour, 12)

  def testLocalTzName(self):
    datetime_tz.localtz_set("UTC")
    self.assertEqual(datetime_tz.localtz_name(), "UTC")
    datetime_tz.localtz_set("Australia/Sydney")
    self.assertEqual(datetime_tz.localtz_name(), "Australia/Sydney")

  def testRequireTimezone(self):
    datetime_tz.require_timezone("Australia/Sydney")
    self.assertRaises(
        AssertionError, datetime_tz.require_timezone, "UTC")
    datetime_tz.localtz_set("UTC")
    datetime_tz.require_timezone("UTC")
    self.assertRaises(
        AssertionError, datetime_tz.require_timezone, "Australia/Sydney")
    datetime_tz.localtz_set("Australia/Sydney")

  def testGetNaive(self):
    # Test datetime_tz, naive datetime and timezoned datetime all produce naive
    naive_dt = datetime.datetime(2015, 7, 11, 12, 34, 54)
    dtz = datetime_tz.datetime_tz(2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    dtnz = datetime.datetime(
        2015, 7, 11, 12, 34, 54, tzinfo=pytz.timezone("Australia/Sydney"))

    self.assertEqual(naive_dt, datetime_tz.get_naive(naive_dt))
    self.assertEqual(naive_dt, datetime_tz.get_naive(dtz))
    self.assertEqual(naive_dt, datetime_tz.get_naive(dtnz))

  def testDateutilParseTzinfos(self):
    parsed_dt = dateutil.parser.parse(
        "Thu Sep 25 10:36:28 UTC 2003",
        tzinfos=datetime_tz._default_tzinfos())
    self.assertTimezoneEqual(parsed_dt.tzinfo, pytz.UTC)

  def testDefaultTzinfos(self):
    def_tz = datetime_tz._default_tzinfos()
    self.assertTrue("Australia/Sydney" in def_tz)
    self.assertFalse("Made/Up" in def_tz)
    self.assertTrue("Australia/Sydney" in def_tz.keys())
    self.assertTrue(def_tz.has_key("Australia/Sydney"))
    self.assertRaises(KeyError, def_tz.get, "Made/Up")
    self.assertEquals(def_tz.get("Made/Up", None), None)


class datetime_tz_test_subclass(datetime_tz.datetime_tz):
  pass


class TestSubclass(TestTimeZoneBase):

  def test_copy(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    dtz_copy = copy.copy(dtz)
    self.assertTrue(isinstance(
        dtz_copy, datetime_tz_test_subclass))
    self.assertEqual(dtz, dtz_copy)

  def test_deepcopy(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    dtz_copy = copy.deepcopy(dtz)
    self.assertTrue(isinstance(
        dtz_copy, datetime_tz_test_subclass))
    self.assertEqual(dtz, dtz_copy)

  def test_astimezone(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    self.assertTrue(isinstance(
        dtz.astimezone(pytz.UTC), datetime_tz_test_subclass))

  def test_replace(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    self.assertTrue(isinstance(
        dtz.replace(year=2014), datetime_tz_test_subclass))

  def test_add(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    self.assertTrue(isinstance(
        dtz + datetime.timedelta(days=1), datetime_tz_test_subclass))

  def test_radd(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    self.assertTrue(isinstance(
        datetime.timedelta(days=1) + dtz, datetime_tz_test_subclass))

  def test_sub(self):
    dtz = datetime_tz_test_subclass(
        2015, 7, 11, 12, 34, 54, "Australia/Sydney")
    self.assertTrue(isinstance(
        dtz - datetime.timedelta(days=1), datetime_tz_test_subclass))


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


class TestWin32MapUpdate(unittest.TestCase):

  def setUp(self):
    # Ignore warnings in datetime_tz as we are going to forcably generate them.
    self.mocked = MockMe()

  def tearDown(self):
    self.mocked.tearDown()

  def testRunUpdate(self):
    def os_path_exists_fake(filename, os_path_exists=os.path.exists):
      if filename.endswith("win32tz_map.py"):
        return False
      return os_path_exists(filename)
    self.mocked("os.path.exists", os_path_exists_fake)

    # Check that when /etc/timezone is a valid input
    def write_map_fake(filename, mode="r", open=open):
      if filename.endswith("win32tz_map.py") and mode == "w":
        return StringIO()
      return open(filename, mode)

    self.mocked("builtins.open", write_map_fake)
    update_win32tz_map.update_stored_win32tz_map()

if __name__ == "__main__":
  unittest.main()
