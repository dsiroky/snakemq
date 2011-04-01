#!/bin/sh

OUTPUT=coverage_report

if [ ! -d $OUTPUT ]; then mkdir $OUTPUT; fi
rm -Rf $OUTPUT/*
python-coverage run --omit "/usr/*" --branch run.py
python-coverage html -d $OUTPUT

