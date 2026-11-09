#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include "config.h"
using namespace cv;
using namespace std;

int main() {
    // DT 0.3 E5: all paths built by concatenation from DATA_ROOT
    std::string clipPath = std::string(DATA_ROOT) +
                           "/game1/billiards-game-clip1.mp4";

    cv::VideoCapture cap(clipPath);
    if (!cap.isOpened()) {
        std::cerr << "Failed to open: " << clipPath << std::endl;
        return -1;
    }

    // DT 1.3: report source size once, then resize to PROCESS_WIDTH
    std::cout << "source=" << cap.get(cv::CAP_PROP_FRAME_WIDTH)
              << "x" << cap.get(cv::CAP_PROP_FRAME_HEIGHT)
              << " -> " << PROCESS_WIDTH << "px wide" << std::endl;

    int64 prevTick   = cv::getTickCount();
    int    frameCount = 0;
    double fps        = 0.0;
    const int FPS_PRINT_EVERY = 30;

    cv::Mat frame;
    while (true) {
        cap >> frame;
        if (frame.empty()) break;

        // DT 1.3: resize preserving aspect (INTER_AREA for downscale)
        int newH = (int)(frame.rows * PROCESS_WIDTH / (double)frame.cols);
        cv::resize(frame, frame, cv::Size(PROCESS_WIDTH, newH),
                   0, 0, cv::INTER_AREA);

        frameCount++;
        if (frameCount % FPS_PRINT_EVERY == 0) {
            int64 now = cv::getTickCount();
            fps = FPS_PRINT_EVERY * cv::getTickFrequency() /
                  (double)(now - prevTick);
            prevTick = now;
            std::cout << "frame=" << frameCount
                      << " size="  << frame.cols << "x" << frame.rows
                      << " fps="   << fps << std::endl;
        }

        // 1.4 — BGR -> Blur -> HSV (order matters)
        Mat blurred;
        GaussianBlur(frame, blurred, Size(BLUR_KSIZE, BLUR_KSIZE), BLUR_SIGMA);

        Mat hsv;
        cvtColor(blurred, hsv, COLOR_BGR2HSV);

        // debug channel split for visual verification
        vector<Mat> ch;
        split(hsv, ch);   // ch[0]=H, ch[1]=S, ch[2]=V


        // 2.1 — cloth mask + invert
        Mat cloth, ball;
        inRange(hsv,
                Scalar(CLOTH_H_LO, CLOTH_S_LO, CLOTH_V_LO),
                Scalar(CLOTH_H_HI, CLOTH_S_HI, CLOTH_V_HI),
                cloth);
        bitwise_not(cloth, ball);

        imshow("cloth", cloth);
        imshow("ball",  ball);

        imshow("out",     frame);     // original BGR
        imshow("blurred", blurred);   // denoised BGR
        imshow("Hue", ch[0]);           // hue
        imshow("Saturation", ch[1]);           // saturation
        imshow("V", ch[2]);           // value

        // cv::imshow("out", frame);

        // Convention (devTracker CONVENTIONS): waitKey 10 ms; ESC (27) or 'q'
        int k = cv::waitKey(10);
        if (k == 27 || k == 'q') break;
    }

    cap.release();
    cv::destroyAllWindows();
    return 0;
}