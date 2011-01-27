#!/bin/bash

ROOT="../.."
SRC="$ROOT/snakemq"

export PYTHONPATH="$ROOT:$PYTHONPATH"

echo "===== pylint ====="
pylint --rcfile=pylint.rc $SRC

echo "===== pep8 ====="
pep8.py --exclude=libs $SRC
