#!/bin/bash


# Determine if lfixer script is still running.
# Usually this means, that latest commit on progress DB was no more than 1 minute ago.

LFIXER_SECONDS_TTL="${LFIXER_SECONDS_TTL:-60}"
LFIXER_DATABASE="${1:-.lfixer.db}"


function healthcheck {
    # Fail if modified more than LFIXER_SECONDS_TTL seconds.
    lastModificationSeconds=`date +%s -r ${1}`
    currentSeconds=`date +%s`
    secondsPassed=$((currentSeconds-lastModificationSeconds))
    test $secondsPassed -lt $LFIXER_SECONDS_TTL
};


healthcheck "${LFIXER_DATABASE}"
