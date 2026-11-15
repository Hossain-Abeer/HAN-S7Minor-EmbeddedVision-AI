#include "rack-detection.h"
#include "config.h"
#include <opencv2/opencv.hpp>

bool detectRack(const std::vector<BallCandidate>& candidates) {
    // 1. Minimum ball count
    if ((int)candidates.size() < RACK_MIN_BALLS) return false;

    // 2. Extract ball centers
    std::vector<cv::Point> centers;
    centers.reserve(candidates.size());
    for (const auto& ball : candidates) {
        centers.push_back(cv::Point((int)ball.center.x, (int)ball.center.y));
    }

    // 3. Convex hull of the cluster
    std::vector<cv::Point> hull;
    cv::convexHull(centers, hull);

    // 4. Approximate hull to a polygon
    std::vector<cv::Point> approx;
    double peri = cv::arcLength(hull, true);
    cv::approxPolyDP(hull, approx, RACK_EPSILON_RATIO * peri, true);

    // 5. Triangle check
    if (approx.size() != 3) return false;

    // 6. Area check (filter small clusters that happen to be triangular)
    double area = cv::contourArea(approx);
    if (area < RACK_MIN_AREA) return false;

    

    return true;
}