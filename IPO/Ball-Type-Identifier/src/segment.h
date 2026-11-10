#pragma once
#include <opencv2/opencv.hpp>
#include <vector>
#include <string>
#include "types.h"

std::vector<BallCandidate> extractCandidates(
    const cv::Mat& hsv, 
    const std::string& rejectPath, 
    cv::Mat& filteredOut
);