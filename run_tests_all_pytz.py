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
import pprint
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

releases = pypi_data['releases']
# Download the pytz versions into the cache.
for release in sorted(releases):
  if release < "2007g":
    continue

  # These lines shouldn't be needed but pypi always runs setup.py even when
  # downloading.
  filename = '*pytz-'+release+'*'
  if glob.glob(os.path.join(CACHE_DIR, filename)):
    print("Skipping release", release, "as it is already downloaded.")
    continue

  print("Downloading pytz release", release)
  print("="*75)
  subprocess.check_call("""\
pip install \
    --download %s \
    pytz==%s
""" % (CACHE_DIR, release), shell=True)
  print("-"*75)

if "--download-only" in sys.argv:
  sys.exit(0)

success = []
failures = []
for release in sorted(releases):
  # Skip very old versions
  if release < "2007g":
    print("Skipping release", release, "as it is isn't supported")
    continue

  print()
  print("Running tests with pytz release", release)
  print("="*75)
  print("Installing...")
  subprocess.check_call("""\
pip install \
    --no-index \
    --find-links=file://%s \
    pytz==%s
""" % (CACHE_DIR, release), shell=True)
  print("-"*75)
  print("Running tests...")
  t = subprocess.Popen('python setup.py test', shell=True)
  if t.wait() != 0:
    failures.append(release)
  else:
    success.append(release)
    #import time
    #time.sleep(30)
  print("="*75)

print("Tests passed on pytz versions:")
pprint.pprint(success)
print()
print("Tests failed on pytz versions:")
pprint.pprint(failures)
print("="*75)

if len(failures) > 0:
  sys.exit(1)
