#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include <ctime>
#include "config.h"
#include "types.h"
#include "preprocess.h"
#include "segment.h"

using namespace cv;
using namespace std;

int main() {
    string clipPath = string(DATA_ROOT) + "/game1/billiards-game-clip1.mp4";
    VideoCapture cap(clipPath);
    if (!cap.isOpened()) {
        cerr << "Failed to open: " << clipPath << endl;
        return -1;
    }

    cout << "source=" << cap.get(CAP_PROP_FRAME_WIDTH) << "x" << cap.get(CAP_PROP_FRAME_HEIGHT)
         << " -> " << PROCESS_WIDTH << "px wide" << endl;

    int64 prevTick = getTickCount();
    int frameCount = 0;
    const int FPS_PRINT_EVERY = 30;
    Mat frame;

    while (true) {
        cap >> frame;
        if (frame.empty()) break;

        int newH = (int)(frame.rows * PROCESS_WIDTH / (double)frame.cols);
        resize(frame, frame, Size(PROCESS_WIDTH, newH), 0, 0, INTER_AREA);

        frameCount++;
        if (frameCount % FPS_PRINT_EVERY == 0) {
            int64 now = getTickCount();
            double fps = FPS_PRINT_EVERY * getTickFrequency() / (double)(now - prevTick);
            prevTick = now;
            cout << "frame=" << frameCount << " size=" << frame.cols << "x" << frame.rows
                 << " fps=" << fps << endl;
        }

        // 1. Preprocess (Enhancement)
        Mat blurred, hsv;
        applyPreprocessing(frame, blurred, hsv);

        // 2. Setup rejection log path
        char datebuf[16];
        time_t t = time(nullptr);
        strftime(datebuf, sizeof(datebuf), "%Y%m%d", localtime(&t));
        string rejectPath = string(DATA_ROOT) + "/IPO/logs/rejects_" + datebuf + ".txt";

        // 3. Segment & Extract
        Mat filtered;
        vector<BallCandidate> candidates = extractCandidates(hsv, rejectPath, filtered);

        // 4. Debug visuals
        imshow("filtered", filtered);
        // imshow("hsv", hsv); 

        int k = waitKey(10);
        if (k == 27 || k == 'q') break;
    }

    cap.release();
    destroyAllWindows();
    return 0;
}