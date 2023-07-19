#!/bin/bash
set -e
latest=$(find /tmp/profile/graphic/pipeline* -printf '%T+ %p\n' | sort -r | head -n 1 | awk '{ print $NF }')
dot ${latest}  -T x11 &
