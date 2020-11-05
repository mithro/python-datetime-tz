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
# pylint: disable=g-import-not-at-top

"""This script updates win32tz_map based on the data at the URL below."""

import hashlib
import os

from defusedxml import ElementTree

try:
  # pylint: disable=redefined-builtin
  from importlib import reload
except ImportError:
  pass

try:
  from datetime_tz import win32tz_map
except ImportError:
  win32tz_map = None

try:
  import urllib.request as urllib2
except ImportError:
  import urllib2

_CLDR_WINZONES_URL = "https://github.com/unicode-org/cldr/raw/master/common/supplemental/windowsZones.xml" # pylint: disable=line-too-long


def download_cldr_win32tz_map_xml():
  """Downloads the XML that maps between Windows and Olson timezone names."""
  return urllib2.urlopen(_CLDR_WINZONES_URL).read()


def create_win32tz_map(windows_zones_xml):
  """Creates a map between Windows and Olson timezone names.

  Args:
    windows_zones_xml: The CLDR XML mapping.

  Yields:
    For "default" territory (001): (win32_name, olson_name)
    Where territory is set: ((win32_name, territory), olson_name)
  """
  parser = ElementTree.fromstring(windows_zones_xml)
  map_timezones = parser.find("windowsZones").find("mapTimezones")

  for child in map_timezones:
    if child.tag == "mapZone":
      win32_name = str(child.attrib.get("other", ""))
      territory = str(child.attrib.get("territory", ""))
      # Some `type` parameters are have multiple values, separated by spaces
      # eg: "America/Denver America/Boise"
      olson_name = str(child.attrib.get("type", "")).split(" ")[0]

      if not win32_name or not olson_name:
        continue

      if territory == "001" or not territory:
        yield (win32_name, olson_name)
      else:
        yield ((win32_name, territory), olson_name)


def update_stored_win32tz_map():
  """Downloads the cldr win32 timezone map and stores it in win32tz_map.py."""
  windows_zones_xml = download_cldr_win32tz_map_xml()
  source_hash = hashlib.md5(windows_zones_xml).hexdigest()

  map_zones = create_win32tz_map(windows_zones_xml)
  map_dir = os.path.dirname(os.path.abspath(__file__))
  map_filename = os.path.join(map_dir, "win32tz_map.py")
  if os.path.exists(map_filename):
    reload(win32tz_map)
    current_hash = getattr(win32tz_map, "source_hash", None)
    if current_hash == source_hash:
      return False

  map_file = open(map_filename, "w")
  map_file.write((
      "'''Map between Windows and Olson timezones taken from {0}\n"
      "Generated automatically by {1}'''\n"
      "source_hash = {2!r}  # md5 sum of xml source data\n"
      "win32timezones = {{\n"
    ).format(_CLDR_WINZONES_URL, __file__, source_hash))

  for z in map_zones:
    map_file.write("  %r: %r,\n" % z)

  map_file.write("}\n")

  map_file.close()
  return True


if __name__ == "__main__":
  update_stored_win32tz_map()
