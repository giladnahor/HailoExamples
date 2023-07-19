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
#include <vector>
#include <sys/resource.h>

// Tappas includes
#include "hailo_objects.hpp"
#include "hailo_common.hpp"

// // Open source includes
// #include <opencv2/opencv.hpp>
// #include <opencv2/imgcodecs.hpp>
// #include <opencv2/imgproc.hpp>
// #include <opencv2/core.hpp>

//******************************************************************
// DATA TYPES
//******************************************************************

struct UserData {
  GstElement* pipeline;
  GMainLoop* main_loop;
  GstElement* text_overlay;
  gboolean print_fps;
  gboolean print_hailo_stats;
  gboolean print_host_stats;
};

class DataAggregator {
public:
  // constructor
  DataAggregator(gpointer user_data) {
    this->data_ = static_cast<UserData*>(user_data);
  }
  void set_power(double power) {
    std::lock_guard<std::mutex> lock(mutex_);
    power_ = power;
    update_string();
  }

  void set_fps(double fps) {
    std::lock_guard<std::mutex> lock(mutex_);
    fps_ = fps;
    update_string();
  }

  void set_temp(double temp) {
    std::lock_guard<std::mutex> lock(mutex_);
    temp_ = temp;
    update_string();
  }

  void set_cpu(double cpu) {
    std::lock_guard<std::mutex> lock(mutex_);
    cpu_ = cpu;
    update_string();
  }

  void set_mem(double mem) {
    std::lock_guard<std::mutex> lock(mutex_);
    mem_ = mem;
    update_string();
  }

  std::string get_string() {
    std::lock_guard<std::mutex> lock(mutex_);
    return data_string_;
  }

private:
  void update_string() {
    std::stringstream ss;
    ss << std::fixed << std::setprecision(2);
    if (data_->print_fps) {
      ss << "FPS: " << fps_ << " ";
    }
    if (data_->print_hailo_stats) {
      ss << "Power: " << power_ << "W, Temp: " << temp_ << "C ";
    }
    if (data_->print_host_stats) {
      ss << "CPU: " << cpu_ << "%, MEM: " << mem_ << "MB ";
    }
    data_string_ = ss.str();
  }

  std::mutex mutex_;
  double power_ = 0.0;
  double fps_ = 0.0;
  double temp_ = 0.0;
  double cpu_ = 0.0;
  double mem_ = 0.0;
  std::string data_string_;
  UserData *data_;
};

//******************************************************************
// GLOBALS
//******************************************************************
pid_t pid;
UserData user_data;
DataAggregator data_aggregator(&user_data);

//******************************************************************
// PIPELINE UTILITIES
//******************************************************************
/**
 * @brief callback of new fps measurement signal
 *
 * @param fpsdisplaysink the element who sent the signal
 * @param fps the fps measured
 * @param droprate drop rate measured
 * @param avgfps average fps measured
 * @param udata extra data from the user
 */
static void fps_measurements_callback(GstElement *fpsdisplaysink,
                                      gdouble fps,
                                      gdouble droprate,
                                      gdouble avgfps,
                                      gpointer udata)
{
    data_aggregator.set_fps(fps);
}

double getProcessCpuUsage(int pid) {
  static double prev_cpu_usage = 0.0;  // Static variable to store previous measurement
  static double prev_sys_cpu_usage = 0.0;  // Static variable to store previous system CPU usage

  // Open the stat file for the process
  std::ifstream procStat("/proc/" + std::to_string(pid) + "/stat");
  std::string line;
  std::getline(procStat, line);

  // Split the line into fields
  std::vector<std::string> fields;
  std::stringstream lineStream(line);
  std::string field;
  while (std::getline(lineStream, field, ' ')) {
    fields.push_back(field);
  }

  // Parse the fields to get the process's CPU usage information
  double user_time = std::stod(fields[13]);
  double system_time = std::stod(fields[14]);
  double child_user_time = std::stod(fields[15]);
  double child_system_time = std::stod(fields[16]);

  // Close the stat file for the process
  procStat.close();

  // Open the stat file for the system
  procStat.open("/proc/stat");
  std::getline(procStat, line);

  // Split the line into fields
  fields.clear();
  lineStream.str(line);
  lineStream.clear();
  while (std::getline(lineStream, field, ' ')) {
    fields.push_back(field);
  }

  // Parse the fields to get the system's CPU usage information
  double sys_user_time = std::stod(fields[2]);
  double sys_nice_time = std::stod(fields[3]);
  double sys_system_time = std::stod(fields[4]);
  double sys_idle_time = std::stod(fields[5]);

  // Close the stat file for the system
  procStat.close();

  // Calculate the change in CPU usage
  double cpu_usage = (user_time + system_time + child_user_time + child_system_time) - prev_cpu_usage;
  double sys_cpu_usage = (sys_user_time + sys_nice_time + sys_system_time + sys_idle_time) - prev_sys_cpu_usage;
  double cpu_usage_percent = (cpu_usage / sys_cpu_usage) * 100.0;

  // Update the static variables for the next measurement
  prev_cpu_usage = user_time + system_time + child_user_time + child_system_time;
  prev_sys_cpu_usage = sys_user_time + sys_nice_time + sys_system_time + sys_idle_time;

  return cpu_usage_percent;
}

double getProcessMemoryUsage(int pid) {
  ///////////////////////////////////////////////////////////////////////////////
  // Note that the memory usage returned by this function might be entirely wrong
  ///////////////////////////////////////////////////////////////////////////////
  
  // // Open the stat file for the process
  // std::ifstream procStat("/proc/" + std::to_string(pid) + "/statm");
  // std::string line;
  // std::getline(procStat, line);

  // // Parse the line to get the process's memory usage
  // double memory_usage_kb;
  // std::stringstream lineStream(line);
  // lineStream >> memory_usage_kb;

  // // Close the stat file for the process
  // procStat.close();
  struct rusage usage;
  getrusage(RUSAGE_SELF, &usage);
  // Convert the memory usage from KB to MB
  return  usage.ru_maxrss / 1024.0;
}

bool update_host_stats_callback()
{
  try {
    // Get CPU usage
    double cpu_usage = getProcessCpuUsage(pid);
    data_aggregator.set_cpu(cpu_usage);
    // Get memory usage
    double memory_usage = getProcessMemoryUsage(pid);
    data_aggregator.set_mem(memory_usage);
  } catch (const std::exception &e) {
    std::cerr << "Error on update_host_stats_callback: " << e.what() << std::endl;
    return false;
  }
  return true;
}

/**
 * @brief Extract the elements from the pipeline. From those extract the pads, 
 *        then set the probe callbacks and signal callbacks on those elements.
 *
 * @param pipeline  -  GstElement*
 *        The pipeline to set probes for.
 *
 * @param print_fps  -  gboolean
 *        If true, then print fps.
 */
void set_probe_callbacks(gpointer user_data)
{
  UserData* data = static_cast<UserData*>(user_data);
  if (data->print_fps) {
    try {   
      // set fps-measurements signal callback to print the measurements
      std::cout << "Setting fps-measurements signal callback" << std::endl;   
      GstElement *display_0 = gst_bin_get_by_name(GST_BIN(data->pipeline), "hailo_display");
      g_signal_connect(display_0, "fps-measurements", G_CALLBACK(fps_measurements_callback), NULL);
    }
    catch (const std::exception& e) {
      std::cout << "Could not set fps-measurements signal callback make sure your display element name is hailo_display" << std::endl;
    }
  }

  if (data->print_host_stats) {
    // set timer to update host stats
    std::cout << "Setting timer to update host stats" << std::endl;
    g_timeout_add_seconds(1, (GSourceFunc)update_host_stats_callback, NULL);
  }
  if (data->print_hailo_stats) {
    // set timer to update hailo stats
    std::cout << "Setting hailo stats" << std::endl;
    try {
      GstElement *hailostats = gst_bin_get_by_name(GST_BIN(data->pipeline), "hailo_stats");
      if (hailostats == nullptr) {
        throw std::runtime_error("Could not set hailo stats make sure your hailodevicestats element name is hailo_stats");
      }
    } catch (const std::exception& e) {
      std::cout << "Error: " << e.what() << std::endl;
      std::cout << "You should add this to your pipeline: hailodevicestats name=hailo_stats silent=false " << std::endl;
    }
  }
}

// This class is used to monitor the bus for messages from GStreamer
class BusWatch {
  public:

  static gboolean bus_callback(GstBus* bus, GstMessage* message, gpointer user_data) {
    UserData* data = static_cast<UserData*>(user_data);

    switch (GST_MESSAGE_TYPE(message)) {
      case GST_MESSAGE_ERROR: {
        // An error occurred in the pipeline
        GError* error = nullptr;
        gchar* debug_info = nullptr;
        gst_message_parse_error(message, &error, &debug_info);
        g_printerr("Error received from element %s: %s\n", GST_OBJECT_NAME(message->src), error->message);
        g_printerr("Debugging info: %s\n", debug_info ? debug_info : "none");
        g_clear_error(&error);
        g_free(debug_info);
        // stop main loop
        g_main_loop_quit(data->main_loop);
        break;
      }
      case GST_MESSAGE_EOS:
        // The pipeline has reached the end of the stream
        g_print("End-Of-Stream reached.\n");
        // stop main loop
        g_main_loop_quit(data->main_loop);
        break;
      case GST_MESSAGE_ELEMENT: {
        const GstStructure* structure = gst_message_get_structure(message);
        // if structure name is HailoDeviceStatsMessage
        if (gst_structure_has_name(structure, "HailoDeviceStatsMessage")) {
          // get the temperature
          const GValue* temperature = gst_structure_get_value(structure, "temperature");
          // get the temperature as a float
          gfloat temperature_float = g_value_get_float(temperature);
          // get the power
          const GValue* power = gst_structure_get_value(structure, "power");
          // get the power as a float
          gfloat power_float = g_value_get_float(power);
          // convert the temperature and power to strings with 2 decimal places
          std::stringstream power_stream;
          power_stream << std::fixed << std::setprecision(2) << power_float;
          std::stringstream temperature_stream;
          temperature_stream << std::fixed << std::setprecision(2) << temperature_float;
          std::string text = "Temperature: " + temperature_stream.str() + " Power: " + power_stream.str();
          data_aggregator.set_temp(temperature_float);
          data_aggregator.set_power(power_float);
          // set the text on the display
          g_object_set(G_OBJECT(data->text_overlay), "text", data_aggregator.get_string().c_str() , NULL);
          }
          break;
        }
      default:
          // Print a message for other message types
          // g_print("Received message of type %s\n", GST_MESSAGE_TYPE_NAME(message));
          break;       
    }
    // We want to keep receiving messages
    return TRUE;
  }
};

//******************************************************************
// MAIN
//******************************************************************
/**
 * @brief Build command line arguments.
 * 
 * @return cxxopts::Options 
 *         The available user arguments.
 */
cxxopts::Options build_arg_parser()
{
  cxxopts::Options options("Hailo App");
  options.allow_unrecognised_options();
  options.add_options()
  ("h, help", "Show this help")
  ("i, input", "Set the input source (default $input_source)", cxxopts::value<std::string>()->default_value(std::string("/dev/video0")))
  ("f, show-fps", "Enable displaying FPS", cxxopts::value<bool>()->default_value("false"))
  ("s, hailo-stats", "Enable displaying Hailo stats", cxxopts::value<bool>()->default_value("false"))
  ("host-stats", "Enable displaying host stats", cxxopts::value<bool>()->default_value("false"));
  return options;
}


void setup_hailo_utils(GstElement *pipeline, GstBus *bus, GMainLoop *main_loop, gboolean print_fps = false, \
gboolean print_hailo_stats = false, gboolean print_host_stats = false)
{
    // get process id
    pid = getpid();
    std::cout << "Parent process id: " << pid << std::endl;
    
    
    // set user_data
    // Set the pipeline element
    user_data.pipeline = pipeline;

    // Set the main loop element
    user_data.main_loop = main_loop;

    // Set additional options
    user_data.print_fps = print_fps;
    user_data.print_hailo_stats = print_hailo_stats;
    user_data.print_host_stats = print_host_stats;
    
    set_probe_callbacks(&user_data);            // Set probe callbacks
    
    // Set the text overlay element
    try {
      GstElement *text_overlay = gst_bin_get_by_name(GST_BIN(pipeline), "text_overlay");
      user_data.text_overlay = text_overlay;
    } catch (const std::exception& e) {
      std::cout << "Could not get text_overlay element make sure your text_overlay element name is text_overlay" << std::endl;
    }
    // Extract closing messages
    gst_bus_add_watch(bus, &BusWatch::bus_callback, &user_data);
    return;
}