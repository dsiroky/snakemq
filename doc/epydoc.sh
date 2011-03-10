#!/bin/bash

export PYTHONPATH=..:../tests:$PYTHONPATH

rm -Rf doc/epydoc/*
epydoc --config epydoc.conf

