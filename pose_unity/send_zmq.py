import json
from pathlib import Path

import hailo
import numpy as np

import sys
import zmq
import cv2

# Importing VideoFrame before importing GST is must
from gsthailo import VideoFrame
from gi.repository import Gst

context = zmq.Context()
socket = None

def init_socket(port=5555):
    global socket
    socket = context.socket(zmq.PUSH)
    socket.bind('tcp://*:{}'.format(port))
    socket.setsockopt(zmq.SNDHWM, 4)  # limit Q size
    # Set the LINGER option to 1000ms
    socket.setsockopt(zmq.LINGER, 0)

def debug(video_frame: VideoFrame):
    try:
        # import ipdb; ipdb.set_trace()
        metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
        meta = metas[0].get_user_string()
        print(f'DEBUG {meta}')
    except:
        print(f'DEBUG NO META')
    return Gst.FlowReturn.OK


def run(video_frame: VideoFrame):
    global socket
    port = 5555
    if socket is None:
        init_socket(port)
        print("init socket {}".format(port))
    image = [] # Bytes
    skeletons = []
    ids = [] # Ints
    try:
        detections = video_frame.roi.get_objects_typed(hailo.HAILO_DETECTION)
        for d in detections:
            if str(d.get_label()) != 'person':
                continue
            id = d.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            tracker_id = id[0].get_id()
            skeleton = {'X': [], 'Y': [], 'ID': tracker_id}
            ids.append(tracker_id)
            landmarks = d.get_objects_typed(hailo.HAILO_LANDMARKS)
            ps = landmarks[0].get_points()
            bbox = d.get_bbox()
            for p in ps:
                skeleton["X"].append(p.x() * bbox.width() + bbox.xmin())
                skeleton["Y"].append(p.y() * bbox.height() + bbox.ymin())
            skeletons.append(skeleton)
        success, map_info = video_frame.buffer.map(Gst.MapFlags.READ)
        shape = (320, 320, 3)
        frame = np.ndarray(
            shape=shape,
            dtype=np.uint8,
            buffer=map_info.data)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = cv2.imencode('.jpg', frame)[1].ravel().tolist()
        
        data = {
            'skeletons': skeletons,
            'ids': ids,
            'image': image,
        }
        socket.send_json(data, flags=zmq.DONTWAIT)    
        print(f'ZMQ plugin sent data')
        video_frame.buffer.unmap(map_info)
    except zmq.Again:
        # No clients available to receive the message
        pass
    except Exception as e:
        print(f'ZMQ plugin enountered error {e}')
    return Gst.FlowReturn.OK

