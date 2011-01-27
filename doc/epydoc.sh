#!/bin/bash

export PYTHONPATH=..:$PYTHONPATH

rm -Rf doc/epydoc/*
epydoc --config epydoc.conf

