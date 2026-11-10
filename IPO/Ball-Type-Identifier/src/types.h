#pragma once
#include <opencv2/opencv.hpp>

struct BallCandidate {
    cv::Rect    bbox;
    cv::Point2f center;
    int         area;
};