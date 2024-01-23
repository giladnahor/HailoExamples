import ipdb; ipdb.set_trace()
import json
from pathlib import Path

import hailo
import numpy as np

# Importing VideoFrame before importing GST is must
from gsthailo import VideoFrame
from gi.repository import Gst

from SerialControl import arduino

current_tracked_id = None
SWITCH_COUNTER_MAX = 30 # used for smoothly switching between ids in time domain
TRACK_WIDTH_RATIO = 0.7 # used for smoothly switching between ids in size domain
id_switch_counter = 0
last_x = 0.5
last_y = 0.5
def run(video_frame: VideoFrame):
    global id_switch_counter, current_tracked_id, last_x, last_y
    # handle the frame
    detections = video_frame.roi.get_objects_typed(hailo.HAILO_DETECTION)
    if (detections is None) or (len(detections) == 0):
        return Gst.FlowReturn.OK
    # find the largest detection
    max_width = 0
    tracked_width = 0
    max_detection = None
    tracked_detection = None
    for i, detection in enumerate(detections):
        if detection.get_label() != 'face':
            continue
        bbox = detection.get_bbox()
        width = bbox.width()
        ids = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if (len(ids) == 0): # not tracked
            continue
        id = ids[0].get_id()
        if id == current_tracked_id:
            tracked_detection = detection
            tracked_width = width
        if width > max_width:
            max_width = width
            max_detection = detection
    if max_detection is None: # no face detected
        return Gst.FlowReturn.OK
    if tracked_detection is None:
        tracked_detection = max_detection
        current_tracked_id = max_detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()
    if (tracked_detection != max_detection) and (tracked_width < max_width * TRACK_WIDTH_RATIO):
        if id_switch_counter > SWITCH_COUNTER_MAX:
            id_switch_counter = 0
            current_tracked_id = max_detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()
            tracked_detection = max_detection
        else:
            id_switch_counter += 1
            print(f'Using tracked id, counter = {id_switch_counter}')
    else:
        id_switch_counter = 0
    bbox = tracked_detection.get_bbox()
    x = (bbox.xmax() + bbox.xmin()) / 2
    y = (bbox.ymax() + bbox.ymin()) / 2
    # landmarks = max_detection.get_objects_typed(hailo.HAILO_LANDMARKS)
    smoothing_factor = 0.5
    if (abs(x - last_x) > 0.2) or (abs(y - last_y) > 0.2):
        smoothing_factor = 0.3
        print('Using low smoothing factor')
    x = x * smoothing_factor + last_x * (1 - smoothing_factor)
    y = y * smoothing_factor + last_y * (1 - smoothing_factor)
    last_x = x
    last_y = y
    # print(f'x={x}, y={y}')
    arduino.update_eye_data(cam_x=x, cam_y=y, eye_x=x, eye_y=y, blink=False)
    arduino.send_eye_data()
    if (x==0) and (y==0):
        import ipdb; ipdb.set_trace()
    
    
    return Gst.FlowReturn.OK

def close():
    arduino.close()
