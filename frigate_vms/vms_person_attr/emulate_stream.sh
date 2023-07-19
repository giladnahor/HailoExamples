#!/bin/bash
set -e
pipeline="v4l2src device=/dev/video0 ! videoconvert ! videoscale ! \
video/x-raw,width=960, height=720, pixel-aspect-ratio=1/1 ,format=I420 ! \
hailopython name=hailopython_run_birdseye qos=false module=/local/workspace/tappas/apps/gstreamer/frigate_vms/common/send_zmq.py function=run_birdseye2 ! \
videoconvert ! autovideosink"
gst-launch-1.0 -v $pipeline