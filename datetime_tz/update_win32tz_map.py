"""This script updates win32tz_map based on the data at the URL below"""

import os
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
try:
    from io import StringIO
except ImportError:
    import StringIO

try:
    from importlib import reload
except ImportError:
    pass
import genshi.input
import hashlib
try:
    from datetime_tz import win32tz_map
except ImportError:
    win32tz_map = None

_CLDR_WINZONES_URL = "http://www.unicode.org/repos/cldr/trunk/common/supplemental/windowsZones.xml"

def download_cldr_win32tz_map_xml():
    """Downloads the xml that maps between Windows and Olson timezone names"""
    return urllib2.urlopen(_CLDR_WINZONES_URL).read()

def create_win32tz_map(windows_zones_xml):
    """Creates a map between Windows and Olson timezone names based on the cldr
    xml mapping. Yields win32_name, olson_name, comment tuples"""
    coming_comment = None
    win32_name = None
    parser = genshi.input.XMLParser(StringIO.StringIO(windows_zones_xml))
    map_zones = {}
    zone_comments = {}
    for kind, data, _ in parser:
        if kind == genshi.core.START and str(data[0]) == 'mapZone':
            attrs = data[1]
            win32_name, olson_name = attrs.get("other"), attrs.get("type").split(" ")[0]
            map_zones[win32_name] = olson_name
        elif kind == genshi.core.END and str(data) == 'mapZone' and win32_name:
            if coming_comment:
                zone_comments[win32_name] = coming_comment
                coming_comment = None
            win32_name = None
        elif kind == genshi.core.COMMENT:
            coming_comment = data.strip()
        elif kind in (genshi.core.START, genshi.core.END, genshi.core.COMMENT):
            coming_comment = None
    for win32_name in sorted(map_zones):
        yield (win32_name, map_zones[win32_name], zone_comments.get(win32_name, None))

def update_stored_win32tz_map():
    """downloads the cldr win32 timezone map and stores it in win32tz_map.py"""
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
    comment = "Map between Windows and Olson timezones taken from %s" % (_CLDR_WINZONES_URL, )
    comment2 = "Generated automatically from datetime_tz.py"
    map_file.write("'''%s\n" % comment)
    map_file.write("%s'''\n" % comment2)
    map_file.write("source_hash = '%s' # md5 sum of xml source data\n" % (source_hash))
    map_file.write("win32timezones = {\n")
    for win32_name, olson_name, comment in map_zones:
        map_file.write("    %r: %r, # %s\n" % (win32_name, olson_name, comment or ''))
    map_file.write("}\n")
    map_file.close()
    return True

if __name__ == '__main__':
    update_stored_win32tz_map()

