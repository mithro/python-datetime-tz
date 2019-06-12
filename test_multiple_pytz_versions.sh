#!/usr/bin/env bash
set -e

versions=( 2011g 2014.1 2016.1 2016.6.1 2017.2 2018.3 2018.9 )
for version in ${versions[@]}; do
  PYTZ_VERSION="==$version" tox -e py
done


