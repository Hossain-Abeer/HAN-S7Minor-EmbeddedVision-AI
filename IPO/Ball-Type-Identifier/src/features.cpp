#include "features.h"
#include "config.h"

//3.1 white ratio
float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox) {
    cv::Rect r(bbox.x + 2, bbox.y + 2, bbox.width - 4, bbox.height - 4);
    if (r.width < 4 || r.height < 4) return 0.0f;

    // clamp to image bounds
    r &= cv::Rect(0, 0, hsv.cols, hsv.rows);
    if (r.width < 4 || r.height < 4) return 0.0f;

    cv::Mat roi = hsv(r);
    cv::Mat white;
    cv::inRange(roi,
        cv::Scalar(0,   0,           WHITE_V_MIN),
        cv::Scalar(179, WHITE_S_MAX, 255),
        white);

    int cnt = cv::countNonZero(white);
    return (float)cnt / (float)(r.width * r.height);
}

//3.2 Edge ratio
void computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball) {
    cv::Rect r = ball.bbox;
    // Inset by 2px to avoid boundary artifacts
    r.x += 2; r.y += 2; r.width -= 4; r.height -= 4;
    if (r.width < 4 || r.height < 4) return;

    // clamp to image bounds (ADDED)
    r &= cv::Rect(0, 0, blurred.cols, blurred.rows);
    if (r.width < 4 || r.height < 4) return;

    cv::Mat roi_bgr = blurred(r);
    cv::Mat gray, edges;
    cv::cvtColor(roi_bgr, gray, cv::COLOR_BGR2GRAY);
    cv::Canny(gray, edges, CANNY_LO, CANNY_HI);
    
    ball.edge_density = cv::countNonZero(edges) / (float)edges.total();
}