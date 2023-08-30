import os

# Directories and Paths
TAPPAS_WORKSPACE = os.environ["TAPPAS_WORKSPACE"]
RESOURCES_DIR = os.path.join(TAPPAS_WORKSPACE, "apps/h8/gstreamer/general/face_recognition/resources")
POSTPROCESS_DIR = os.path.join(TAPPAS_WORKSPACE, "apps/h8/gstreamer/libs/post_processes/")
APPS_LIBS_DIR = os.path.join(TAPPAS_WORKSPACE, "apps/h8/gstreamer/libs/apps/vms/")
CROPPER_SO = os.path.join(POSTPROCESS_DIR, "cropping_algorithms/libvms_croppers.so")

# Face Alignment
FACE_ALIGN_SO = os.path.join(APPS_LIBS_DIR, "libvms_face_align.so")

# Face Recognition
RECOGNITION_POST_SO = os.path.join(POSTPROCESS_DIR, "libface_recognition_post.so")
RECOGNITION_HEF_PATH = os.path.join(RESOURCES_DIR, "arcface_mobilefacenet_v1.hef")

# Face Detection and Landmarking
DEFAULT_HEF_PATH = os.path.join(RESOURCES_DIR, "scrfd_10g.hef")
POSTPROCESS_SO = os.path.join(POSTPROCESS_DIR, "libscrfd_post.so")
FACE_JSON_CONFIG_PATH = os.path.join(RESOURCES_DIR, "configs/scrfd.json")
FUNCTION_NAME = "scrfd_10g"

hef_path = DEFAULT_HEF_PATH
input_source = os.path.join(RESOURCES_DIR, "face_recognition.mp4")

# Assuming you get the XV_SUPPORTED variable from the environment like in bash
XV_SUPPORTED = os.environ.get("XV_SUPPORTED", "false")
video_sink_element = "xvimagesink" if XV_SUPPORTED == "true" else "ximagesink"

additional_parameters = ""
print_gst_launch_only = False
vdevice_key = 1
function_name = FUNCTION_NAME
local_gallery_file = os.path.join(RESOURCES_DIR, "gallery/face_recognition_local_gallery.json")

def get_pipeline(current_path):
    
    # RECOGNITION_PIPELINE = (
    #     f"hailocropper so-path={CROPPER_SO} function-name=face_recognition internal-offset=true name=cropper2 "
    #     "hailoaggregator name=agg2 "
    #     "cropper2. ! queue name=bypess2_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! agg2. "
    #     f"cropper2. ! queue name=pre_face_align_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
    #     f"hailofilter so-path={FACE_ALIGN_SO} name=face_align_hailofilter use-gst-buffer=true qos=false ! "
    #     "queue name=detector_pos_face_align_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
    #     f"hailonet hef-path={RECOGNITION_HEF_PATH} scheduling-algorithm=1 vdevice-key={vdevice_key} ! "
    #     "queue name=recognition_post_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
    #     f"hailofilter so-path={RECOGNITION_POST_SO} name=face_recognition_hailofilter qos=false ! "
    #     "queue name=recognition_pre_agg_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
    #     "agg2. agg2. "
    # )

    FACE_DETECTION_PIPELINE = (
        f"hailonet hef-path={hef_path} ! "
        "queue name=detector_post_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"hailofilter so-path={POSTPROCESS_SO} name=face_detection_hailofilter qos=false config-path={FACE_JSON_CONFIG_PATH} function_name={function_name}"
    )

    FACE_TRACKER = (
        "hailotracker name=hailo_face_tracker class-id=-1 kalman-dist-thr=0.7 iou-thr=0.8 init-iou-thr=0.9 "
        "keep-new-frames=2 keep-tracked-frames=2 keep-lost-frames=2 keep-past-metadata=true qos=false debug=true "
    )

    DETECTOR_PIPELINE = (
        f"tee name=t hailomuxer name=hmux "
        "t. ! "
        "queue name=detector_bypass_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        "hmux. "
        "t. ! "
        "videoscale name=face_videoscale method=0 n-threads=2 add-borders=false qos=false ! "
        "videoconvert name=detection_convert n-threads=2 qos=false ! "
        "video/x-raw, pixel-aspect-ratio=1/1 ! "
        f"queue name=pre_face_detector_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"{FACE_DETECTION_PIPELINE} ! "
        "queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        "hmux. "
        "hmux. "
    )

    pipeline = (
        "queue name=hailo_pre_convert_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        "videoconvert n-threads=2 qos=false ! "
        "video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 ! "
        "queue name=pre_detector_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"{DETECTOR_PIPELINE} ! "
        "queue name=pre_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"{FACE_TRACKER} ! "
        "queue name=hailo_post_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        # f"{RECOGNITION_PIPELINE} ! "
        # "queue name=hailo_pre_gallery_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        # f"hailogallery gallery-file-path={local_gallery_file} "
        # "load-local-gallery=true similarity-thr=.4 gallery-queue-size=20 class-id=-1 ! "
        # "queue name=hailo_pre_draw2 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"hailopython qos=false module={current_path}/arduino_ctrl.py finalize-function=close name=python_filter ! "
        "hailooverlay name=hailo_overlay qos=false show-confidence=false local-gallery=true line-thickness=5 font-thickness=2 landmark-point-radius=8 ! "
        "queue name=hailo_post_draw leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        "videoconvert n-threads=4 qos=false name=display_videoconvert qos=false ! "
        f"queue name=hailo_display_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
        f"fpsdisplaysink video-sink={video_sink_element} name=hailo_display sync=false text-overlay=true "
        )
    return pipeline