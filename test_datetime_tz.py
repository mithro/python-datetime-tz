# -*- coding: utf-8 -*-

from j5.OS import datetime_tz
import datetime
import pytz

def test_compare_tz_first():
    a = datetime.datetime(2012,3,4,1,2,3)
    b = datetime_tz.datetime_tz(2012,3,4,1,2,3)
    assert a == b

def test_compare_tz_second():
    a = datetime.datetime(2012,3,4,1,2,3)
    b = datetime_tz.datetime_tz(2012,3,4,1,2,3)
    assert b == a

def test_compare_greater():
    a = datetime.datetime(2012,3,4,3,2,3)
    b = datetime_tz.datetime_tz(2012,3,4,1,2,3)
    assert a > b
    assert a >= b
    a = datetime.datetime(2012,3,3,3,2,3)
    assert b > a
    assert b >= a

def test_compare_less():
    a = datetime.datetime(2012,3,4,3,2,3)
    b = datetime_tz.datetime_tz(2012,3,4,1,2,3)
    assert b < a
    assert b <= a
    a = datetime.datetime(2012,3,3,3,2,3)
    assert a < b
    assert a <= b

def test_compare_notequal():
    a = datetime.datetime(2012,3,4,3,2,3)
    b = datetime_tz.datetime_tz(2012,3,4,1,2,3)
    assert a != b
    assert b != a

def test_instantiation():
    a = datetime.datetime(2012, 3, 4, 3, 2, 3)
    c = None
    try:
        c = datetime_tz.datetime_tz(a)
    except TypeError as e:
        if not e.message == "Must specify a timezone!":
            c = False
    assert c is None

_original_localtz = datetime_tz.localtz

def patch_datetime_module():
    """Patches the datetime module to work on virtual time"""
    datetime_tz.localtz = localtz

def unpatch_datetime_module():
    """Restores the datetime module to work on real time"""
    datetime_tz.localtz = _original_localtz

def localtz():
    return datetime.datetime.localtz_override

class TestDST():
    def test_DST_missing_hour(self):
        """Test missing hour"""
        datetime.datetime.localtz_override = pytz.timezone("America/Chicago")
        exc = pytz.NonExistentTimeError

        assert self.runTest(datetime_tz.datetime_tz, exc, True, 2014, 03, 9, 1, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, True, datetime.datetime(2014, 03, 9, 1, 10, 0, 0))

        assert self.runTest(datetime_tz.datetime_tz, exc, False, 2014, 03, 9, 2, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, False, datetime.datetime(2014, 03, 9, 2, 10, 0, 0))

        assert self.runTest(datetime_tz.datetime_tz, exc, True, 2014, 03, 9, 3, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, True, datetime.datetime(2014, 03, 9, 3, 10, 0, 0))


    def test_DST_ambiguous_hour(self):
        """Test Ambiguous Hour"""
        datetime.datetime.localtz_override = pytz.timezone("America/Chicago")
        exc = pytz.AmbiguousTimeError

        assert self.runTest(datetime_tz.datetime_tz, exc, True, 2013, 11, 3, 0, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, True, datetime.datetime(2013, 11, 3, 0, 10, 0, 0))

        assert self.runTest(datetime_tz.datetime_tz, exc, False, 2013, 11, 3, 1, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, False, datetime.datetime(2013, 11, 3, 1, 10, 0, 0))

        assert self.runTest(datetime_tz.datetime_tz, exc, True, 2013, 11, 3, 2, 10, 0, 0)
        assert self.runTest(datetime_tz.localize, exc, True, datetime.datetime(2013, 11, 3, 2, 10, 0, 0))

    def test_DST_around_init(self):
        """Test around the init for TypeError"""
        tz = pytz.timezone("America/Chicago")
        datetime.datetime.localtz_override = tz
        exc = pytz.AmbiguousTimeError

        assert self.runTest(datetime_tz.datetime_tz, exc, False, 2013, 11, 3, 1, 10, 0, 0)
        assert self.runTest(datetime_tz.datetime_tz, exc, True, 2013, 11, 3, 2, 10, 0, 0)

        assert self.runTest(datetime_tz.datetime_tz, TypeError, False, datetime.datetime(2013, 11, 3, 1, 10, 0, 0))
        assert self.runTest(datetime_tz.datetime_tz, exc, True,  datetime.datetime(2013, 11, 3, 1, 10, 0, 0, tzinfo=tz))

        assert self.runTest(datetime_tz.datetime_tz, TypeError, False,  datetime.datetime(2013, 11, 3, 1, 10, 0, 0))
        assert self.runTest(datetime_tz.datetime_tz, exc, True,  datetime.datetime(2013, 11, 3, 1, 10, 0, 0, tzinfo=tz))

        assert self.runTest(datetime_tz.datetime_tz, TypeError, False,  datetime.datetime(2013, 11, 3, 1, 10, 0, 0))
        assert self.runTest(datetime_tz.datetime_tz, exc, True,  datetime.datetime(2013, 11, 3, 1, 10, 0, 0, tzinfo=tz))


    @classmethod
    def runTest(self,func, exc, should_work, *args, **kwargs):
        a = None
        try:
            a = func(*args, **kwargs)
        except exc as e:
            pass
        if should_work is None:
            return True # We don't care either way, but we need to still raise other Exceptions
        return not (a is None) == should_work

    def setup(self):
        patch_datetime_module()

    def teardown(self):
        unpatch_datetime_module()