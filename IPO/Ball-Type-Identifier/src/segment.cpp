#include "segment.h"
#include "config.h"
#include <fstream>
#include <iostream>
#include <vector>

std::vector<BallCandidate> extractCandidates(
    const cv::Mat& hsv, 
    const std::string& rejectPath, 
    cv::Mat& filteredOut
) {
    std::vector<BallCandidate> candidates;

    // 2.1 — cloth mask + invert
    cv::Mat cloth, ball;
    cv::inRange(hsv,
                cv::Scalar(CLOTH_H_LO, CLOTH_S_LO, CLOTH_V_LO),
                cv::Scalar(CLOTH_H_HI, CLOTH_S_HI, CLOTH_V_HI),
                cloth);
    cv::bitwise_not(cloth, ball);

    // Fix: Re-include the green solid ball (6-ball) which overlaps with cloth
    cv::Mat greenBall;
    cv::inRange(hsv, cv::Scalar(40, 150, 50), cv::Scalar(75, 255, 255), greenBall);
    cv::bitwise_or(ball, greenBall, ball);


    // 2.2 — morphology
    cv::Mat morphK = cv::getStructuringElement(cv::MORPH_RECT,
            cv::Size(MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE));
    cv::Mat m;
    cv::morphologyEx(ball, m, cv::MORPH_OPEN,  morphK, cv::Point(-1,-1), MORPH_ITER);
    cv::morphologyEx(m,    m, cv::MORPH_CLOSE, morphK, cv::Point(-1,-1), MORPH_ITER);

    // 2.3 — Find contours + filter
    cv::Mat mCopy = m.clone();
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(mCopy, contours, cv::RETR_LIST, cv::CHAIN_APPROX_SIMPLE);

    std::ofstream rej(rejectPath, std::ios::app);
    filteredOut = cv::Mat::zeros(m.size(), CV_8UC1);
    int nAccepted = 0, nRejectArea = 0, nRejectCirc = 0, nRejectAspect = 0;

    for (size_t i = 0; i < contours.size(); i++) {
        double area = cv::contourArea(contours[i]);
        cv::Rect bb = cv::boundingRect(contours[i]);

        if (area < MIN_BALL_AREA || area > MAX_BALL_AREA) {
            nRejectArea++;
            rej << "area " << area << " | bbox " << bb.x << "," << bb.y << "," << bb.width << "," << bb.height << "\n";
            continue;
        }

        double peri = cv::arcLength(contours[i], true);
        double circ = (peri > 0) ? (4.0 * CV_PI * area / (peri * peri)) : 0.0;
        if (circ < MIN_CIRCULARITY) {
            nRejectCirc++;
            rej << "circ " << circ << " | bbox " << bb.x << "," << bb.y << "," << bb.width << "," << bb.height << "\n";
            continue;
        }

        float aspect = (float)bb.width / bb.height;
        if (aspect < ASPECT_MIN || aspect > ASPECT_MAX) {
            nRejectAspect++;
            rej << "aspect " << aspect << " | bbox " << bb.x << "," << bb.y << "," << bb.width << "," << bb.height << "\n";
            continue;
        }

        // Accepted
        nAccepted++;
        cv::drawContours(filteredOut, contours, (int)i, cv::Scalar(255), -1);
        cv::rectangle(filteredOut, bb, cv::Scalar(128), 1);

        cv::Moments mu = cv::moments(contours[i]);
        cv::Point2f center(
            (float)(mu.m10 / (mu.m00 + 1e-5)),
            (float)(mu.m01 / (mu.m00 + 1e-5))  // <-- Fixed trailing comma bug here
        );
        candidates.push_back({ bb, center, (int)area });
    }
    rej.close();

    std::cout << "contours=" << contours.size()
              << " accepted=" << nAccepted
              << " candidates=" << candidates.size() 
              << " rejArea=" << nRejectArea
              << " rejCirc=" << nRejectCirc
              << " rejAspect=" << nRejectAspect << "\n";

    return candidates;
}