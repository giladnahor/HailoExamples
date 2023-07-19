#!/bin/bash
set -e

function init_variables() {
    export LIBVA_DRIVER_NAME=i965
    print_help_if_needed $@

    script_dir=$(dirname $(realpath "$0"))
    source $script_dir/../../../../scripts/misc/checks_before_run.sh

    readonly APP_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/frigate_vms/vms_lpr"
    readonly COMMON_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/frigate_vms/common"
    
    # Basic Directories
    readonly POSTPROCESS_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/libs/post_processes"
    readonly APPS_LIBS_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/libs/apps/license_plate_recognition/"
    readonly CROPPING_ALGORITHMS_DIR="$POSTPROCESS_DIR/cropping_algorithms"
    readonly RESOURCES_DIR="$APP_DIR/resources"
    readonly DEFAULT_LICENCE_PLATE_JSON_CONFIG_PATH="$RESOURCES_DIR/configs/yolov4_licence_plate.json" 
    readonly DEFAULT_VEHICLE_JSON_CONFIG_PATH="$RESOURCES_DIR/configs/yolov5_vehicle_detection.json" 

    # Default Video
    readonly DEFAULT_VIDEO_SOURCE="$RESOURCES_DIR/video0.mp4"

    # Vehicle Detection Macros
    readonly VEHICLE_DETECTION_HEF="$RESOURCES_DIR/yolov5m_vehicles.hef"
    readonly VEHICLE_DETECTION_POST_SO="$POSTPROCESS_DIR/libyolo_post.so"
    readonly VEHICLE_DETECTION_POST_FUNC="yolov5_vehicles_only"

    # License Plate Detection Macros
    readonly LICENSE_PLATE_DETECTION_HEF="$RESOURCES_DIR/tiny_yolov4_license_plates.hef"
    readonly LICENSE_PLATE_DETECTION_POST_SO="$POSTPROCESS_DIR/libyolo_post.so"
    readonly LICENSE_PLATE_DETECTION_POST_FUNC="tiny_yolov4_license_plates"

    # License Plate OCR Macros
    readonly LICENSE_PLATE_OCR_HEF="$RESOURCES_DIR/lprnet.hef"
    readonly LICENSE_PLATE_OCR_POST_SO="$POSTPROCESS_DIR/libocr_post.so"

    # Cropping Algorithm Macros
    readonly LICENSE_PLATE_CROP_SO="$CROPPING_ALGORITHMS_DIR/liblpr_croppers.so"
    readonly LICENSE_PLATE_DETECTION_CROP_FUNC="vehicles_without_ocr"
    readonly LICENSE_PLATE_OCR_CROP_FUNC="license_plate_quality_estimation"

    # Pipeline Utilities
    readonly LPR_OVERLAY="$APPS_LIBS_DIR/liblpr_overlay.so"
    readonly LPR_OCR_SINK="$APPS_LIBS_DIR/liblpr_ocrsink.so"

    video_sink_element=$([ "$XV_SUPPORTED" = "true" ] && echo "xvimagesink" || echo "ximagesink")
    input_source=$DEFAULT_VIDEO_SOURCE

    print_gst_launch_only=false
    additonal_parameters=""
    stats_element=""
    debug_stats_export=""
    sync_pipeline=true
    device_id_prop=""
    tee_name="context_tee"
    internal_offset=false
    pipeline_1=""
    licence_plate_json_config_path=$DEFAULT_LICENCE_PLATE_JSON_CONFIG_PATH 
    car_json_config_path=$DEFAULT_VEHICLE_JSON_CONFIG_PATH 
    
    debug_element="hailopython name=hailopython_debug qos=false module=${COMMON_DIR}/send_zmq.py function=debug "
    
    debug_element2="hailopython name=hailopython_debug2 qos=false module=${COMMON_DIR}/send_zmq.py function=debug2 "
    
    debug_element3="hailopython name=hailopython_debug3 qos=false module=${COMMON_DIR}/send_zmq.py function=debug3 "
    
    QUEUE="queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 "
    
    source_element="filesrc location=$input_source name=src_0 ! decodebin ! \
    $QUEUE ! hailopython name=hailopython_debug qos=false module=${COMMON_DIR}/add_metadata.py function=lpr0 "

    # videobox name=videobox0 top=-140 bottom=-140 qos=false ! \
    ZMQ_PIPLINE="
    videoconvert name=pre_comp_videoconvert_$n qos=false ! \
    video/x-raw,format=I420 ! \
    queue name=pre_comp_queue_$n leaky=no max-size-buffers=10 max-size-bytes=0 max-size-time=0 ! \
    hailopython name=hailopython_camera_$n qos=false module=${COMMON_DIR}/send_zmq.py function=run_lpr "
}

function print_help_if_needed() {
    while test $# -gt 0; do
        if [ "$1" = "--help" ] || [ "$1" == "-h" ]; then
            print_usage
        fi

        shift
    done
}

function print_usage() {
    echo "LPR pipeline usage:"
    echo ""
    echo "Options:"
    echo "  -h --help                  Show this help"
    echo "  --show-fps                 Print fps"
    echo "  --print-gst-launch         Print the ready gst-launch command without running it"
    echo "  --print-device-stats       Print the power and temperature measured"
    exit 0
}

function parse_args() {
    while test $# -gt 0; do
        if [ "$1" = "--print-gst-launch" ]; then
            print_gst_launch_only=true
        elif [ "$1" = "--print-device-stats" ]; then
            hailo_bus_id=$(hailortcli scan | awk '{ print $NF }' | tail -n 1)
            device_id_prop="device_id=$hailo_bus_id"
            stats_element="hailodevicestats $device_id_prop"
            debug_stats_export="GST_DEBUG=hailodevicestats:5"
        elif [ "$1" = "--show-fps" ]; then
            echo "Printing fps"
            additonal_parameters="-v | grep -e hailo_display -e hailodevicestats"
        else
            echo "Received invalid argument: $1. See expected arguments below:"
            print_usage
            exit 1
        fi

        shift
    done
}

init_variables $@
parse_args $@
internal_offset=true

function create_lp_detection_pipeline() {
    pipeline_1="queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                hailocropper so-path=$LICENSE_PLATE_CROP_SO function-name=$LICENSE_PLATE_DETECTION_CROP_FUNC internal-offset=$internal_offset drop-uncropped-buffers=true name=cropper1 \
                hailoaggregator name=agg1 flatten-detections=false \
                cropper1. ! \
                    queue leaky=no max-size-buffers=50 max-size-bytes=0 max-size-time=0 ! \
                agg1. \
                cropper1. ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                    hailonet hef-path=$LICENSE_PLATE_DETECTION_HEF vdevice-key=1 scheduling-algorithm=1 scheduler-threshold=5 scheduler-timeout-ms=100 ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                    hailofilter so-path=$LICENSE_PLATE_DETECTION_POST_SO config-path=$licence_plate_json_config_path function-name=$LICENSE_PLATE_DETECTION_POST_FUNC qos=false ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                agg1. \
                agg1. ! queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                hailocropper so-path=$LICENSE_PLATE_CROP_SO function-name=$LICENSE_PLATE_OCR_CROP_FUNC internal-offset=$internal_offset drop-uncropped-buffers=true name=cropper2 \
                hailoaggregator name=agg2 flatten-detections=false \
                cropper2. ! \
                    queue leaky=no max-size-buffers=50 max-size-bytes=0 max-size-time=0 ! \
                agg2. \
                cropper2. ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                    hailonet hef-path=$LICENSE_PLATE_OCR_HEF vdevice-key=1 scheduling-algorithm=1 scheduler-threshold=1 scheduler-timeout-ms=100 ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                    hailofilter so-path=$LICENSE_PLATE_OCR_POST_SO qos=false ! \
                    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
                agg2. \
                agg2. ! queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0"
}
create_lp_detection_pipeline $@

PIPELINE="${debug_stats_export} gst-launch-1.0 ${stats_element} \
    $source_element ! \
    $QUEUE ! \
    videoscale ! video/x-raw, pixel-aspect-ratio=1/1 ! videoconvert ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailonet hef-path=$VEHICLE_DETECTION_HEF vdevice-key=1 scheduling-algorithm=1 scheduler-threshold=1 scheduler-timeout-ms=100 ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailofilter so-path=$VEHICLE_DETECTION_POST_SO function-name=$VEHICLE_DETECTION_POST_FUNC config-path=$car_json_config_path qos=false ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailotracker name=hailo_tracker keep-past-metadata=false kalman-dist-thr=.5 iou-thr=.6 keep-tracked-frames=2 keep-lost-frames=2 ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    tee name=$tee_name \
    $tee_name. ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    videoscale name=overlay_videoscale method=0 n-threads=6 add-borders=false qos=false ! video/x-raw, width=640,height=360,pixel-aspect-ratio=1/1 ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailooverlay line-thickness=3 font-thickness=1 qos=false ! \
    hailofilter use-gst-buffer=true so-path=$LPR_OVERLAY qos=false ! \
    $ZMQ_PIPLINE ! \
    videoconvert ! \
    fpsdisplaysink video-sink=$video_sink_element name=hailo_display sync=$sync_pipeline text-overlay=false \
    $tee_name. ! \
    $pipeline_1 ! \
    hailofilter use-gst-buffer=true so-path=$LPR_OCR_SINK qos=false ! \
    fakesink sync=false async=false  ${additonal_parameters}"

echo "Running License Plate Recognition"
echo ${PIPELINE}

if [ "$print_gst_launch_only" = true ]; then
    exit 0
fi

eval ${PIPELINE}
