try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys

data = dict(
    name='python-datetime-tz',
    version='0.2',
    author='Tim Ansell',
    author_email='mithro@mithis.com',
    url='http://github.com/mithro/python-datetime-tz',
    description="""\
A drop in replacement for Python's datetime module which cares deeply about timezones.
""",
    license="License :: OSI Approved :: Apache Software License",
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Internationalization",
    ],
    packages=['datetime_tz'],
    install_requires=['pytz'],
    py_modules=['datetime_tz','datetime_tz.pytz_abbr'],
    test_suite='tests',
)

if sys.version[:3] < '3.0':
    data['install_requires'].append('python-dateutil >= 1.4, < 2.0')
else:
    data['install_requires'].append('python-dateutil == 2.0')

setup(**data)
