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

try:
  import functools
except ImportError, e:
  class functools(object):
    def wraps(f, *args, **kw):
      return f

import pytz
import dateutil.parser

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
      raise pytz.UnknownTimeZoneError("Unknown timezone!")
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
      except (IOError, pytz.UnknownTimeZoneError), e:
        warnings.warn("Your /etc/timezone file references a timezone (%r) that"
                      " is not valid (%r)." % (tz, e))

    # Problem reading the /etc/timezone file
    except IOError, e:
      warnings.warn("Could not access your /etc/timezone file: %s" % e)


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
      else:
        warning += "We detected no matches for your /etc/localtime."
      warnings.warn(warning)

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

  def __new__(cls, *newargs, **kw):
    if len(newargs) >= 1 and isinstance(newargs[0], datetime.datetime):
      args = list(newargs[0].timetuple()[0:6])+[newargs[0].microsecond]

      if not newargs[0].tzinfo is None:
        if "tzinfo" in kw:
          raise TypeError("Can not give a timezone with timezone aware"
                          " datetime object! (Use localize.)")
        args.append(newargs[0].tzinfo)
      else:
        if isinstance(newargs[-1], (datetime.tzinfo, basestring)):
          kw["tzinfo"] = _tzinfome(newargs[-1])
        elif "tzinfo" in kw:
          if kw["tzinfo"] is not None:
            kw["tzinfo"] = _tzinfome(kw["tzinfo"])
        else:
          raise TypeError("Must give a timezone for naive datetime objects!")
    else:
      args = list(newargs)

      # Try and find out if we where given a string instead of a tzinfo object.
      if len(args) > 7:
        if isinstance(args[-1], basestring):
          args[-1] = _tzinfome(args[-1])
      elif "tzinfo" in kw:
        kw["tzinfo"] = _tzinfome(kw["tzinfo"])
      else:
        kw["tzinfo"] = localtz()

    obj = datetime.datetime.__new__(cls, *args, **kw)

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
    return datetime.date(this.year, this.month, this.day)

  def totimestamp(self):
    """Convert this datetime object back to a unix timestamp.

    The Unix epoch is the time 00:00:00 UTC on January 1, 1970.

    Returns:
      Unix timestamp.
    """
    return calendar.timegm(self.utctimetuple())+1e-6*self.microsecond

  def __localize(self, tzinfo):
    """Returns a version of this naive timestamp with the given timezone.

    Args:
      tzinfo: Either a datetime.tzinfo object or a string (which will be looked
              up in pytz.

    Returns:
      A datetime_tz object in the given timezone.
    """
    # Assert we are a naive datetime object
    assert self.tzinfo is None

    tzinfo = _tzinfome(tzinfo)
    d = tzinfo.localize(self.asdatetime(naive=True))

    return datetime_tz(d)

  def normalize(self, tzinfo):
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
    d = tzinfo.normalize(self.asdatetime(naive=False))

    return datetime_tz(d)

  astimezone = normalize

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
      "start of yesterday"
      "end of tommorrow"
      "end of 3rd of March"
    (does not yet support "5 months ago" yet)

    """
    # Default for empty fields are:
    #  year/month/day == now
    #  hour/minute/second/microsecond == 0
    toparse = toparse.strip().lower()

    if tzinfo is None:
      dt = cls.now()
    else:
      dt = cls.now(tzinfo)

    default = dt.replace(hour=0, minute=0, second=0, microsecond=0)

    if toparse.startswith("end of "):
      toparse = toparse.replace("end of ", "")

      dt += datetime.timedelta(days=1)
      dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
      dt -= datetime.timedelta(microseconds=1)

      default = dt
    if toparse.startswith("start of "):
      toparse = toparse.replace("start of ", "")

      dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
      default = dt

    toparse = toparse.strip()

    if toparse in ["now", "today"]:
      pass

    elif toparse == "yesterday":
      dt -= datetime.timedelta(days=1)

    elif toparse == "tommorrow":
      dt += datetime.timedelta(days=1)

    elif "ago" in toparse:
      # Remove the "ago" bit
      toparse = toparse[:-3]

      # Match the following
      # an hour ago
      # 1h ago
      # 1 h ago
      # 1 hour ago
      # 2 hours ago
      # Same with minutes, seconds, etc.

      # FIXME: We should add support for 5 months, 1 year, etc but timedelta
      # does not support them.
      tocheck = ("days", "hours", "minutes", "seconds")
      result = []
      for i, bit in enumerate(tocheck):
        regex = "([0-9]+|(a)|(an))( )*([%s]((%s)?s?))( )*" % (
            bit[0], bit[1:-1])

        matches = re.search(regex, toparse)
        if matches is None:
          result.append(0)
        else:
          amount = matches.group(1)

          if amount in ("a", "an"):
            result.append(1)
          else:
            result.append(int(amount))

      delta = datetime.timedelta(**dict(zip(tocheck, result)))
      dt -= delta
    else:
      dt = dateutil.parser.parse(toparse, default=default)
      if dt is None:
        raise ValueError('Was not able to parse date!')

      if not tzinfo is None:
        args = list(dt.timetuple()[0:6])+[0, tzinfo]
        dt = datetime_tz(*args)
      elif dt.tzinfo is None:
        dt = cls(dt, tzinfo=None)
        dt = datetime_tz.__localize(dt, localtz())

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
    return d.normalize(localtz())

  @classmethod
  def utcnow(cls):
    """Return a new datetime representing UTC day and time."""
    obj = datetime.datetime.utcnow()
    obj = cls(obj, tzinfo=None)
    obj = datetime_tz.__localize(obj, pytz.utc)
    return obj

  @classmethod
  def now(cls, tzinfo=None):
    """[tz] -> new datetime with tz's local day and time."""
    obj = datetime.datetime.now()
    obj = cls(obj, tzinfo=None)
    obj = datetime_tz.__localize(obj, localtz())
    if not tzinfo is None:
      obj = obj.normalize(tzinfo)
    return obj

  today = now

  @staticmethod
  def fromordinal(ordinal):
    raise SyntaxError("Not enough information to create a datetime_tz object "
                      "from an ordinal. Please use datetime.date.fromordinal")


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

for methodname in ["__add__", "__radd__", "__rsub__", "__sub__", "combine",
                   "replace"]:

  # Make sure we have not already got an override for this method
  assert methodname not in datetime_tz.__dict__

  _wrap_method(methodname)
