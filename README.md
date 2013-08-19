
datetime_tz module
===============================================================================

This module depends on:
    * pytz - For providing the Timezone database.
    * dateutil - For providing parsing of many common formats.

A version of the python-datetime module which deeply cares about timezone
(instead of ignoring the problem). The module automatically detects your
current timezone using a variety of different methods.

The module also includes extra functionality;

    * Full integration with pytz (just give it the string of the timezone!)
    * Proper support for going to/from Unix timestamps (which are in UTC!).
    * Smart Parsing which attempts to accept all formats.


