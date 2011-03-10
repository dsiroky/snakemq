#!/bin/bash

SVNVER=`svn info | grep Revision | cut -d ' ' -f 2`

tar -zcv \
  --exclude .svn \
  --exclude '*.py[co]' \
  -f snakemq-$SVNVER.tgz \
  snakemq
