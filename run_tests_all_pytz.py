#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 et sts=2 ai:
#
# Copyright 2015 Google Inc.
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

from __future__ import print_function

"""Run the tests against every pytz version available."""

__author__ = "tansell@google.com (Tim Ansell)"

try:
  import simplejson
except ImportError:
  import json as simplejson

import glob
import os
import os.path
import subprocess
import sys
import urllib

if not hasattr(sys, 'real_prefix'):
  print("""\
This script should only be run inside a virtualenv because it is going to
modify the install version of things.
""")
  sys.exit(1)

CACHE_DIR = os.path.expanduser(os.path.join('~', '.cache', 'pypi'))
if not os.path.exists(CACHE_DIR):
  os.makedirs(CACHE_DIR)
print("Using a download cache directory of", repr(CACHE_DIR))

# Get the pytz versions from pypi
pypi_data_raw = urllib.urlopen('https://pypi.python.org/pypi/pytz/json').read()
pypi_data = simplejson.loads(pypi_data_raw)

# Hack to work around https://github.com/pypa/pip/issues/2902
def mangle_release(release):
  if release < "2007g":
    return None

  if release.endswith('r'):
     return release[:-1]+'.post0'
  return release

releases = pypi_data['releases']
# Download the pytz versions into the cache.
for release in sorted(releases):
  # These lines shouldn't be needed but pypi always runs setup.py even when
  # downloading.
  filename = '*pytz-'+release+'*'
  if glob.glob(os.path.join(CACHE_DIR, filename)):
    print("Not downloading release", release, "(already downloaded).")
    continue

  mangled = mangle_release(release)
  if not mangled:
    continue

  print("Downloading pytz release", release)
  print("="*75)
  subprocess.check_call("""\
pip install \
    --pre \
    --no-binary all \
    --download %s \
    pytz==%s
""" % (CACHE_DIR, mangled), shell=True)
  print("-"*75)

if "--download-only" in sys.argv:
  sys.exit(0)

success = []
failures = []
for release in sorted(releases):
  mangled = mangle_release(release)
  if not mangled:
    print("Skipping release", release, "as it is isn't supported")
    continue

  print()
  print("Running tests with pytz release", release)
  print("="*75)
  print("Installing...")
  subprocess.check_call("""\
pip install \
    --pre \
    --no-binary all \
    --no-index \
    --find-links=file://%s \
    pytz==%s
""" % (CACHE_DIR, mangled), shell=True)
  print("-"*75)
  print("Running tests...")
  t = subprocess.Popen('python setup.py test', shell=True)
  if t.wait() != 0:
    failures.append(release)
  else:
    success.append(release)
  print("="*75)

print("Tests passed on pytz versions:")
print(success)
print()
print("Tests failed on pytz versions:")
print(failures)
print("="*75)

if len(failures) > 0:
  sys.exit(1)
