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
# pylint: disable-msg=W0212,C6409,C6111,W0622,W0704,W0611

"""Tests for the datetime_tz module."""

__author__ = "tansell@google.com (Tim Ansell)"

import __builtin__
import datetime
import os
import StringIO
import unittest
import warnings
import dateutil
import pytz

import datetime_tz


FMT = "%Y-%m-%d %H:%M:%S %Z%z"


# Older versions of pytz only have AmbiguousTimeError, while newer versions
# throw NonExistentTimeError.
if not hasattr(pytz, "NonExistentTimeError"):
  pytz.NonExistentTimeError = pytz.AmbiguousTimeError


import datetime_tz


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

    self.mocked("__builtin__.file", timezone_valid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(pytz.timezone("Australia/Sydney").zone, tzinfo.zone)

    # Check that when /etc/timezone is invalid timezone
    def timezone_invalid_fake(filename, file=open):
      if filename == "/etc/timezone":
        return StringIO.StringIO("Invalid-Timezone")
      return file(filename)

    self.mocked("__builtin__.file", timezone_invalid_fake)
    tzinfo = datetime_tz._detect_timezone_etc_timezone()
    self.assertEqual(None, tzinfo)

    # Check that when /etc/timezone is random "binary" data
    def timezone_binary_fake(filename, file=open):
      if filename == "/etc/timezone":
        return StringIO.StringIO("\0\r\n\t\0\r\r\n\0")
      return file(filename)

    self.mocked("__builtin__.file", timezone_binary_fake)
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
    self.mocked("__builtin__.file", localtime_valid_fake)

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
    #self.assertEqual(a.strftime("%s"), "1215284643")

    italy = pytz.timezone("Europe/Rome")
    b = a.astimezone(italy)
    self.assertEqual(str(b), "2008-07-06 07:04:03+02:00")
    self.assertEqual(b.totimestamp(), 1215320643.0)
    #self.assertNotEqual(b.strftime("%s"), "1215284643")

    # TODO(tansell): We still discard timezone information in strptime...
    # datetime.strptime silently throws away all timezone information. If you
    # look very closely, it even says so in its documentation

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

    # Creation from a naive datetime object not in DST
    d6 = datetime.datetime(2008, 12, 5)
    try:
      d7 = datetime_tz.datetime_tz(d6)
      self.fail("Was able to create from a naive datetime without a timezone")
    except TypeError:
      pass

    d7 = datetime_tz.datetime_tz(d6, "US/Pacific")
    self.assert_(isinstance(d7, datetime_tz.datetime_tz))
    self.assertEqual(d7.tzinfo.zone, "US/Pacific")
    self.assertEqual(d7.tzinfo._dst, datetime.timedelta(0))

    # Creation from a naive datetime object in DST
    d6 = datetime.datetime(2008, 7, 13)
    try:
      d7 = datetime_tz.datetime_tz(d6)
      self.fail("Was able to create from a naive datetime without a timezone")
    except TypeError:
      pass

    d7 = datetime_tz.datetime_tz(d6, "US/Pacific")

    self.assert_(isinstance(d7, datetime_tz.datetime_tz))
    self.assertEqual(d7.tzinfo.zone, "US/Pacific")
    self.assertEqual(d7.tzinfo._dst, datetime.timedelta(0, 3600))

    datetime_tz.localtz_set(pytz.utc)
    d0 = datetime_tz.datetime_tz(2008, 10, 1)
    self.assert_(isinstance(d0, datetime_tz.datetime_tz))
    self.assertEqual(d0.tzinfo, pytz.utc)

    d1 = datetime_tz.datetime_tz(d1)
    self.assert_(isinstance(d1, datetime_tz.datetime_tz))
    self.assertEqual(d1.tzinfo, pytz.utc)
    self.assertEqual(d0, d1)
    self.assertFalse(d0 is d1)

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

    self.assert_(isinstance(dadd, datetime_tz.datetime_tz))
    self.assert_(isinstance(dsub, datetime_tz.datetime_tz))
    self.assert_(isinstance(dradd, datetime_tz.datetime_tz))
    self.assert_(isinstance(drsub, datetime_tz.datetime_tz))
    self.assert_(isinstance(dreplace, datetime_tz.datetime_tz))

    try:
      # Make sure the wrapped functions still look like the original functions
      self.assertEqual(dreplace.combine.__name__,
                       datetime.datetime.combine.__name__)
      self.assertEqual(dreplace.combine.__doc__,
                       datetime.datetime.combine.__doc__)
    except ImportError:
      pass

    try:
      dreplace = datetime_tz.datetime_tz.now()
      dreplace = dreplace.replace(days=1)

      self.assert_(False)
    except TypeError:
      pass

    try:
      dreplace.replace(tzinfo=None)

      self.fail("Was able to replace tzinfo with none!")
    except TypeError:
      pass

  def testUtcFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in -100000000, -1, 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.utcfromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo, pytz.utc)
      self.assertEqual(d.totimestamp(), timestamp)

  def testFromTimestamp(self):
    datetime_tz.localtz_set("US/Pacific")

    for timestamp in -100000000, -1, 0, 1, 1233300000:
      d = datetime_tz.datetime_tz.fromtimestamp(timestamp)

      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo.zone, pytz.timezone("US/Pacific").zone)
      self.assertEqual(d.totimestamp(), timestamp)

      # Changing the timezone should have no effect on the timestamp produced.
      d = d.astimezone("UTC")
      self.assert_(isinstance(d, datetime_tz.datetime_tz))
      self.assertEqual(d.tzinfo, pytz.utc)
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
    #self.assertRaises(pytz.NonExistentTimeError, loc_dt.replace,
    #                  day=26, is_dst=False)
    #self.assertRaises(pytz.NonExistentTimeError, loc_dt.replace,
    #                  day=28, is_dst=True)

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
    tommorrow = now+datetime.timedelta(days=1)

    @staticmethod
    def now_fake(tzinfo):
      if tz is tzinfo:
        return now
      else:
        assert False
    self.mocked("datetime_tz.datetime_tz.now", now_fake)

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

    d = datetime_tz.datetime_tz.smartparse("an hour and a day ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=1))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1d 2h ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(days=1, hours=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2h5m32s ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-datetime.timedelta(hours=2, minutes=5, seconds=32))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("1y 2 month ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=2))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("2 months and 3m ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        months=2, minutes=3))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("3m4months1y ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=4, minutes=3))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("3m4months and 1y ago", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now-dateutil.relativedelta.relativedelta(
        years=1, months=4, minutes=3))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    self.assertRaises(ValueError,
                      datetime_tz.datetime_tz.smartparse,
                      "5 billion years ago", tz)

    self.assertRaises(ValueError,
                      datetime_tz.datetime_tz.smartparse,
                      "5 ago", tz)

    # FIXME: These below should actually test the equivalence
    d = datetime_tz.datetime_tz.smartparse("start of today", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d, now.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("start of tommorrow", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(
        d, tommorrow.replace(hour=0, minute=0, second=0, microsecond=0))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("start of yesterday", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of today", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of tommorrow", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(
        d, tommorrow.replace(
            hour=23, minute=59, second=59, microsecond=999999))
    self.assertEqual(d.tzinfo.zone, tz.zone)

    d = datetime_tz.datetime_tz.smartparse("end of yesterday", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(d.tzinfo.zone, tz.zone)
    # FIXME: These above should actually test the equivalence

    self.mocked.tearDown()

    # Test datetime string with timezone information,
    # also provide timezone argument
    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00-05:00", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.FixedOffset(-300))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00+0800", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00+08:00")
    self.assertEqual(d.tzinfo, pytz.FixedOffset(480))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST-05:00", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 EST 2009", tz)
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    # Test datetime string with timezone information,
    # no more timezone argument
    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00-05:00")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.FixedOffset(-300))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00+0800")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00+08:00")
    self.assertEqual(d.tzinfo, pytz.FixedOffset(480))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    d = datetime_tz.datetime_tz.smartparse("2009-11-09 23:00:00 EST-05:00")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 EST 2009")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2009-11-09 23:00:00-05:00")
    self.assertEqual(d.tzinfo, pytz.timezone("US/Eastern"))

    # UTC, nice and easy
    d = datetime_tz.datetime_tz.smartparse("Tue Jul 03 06:00:01 UTC 2010")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2010-07-03 06:00:01+00:00")
    self.assertEqual(d.tzinfo, pytz.timezone("UTC"))

    # Try Pacific standard time
    d = datetime_tz.datetime_tz.smartparse("2002-10-27 01:20:00 EST")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2002-10-27 01:20:00-05:00")
    self.assertEqual(d.tzinfo.zone, pytz.timezone("US/Eastern").zone)

    d = datetime_tz.datetime_tz.smartparse("2002-10-27 01:20:00 EDT")
    self.assert_(isinstance(d, datetime_tz.datetime_tz))
    self.assertEqual(str(d), "2002-10-27 01:20:00-04:00")
    self.assertEqual(d.tzinfo.zone, pytz.timezone("US/Eastern").zone)

    # Using Oslon timezones means you end up with ambigious dates.
    #   2002-10-27 01:30:00 US/Eastern
    #  could be either,
    #   2002-10-27 01:30:00 EDT-0400
    #   2002-10-27 01:30:00 EST-0500
    try:
      d = datetime_tz.datetime_tz.smartparse(
          "Tue Jul 03 06:00:01 US/Pacific 2010")
      self.assert_(False)
    except ValueError:
      pass

    # Make sure we get exceptions when invalid timezones are used.
    try:
      d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 Random 2009")
      self.assert_(False)
    except ValueError:
      pass

    try:
      d = datetime_tz.datetime_tz.smartparse("Mon Nov 09 23:00:00 XXX 2009")
      self.assert_(False)
    except ValueError:
      pass

    ###########################################################################
    toparse = datetime_tz.datetime_tz(2008, 06, 5)
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
    self.assertEqual(
        d, toparse.replace(hour=0, minute=0, second=0, microsecond=0))

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
    self.assertEqual(
        d, toparse.replace(hour=0, minute=0, second=0, microsecond=0))


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
