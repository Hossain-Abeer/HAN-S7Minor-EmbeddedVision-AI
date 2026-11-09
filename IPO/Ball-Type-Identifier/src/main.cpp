#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include "config.h"

int main() {
    // DT 0.3 E5: all paths built by concatenation from DATA_ROOT
    std::string clipPath = std::string(DATA_ROOT) +
                           "/game1/billiards-game-clip1.mp4";

    cv::VideoCapture cap(clipPath);
    if (!cap.isOpened()) {
        std::cerr << "Failed to open: " << clipPath << std::endl;
        return -1;
    }

    cv::Mat frame;
    while (true) {
        cap >> frame;
        if (frame.empty()) break;

        cv::imshow("out", frame);

        // Convention (devTracker CONVENTIONS): waitKey 10 ms; ESC (27) or 'q'
        int k = cv::waitKey(10);
        if (k == 27 || k == 'q') break;
    }

    cap.release();
    cv::destroyAllWindows();
    return 0;
}