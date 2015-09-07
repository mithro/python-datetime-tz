
datetime_tz module
===============================================================================

A version of the python-datetime module which deeply cares about timezone
(instead of ignoring the problem). The module automatically detects your
current timezone using a variety of different methods.

The module also includes extra functionality;

 * Full integration with pytz (just give it the string of the timezone!)
 * Proper support for going to/from Unix timestamps (which are in UTC!).
 * Smart Parsing which attempts to accept all formats.

This module depends on:

 * pytz - For providing the Timezone database.
 * dateutil - For providing parsing of many common formats.

For development:
 * PyLint - Needed for checking for link.
 * Genshi - Needed for building windows mapping file.

[![Build Status](https://travis-ci.org/mithro/python-datetime-tz.png?branch=master)](https://travis-ci.org/mithro/python-datetime-tz)
[![Coverage Status](https://coveralls.io/repos/mithro/python-datetime-tz/badge.png)](https://coveralls.io/r/mithro/python-datetime-tz)
[![PyPi Version](https://pypip.in/v/python-datetime-tz/badge.png)](https://crate.io/packages/python-coveralls/)
[![PyPi Downloads](https://pypip.in/d/python-datetime-tz/badge.png)](https://crate.io/packages/python-coveralls/)
