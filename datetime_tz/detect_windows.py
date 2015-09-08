# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 et sts=2 ai:
#
# Copyright 2014 David M
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
# pylint: disable=invalid-name,protected-access

"""datetime_tz windows support."""

__author__ = "davidm"

import ctypes
import warnings
import locale

import pytz

try:
  # pylint: disable=g-import-not-at-top
  from datetime_tz import win32tz_map
except ImportError:
  warnings.warn("win32tz_map has not been generated yet.")

try:
  # pylint: disable=g-import-not-at-top
  import win32timezone
except ImportError:
  win32timezone = None

# The following code is a workaround to
# GetDynamicTimeZoneInformation not being present in win32timezone


class SYSTEMTIME_c(ctypes.Structure):
  """ctypes structure for SYSTEMTIME."""
  # pylint: disable=too-few-public-methods
  _fields_ = [
      ("year", ctypes.c_ushort),
      ("month", ctypes.c_ushort),
      ("day_of_week", ctypes.c_ushort),
      ("day", ctypes.c_ushort),
      ("hour", ctypes.c_ushort),
      ("minute", ctypes.c_ushort),
      ("second", ctypes.c_ushort),
      ("millisecond", ctypes.c_ushort),
  ]


class TZI_c(ctypes.Structure):
  """ctypes structure for TIME_ZONE_INFORMATION."""
  # pylint: disable=too-few-public-methods
  _fields_ = [
      ("bias", ctypes.c_long),
      ("standard_name", ctypes.c_wchar*32),
      ("standard_start", SYSTEMTIME_c),
      ("standard_bias", ctypes.c_long),
      ("daylight_name", ctypes.c_wchar*32),
      ("daylight_start", SYSTEMTIME_c),
      ("daylight_bias", ctypes.c_long),
  ]


class DTZI_c(ctypes.Structure):
  """ctypes structure for DYNAMIC_TIME_ZONE_INFORMATION."""
  # pylint: disable=too-few-public-methods
  _fields_ = TZI_c._fields_ + [
      ("key_name", ctypes.c_wchar*128),
      ("dynamic_daylight_time_disabled", ctypes.c_bool),
  ]


# Global variable for mapping Window timezone names in the current
# locale to english ones. Initialized when needed
win32timezone_to_en = {}


def _detect_timezone_windows():
  """Detect timezone on the windows platform."""
  # pylint: disable=global-statement
  global win32timezone_to_en

  # Try and fetch the key_name for the timezone using
  # Get(Dynamic)TimeZoneInformation
  tzi = DTZI_c()
  kernel32 = ctypes.windll.kernel32
  getter = kernel32.GetTimeZoneInformation
  getter = getattr(kernel32, "GetDynamicTimeZoneInformation", getter)

  # code is for daylight savings: 0 means disabled/not defined, 1 means enabled
  # but inactive, 2 means enabled and active
  _ = getter(ctypes.byref(tzi))

  win32tz_key_name = tzi.key_name
  if not win32tz_key_name:
    if win32timezone is None:
      return None
    # We're on Windows before Vista/Server 2008 - need to look up the
    # standard_name in the registry.
    # This will not work in some multilingual setups if running in a language
    # other than the operating system default
    win32tz_name = tzi.standard_name
    if not win32timezone_to_en:
      win32timezone_to_en = dict(
          win32timezone.TimeZoneInfo._get_indexed_time_zone_keys("Std"))
    win32tz_key_name = win32timezone_to_en.get(win32tz_name, win32tz_name)

  territory = locale.getdefaultlocale()[0].split("_", 1)[1]
  olson_name = win32tz_map.win32timezones.get((win32tz_key_name, territory), win32tz_map.win32timezones.get(win32tz_key_name, None))
  if not olson_name:
    return None
  if not isinstance(olson_name, str):
    olson_name = olson_name.encode("ascii")

  return pytz.timezone(olson_name)
