#!/usr/bin/env python3

import os
from re import T
import sys
import threading
import time
import argparse
import logging
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GLib, GObject, Gst

# Debug lines
# export GST_TRACERS="framerate(period=1,filter=funnel)"


# this is used to let vscode know about spawned threads
#import ptvsd

###########################
# ENVIRONMENT VARIABLES
###########################

# get environment variables
TAPPAS_WORKSPACE = os.environ['TAPPAS_WORKSPACE']

APP_DIR=f'{TAPPAS_WORKSPACE}/apps/gstreamer/frigate_vms/vms_person_attr/'
COMMON_DIR=f'{TAPPAS_WORKSPACE}/apps/gstreamer/frigate_vms/common'
RESOURCES_DIR=f'{APP_DIR}/resources'
POSTPROCESS_DIR=f'{TAPPAS_WORKSPACE}/apps/gstreamer/libs/post_processes/'
VMS_POSTPROCESS_DIR=f'{TAPPAS_WORKSPACE}/apps/gstreamer/libs/apps/vms/'
DEFAULT_JSON_CONFIG_PATH=f'{RESOURCES_DIR}/configs/yolov5_personface.json'
FUNCTION_NAME='yolov5_personface'
DEFAULT_VDEVICE_KEY='1'
DETECTION_HEF_PATH=f'{RESOURCES_DIR}/yolov5s_personface_rgba.hef'
FACE_ATTR_HEF_PATH=f'{RESOURCES_DIR}/face_attr_resnet_v1_18_rgbx.hef'
PERSON_ATTR_HEF_PATH=f'{RESOURCES_DIR}/person_attr_resnet_v1_18_rgbx.hef'
DEFAULT_DETECTION_POSTPROCESS_SO=f'{POSTPROCESS_DIR}/libyolo_post.so'
FACE_ATTR_POSTPROCESS_SO=f'{VMS_POSTPROCESS_DIR}/libface_attributes_post.so'
PERSON_ATTR_POSTPROCESS_SO=f'{VMS_POSTPROCESS_DIR}/libperson_attributes_post.so'
CROPING_ALGORITHMS_DIR=f'{POSTPROCESS_DIR}/cropping_algorithms'
DEFAULT_CROP_SO=f'{CROPING_ALGORITHMS_DIR}/libvms_croppers.so'


RTSP_SOURCES= [
"rtsp://10.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://20.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://30.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://40.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://50.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://60.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://70.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo",
"rtsp://80.0.0.200/axis-media/media.amp/?fps=25 user-id=root user-pw=hailo"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

###########################
# common functions
###########################
import subprocess
import re

def get_video_sink_element():
    try:
        if os.environ['XV_SUPPORTED'] == 'true':
            return 'xvimagesink'
    except KeyError:
        pass
    # TBD ximagesink
    return 'autovideosink'

def get_hailo_bus_id():
    res = subprocess.run(['hailortcli', 'scan'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    devices = re.findall("\d{4}:\d{2}:\d{2}\.\d",res)
    return devices[0]

def create_compositor_locations(rows=4, cols=8, xres=320, yres=240, num_of_src=None):
    if num_of_src is None:
        num_of_src = rows * cols
    compositor_locations=''
    for r in range(rows):
        for c in range(cols):
            if (r*cols + c > num_of_src):
                break
            compositor_locations +=f'sink_{r*cols+c}::xpos={c * xres} sink_{r*cols+c}::ypos={r * yres} '

    return compositor_locations

def get_queue(size=3, name=None, leaky='no',  max_size_bytes=0, max_size_time=0):
    if name is None:
        name_str = ''
    else:
        name_str = f'name={name}'
    q = f'queue {name_str} leaky={leaky} max-size-buffers={size} max-size-bytes={max_size_bytes} max-size-time={max_size_time} '
    return q

###########################
# create pipeline functions
###########################
def get_debug():
    debug = f'hailopython name=debug qos=false module={COMMON_DIR}/send_zmq.py function=debug '
    return debug

def get_compositor_locations():
    compositor_locations="sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=320 sink_1::ypos=0 sink_2::xpos=640 sink_2::ypos=0 \
                    sink_3::xpos=0 sink_3::ypos=240 sink_8::xpos=320 sink_8::ypos=280 sink_4::xpos=640 sink_4::ypos=240 \
                    sink_5::xpos=0 sink_5::ypos=480 sink_6::xpos=320 sink_6::ypos=480 sink_7::xpos=640 sink_7::ypos=480"
    return compositor_locations

def get_scaler():
    scaler=f'videocrop top=80 bottom=80 ! video/x-raw,width=640,height=480,pixel-aspect-ratio=1/1 ! \
        videoscale n-threads=4 ! \
        video/x-raw,width=320, height=240, pixel-aspect-ratio=1/1 ,format=I420 '
    return scaler

def get_logo():
    logo=f'filesrc location={COMMON_DIR}/hailo_logo_fix.png ! decodebin ! \
        videoconvert ! video/x-raw ,format=I420 ! imagefreeze ! comp.sink_8 '
    return logo

def get_decode_element():
    # decode_element=f'qtdemux ! decodebin ! videoconvert ! video/x-raw, format=RGBA, width=1920, height=1080'
    decode_element=f'decodebin ! {get_queue(3)} ! videoscale ! {get_queue(3)} ! videoconvert ! video/x-raw, format=RGBA, width=1920, height=1080'
    return decode_element

def create_test_src(index=0):
    src_q_name = f'src_q_{index}'
    test_src = f'videotestsrc ! {get_queue(3, src_q_name)} ! \
        {get_decode_element()} ! '
    return test_src

def create_rtsp_src(index=0, rtsp_source=None):
    src_q_name = f'src_q_{index}'
    rtsp_src = f'rtspsrc location={rtsp_source} name=source_{index} message-forward=true ! \
                rtph264depay ! \
                {get_queue(3, src_q_name)} ! \
                {get_decode_element()} ! '
    return rtsp_src

def create_file_src(index=0, uri=None):
    # file://{RESOURCES_DIR}/video{index}.mp4
    src_q_name = f'src_q_{index}'
    file_src = f'uridecodebin3 uri={uri} ! \
                {get_queue(3, src_q_name)} ! \
                {get_decode_element()} ! '
    return file_src

def create_sources(start=0, end=8, src_type='test',input_file=None):
    
    sources = ''
    
    for index in range(start, end):
        if (src_type == 'file'):
            sources += create_file_src(index, uri=f'file://{input_file}') 
        else:
            if (src_type == 'rtsp'):
                sources += create_rtsp_src(index, rtsp_source=RTSP_SOURCES[index])
            else:
                sources += create_test_src(index)
        pre_roundrobin_q_name = f'pre_roundrobin_q_{index}'
        sources += f'{get_queue(8, pre_roundrobin_q_name)} ! \
                    hailopython name=hailopython_add_meta_{index} qos=false module={COMMON_DIR}/add_metadata.py function=camera{index} ! \
                    roundrobin.sink_{index} '
                    # disp_router.src_{index} ! \
                    # {get_queue(8)} ! \
                    # videoconvert name=pre_comp_videoconvert_{index} qos=false ! \
                    # video/x-raw,format=I420 ! \
                    # {get_queue(8)} ! \
                    # videoconvert ! fpsdisplaysink video-sink=xvimagesink sync=false name=disp_{index} '
    return sources

def build_disp_streamrouter():
    streamrouter_disp_element='hailostreamrouter name=disp_router \
    src_0::input-streams=\"<sink_0>\" src_1::input-streams=\"<sink_1>\" \
    src_2::input-streams=\"<sink_2>\" src_3::input-streams=\"<sink_3>\" \
    src_4::input-streams=\"<sink_4>\" src_5::input-streams=\"<sink_5>\" \
    src_6::input-streams=\"<sink_6>\" src_7::input-streams=\"<sink_7>\" '
    # streamrouter_disp_element='hailostreamrouter name=disp_router \
    # src_0::input-streams=<sink_0> src_1::input-streams=<sink_1> \
    # src_2::input-streams=<sink_2> src_3::input-streams=<sink_3> \
    # src_4::input-streams=<sink_4> src_5::input-streams=<sink_5> \
    # src_6::input-streams=<sink_6> src_7::input-streams=<sink_7> '
    return streamrouter_disp_element

def build_attr_streamrouter():
    streamrouter_attr_element='hailostreamrouter name=attr_router \
    src_0::input-streams=\"<sink_0,>\" \
    src_1::input-streams=\"<sink_0,>\" '
    # streamrouter_attr_element='hailostreamrouter name=attr_router \
    # src_0::input-streams=<sink_1, sink_3, sink_5, sink_7> \
    # src_1::input-streams=<sink_0, sink_2, sink_4, sink_6> '
    return streamrouter_attr_element

def init_sub_piplines():
    global DETECTOR_PIPELINE, ATTR_PIPELINE, COMP_DISP_PIPELINE
    
    internal_offset='true'
    streamrouter_disp_element = build_disp_streamrouter()
    streamrouter_attr_element = build_attr_streamrouter()
    compositor_locations = get_compositor_locations()
    
    PERSON_TRACKER="hailotracker name=hailo_person_tracker class-id=1 kalman-dist-thr=0.7 iou-thr=0.7 init-iou-thr=0.8 \
        keep-new-frames=2 keep-tracked-frames=4 keep-lost-frames=8 qos=false"

    FACE_TRACKER="hailotracker name=hailo_face_tracker class-id=2 kalman-dist-thr=0.7 iou-thr=0.7 init-iou-thr=0.8 \
        keep-new-frames=2 keep-tracked-frames=4 keep-lost-frames=8 qos=false"

    FACE_ATTR_INFER_POST=f'queue name=face_attr_pre_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailonet hef-path={FACE_ATTR_HEF_PATH} scheduling-algorithm=1 vdevice-key={DEFAULT_VDEVICE_KEY} ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter use-gst-buffer=true function-name=face_attributes_rgba so-path={FACE_ATTR_POSTPROCESS_SO} qos=false ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0'

    PERSON_ATTR_INFER_POST=f'queue name=person_attr_pre_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailonet hef-path={PERSON_ATTR_HEF_PATH} scheduling-algorithm=1 vdevice-key={DEFAULT_VDEVICE_KEY} ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter use-gst-buffer=true function-name=person_attributes_rgba so-path={PERSON_ATTR_POSTPROCESS_SO} qos=false ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0'

    PERSON_FACE_DETECTION_PIPELINE=f'hailonet scheduling-algorithm=1 hef-path={DETECTION_HEF_PATH} vdevice-key={DEFAULT_VDEVICE_KEY} ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter name=detector_hailofilter so-path={DEFAULT_DETECTION_POSTPROCESS_SO} config-path={DEFAULT_JSON_CONFIG_PATH} function-name={FUNCTION_NAME} qos=false'

    PERSON_ATTR_PIPELINE=f'attr_router.src_0 ! \
           queue name=pre_person_cropper_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
           hailocropper so-path={DEFAULT_CROP_SO} function-name=person_attributes internal-offset={internal_offset} name=person_attr_cropper \
           hailoaggregator name=person_attr_agg \
           person_attr_cropper. ! queue name=person_attr_bypass_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! person_attr_agg. \
           person_attr_cropper. ! {PERSON_ATTR_INFER_POST} ! person_attr_agg. \
           person_attr_agg. ! \
           queue name=person_attr_fakesink_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! fakesink name=person_hailo_display sync=false '

    FACE_ATTR_PIPELINE=f'attr_router.src_1 ! \
        queue name=pre_face_cropper_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailocropper so-path={DEFAULT_CROP_SO} function-name=face_attributes internal-offset={internal_offset} name=face_attr_cropper \
        hailoaggregator name=face_attr_agg \
        face_attr_cropper. ! queue name=fate_attr_bypass_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! face_attr_agg. \
        face_attr_cropper. ! {FACE_ATTR_INFER_POST} ! face_attr_agg. \
        face_attr_agg. ! \
        queue name=face_attr_fakesink_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! fakesink name=face_hailo_display sync=false '

    DISPLAY_PIPELINE_BRANCH=f'queue name=pre_overlay_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailooverlay qos=false show-confidence=false ! queue name=post_overlay_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! '

    DETECTOR_PIPELINE=f'\
        tee name=t hailomuxer name=hmux \
        t. ! queue name=detector_bypass_q leaky=no max-size-buffers=60 max-size-bytes=0 max-size-time=0 ! hmux. \
        t. ! queue name=detector_pre_scale_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        videoscale name=detector_videoscale method=0 n-threads=6 add-borders=false qos=false ! video/x-raw, pixel-aspect-ratio=1/1 ! \
        queue name=pre_detector_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        {PERSON_FACE_DETECTION_PIPELINE} ! \
        queue name=pre_person_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        {PERSON_TRACKER} ! \
        queue name=pre_face_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        {FACE_TRACKER} ! \
        queue name=post_face_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        tee name=disp_t \
        disp_t. ! queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! hmux. \
        disp_t. ! \
        {DISPLAY_PIPELINE_BRANCH} '

    COMP_DISP_PIPELINE=f'\
            compositor background=1 name=comp start-time-selection=0 {compositor_locations} ! \
            queue name=hailo_video_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
            fpsdisplaysink video-sink={get_video_sink_element()} name=hailo_display sync=false text-overlay=true'
    
    ATTR_PIPELINE=f'hmux. ! \
        queue name=post_detector_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        {streamrouter_attr_element} \
        {FACE_ATTR_PIPELINE} \
        {PERSON_ATTR_PIPELINE} '

def build_pipeline(src_type='test', input_file=None):
    init_sub_piplines()
    sources = create_sources(0, 1, src_type=src_type, input_file=input_file)
    
    pipeline = ''
    pipeline += f'{sources}'
    # pipeline += get_logo()
    pipeline += f'hailoroundrobin name=roundrobin funnel-mode=false ! '
    pipeline += get_queue(30, "pre_detector_pipe_q") + ' ! '
    pipeline += f'{DETECTOR_PIPELINE} '
    pipeline += f'{ATTR_PIPELINE} '
    pipeline += 'fakesink'
    # pipeline += f'{COMP_DISP_PIPELINE} '
    
    return pipeline

###########################
# pipeilne CB functions
###########################

class ProbeData:
    def __init__(self, pipe):
        self.pipe = pipe
        self.buffer_last_time = None
        self.start_time = None

        
def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.QOS:
        print(f'QOS message from {message.src.name}')
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    elif t in (Gst.MessageType.SEGMENT_DONE, Gst.MessageType.EOS):
        print(f'EOS from {message.src.name}')
    return True


def probe_cb(pad, info, pdata, i, first, last):
    # print('PROBE_CB')
    pdata.buffer_last_time = time.time()
    return Gst.PadProbeReturn.OK

def timeout_cb(loop, pdata):
    # print('TIMEOUT_CB')
    if  pdata.start_time is None:
        pdata.start_time = time.time()
    if  pdata.buffer_last_time is not None:
        cur_time = time.time()
        if cur_time - pdata.buffer_last_time > 2:
            print('Timeout killing pipeline')
            print(f'Run for {cur_time - pdata.start_time}')
            loop.quit()
            return False
    return True

###########################
# Main
###########################

def main(src_type='test', input_file=None):
    
    GObject.threads_init()
    Gst.init(None)

    pipeline = build_pipeline(src_type=src_type, input_file=input_file)
    print(pipeline)
    pipe = Gst.parse_launch(pipeline)
   
    pdata = ProbeData(pipe)
    
    loop = GObject.MainLoop()

    GLib.timeout_add_seconds(1, timeout_cb, loop, pdata)

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    video_q_elem = pipe.get_by_name('post_face_tracker_q')
    sinkpad = video_q_elem.get_static_pad('sink')
    # add probe to element sinkpad for every buffer
    sinkpad.add_probe(Gst.PadProbeType.BUFFER, probe_cb, pdata, 0, 0, 0)
    pipe.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    
    # cleanup
    print('Shutting down...')
    pipe.set_state(Gst.State.NULL)
    print('Shut down...')

if __name__ == '__main__':
    src_type = 'file'
    python_on_top = True
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        python_on_top = sys.argv[2] != 'False'
    no_display = False

    if python_on_top:
        sys.exit(main(src_type=src_type, input_file=input_file))
    else:
        pipeline = build_pipeline(src_type)
        print("-------------Running on shell--------------")
        cmd = f'gst-top-1.0 gst-launch-1.0 --no-position {pipeline}'
        print(cmd)
        os.system(cmd)
