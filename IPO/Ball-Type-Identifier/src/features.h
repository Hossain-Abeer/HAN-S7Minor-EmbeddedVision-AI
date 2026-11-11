#pragma once
#include <opencv2/opencv.hpp>
#include "types.h"

float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox); //3.1
void computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball); // 3.2 