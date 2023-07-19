import json
from pathlib import Path

import hailo
import numpy as np

import sys
import zmq

# Importing VideoFrame before importing GST is must
from gsthailo import VideoFrame
from gi.repository import Gst

context = zmq.Context()
sockets = {}

def init_socket(stream_id, port=5557):
    sockets[stream_id] = context.socket(zmq.PUB)
    sockets[stream_id].bind('tcp://*:{}'.format(port))
    sockets[stream_id].setsockopt(zmq.SNDHWM, 4)  # limit Q size
    
def debug(video_frame: VideoFrame):
    try:
        # import ipdb; ipdb.set_trace()
        metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
        meta = metas[0].get_user_string()
        print(f'DEBUG {meta}')
    except:
        print(f'DEBUG NO META')
    return Gst.FlowReturn.OK

def debug2(video_frame: VideoFrame):
    try:
        metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
        meta = metas[0].get_user_string()
        detections = video_frame.roi.get_objects_typed(hailo.HAILO_DETECTION)
        labels = [d.get_label() for d in detections]
        classifications = [d.get_objects_typed(hailo.HAILO_CLASSIFICATION) for d in detections]
        class_type = []
        for c in classifications:
            if len(c) > 0:
                class_type.append(c[0].get_classification_type())
        print(f'DEBUG2 {meta} {labels} {class_type}')
    except:
        print(f'DEBUG2 NO META')
    return Gst.FlowReturn.OK
def debug3(video_frame: VideoFrame):
    try:
        metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
        meta = metas[0].get_user_string()
        detections = video_frame.roi.get_objects_typed(hailo.HAILO_DETECTION)
        labels = [d.get_label() for d in detections]
        classifications = [d.get_objects_typed(hailo.HAILO_CLASSIFICATION) for d in detections]
        class_type = []
        for c in classifications:
            if len(c) > 0:
                class_type.append(c[0].get_classification_type())
        print(f'DEBUG3 {meta} {labels} {class_type}')
    except:
        print(f'DEBUG3 NO META')
    return Gst.FlowReturn.OK

def run_camera(video_frame: VideoFrame):
    stream_id = 0
    port = 5557
    # import ipdb; ipdb.set_trace()
    metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
    meta = metas[0].get_user_string()
    # print(f'run camera {meta}')
    if stream_id not in sockets:
        init_socket(stream_id, port)
        print("init socket {}".format(port))
    zmq_send(video_frame.buffer, video_frame.roi, sockets[stream_id], meta)
    return Gst.FlowReturn.OK

def run_lpr(video_frame: VideoFrame):
    stream_id = 2
    port = 5558
    metas = video_frame.roi.get_objects_typed(hailo.HAILO_USER_META)
    meta = metas[0].get_user_string()
    if stream_id not in sockets:
        init_socket(stream_id, port)
        print("init socket {}".format(port))
    zmq_send(video_frame.buffer, video_frame.roi, sockets[stream_id], meta, shape=(640, 540, 1))
    return Gst.FlowReturn.OK

def run_birdseye(video_frame: VideoFrame):
    stream_id = 1
    port = 6666
    if stream_id not in sockets:
        init_socket(stream_id, port)
        print("init socket {}".format(port))
    zmq_send(video_frame.buffer, video_frame.roi, sockets[stream_id], only_frame=True, shape=(960, 1080, 1))
    return Gst.FlowReturn.OK

def run_birdseye2(video_frame: VideoFrame):
    stream_id = 1
    port = 7666
    if stream_id not in sockets:
        init_socket(stream_id, port)
        print("init socket {}".format(port))
    zmq_send(video_frame.buffer, video_frame.roi, sockets[stream_id], only_frame=True, shape=(960, 1080, 1))
    return Gst.FlowReturn.OK


def run(video_frame: VideoFrame):
    run_camera(video_frame)
    return Gst.FlowReturn.OK

labels_list = ['person', 'face', 'car']

def zmq_send(gst_buff: Gst.Buffer, roi: hailo.HailoROI, socket, meta=None, only_frame=False, shape=(640, 960, 1), format='I420'):
    success, map_info = gst_buff.map(Gst.MapFlags.READ)
    if format == 'I420':
        real_shape = (shape[0], int(shape[1]/1.5), 1)
    else:
        real_shape = shape
    frame = np.ndarray(
        shape=shape,
        dtype=np.uint8,
        buffer=map_info.data)
    if only_frame:
        packet = frame
    else:
        detections = []
        for obj in roi.get_objects_typed(hailo.HAILO_DETECTION):
            if obj.get_type() == hailo.HAILO_DETECTION:
                label = obj.get_label()
                if label not in labels_list:
                    continue
                bbox = obj.get_bbox()
                xmin = int(np.clip(bbox.xmin(), 0, 1) * real_shape[1])
                ymin = int(np.clip(bbox.ymin(), 0, 1) * real_shape[0])
                xmax = int(np.clip(bbox.xmax(), 0, 1) * real_shape[1])
                ymax = int(np.clip(bbox.ymax(), 0, 1) * real_shape[0])
                # get classification attributes
                classifications = []
                for classification in obj.get_objects_typed(hailo.HAILO_CLASSIFICATION):
                    classifications.append({
                        'label': classification.get_label(),
                        'score': float(classification.get_confidence()),
                        'type': classification.get_classification_type()
                    })
                
                # get tracking id
                tracking_id = None
                ids = obj.get_objects_typed(hailo.HAILO_UNIQUE_ID)
                if ids:
                    tracking_id = ids[0].get_id()
                # build detection structure
                det = (
                    label,
                    obj.get_confidence(),
                    (xmin, ymin, xmax, ymax),
                    (xmax - xmin) * (ymax - ymin),
                    (0, 0, real_shape[0], real_shape[1]),  # region,
                    classifications,
                    tracking_id,
                )
                detections.append(det)
        packet = (frame, detections, meta)
    socket.send_pyobj(packet)
    gst_buff.unmap(map_info)
