#!/bin/bash
set -e

function init_variables() {
    print_help_if_needed $@
    script_dir=$(dirname $(realpath "$0"))
    source $script_dir/../../../../scripts/misc/checks_before_run.sh
    readonly APP_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/general/pose_unity"
    readonly POSTPROCESS_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/libs/post_processes/"
    readonly RESOURCES_DIR="$APP_DIR/resources"
    readonly DEFAULT_POSTPROCESS_SO="$POSTPROCESS_DIR/libcenterpose_post.so"
    readonly DEFAULT_NETWORK_NAME="centerpose"
    readonly DEFAULT_VIDEO_SOURCE="$TAPPAS_WORKSPACE/apps/gstreamer/general/detection/resources/detection.mp4"
    readonly DEFAULT_HEF_PATH="$RESOURCES_DIR/centerpose_regnetx_1.6gf_fpn.hef"
    readonly CENRTERPOSE_TRACKING_SO="$POSTPROCESS_DIR/libcenterpose_tracking.so"
    
    postprocess_so=$DEFAULT_POSTPROCESS_SO
    network_name=$DEFAULT_NETWORK_NAME
    input_source=$DEFAULT_VIDEO_SOURCE
    hef_path=$DEFAULT_HEF_PATH
    network_name=$DEFAULT_NETWORK_NAME
    sync_pipeline=false

    print_gst_launch_only=false
    additonal_parameters=""

    video_sink_element=$([ "$XV_SUPPORTED" = "true" ] && echo "xvimagesink" || echo "ximagesink")
}

function print_usage() {
    echo "Pose Estimation pipeline usage:"
    echo ""
    echo "Options:"
    echo "  --help                  Show this help"
    echo "  -i INPUT --input INPUT  Set the video source - Could be path to video file or a video device path"
    echo "  --network NETWORK       Set network to use. choose from [centerpose, centerpose_416], default is centerpose"
    echo "  --show-fps              Printing fps"
    echo "  --print-gst-launch      Print the ready gst-launch command without running it"
    exit 0
}

function print_help_if_needed() {
    while test $# -gt 0; do
        if [ "$1" = "--help" ] || [ "$1" == "-h" ]; then
            print_usage
        fi

        shift
    done
}

function parse_args() {
    while test $# -gt 0; do
        if [ "$1" = "--show-fps" ]; then
            echo "Printing fps"
            additonal_parameters="-v | grep hailo_display"
        elif [ "$1" = "--print-gst-launch" ]; then
            print_gst_launch_only=true
        elif [ "$1" = "--input" ] || [ "$1" = "-i" ]; then
            input_source="$2"
            shift
        elif [ $1 == "--network" ]; then
            if [ $2 == "centerpose_416" ]; then
                network_name="centerpose_416"
                hef_path="$RESOURCES_DIR/centerpose_repvgg_a0.hef"
            elif [ $2 != "centerpose" ]; then
                echo "Received invalid network: $2. See expected arguments below:"
                print_usage
                exit 1
            fi
            shift
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

# If the video provided is from a camera
if [[ $input_source =~ "/dev/video" ]]; then
    source_element="v4l2src device=$input_source name=src_0 ! image/jpeg ! jpegdec ! videoflip video-direction=horiz"
else
    source_element="filesrc location=$input_source name=src_0 ! decodebin"
fi

PIPELINE="gst-launch-1.0 --no-position \
    $source_element ! \
    videoscale ! video/x-raw, pixel-aspect-ratio=1/1 ! videoconvert ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailonet hef-path=$hef_path is-active=true ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailofilter so-path=$postprocess_so qos=false function-name=$network_name ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailotracker name=hailo_tracker keep-past-metadata=false kalman-dist-thr=.5 iou-thr=.6 keep-tracked-frames=2 keep-lost-frames=2 ! \
    queue ! \
    hailofilter so-path=$CENRTERPOSE_TRACKING_SO qos=false function-name=debug ! \
    hailooverlay qos=false ! \
    videoconvert ! \
    fpsdisplaysink video-sink=$video_sink_element name=hailo_display sync=$sync_pipeline text-overlay=false ${additonal_parameters}"
    
    # videoscale ! video/x-raw, pixel-aspect-ratio=1/1, width=320, height=320 ! \
    # hailopython name=hailopython_debug qos=false module=${APP_DIR}/send_zmq.py ! \
    # hailopython name=pose_tracker qos=false module=${APP_DIR}/PoseTracker.py ! \
    
echo ${PIPELINE}
if [ "$print_gst_launch_only" = true ]; then
    exit 0
fi
eval ${PIPELINE}
