from setuptools import setup, find_packages

setup(
    name='python-datetime_tz',
    version='0.1',
    author='Tim Ansell',
    author_email='mithro@mithis.com',
    
    packages=find_packages(),
    include_package_data=True,
    
    install_requires=[
        'python-dateutil',
        'pytz'
    ]
)
