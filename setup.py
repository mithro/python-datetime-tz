try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys

data = dict(
    name='python-datetime_tz',
    version='0.1',
    author='Tim Ansell',
    author_email='mithro@mithis.com',
    packages=['datetime_tz'],
    install_requires=['pytz'],
    py_modules=['datetime_tz','pytz_abbr'],
    test_suite='tests',
)

if sys.version[:3] < '3.0':
    data['install_requires'].append('python-dateutil >= 1.4')
else:
    data['install_requires'].append('python-dateutil == 2.0')

setup(**data)
