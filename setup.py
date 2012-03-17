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
)

if sys.version[:3] < '3.0':
    data['install_requires'].append('python-dateutil == 1.5')
else:
    data['install_requires'].append('python-dateutil == 2.0')

setup(**data)
