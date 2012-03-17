#!/usr/bin/python
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
#
# Disable the invalid name warning as we are inheriting from a standard library
# object.
# pylint: disable-msg=C6409,W0212

"""A version of the datetime module which *cares* about timezones.

This module will never return a naive datetime object. This requires the module
know your local timezone, which it tries really hard to figure out.

You can override the detection by using the datetime.tzaware.defaulttz_set
method. It the module is unable to figure out the timezone itself this method
*must* be called before the normal module is imported. If done before importing
it can also speed up the time taken to import as the defaulttz will no longer
try and do the detection.
"""

__author__ = "tansell@google.com (Tim Ansell)"

import calendar
import datetime
import os
import os.path
import re
import time
import warnings
import dateutil.parser
import dateutil.relativedelta
import dateutil.tz
import pytz
import pytz_abbr


try:
  # pylint: disable-msg=C6204
  import functools
except ImportError, e:

  class functools(object):
    """Fake replacement for a full functools."""

    # pylint: disable-msg=W0613
    @staticmethod
    def wraps(f, *args, **kw):
      return f


# Need to patch pytz.utc to have a _utcoffset so you can normalize/localize
# using it.
pytz.utc._utcoffset = datetime.timedelta()


timedelta = datetime.timedelta


def _tzinfome(tzinfo):
  """Gets a tzinfo object from a string.

  Args:
    tzinfo: A string (or string like) object, or a datetime.tzinfo object.

  Returns:
    An datetime.tzinfo object.

  Raises:
    UnknownTimeZoneError: If the timezone given can't be decoded.
  """
  if not isinstance(tzinfo, datetime.tzinfo):
    try:
      tzinfo = pytz.timezone(tzinfo)
    except AttributeError:
      raise pytz.UnknownTimeZoneError("Unknown timezone! %s" % tzinfo)
  return tzinfo


# Our "local" timezone
_localtz = None


def localtz():
  """Get the local timezone.

  Returns:
    The localtime timezone as a tzinfo object.
  """
  # pylint: disable-msg=W0603
  global _localtz
  if _localtz is None:
    _localtz = detect_timezone()
  return _localtz


def localtz_set(timezone):
  """Set the local timezone."""
  # pylint: disable-msg=W0603
  global _localtz
  _localtz = _tzinfome(timezone)


def detect_timezone():
  """Try and detect the timezone that Python is currently running in.

  We have a bunch of different methods for trying to figure this out (listed in
  order they are attempted).
    * Try TZ environment variable.
    * Try and find /etc/timezone file (with timezone name).
    * Try and find /etc/localtime file (with timezone data).
    * Try and match a TZ to the current dst/offset/shortname.

  Returns:
    The detected local timezone as a tzinfo object

  Raises:
    pytz.UnknownTimeZoneError: If it was unable to detect a timezone.
  """
  # First we try the TZ variable
  tz = _detect_timezone_environ()
  if tz is not None:
    return tz

  # Second we try /etc/timezone and use the value in that
  tz = _detect_timezone_etc_timezone()
  if tz is not None:
    return tz

  # Next we try and see if something matches the tzinfo in /etc/localtime
  tz = _detect_timezone_etc_localtime()
  if tz is not None:
    return tz

  # Next we try and use a similiar method to what PHP does.
  # We first try to search on time.tzname, time.timezone, time.daylight to
  # match a pytz zone.
  warnings.warn("Had to fall back to worst detection method (the 'PHP' "
                "method).")

  tz = _detect_timezone_php()
  if tz is not None:
    return tz

  raise pytz.UnknownTimeZoneError("Unable to detect your timezone!")


def _detect_timezone_environ():
  if "TZ" in os.environ:
    try:
      return pytz.timezone(os.environ["TZ"])
    except (IOError, pytz.UnknownTimeZoneError):
      warnings.warn("You provided a TZ environment value (%r) we did not "
                    "understand!" % os.environ["TZ"])


def _detect_timezone_etc_timezone():
  if os.path.exists("/etc/timezone"):
    try:
      tz = file("/etc/timezone").read().strip()
      try:
        return pytz.timezone(tz)
      except (IOError, pytz.UnknownTimeZoneError), ei:
        warnings.warn("Your /etc/timezone file references a timezone (%r) that"
                      " is not valid (%r)." % (tz, ei))

    # Problem reading the /etc/timezone file
    except IOError, eo:
      warnings.warn("Could not access your /etc/timezone file: %s" % eo)


def _detect_timezone_etc_localtime():
  matches = []
  if os.path.exists("/etc/localtime"):
    localtime = pytz.tzfile.build_tzinfo("/etc/localtime",
                                         file("/etc/localtime"))

    # See if we can find a "Human Name" for this..
    for tzname in pytz.all_timezones:
      tz = _tzinfome(tzname)

      if dir(tz) != dir(localtime):
        continue

      for attrib in dir(tz):
        # Ignore functions and specials
        if callable(getattr(tz, attrib)) or attrib.startswith("__"):
          continue

        # This will always be different
        if attrib == "zone" or attrib == "_tzinfos":
          continue

        if getattr(tz, attrib) != getattr(localtime, attrib):
          break

      # We get here iff break didn't happen, i.e. no meaningful attributes
      # differ between tz and localtime
      else:
        matches.append(tzname)

    if len(matches) == 1:
      return _tzinfome(matches[0])
    else:
      # Warn the person about this!
      warning = "Could not get a human name for your timezone: "
      if len(matches) > 1:
        warning += ("We detected multiple matches for your /etc/localtime. "
                    "(Matches where %s)" % matches)
        return _tzinfome(matches[0])
      else:
        warning += "We detected no matches for your /etc/localtime."
      warnings.warn(warning)

      # Register /etc/localtime as the timezone loaded.
      pytz._tzinfo_cache['/etc/localtime'] = localtime
      return localtime


def _detect_timezone_php():
  tomatch = (time.tzname[0], time.timezone, time.daylight)
  now = datetime.datetime.now()

  matches = []
  for tzname in pytz.all_timezones:
    try:
      tz = pytz.timezone(tzname)
    except IOError:
      continue

    try:
      indst = tz.localize(now).timetuple()[-1]

      if tomatch == (tz._tzname, -tz._utcoffset.seconds, indst):
        matches.append(tzname)

    # pylint: disable-msg=W0704
    except AttributeError:
      pass

  if len(matches) > 1:
    warnings.warn("We detected multiple matches for the timezone, choosing "
                  "the first %s. (Matches where %s)" % (matches[0], matches))
    return pytz.timezone(matches[0])


class datetime_tz(datetime.datetime):
  """An extension of the inbuilt datetime adding more functionality.

  The extra functionality includes:
    * Partial parsing support (IE 2006/02/30 matches %Y/%M/%D %H:%M)
    * Full integration with pytz (just give it the string of the timezone!)
    * Proper support for going to/from Unix timestamps (which are in UTC!).
  """
  __slots__ = ["is_dst"]

  def __new__(cls, *args, **kw):
    args = list(args)
    if not args:
      raise TypeError("Not enough arguments given.")

    # See if we are given a tzinfo object...
    tzinfo = None
    if isinstance(args[-1], (datetime.tzinfo, basestring)):
      tzinfo = _tzinfome(args.pop(-1))
    elif kw.get("tzinfo", None) is not None:
      tzinfo = _tzinfome(kw.pop("tzinfo"))

    # Create a datetime object if we don't have one
    if isinstance(args[0], datetime.datetime):
      # Convert the datetime instance to a datetime object.
      newargs = (list(args[0].timetuple()[0:6]) +
                 [args[0].microsecond, args[0].tzinfo])
      dt = datetime.datetime(*newargs)

      if tzinfo is None and dt.tzinfo is None:
        raise TypeError("Must specify a timezone!")

      if tzinfo is not None and dt.tzinfo is not None:
        raise TypeError("Can not give a timezone with timezone aware"
                        " datetime object! (Use localize.)")
    else:
      dt = datetime.datetime(*args, **kw)

    if dt.tzinfo is not None:
      # Re-normalize the dt object
      dt = dt.tzinfo.normalize(dt)

    else:
      if tzinfo is None:
        tzinfo = localtz()

      try:
        dt = tzinfo.localize(dt, is_dst=None)
      except pytz.AmbiguousTimeError:
        is_dst = None
        if "is_dst" in kw:
          is_dst = kw.pop("is_dst")

        try:
          dt = tzinfo.localize(dt, is_dst)
        except IndexError:
          raise pytz.AmbiguousTimeError("No such time exists!")

    newargs = list(dt.timetuple()[0:6])+[dt.microsecond, dt.tzinfo]
    obj = datetime.datetime.__new__(cls, *newargs)
    obj.is_dst = obj.dst() != datetime.timedelta(0)
    return obj

  def asdatetime(self, naive=True):
    """Return this datetime_tz as a datetime object.

    Args:
      naive: Return *without* any tz info.

    Returns:
      This datetime_tz as a datetime object.
    """
    args = list(self.timetuple()[0:6])+[self.microsecond]
    if not naive:
      args.append(self.tzinfo)
    return datetime.datetime(*args)

  def asdate(self):
    """Return this datetime_tz as a date object.

    Returns:
      This datetime_tz as a date object.
    """
    return datetime.date(self.year, self.month, self.day)

  def totimestamp(self):
    """Convert this datetime object back to a unix timestamp.

    The Unix epoch is the time 00:00:00 UTC on January 1, 1970.

    Returns:
      Unix timestamp.
    """
    return calendar.timegm(self.utctimetuple())+1e-6*self.microsecond

  def astimezone(self, tzinfo):
    """Returns a version of this timestamp converted to the given timezone.

    Args:
      tzinfo: Either a datetime.tzinfo object or a string (which will be looked
              up in pytz.

    Returns:
      A datetime_tz object in the given timezone.
    """
    # Assert we are not a naive datetime object
    assert self.tzinfo is not None

    tzinfo = _tzinfome(tzinfo)

    d = self.asdatetime(naive=False).astimezone(tzinfo)
    return datetime_tz(d)

  # pylint: disable-msg=C6113
  def replace(self, **kw):
    """Return datetime with new specified fields given as arguments.

    For example, dt.replace(days=4) would return a new datetime_tz object with
    exactly the same as dt but with the days attribute equal to 4.

    Any attribute can be replaced, but tzinfo can not be set to None.

    Args:
      Any datetime_tz attribute.

    Returns:
      A datetime_tz object with the attributes replaced.

    Raises:
      TypeError: If the given replacement is invalid.
    """
    if "tzinfo" in kw:
      if kw["tzinfo"] is None:
        raise TypeError("Can not remove the timezone use asdatetime()")

    is_dst = None
    if "is_dst" in kw:
      is_dst = kw["is_dst"]
      del kw["is_dst"]
    else:
      # Use our own DST setting..
      is_dst = self.is_dst

    replaced = self.asdatetime().replace(**kw)

    return datetime_tz(replaced, tzinfo=self.tzinfo.zone, is_dst=is_dst)

  # pylint: disable-msg=C6310
  @classmethod
  def smartparse(cls, toparse, tzinfo=None):
    """Method which uses dateutil.parse and extras to try and parse the string.

    Valid dates are found at:
     http://labix.org/python-dateutil#head-1443e0f14ad5dff07efd465e080d1110920673d8-2

    Other valid formats include:
      "now" or "today"
      "yesterday"
      "tommorrow"
      "5 minutes ago"
      "10 hours ago"
      "10h5m ago"
      "start of yesterday"
      "end of tommorrow"
      "end of 3rd of March"

    Args:
      toparse: The string to parse.
      tzinfo: Timezone for the resultant datetime_tz object should be in.
              (Defaults to your local timezone.)

    Returns:
      New datetime_tz object.

    Raises:
      ValueError: If unable to make sense of the input.
    """
    # Default for empty fields are:
    #  year/month/day == now
    #  hour/minute/second/microsecond == 0
    toparse = toparse.strip()

    if tzinfo is None:
      dt = cls.now()
    else:
      dt = cls.now(tzinfo)

    default = dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # Remove "start of " and "end of " prefix in the string
    if toparse.lower().startswith("end of "):
      toparse = toparse[7:].strip()

      dt += datetime.timedelta(days=1)
      dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
      dt -= datetime.timedelta(microseconds=1)

      default = dt

    elif toparse.lower().startswith("start of "):
      toparse = toparse[9:].strip()

      dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
      default = dt

    # Handle strings with "now", "today", "yesterday", "tomorrow" and "ago".
    # Need to use lowercase
    toparselower = toparse.lower()

    if toparselower in ["now", "today"]:
      pass

    elif toparselower == "yesterday":
      dt -= datetime.timedelta(days=1)

    elif toparselower == "tommorrow":
      dt += datetime.timedelta(days=1)

    elif "ago" in toparselower:
      # Remove the "ago" bit
      toparselower = toparselower[:-3]
      # Replace all "a day and an hour" with "1 day 1 hour"
      toparselower = toparselower.replace("a ", "1 ")
      toparselower = toparselower.replace("an ", "1 ")
      toparselower = toparselower.replace(" and ", " ")

      # Match the following
      # 1 hour ago
      # 1h ago
      # 1 h ago
      # 1 hour ago
      # 2 hours ago
      # Same with minutes, seconds, etc.

      tocheck = ("seconds", "minutes", "hours", "days", "weeks", "months",
                 "years")
      result = {}
      for match in re.finditer("([0-9]+)([^0-9]*)", toparselower):
        amount = int(match.group(1))
        unit = match.group(2).strip()

        for bit in tocheck:
          regex = "^([%s]|((%s)s?))$" % (
              bit[0], bit[:-1])

          bitmatch = re.search(regex, unit)
          if bitmatch:
            result[bit] = amount
            break
        else:
          raise ValueError("Was not able to parse date unit %r!" % unit)

      delta = dateutil.relativedelta.relativedelta(**result)
      dt -= delta

    else:
      # Handle strings with normal datetime format, use original case.
      dt = dateutil.parser.parse(toparse, default=default.asdatetime(),
                                 tzinfos=pytz_abbr.tzinfos)
      if dt is None:
        raise ValueError("Was not able to parse date!")

      if dt.tzinfo is pytz_abbr.unknown:
        dt = dt.replace(tzinfo=None)

      if dt.tzinfo is None:
        if tzinfo is None:
          tzinfo = localtz()
        dt = cls(dt, tzinfo)
      else:
        if isinstance(dt.tzinfo, pytz_abbr.tzabbr):
          abbr = dt.tzinfo
          dt = dt.replace(tzinfo=None)
          dt = cls(dt, abbr.zone, is_dst=abbr.dst)

        dt = cls(dt)

    return dt

  @classmethod
  def utcfromtimestamp(cls, timestamp):
    """Returns a datetime object of a given timestamp (in UTC)."""
    obj = datetime.datetime.utcfromtimestamp(timestamp)
    obj = pytz.utc.localize(obj)
    return cls(obj)

  @classmethod
  def fromtimestamp(cls, timestamp):
    """Returns a datetime object of a given timestamp (in local tz)."""
    d = cls.utcfromtimestamp(timestamp)
    return d.astimezone(localtz())

  @classmethod
  def utcnow(cls):
    """Return a new datetime representing UTC day and time."""
    obj = datetime.datetime.utcnow()
    obj = cls(obj, tzinfo=pytz.utc)
    return obj

  @classmethod
  def now(cls, tzinfo=None):
    """[tz] -> new datetime with tz's local day and time."""
    obj = cls.utcnow()
    if tzinfo is None:
      tzinfo = localtz()
    return obj.astimezone(tzinfo)

  today = now

  @staticmethod
  def fromordinal(ordinal):
    raise SyntaxError("Not enough information to create a datetime_tz object "
                      "from an ordinal. Please use datetime.date.fromordinal")


class iterate(object):
  """Helpful iterators for working with datetime_tz objects."""

  @staticmethod
  def between(start, delta, end=None):
    """Return an iterator between this date till given end point.

    Example usage:
      >>> d = datetime_tz.smartparse("5 days ago")
      2008/05/12 11:45
      >>> for i in d.between(timedelta(days=1), datetime_tz.now()):
      >>>    print i
      2008/05/12 11:45
      2008/05/13 11:45
      2008/05/14 11:45
      2008/05/15 11:45
      2008/05/16 11:45

    Args:
      start: The date to start at.
      delta: The interval to iterate with.
      end: (Optional) Date to end at. If not given the iterator will never
           terminate.

    Yields:
      datetime_tz objects.
    """
    toyield = start
    while end is None or toyield < end:
      yield toyield
      toyield += delta

  @staticmethod
  def weeks(start, end=None):
    """Iterate over the weeks between the given datetime_tzs.

    Args:
      start: datetime_tz to start from.
      end: (Optional) Date to end at, if not given the iterator will never
           terminate.

    Returns:
      An iterator which generates datetime_tz objects a week apart.
    """
    return iterate.between(start, datetime.timedelta(days=7), end)

  @staticmethod
  def days(start, end=None):
    """Iterate over the days between the given datetime_tzs.

    Args:
      start: datetime_tz to start from.
      end: (Optional) Date to end at, if not given the iterator will never
           terminate.

    Returns:
      An iterator which generates datetime_tz objects a day apart.
    """
    return iterate.between(start, datetime.timedelta(days=1), end)

  @staticmethod
  def hours(start, end=None):
    """Iterate over the hours between the given datetime_tzs.

    Args:
      start: datetime_tz to start from.
      end: (Optional) Date to end at, if not given the iterator will never
           terminate.

    Returns:
      An iterator which generates datetime_tz objects a hour apart.
    """
    return iterate.between(start, datetime.timedelta(hours=1), end)

  @staticmethod
  def minutes(start, end=None):
    """Iterate over the minutes between the given datetime_tzs.

    Args:
      start: datetime_tz to start from.
      end: (Optional) Date to end at, if not given the iterator will never
           terminate.

    Returns:
      An iterator which generates datetime_tz objects a minute apart.
    """
    return iterate.between(start, datetime.timedelta(minutes=1), end)

  @staticmethod
  def seconds(start, end=None):
    """Iterate over the seconds between the given datetime_tzs.

    Args:
      start: datetime_tz to start from.
      end: (Optional) Date to end at, if not given the iterator will never
           terminate.

    Returns:
      An iterator which generates datetime_tz objects a second apart.
    """
    return iterate.between(start, datetime.timedelta(minutes=1), end)


def _wrap_method(name):
  """Wrap a method.

  Patch a method which might return a datetime.datetime to return a
  datetime_tz.datetime_tz instead.

  Args:
    name: The name of the method to patch
  """
  method = getattr(datetime.datetime, name)

  # Have to give the second argument as method has no __module__ option.
  @functools.wraps(method, ("__name__", "__doc__"), ())
  def wrapper(*args, **kw):
    r = method(*args, **kw)

    if isinstance(r, datetime.datetime) and not isinstance(r, datetime_tz):
      r = datetime_tz(r)
    return r

  setattr(datetime_tz, name, wrapper)

for methodname in ["__add__", "__radd__", "__rsub__", "__sub__", "combine"]:

  # Make sure we have not already got an override for this method
  assert methodname not in datetime_tz.__dict__

  _wrap_method(methodname)


__all__ = ['datetime_tz', 'detect_timezone', 'iterate', 'localtz',
    'localtz_set', 'timedelta', '_detect_timezone_environ',
    '_detect_timezone_etc_localtime', '_detect_timezone_etc_timezone',
    '_detect_timezone_php']
