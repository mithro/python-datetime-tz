#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright 2010 Google Inc. All Rights Reserved.
#

"""
Common time zone acronyms/abbreviations for use with the datetime_tz module.

*WARNING*: There are lots of caveats when using this module which are listed
below.

CAVEAT 1: The acronyms/abbreviations are not globally unique, they are not even
unique within a region. For example, EST can mean any of,
  Eastern Standard Time in Australia (which is 10 hour ahead of UTC)
  Eastern Standard Time in North America (which is 5 hours behind UTC)

Where there are two abbreviations the more popular one will appear in the all
dictionary, while the less common one will only appear in that countries region
dictionary. IE If using all, EST will be mapped to Eastern Standard Time in
North America.

CAVEAT 2: Many of the acronyms don't map to a neat Oslon timezones. For example,
Eastern European Summer Time (EEDT) is used by many different countries in
Europe *at different times*! If the acronym does not map neatly to one zone it
is mapped to the Etc/GMT+-XX Oslon zone. This means that any date manipulations
can end up with idiot things like summer time in the middle of winter.

CAVEAT 3: The Summer/Standard time difference is really important! For an hour
each year it is needed to determine which time you are actually talking about.
    2002-10-27 01:20:00 EST != 2002-10-27 01:20:00 EDT
"""

import datetime
import pytz
import pytz.tzfile


class tzabbr(datetime.tzinfo):
  """A timezone abbreviation.

  *WARNING*: This is not a tzinfo implementation! Trying to use this as tzinfo
  object will result in failure.  We inherit from datetime.tzinfo so we can get
  through the dateutil checks.
  """
  pass


# A "marker" tzinfo object which is used to signify an unknown timezone.
unknown = datetime.tzinfo(0)


regions = {'all': {}, 'military': {}}
# Create a special alias for the all and military regions
all = regions['all']
military = regions['military']


def tzabbr_register(abbr, name, region, zone, dst):
  """Register a new timezone abbreviation in the global registry.

  If another abbreviation with the same name has already been registered it new
  abbreviation will only be registered in region specific dictionary.
  """
  newabbr = tzabbr()
  newabbr.abbr = abbr
  newabbr.name = name
  newabbr.region = region
  newabbr.zone = zone
  newabbr.dst = dst

  if abbr not in all:
    all[abbr] = newabbr

  if not region in regions:
    regions[region] = {}

  assert abbr not in regions[region]
  regions[region][abbr] = newabbr


def tzinfos_create(use_region):
  abbrs = regions[use_region]

  def tzinfos(abbr, offset):
    if abbr:
      if abbr in abbrs:
        result = abbrs[abbr]
        if offset:
          # FIXME: Check the offset matches the abbreviation we just selected.
          pass
        return result
      else:
        raise ValueError, "Unknown timezone found %s" % abbr
    if offset == 0:
      return pytz.utc
    if offset:
      return pytz.FixedOffset(offset/60)
    return unknown

  return tzinfos


# Create a special alias for the all tzinfos
tzinfos = tzinfos_create('all')


# Create the abbreviations.
# *WARNING*: Order matters!
tzabbr_register("A", u"Alpha Time Zone", u"Military", "Etc/GMT-1", False)
tzabbr_register("ACDT", u"Australian Central Daylight Time", u"Australia",
                "Australia/Adelaide", True)
tzabbr_register("ACST", u"Australian Central Standard Time", u"Australia",
                "Australia/Adelaide", False)
tzabbr_register("ADT", u"Atlantic Daylight Time", u"North America",
                "America/Halifax", True)
tzabbr_register("AEDT", u"Australian Eastern Daylight Time", u"Australia",
                "Australia/Sydney", True)
tzabbr_register("AEST", u"Australian Eastern Standard Time", u"Australia",
                "Australia/Sydney", False)
tzabbr_register("AKDT", u"Alaska Daylight Time", u"North America",
                "US/Alaska", True)
tzabbr_register("AKST", u"Alaska Standard Time", u"North America",
                "US/Alaska", False)
tzabbr_register("AST", u"Atlantic Standard Time", u"North America",
                "America/Halifax", False)
tzabbr_register("AWDT", u"Australian Western Daylight Time", u"Australia",
                "Australia/West", True)
tzabbr_register("AWST", u"Australian Western Standard Time", u"Australia",
                "Australia/West", False)
tzabbr_register("B", u"Bravo Time Zone", u"Military", "Etc/GMT-2", False)
tzabbr_register("BST", u"British Summer Time", u"Europe", "Europe/London", True)
tzabbr_register("C", u"Charlie Time Zone", u"Military", "Etc/GMT-2", False)
tzabbr_register("CDT", u"Central Daylight Time", u"North America",
                "US/Central", True)
tzabbr_register("CEDT", u"Central European Daylight Time", u"Europe",
                "Etc/GMT+2", True)
tzabbr_register("CEST", u"Central European Summer Time", u"Europe",
                "Etc/GMT+2", True)
tzabbr_register("CET", u"Central European Time", u"Europe", "Etc/GMT+1", False)
tzabbr_register("CST", u"Central Standard Time", u"North America",
                "US/Central", False)
tzabbr_register("CXT", u"Christmas Island Time", u"Australia",
                "Indian/Christmas", False)
tzabbr_register("D", u"Delta Time Zone", u"Military", "Etc/GMT-2", False)
tzabbr_register("E", u"Echo Time Zone", u"Military", "Etc/GMT-2", False)
tzabbr_register("EDT", u"Eastern Daylight Time", u"North America",
                "US/Eastern", True)
tzabbr_register("EEDT", u"Eastern European Daylight Time", u"Europe",
                "Etc/GMT+3", True)
tzabbr_register("EEST", u"Eastern European Summer Time", u"Europe",
                "Etc/GMT+3", True)
tzabbr_register("EET", u"Eastern European Time", u"Europe", "Etc/GMT+2", False)
tzabbr_register("EST", u"Eastern Standard Time", u"North America",
                "US/Eastern", False)
tzabbr_register("F", u"Foxtrot Time Zone", u"Military", "Etc/GMT-6", False)
tzabbr_register("G", u"Golf Time Zone", u"Military", "Etc/GMT-7", False)
tzabbr_register("GMT", u"Greenwich Mean Time", u"Europe", pytz.utc, False)
tzabbr_register("H", u"Hotel Time Zone", u"Military", "Etc/GMT-8", False)
#tzabbr_register("HAA", u"Heure Avancée de l'Atlantique", u"North America", u"UTC - 3 hours")
#tzabbr_register("HAC", u"Heure Avancée du Centre", u"North America", u"UTC - 5 hours")
tzabbr_register("HADT", u"Hawaii-Aleutian Daylight Time", u"North America",
                "Pacific/Honolulu", True)
#tzabbr_register("HAE", u"Heure Avancée de l'Est", u"North America", u"UTC - 4 hours")
#tzabbr_register("HAP", u"Heure Avancée du Pacifique", u"North America", u"UTC - 7 hours")
#tzabbr_register("HAR", u"Heure Avancée des Rocheuses", u"North America", u"UTC - 6 hours")
tzabbr_register("HAST", u"Hawaii-Aleutian Standard Time", u"North America",
                "Pacific/Honolulu", False)
#tzabbr_register("HAT", u"Heure Avancée de Terre-Neuve", u"North America", u"UTC - 2:30 hours")
#tzabbr_register("HAY", u"Heure Avancée du Yukon", u"North America", u"UTC - 8 hours")
tzabbr_register("HDT", u"Hawaii Daylight Time", u"North America",
                "Pacific/Honolulu", True)
#tzabbr_register("HNA", u"Heure Normale de l'Atlantique", u"North America", u"UTC - 4 hours")
#tzabbr_register("HNC", u"Heure Normale du Centre", u"North America", u"UTC - 6 hours")
#tzabbr_register("HNE", u"Heure Normale de l'Est", u"North America", u"UTC - 5 hours")
#tzabbr_register("HNP", u"Heure Normale du Pacifique", u"North America", u"UTC - 8 hours")
#tzabbr_register("HNR", u"Heure Normale des Rocheuses", u"North America", u"UTC - 7 hours")
#tzabbr_register("HNT", u"Heure Normale de Terre-Neuve", u"North America", u"UTC - 3:30 hours")
#tzabbr_register("HNY", u"Heure Normale du Yukon", u"North America", u"UTC - 9 hours")
tzabbr_register("HST", u"Hawaii Standard Time", u"North America",
                "Pacific/Honolulu", False)
tzabbr_register("I", u"India Time Zone", u"Military", "Etc/GMT-9", False)
tzabbr_register("IST", u"Irish Summer Time", u"Europe", "Europe/Dublin", True)
tzabbr_register("K", u"Kilo Time Zone", u"Military", "Etc/GMT-10", False)
tzabbr_register("L", u"Lima Time Zone", u"Military", "Etc/GMT-11", False)
tzabbr_register("M", u"Mike Time Zone", u"Military", "Etc/GMT-12", False)
tzabbr_register("MDT", u"Mountain Daylight Time", u"North America",
                "US/Mountain", True)
#tzabbr_register("MESZ", u"Mitteleuroäische Sommerzeit", u"Europe", u"UTC + 2 hours")
#tzabbr_register("MEZ", u"Mitteleuropäische Zeit", u"Europe", u"UTC + 1 hour")
tzabbr_register("MSD", u"Moscow Daylight Time", u"Europe",
                "Europe/Moscow", True)
tzabbr_register("MSK", u"Moscow Standard Time", u"Europe",
                "Europe/Moscow", False)
tzabbr_register("MST", u"Mountain Standard Time", u"North America",
                "US/Mountain", False)
tzabbr_register("N", u"November Time Zone", u"Military", "Etc/GMT+1", False)
tzabbr_register("NDT", u"Newfoundland Daylight Time", u"North America",
                "America/St_Johns", True)
tzabbr_register("NFT", u"Norfolk (Island) Time", u"Australia",
                "Pacific/Norfolk", False)
tzabbr_register("NST", u"Newfoundland Standard Time", u"North America",
                "America/St_Johns", False)
tzabbr_register("O", u"Oscar Time Zone", u"Military", "Etc/GMT+2", False)
tzabbr_register("P", u"Papa Time Zone", u"Military", "Etc/GMT+3", False)
tzabbr_register("PDT", u"Pacific Daylight Time", u"North America",
                "US/Pacific", True)
tzabbr_register("PST", u"Pacific Standard Time", u"North America",
                "US/Pacific", False)
tzabbr_register("Q", u"Quebec Time Zone", u"Military", "Etc/GMT+4", False)
tzabbr_register("R", u"Romeo Time Zone", u"Military", "Etc/GMT+5", False)
tzabbr_register("S", u"Sierra Time Zone", u"Military", "Etc/GMT+6", False)
tzabbr_register("T", u"Tango Time Zone", u"Military", "Etc/GMT+7", False)
tzabbr_register("U", u"Uniform Time Zone", u"Military", "Etc/GMT+8", False)
tzabbr_register("UTC", u"Coordinated Universal Time", u"Europe",
                pytz.utc, False)
tzabbr_register("V", u"Victor Time Zone", u"Military", "Etc/GMT+9", False)
tzabbr_register("W", u"Whiskey Time Zone", u"Military", "Etc/GMT+10", False)
tzabbr_register("WDT", u"Western Daylight Time", u"Australia",
                "Australia/West", True)
tzabbr_register("WEDT", u"Western European Daylight Time", u"Europe",
                "Etc/GMT+1", True)
tzabbr_register("WEST", u"Western European Summer Time", u"Europe",
                "Etc/GMT+1", True)
tzabbr_register("WET", u"Western European Time", u"Europe", pytz.utc, False)
tzabbr_register("WST", u"Western Standard Time", u"Australia",
                "Australia/West", False)
tzabbr_register("X", u"X-ray Time Zone", u"Military", "Etc/GMT+11", False)
tzabbr_register("Y", u"Yankee Time Zone", u"Military", "Etc/GMT+12", False)
tzabbr_register("Z", u"Zulu Time Zone", u"Military", pytz.utc, False)
