#!/bin/bash

ROOT="../.."
SRC="$ROOT/snakemq"

export PYTHONPATH="$ROOT:$PYTHONPATH"

echo "===== pylint ====="
pylint --rcfile=pylint.rc $SRC

echo "===== pep8 ====="
# E302 expected 2 blank lines
# E501 line too long
pep8.py -r --ignore=E302,E501 --exclude=libs $SRC
