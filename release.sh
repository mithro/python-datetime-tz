#!/bin/bash

rm -rf py2
virtualenv-2.7 py2
(
  . py2/bin/activate
  pip install --upgrade pip
  pip install --upgrade setuptools
  pip install -r requirements.txt
  pip install wheel
  python setup.py clean
  python setup.py sdist
  python setup.py bdist_wheel
  python setup.py sdist upload
  python setup.py bdist_wheel upload
  #PS1="py2setup # " bash --norc
)

rm -rf py3
virtualenv-3.4 py3
(
  . py3/bin/activate
  pip install --upgrade pip
  pip install --upgrade setuptools
  pip install wheel
  pip install -r requirements.txt
  python setup.py clean
  python setup.py sdist
  python setup.py bdist_wheel
  python setup.py sdist upload
  python setup.py bdist_wheel upload
  #PS1="py3setup # " bash --norc
)
