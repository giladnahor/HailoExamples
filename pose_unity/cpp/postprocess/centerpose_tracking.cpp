
/**
* Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
* Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)

**/

#include <cmath>
#include <iostream>
#include <stdio.h>
#include <string>
#include <vector>
#include <time.h>
#include <map>
#include <memory>
#include <mutex>

// Tappas includes
#include "hailo_objects.hpp"
#include "hailo_xtensor.hpp"
#include "hailo_common.hpp"
#include "centerpose_tracking.hpp"

#include "common/tensors.hpp"
#include "common/math.hpp"
#include "common/nms.hpp"

#include "xtensor/xadapt.hpp"
#include "xtensor/xarray.hpp"
#include "xtensor/xcontainer.hpp"
#include "xtensor/xeval.hpp"
#include "xtensor/xtensor.hpp"
#include "xtensor/xindex_view.hpp"
#include "xtensor/xio.hpp"
#include "xtensor/xmanipulation.hpp"
#include "xtensor/xmasked_view.hpp"
#include "xtensor/xoperation.hpp"
#include "xtensor/xpad.hpp"
#include "xtensor/xrandom.hpp"
#include "xtensor/xshape.hpp"
#include "xtensor/xsort.hpp"
#include "xtensor/xstrided_view.hpp"
#include "xtensor/xview.hpp"

const std::vector<std::pair<int, int>> centerpose_joint_pairs =
    {
        {0, 1}, {1, 3}, {0, 2}, {2, 4}, {5, 6}, {5, 7}, {7, 9}, {6, 8}, {8, 10}, {5, 11}, {6, 12}, {11, 12}, {11, 13}, {12, 14}, {13, 15}, {14, 16}};

class TrackedObject {
 public:
  explicit TrackedObject(int window_size = 5);

  void update(const std::vector<HailoPoint>& points);
  bool isExpired(float expiration_time);
  std::vector<HailoPoint> getLastFilteredSample();
  //function to set window size
  void setWindowSize(int window_size);

 private:
  int window_size_;
  std::vector<std::vector<HailoPoint>> samples_;
  uint64_t start_timestamp_;
  uint64_t last_timestamp_;

  std::vector<HailoPoint> medianFilter(const std::vector<HailoPoint>& points);
  
};

TrackedObject::TrackedObject(int window_size) : window_size_(window_size) {}
void TrackedObject::setWindowSize(int window_size){window_size_ = window_size;}
void TrackedObject::update(const std::vector<HailoPoint>& points) {
  // Get the current time
  time_t current_time;
  time(&current_time);
  uint64_t timestamp = static_cast<uint64_t>(current_time);

  // Update the last timestamp
  last_timestamp_ = timestamp;

  // Update the start timestamp if this is the first sample
  if (samples_.empty()) {
    start_timestamp_ = timestamp;
  }

  // Add the new sample to the list of samples
  samples_.push_back(points);

  // If the window size has been reached, remove the oldest sample
  while (samples_.size() > window_size_) {
    samples_.erase(samples_.begin());
  }
}

bool TrackedObject::isExpired(float expiration_time) {
  // Check if the elapsed time since the last update is greater than the expiration time
  if (samples_.empty()) {
    return true;
  }
  time_t current_time;
  time(&current_time);
  uint64_t timestamp = static_cast<uint64_t>(current_time);
  auto elapsed_time = timestamp - last_timestamp_;
  return elapsed_time > expiration_time;
}

std::vector<HailoPoint> TrackedObject::getLastFilteredSample() {
  // If there are no samples, return an empty vector
  if (samples_.empty()) {
    return std::vector<HailoPoint>();
  }

  // If there is only one sample, return it
  if (samples_.size() == 1) {
    return samples_[0];
  }

  // If there are multiple samples, return the median-filtered sample
  return medianFilter(samples_[samples_.size() - 1]);
}

std::vector<HailoPoint> TrackedObject::medianFilter(const std::vector<HailoPoint>& points) {
  // Initialize the filtered sample as a vector of the same size as the input points
  std::vector<HailoPoint> filtered_sample;
  filtered_sample.reserve((int)points.size());
  // Iterate over the points and calculate the filtered value for each coordinate
  for (int i = 0; i < points.size(); i++) {
    // Initialize the x and y coordinates of the filtered sample to 0
    float x_filtered = 0.0;
    float y_filtered = 0.0;
    float confidence_filtered = 0.0;

    // Iterate over the samples and calculate the weighted average of the x and y coordinates
    for (int j = 0; j < samples_.size(); j++) {
      // Get the current sample
      const std::vector<HailoPoint>& sample = samples_[j];
      // Get the current point from the sample
      const HailoPoint& point = sample[i];
      // Update the weighted average of the x and y coordinates using the confidence as the weight
      x_filtered += point.x() * point.confidence();
      y_filtered += point.y() * point.confidence();
      confidence_filtered += point.confidence();
    }
    // Divide the weighted sum by the total confidence to get the average
    float total_confidence = std::accumulate(samples_.begin(), samples_.end(), 0.0, [i](float sum, const std::vector<HailoPoint>& sample) {
      return sum + sample[i].confidence();
    });
    x_filtered /= total_confidence;
    y_filtered /= total_confidence;
    confidence_filtered /= samples_.size();
    // Add the filtered point to the filtered sample
    filtered_sample.emplace_back(x_filtered, y_filtered, confidence_filtered);
  }

  return filtered_sample;
}

/////////////////////////////////////////////////////////

class PoseTracker
{
private:
  // A mutex to protect access to the tracked objects map
  std::mutex m_mutex;

  // A map of tracked objects, keyed by their unique ID
  std::map<int, std::unique_ptr<TrackedObject>> m_tracked_objects;

  // A threshold for determining if a tracked object is expired
  float m_expiration_threshold;
  // window size for median filter
  int window_size_;

public:
  /**
   * @brief Construct a new Pose Tracker object
   *
   * @param expiration_threshold The threshold for determining if a tracked object is expired, in seconds
   */
  PoseTracker(float expiration_threshold, int window_size) : m_expiration_threshold(expiration_threshold), window_size_(window_size) {}

 /**
   * @brief Update the tracker with a new sample
   *
   * @param unique_id The unique ID of the tracked object
   * @param sample The new sample of the tracked object
   */
  void update(int unique_id, const std::vector<HailoPoint>& sample)
  {
    std::lock_guard<std::mutex> lock(m_mutex);

    // Check if the tracked object already exists in the map
    auto it = m_tracked_objects.find(unique_id);
    if (it == m_tracked_objects.end())
    {
      // If the tracked object does not exist, create a new TrackedObject and add it to the map
      m_tracked_objects[unique_id] = std::make_unique<TrackedObject>(window_size_);
      m_tracked_objects[unique_id]->update(sample);
    }
    else
    {
      // If the tracked object exists, update it with the new sample
      it->second->update(sample);
    }
  }

  /**
   * @brief Get the last filtered sample for a tracked object
   *
   * @param unique_id The unique ID of the tracked object
   * @return std::vector<HailoPoint> The last filtered sample of the tracked object, or an empty vector if the tracked object does not exist
   */
  std::vector<HailoPoint> getLastFilteredSample(int unique_id)
{
  std::lock_guard<std::mutex> lock(m_mutex);

  // Check if the tracked object exists in the map
  auto it = m_tracked_objects.find(unique_id);
  if (it == m_tracked_objects.end())
  {
    // If the tracked object does not exist, return an empty vector
    return std::vector<HailoPoint>();
  }
  else
  {
    // If the tracked object exists, return its last filtered sample
    return it->second->getLastFilteredSample();
  }
}

void cleanup()
{
  std::lock_guard<std::mutex> lock(m_mutex);

  // Iterate over the tracked objects map
  for (auto it = m_tracked_objects.begin(); it != m_tracked_objects.end(); )
  {
    // Check if the tracked object is expired
    if (it->second->isExpired(m_expiration_threshold))
    {
      // If the tracked object is expired, remove it from the map
      it = m_tracked_objects.erase(it);
    }
    else
    {
      // If the tracked object is not expired, move to the next entry in the map
      ++it;
    }
  }
}

void setWindowSize(int window_size){
  if (window_size_ != window_size){
    window_size_ = window_size;
    for (auto it = m_tracked_objects.begin(); it != m_tracked_objects.end(); ++it){
      it->second->setWindowSize(window_size);
    }
  }
}

std::vector<int> getTrackedIds()
{
  std::lock_guard<std::mutex> lock(m_mutex);

  std::vector<int> ids;
  ids.reserve(m_tracked_objects.size());

  // Iterate over the tracked objects map and add the unique IDs to the vector
  for (const auto& [id, tracked_object] : m_tracked_objects)
  {
    ids.push_back(id);
  }

  return ids;
}

};

int get_tracking_id(HailoDetectionPtr detection)
{
    for (auto obj : detection->get_objects_typed(HAILO_UNIQUE_ID))
    {
        HailoUniqueIDPtr id = std::dynamic_pointer_cast<HailoUniqueID>(obj);
        if (id->get_mode() == TRACKING_ID)
        {
            return id->get_id();
        }
    }
    return -1;
}

/////////////////////////////////////////////////////////
// Global variables
auto tracker = PoseTracker(1, 3);
auto window_size = 3;
auto frame_count = 0;

void init(const std::string config_path, const std::string function_name){
    try {
      // Convert the string to an integer
      window_size = std::stoi(config_path);
    } catch (const std::invalid_argument& e) {
      std::cerr << "Error converting windowsize to int: " << e.what() << std::endl;
    }

    tracker.setWindowSize(window_size);
}

void filter(HailoROIPtr roi)
{
  auto detections = hailo_common::get_hailo_detections(roi);

  for (auto detection : detections ){
      if (detection->get_label() == "person")
      {
          std::vector<HailoObjectPtr> old_landmarks;;
          for (auto landmarks : hailo_common::get_hailo_landmarks(detection))
          {
              if (landmarks->get_landmarks_type() != "centerpose")
                  continue;
              auto threshold = landmarks->get_threshold();
              std::vector<HailoPoint> points = landmarks->get_points();
              int tracking_id = get_tracking_id(detection);
              if (tracking_id == -1)
                continue;
              tracker.update(tracking_id, points);
              points = tracker.getLastFilteredSample(tracking_id);
              // Add HailoLandmarks pointer to the detection.
              detection->add_object(std::make_shared<HailoLandmarks>("centerpose", points, threshold, centerpose_joint_pairs));
              old_landmarks.push_back((HailoObjectPtr)landmarks);
          }
          tracker.cleanup();
          hailo_common::remove_objects(detection, old_landmarks);
      }
  }
}

void debug(HailoROIPtr roi)
  {
    frame_count++;
    if (frame_count % 100 == 0)
    {
      std::cout << "Frame: " << frame_count << std::endl;
      std::cout << "Tracked IDs: ";
      for (auto id : tracker.getTrackedIds())
      {
        std::cout << id << " ";
      }
      std::cout << std::endl;
      window_size = (window_size % 8) + 1;
      std::cout << "Window size: " << window_size << std::endl;
      tracker.setWindowSize(window_size);
    }
    hailo_common::add_classification(roi, "test", std::to_string(window_size), 1.0f);
    filter(roi);
  }
