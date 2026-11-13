#include "preprocess.h"
#include "config.h"

void applyPreprocessing(const cv::Mat& frame, cv::Mat& blurred, cv::Mat& hsv) {
    // 1.4 — BGR -> Blur -> HSV (order matters)
    cv::GaussianBlur(frame, blurred, cv::Size(BLUR_KSIZE, BLUR_KSIZE), BLUR_SIGMA);
    cv::cvtColor(blurred, hsv, cv::COLOR_BGR2HSV);
}