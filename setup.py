try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='python-datetime_tz',
    version='0.1',
    author='Tim Ansell',
    author_email='mithro@mithis.com',
    packages=['datetime_tz'],
    install_requires=[
        'python-dateutil == 1.5',
        'pytz'
    ]
)
