#!/bin/bash -e
rm -rf release_env
rm -rf dist/
python3 -m virtualenv release_env
source release_env/bin/activate
(
pip install -U pip
pip install -U twine
pip install -U pep517
# Run the build
python -m pep517.build . -b -s

# Upload the files with twine
twine upload dist/*
)
