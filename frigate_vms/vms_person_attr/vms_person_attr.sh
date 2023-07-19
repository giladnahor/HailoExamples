#!/bin/bash
set -e

function init_variables() {
    export LIBVA_DRIVER_NAME=i965
    print_help_if_needed $@
    script_dir=$(dirname $(realpath "$0"))
    source $script_dir/../../../../scripts/misc/checks_before_run.sh --check-vaapi

    readonly APP_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/frigate_vms/vms_person_attr/"
    readonly COMMON_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/frigate_vms/common"
    readonly RESOURCES_DIR="$APP_DIR/resources"
    readonly POSTPROCESS_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/libs/post_processes/"
    readonly VMS_POSTPROCESS_DIR="$TAPPAS_WORKSPACE/apps/gstreamer/libs/apps/vms/"
    readonly DEFAULT_JSON_CONFIG_PATH="$RESOURCES_DIR/configs/yolov5_personface.json"
    readonly FUNCTION_NAME="yolov5_personface"
    readonly DEFAULT_VDEVICE_KEY="1"

    readonly DETECTION_HEF_PATH="$RESOURCES_DIR/yolov5s_personface_rgba.hef"
    readonly FACE_ATTR_HEF_PATH="$RESOURCES_DIR/face_attr_resnet_v1_18_rgbx.hef"
    readonly PERSON_ATTR_HEF_PATH="$RESOURCES_DIR/person_attr_resnet_v1_18_rgbx.hef"

    readonly DEFAULT_DETECTION_POSTPROCESS_SO="$POSTPROCESS_DIR/libyolo_post.so"
    readonly FACE_ATTR_POSTPROCESS_SO="$VMS_POSTPROCESS_DIR/libface_attributes_post.so"
    readonly PERSON_ATTR_POSTPROCESS_SO="$VMS_POSTPROCESS_DIR/libperson_attributes_post.so"

    readonly CROPING_ALGORITHMS_DIR="$POSTPROCESS_DIR/cropping_algorithms"
    readonly DEFAULT_CROP_SO="$CROPING_ALGORITHMS_DIR/libvms_croppers.so"


    detection_postprocess_so=$DEFAULT_DETECTION_POSTPROCESS_SO
    json_config_path=$DEFAULT_JSON_CONFIG_PATH
    crop_so=$DEFAULT_CROP_SO
    num_of_src=8
    additonal_parameters=""
    sources=""
    parsers=""
    # decode_element="qtdemux ! \
    #                 vaapidecodebin ! video/x-raw, format=RGBA, width=1920, height=1080"
    decode_element="qtdemux ! \
                    decodebin ! \
                    videoconvert ! \
                    video/x-raw, format=RGBA, width=1920, height=1080"
    create_compositor_table

    print_gst_launch_only=false
    video_sink_element=$([ "$XV_SUPPORTED" = "true" ] && echo "xvimagesink" || echo "ximagesink")

    hailo_bus_id=$(hailortcli scan | awk '{ print $NF }' | tail -n 1)
    device_id_prop="device_id=$hailo_bus_id"
    stats_element="hailodevicestats $device_id_prop"
}

function create_compositor_table(){
    # # create a compositor table of 4 rows and 4 columns of frame size 640X640
    # comp_row0="sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=640 sink_1::ypos=0 sink_2::xpos=1280 sink_2::ypos=0 sink_3::xpos=1920 sink_3::ypos=0"
    # comp_row1="sink_4::xpos=0 sink_4::ypos=640 sink_5::xpos=640 sink_5::ypos=640 sink_6::xpos=1280 sink_6::ypos=640 sink_7::xpos=1920 sink_7::ypos=640"
    # comp_row2="sink_8::xpos=0 sink_8::ypos=1280 sink_9::xpos=640 sink_9::ypos=1280 sink_10::xpos=1280 sink_10::ypos=1280 sink_11::xpos=1920 sink_11::ypos=1280"
    # comp_row3="sink_12::xpos=0 sink_12::ypos=1920 sink_13::xpos=640 sink_13::ypos=1920 sink_14::xpos=1280 sink_14::ypos=1920 sink_15::xpos=1920 sink_15::ypos=1920"
    # compositor_locations="$comp_row0 $comp_row1 $comp_row2 $comp_row3"
    frame_size=640
    compositor_locations="sink_0::xpos=0 sink_0::ypos=0 sink_1::xpos=320 sink_1::ypos=0 sink_2::xpos=640 sink_2::ypos=0 \
                    sink_3::xpos=0 sink_3::ypos=240 sink_8::xpos=320 sink_8::ypos=280 sink_4::xpos=640 sink_4::ypos=240 \
                    sink_5::xpos=0 sink_5::ypos=480 sink_6::xpos=320 sink_6::ypos=480 sink_7::xpos=640 sink_7::ypos=480"
    
}

function print_usage() {
    echo "Multistream Detection hailo - pipeline usage:"
    echo ""
    echo "Options:"
    echo "  --help                          Show this help"
    echo "  --show-fps                      Printing fps"
    echo "  --num-of-sources NUM            Setting number of sources to given input (default value is 8, value between 2-8)"
    echo "  --print-gst-launch              Print the ready gst-launch command without running it"
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
        if [ "$1" = "--help" ] || [ "$1" == "-h" ]; then
            print_usage
            exit 0
        elif [ "$1" = "--print-gst-launch" ]; then
            print_gst_launch_only=true
        elif [ "$1" = "--num-of-sources" ]; then
            if [ "$2" -lt 2 ] || [ "$2" -gt 8 ]; then
                echo "Invalid argument received: num-of-sources must be between 2-8"
                exit 1
            fi
            shift
            echo "Setting number of sources to $1"
            num_of_src=$1
        elif [ "$1" = "--show-fps" ]; then
            echo "Printing fps"
            additonal_parameters="-v | grep hailo_display:"
        else
            echo "Received invalid argument: $1. See expected arguments below:"
            print_usage
            exit 1
        fi
        shift
    done
}
    
function create_sources() {
    start_index=0
    identity=""
    scaler="videocrop top=80 bottom=80 ! video/x-raw,width=640,height=480,pixel-aspect-ratio=1/1 ! \
        videoscale n-threads=4 ! \
        video/x-raw,width=320, height=240, pixel-aspect-ratio=1/1 ,format=I420 ! "
    logo="filesrc location=${COMMON_DIR}/hailo_logo_fix.png ! decodebin ! videoconvert ! video/x-raw ,format=I420 ! imagefreeze ! comp.sink_8"

    # use_camera=true
    # if ( $use_camera ); then
    #     sources+="v4l2src device=/dev/video2 name=webcam_src ! \
    #         video/x-raw,width=640,height=480,pixel-aspect-ratio=1/1 ! \
    #         videoscale n-threads=4 ! \
    #         queue name=webcam_q leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
    #         videoconvert ! \
    #         video/x-raw, format=RGBA, width=1920, height=1080 ! \
    #         queue name=webcam_rgba_q leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
    #         tee name=webcam_tee "
    # fi
    
    for ((n = $start_index; n < $num_of_src; n++)); do
        file="filesrc location=$RESOURCES_DIR/video$n.mp4 name=source_$n ! \
                queue name=pre_decode_q_$n leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
                $decode_element ! "
        # webcam="webcam_tee. ! queue name=pre_decode_q_$n leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
        # if ( $use_camera ); then
        #     source=$webcam
        # else
        #     source=$file
        # fi
        source=$file
        sources+="$source \
                queue name=pre_roundrobin_q_$n leaky=no max-size-buffers=8 max-size-bytes=0 max-size-time=0 ! \
                hailopython name=hailopython_add_meta_$n qos=false module=${COMMON_DIR}/add_metadata.py function=camera$n ! \
                roundrobin.sink_$n \
                disp_router.src_$n ! \
                queue name=pre_comp_videoconvert_queue_$n leaky=no max-size-buffers=10 max-size-bytes=0 max-size-time=0 ! \
                videoconvert name=pre_comp_videoconvert_$n qos=false ! \
                video/x-raw,format=I420 ! \
                queue name=pre_comp_queue_$n leaky=no max-size-buffers=10 max-size-bytes=0 max-size-time=0 ! \
                hailopython name=hailopython_camera_$n qos=false module=${COMMON_DIR}/send_zmq.py function=run_camera ! \
                $scaler \
                comp.sink_$n "

        streamrouter_disp_element+=" src_$n::input-streams='<sink_$n>'"
    done
    
}

function main() {
    init_variables $@
    parse_args $@
    internal_offset=true

    streamrouter_disp_element="hailostreamrouter name=disp_router"
    streamrouter_input_streams="src_0::input-streams='<sink_1, sink_3, sink_5, sink_7>' src_1::input-streams='<sink_0, sink_2, sink_4, sink_6>'"

    create_sources

    PERSON_TRACKER="hailotracker name=hailo_person_tracker class-id=1 kalman-dist-thr=0.7 iou-thr=0.7 init-iou-thr=0.8 \
        keep-new-frames=2 keep-tracked-frames=4 keep-lost-frames=8 qos=false"

    FACE_TRACKER="hailotracker name=hailo_face_tracker class-id=2 kalman-dist-thr=0.7 iou-thr=0.7 init-iou-thr=0.8 \
        keep-new-frames=2 keep-tracked-frames=4 keep-lost-frames=8 qos=false"

    FACE_ATTR_INFER_POST="queue name=face_attr_pre_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailonet hef-path=$FACE_ATTR_HEF_PATH scheduling-algorithm=1 vdevice-key=$DEFAULT_VDEVICE_KEY ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter use-gst-buffer=true function-name=face_attributes_rgba so-path=$FACE_ATTR_POSTPROCESS_SO qos=false ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0"

    PERSON_ATTR_INFER_POST="queue name=person_attr_pre_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailonet hef-path=$PERSON_ATTR_HEF_PATH scheduling-algorithm=1 vdevice-key=$DEFAULT_VDEVICE_KEY ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter use-gst-buffer=true function-name=person_attributes_rgba so-path=$PERSON_ATTR_POSTPROCESS_SO qos=false ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0"

    PERSON_FACE_DETECTION_PIPELINE="\
        hailonet scheduling-algorithm=1 hef-path=$DETECTION_HEF_PATH vdevice-key=$DEFAULT_VDEVICE_KEY ! \
        queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailofilter name=detector_hailofilter so-path=$detection_postprocess_so config-path=$json_config_path function-name=$FUNCTION_NAME qos=false"

    PERSON_ATTR_PIPELINE="router.src_0 ! \
           queue name=pre_person_cropper_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
           hailocropper so-path=$crop_so function-name=person_attributes internal-offset=$internal_offset name=person_attr_cropper \
           hailoaggregator name=person_attr_agg \
           person_attr_cropper. ! queue name=person_attr_bypass_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! person_attr_agg. \
           person_attr_cropper. ! $PERSON_ATTR_INFER_POST ! person_attr_agg. \
           person_attr_agg. ! \
           queue name=person_attr_fakesink_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! fakesink name=person_hailo_display sync=false "

    FACE_ATTR_PIPELINE="router.src_1 ! \
        queue name=pre_face_cropper_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailocropper so-path=$crop_so function-name=face_attributes internal-offset=$internal_offset name=face_attr_cropper \
        hailoaggregator name=face_attr_agg \
        face_attr_cropper. ! queue name=fate_attr_bypass_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! face_attr_agg. \
        face_attr_cropper. ! $FACE_ATTR_INFER_POST ! face_attr_agg. \
        face_attr_agg. ! \
        queue name=face_attr_fakesink_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! fakesink name=face_hailo_display sync=false "

    DISPLAY_PIPELINE_BRANCH="\
        queue name=pre_overlay_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailooverlay qos=false show-confidence=false ! queue name=post_overlay_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        $streamrouter_disp_element "

    DETECTOR_PIPELINE="tee name=t hailomuxer name=hmux \
        t. ! queue name=detector_bypass_q leaky=no max-size-buffers=60 max-size-bytes=0 max-size-time=0 ! hmux. \
        t. ! queue name=detector_pre_scale_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        videoscale name=detector_videoscale method=0 n-threads=6 add-borders=false qos=false ! video/x-raw, width=$frame_size,height=$frame_size,pixel-aspect-ratio=1/1 ! \
        queue name=pre_detector_infer_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        $PERSON_FACE_DETECTION_PIPELINE ! \
        queue name=pre_person_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        $PERSON_TRACKER ! \
        queue name=pre_face_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        $FACE_TRACKER ! \
        queue name=post_face_tracker_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        tee name=disp_t \
        disp_t. ! queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! hmux. \
        disp_t. ! \
        $DISPLAY_PIPELINE_BRANCH "

    pipeline_comp_displaysink="\
            compositor background=1 name=comp start-time-selection=0 $compositor_locations ! \
            queue name=hailo_video_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
            hailopython name=hailopython_run_birdseye qos=false module=${COMMON_DIR}/send_zmq.py function=run_birdseye ! \
            fpsdisplaysink video-sink=$video_sink_element name=hailo_display sync=false text-overlay=false"
    
    ATTR_PIPELINE="hmux. ! \
        queue name=post_detector_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
        hailostreamrouter name=router $streamrouter_input_streams \
        $FACE_ATTR_PIPELINE \
        $PERSON_ATTR_PIPELINE "
           
pipeline="gst-launch-1.0 --no-position \
           $sources \
           $logo \
           hailoroundrobin name=roundrobin funnel-mode=false ! \
           queue leaky=no name=pre_detector_pipe_q max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
           $DETECTOR_PIPELINE \
           $ATTR_PIPELINE \
           $pipeline_comp_displaysink \
           ${additonal_parameters}"

    echo ${pipeline}
    if [ "$print_gst_launch_only" = true ]; then
        exit 0
    fi

    echo "Running Pipeline..."
    eval "${pipeline}"

}

main $@
