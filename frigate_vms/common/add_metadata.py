import json
from pathlib import Path

import hailo
import numpy as np

# Importing VideoFrame before importing GST is must
from gsthailo import VideoFrame
from gi.repository import Gst

def lpr0(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('lpr0')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera0(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera0')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera1(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera1')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera2(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera2')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera3(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera3')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera4(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera4')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera5(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera5')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera6(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera6')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def camera7(video_frame: VideoFrame):
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera7')
    video_frame.roi.add_object(meta)   
    return Gst.FlowReturn.OK

def run(video_frame: VideoFrame):
    # meta = hailo.HailoClassification("streamID", 0, "camera0", 1.0)
    meta = hailo.HailoUserMeta()
    meta.set_user_string('camera0')
    video_frame.roi.add_object(meta)
    return Gst.FlowReturn.OK

