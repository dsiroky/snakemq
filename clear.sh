#!/bin/bash

find -name '*.py[co]' -delete
find -name __pycache__ -exec rm -Rf {} \;
rm -Rf dist build

