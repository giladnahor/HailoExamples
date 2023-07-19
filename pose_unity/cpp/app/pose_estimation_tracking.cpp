/**
* Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
* Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
**/
// General cpp includes
#include <chrono>
#include <condition_variable>
#include <cxxopts.hpp>
#include <gst/gst.h>
#include <gst/video/video.h>
#include <gst/app/gstappsink.h>
#include <iostream>
#include <mutex>
#include <chrono>
#include <ctime>
#include <shared_mutex>
#include <stdio.h>
#include <thread>
#include <unistd.h>
#include <glib.h>
#include <string>
#include <fstream>
#include <sstream>

// Tappas includes
#include "hailo_objects.hpp"
#include "hailo_common.hpp"

// Open source includes
#include <opencv2/opencv.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/core.hpp>

// Hailo app cpp utils include
#include "hailo_app_cpp_utils.hpp"
//******************************************************************
// Pipeline Macros
//******************************************************************

const std::string TAPPAS_WORKSPACE = "/local/workspace/tappas";
const std::string APP_DIR = TAPPAS_WORKSPACE + "/apps/gstreamer/general/pose_unity";
const std::string POSTPROCESS_DIR = TAPPAS_WORKSPACE + "/apps/gstreamer/libs/post_processes/";
const std::string RESOURCES_DIR = APP_DIR + "/resources";
const std::string DEFAULT_POSTPROCESS_SO = POSTPROCESS_DIR + "/libcenterpose_post.so";
const std::string DEFAULT_NETWORK_NAME = "centerpose";
const std::string DEFAULT_VIDEO_SOURCE = TAPPAS_WORKSPACE + "/apps/gstreamer/general/detection/resources/detection.mp4";
const std::string DEFAULT_HEF_PATH = RESOURCES_DIR + "/centerpose_regnetx_1.6gf_fpn.hef";
const std::string CENRTERPOSE_TRACKING_SO = POSTPROCESS_DIR + "/libcenterpose_tracking.so";

//******************************************************************
// PIPELINE CREATION
//******************************************************************
/**
 * @brief Create the pipeline string object
 *
 * @param input_src  -  std::string
 *        A video file path or usb camera name (/dev/video*)
 *  
 * @return std::string
 *         The full pipeline string.
 */
std::string create_pipeline_string(std::string input_src, std::string window_size, bool debug_mode, bool disable_landmark_tracking)
{
  std::string src_pipeline_string = "";
  std::string pipeline_string = "";
  std::string internal_offset = "";
  std::string stats_pipeline = " hailodevicestats name=hailo_stats silent=false ";
  std::string debug_tracker = "";

  if (debug_mode)
  {
      debug_tracker = " debug=true ";
  }
  // Source sub-pipeline
  if (input_src.rfind("/dev/video", 0) == 0)
  {
      src_pipeline_string = "v4l2src name=video_src device=" + input_src + " name=src_0 ! image/jpeg ! jpegdec ! videoflip video-direction=horiz ! ";
      internal_offset = "false";
  } else {
      src_pipeline_string = "filesrc name=video_src location=" + input_src + " name=src_0 ! decodebin ! ";
      internal_offset = "true";
  }
  pipeline_string = src_pipeline_string + " videoscale ! video/x-raw, pixel-aspect-ratio=1/1 ! videoconvert qos=false ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailonet hef-path=" + DEFAULT_HEF_PATH + " ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailofilter so-path=" + DEFAULT_POSTPROCESS_SO + " qos=false function-name=" +  DEFAULT_NETWORK_NAME + " ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailotracker name=hailo_tracker keep-past-metadata=false kalman-dist-thr=.5 iou-thr=.6 keep-tracked-frames=2 keep-lost-frames=10 " + debug_tracker + " ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! ";
  if (!disable_landmark_tracking)
  {
      pipeline_string = pipeline_string + " hailofilter so-path=" + CENRTERPOSE_TRACKING_SO + " qos=false config-path=" + window_size + " ! ";
  }
  pipeline_string = pipeline_string + " queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  hailooverlay qos=false ! \
  queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! \
  textoverlay name=text_overlay ! \
  videoconvert ! \
  hailopython  module=" + APP_DIR + "/send_zmq.py ! \
  fpsdisplaysink video-sink=xvimagesink name=hailo_display sync=" + internal_offset + " text-overlay=false signal-fps-measurements=true ";
  pipeline_string = pipeline_string + stats_pipeline;
  std::cout << "Pipeline:" <<std::endl;
  std::cout << "gst-launch-1.0 " << pipeline_string << std::endl;
  // Combine and return the pipeline:
  return (pipeline_string);
}

//******************************************************************
// MAIN
//******************************************************************


int main(int argc, char *argv[])
{
  // build argument parser
  cxxopts::Options options = build_arg_parser();
  // add custom options
  options.add_options()
  ("w, window", "Set tracker smoothing window size", cxxopts::value<std::string>()->default_value(std::string("4")))
  ("d, debug", "Enable tracker debug", cxxopts::value<bool>()->default_value("false"))
  ("disable-landmarks-tracking", "disables landmarks tracking", cxxopts::value<bool>()->default_value("false"));
  // parse arguments
  auto result = options.parse(argc, argv);
  if (result.count("help"))
  {
      std::cout << options.help() << std::endl;
      exit(0);
  }
  
  // Prepare pipeline components
  GstBus *bus;
  GMainLoop *main_loop;
  std::string src_pipeline_string;
  gst_init(&argc, &argv);  // Initialize Gstreamer
  // Create the main loop
  main_loop = g_main_loop_new (NULL, FALSE);

  // Create the pipeline
  std::string pipeline_string = create_pipeline_string(result["input"].as<std::string>(), 
  result["window"].as<std::string>(),
  result["debug"].as<bool>(), result["disable-landmarks-tracking"].as<bool>());
  
  // Parse the pipeline string and create the pipeline
  GstElement *pipeline = gst_parse_launch(pipeline_string.c_str(), NULL);
  
  // Get the bus
  bus = gst_element_get_bus(pipeline);

  // Run hailo utils setup
  setup_hailo_utils(pipeline, bus, main_loop, 
  result["show-fps"].as<bool>(), 
  result["hailo-stats"].as<bool>(), 
  result["host-stats"].as<bool>());
  
  // Set the pipeline state to PLAYING
  gst_element_set_state(pipeline, GST_STATE_PLAYING);
  
  // Run the main loop this is blocking will run until the main loop is stopped
  g_main_loop_run(main_loop);
  
  // Free resources
  gst_element_set_state(pipeline, GST_STATE_NULL);
  gst_deinit();
  gst_object_unref(pipeline);
  gst_object_unref(bus);
  g_main_loop_unref (main_loop);

  return 0;
}