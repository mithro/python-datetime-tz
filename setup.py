from setuptools import setup, find_packages

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
