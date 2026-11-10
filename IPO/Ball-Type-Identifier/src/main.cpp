#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include "config.h"
using namespace cv;
using namespace std;

//devtracker 2.3 - Contour+filters
#include <fstream>
#include <ctime>

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

        //imshow("cloth", cloth);
        imshow("ball",  ball);

        // 2.2 — morphology
        Mat morphK = getStructuringElement(MORPH_RECT,
                Size(MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE));
        Mat m;
        morphologyEx(ball, m, MORPH_OPEN,  morphK, Point(-1,-1), MORPH_ITER);
        morphologyEx(m,    m, MORPH_CLOSE, morphK, Point(-1,-1), MORPH_ITER);
        imshow("morph", m);


        // 2.3 — Find contours + filter by area / circularity / aspect
        Mat mCopy = m.clone();
        vector<vector<Point>> contours;
        findContours(mCopy, contours, RETR_LIST, CHAIN_APPROX_SIMPLE);

        char datebuf[16];
        time_t t = time(nullptr);
        strftime(datebuf, sizeof(datebuf), "%Y%m%d", localtime(&t));
        string rejectPath = string(DATA_ROOT) + "/IPO/logs/rejects_" + datebuf + ".txt";
        ofstream rej(rejectPath, ios::app);

        Mat filtered = Mat::zeros(m.size(), CV_8UC1);
        int nAccepted = 0, nRejectArea = 0, nRejectCirc = 0, nRejectAspect = 0;

        for (size_t i = 0; i < contours.size(); i++) {
            double area = contourArea(contours[i]);
            Rect bb = boundingRect(contours[i]);

            if (area < MIN_BALL_AREA || area > MAX_BALL_AREA) {
                nRejectArea++;
                rej << "area " << area << " | bbox " << bb.x << "," << bb.y << "," << bb.width << "," << bb.height << "\n";
                continue;
            }

            double peri = arcLength(contours[i], true);
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

            nAccepted++;
            drawContours(filtered, contours, (int)i, Scalar(255), -1);
            rectangle(filtered, bb, Scalar(128), 1);
        }
        rej.close();

        cout << "contours=" << contours.size()
            << " accepted=" << nAccepted
            << " rejArea=" << nRejectArea
            << " rejCirc=" << nRejectCirc
            << " rejAspect=" << nRejectAspect << "\n";

        imshow("filtered", filtered);        
        //imshow("out",     frame);     // original BGR
        //imshow("blurred", blurred);   // denoised BGR

        //imshow("Hue", ch[0]);           // hue
        //imshow("Saturation", ch[1]);           // saturation
        //imshow("Value", ch[2]);           // value
        



        // cv::imshow("out", frame);

        // Convention (devTracker CONVENTIONS): waitKey 10 ms; ESC (27) or 'q'
        int k = cv::waitKey(10);
        if (k == 27 || k == 'q') break;
    }

    cap.release();
    cv::destroyAllWindows();
    return 0;
}