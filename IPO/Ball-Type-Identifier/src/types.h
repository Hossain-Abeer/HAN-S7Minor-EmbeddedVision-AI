#pragma once
#include <opencv2/opencv.hpp>
#include "config.h" // for BallType enum

struct BallCandidate {
    cv::Rect    bbox;
    cv::Point2f center;
    int         area;
    float       white_ratio = 0.0f;   // 3.1
    float       edge_density = 0.0f; // 3.2
    BallType    type = BallType::UNCERTAIN; //3.5 
};

