#pragma once
#include <opencv2/opencv.hpp>

void applyPreprocessing(const cv::Mat& frame, cv::Mat& blurred, cv::Mat& hsv);