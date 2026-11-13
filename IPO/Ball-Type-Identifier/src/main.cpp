#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include <ctime>
#include "config.h"
#include "types.h"
#include "preprocess.h"
#include "segment.h"
#include "features.h"
#include <cstdio>
#include "classify.h" //3.5 for classifyBallType

using namespace cv;
using namespace std;

/*
int main() {
    string clipPath = string(DATA_ROOT) + "/game1/billiards-game-clip1.mp4";
    VideoCapture cap(clipPath);
    if (!cap.isOpened()) {
        cerr << "Failed to open: " << clipPath << endl;
        return -1;
    }*/

    //4.4 CLI access
int main(int argc, char** argv) {
    // Default to clip1 if no argument is provided
    string clipName = "billiards-game-clip1.mp4"; 
    
    // If a filename is passed via terminal, use that instead
    if (argc > 1) {
        clipName = argv[1]; 
    }

    // Allow passing the full path or just the filename
    string clipPath = clipName;
    if (clipName.find("/") == string::npos && clipName.find("\\") == string::npos) {
        clipPath = string(DATA_ROOT) + "/game1/" + clipName;
    }

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

    // 4.2 Setup log file and redirect stdout
    char timebuf[32];
    time_t t = time(nullptr);
    strftime(timebuf, sizeof(timebuf), "%Y%m%d_%H%M%S", localtime(&t));
    string logPath = string(DATA_ROOT) + "/IPO/logs/4.2-log-consol_out_" + timebuf + ".txt";
    
    if (!freopen(logPath.c_str(), "w", stdout)) {
        cerr << "Failed to redirect stdout to log file!" << endl;
        return -1;
    }

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

        // 2. Setup rejection log path (reuse timebuf from 4.2 setup)
        string rejectPath = string(DATA_ROOT) + "/IPO/logs/rejects_" + timebuf + ".txt";

        // 3. Segment & Extract
        Mat filtered;
        vector<BallCandidate> candidates = extractCandidates(hsv, rejectPath, filtered); 

        // 4.2 — Counters for SUMMARY log (UNCERTAIN is separate)
        int nCue = 0, nSolid = 0, nStripe = 0, nUncertain = 0;

        //3.1. Feature extraction (white ratio)
        /*
        for (size_t i = 0; i < candidates.size(); ++i) {
        candidates[i].white_ratio = computeWhiteRatio(hsv, candidates[i].bbox);
        std::cout << "frame=" << frameCount
                << " ball=" << i
                << " bbox=(" << candidates[i].bbox.x << ","
                                << candidates[i].bbox.y << ","
                                << candidates[i].bbox.width << ","
                                << candidates[i].bbox.height << ")"
                << " wr=" << candidates[i].white_ratio << std::endl;
        }
        */

        /*
        // 3.1 & 3.2. Feature extraction
        for (auto& ball : candidates) {
            // Corrected signature & assignment:
            ball.white_ratio = computeWhiteRatio(hsv, ball.bbox); 
            computeEdgeDensity(blurred, ball); 
            // Debug output
            std::cout << "frame=" << frameCount
                      << " ball=" << (&ball - &candidates[0]) // safe index for range-based loop
                      << " wr=" << ball.white_ratio
                      << " ed=" << ball.edge_density << std::endl;
            
            // Draw on the original frame
            char text[64];
            snprintf(text, sizeof(text), "%.2f|%.2f", ball.white_ratio, ball.edge_density);
            cv::rectangle(frame, ball.bbox, cv::Scalar(0, 255, 0), 1);
            cv::putText(frame, text, cv::Point(ball.bbox.x, ball.bbox.y - 5), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.4, cv::Scalar(0, 255, 255), 1);
        }

        // 3.5 Classification:
        for (auto& ball : candidates) {
            ball.white_ratio = computeWhiteRatio(hsv, ball.bbox); 
            computeEdgeDensity(blurred, ball); 
            
            // 3.5 Classification
            ball.type = classifyBall(ball);

            // Determine label and color for overlay
            std::string label;
            cv::Scalar color;
            switch (ball.type) {
                case BallType::CUE:
                    label = "CUE"; color = cv::Scalar(255, 255, 255); break;
                case BallType::SOLID:
                    label = "SOLID"; color = cv::Scalar(0, 0, 255); break;
                case BallType::STRIPE:
                    label = "STRIPE"; color = cv::Scalar(255, 255, 0); break;
                case BallType::UNCERTAIN:
                    label = "?"; color = cv::Scalar(0, 255, 255); break;
            }

            // Debug output
            std::cout << "frame=" << frameCount
                      << " ball=" << (&ball - &candidates[0])
                      << " wr=" << ball.white_ratio
                      << " ed=" << ball.edge_density
                      << " class=" << label << std::endl;
            
            // Draw on the original frame
            char text[64];
            snprintf(text, sizeof(text), "%s", label.c_str());
            cv::rectangle(frame, ball.bbox, color, 1);
            cv::putText(frame, text, cv::Point(ball.bbox.x, ball.bbox.y - 5), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.5, color, 1);
        }
                        */

        
        

        // 3.1, 3.2, & 3.5. Feature extraction + Classification
        for (auto& ball : candidates) {
            // 1. Extract features ONCE
            ball.white_ratio = computeWhiteRatio(hsv, ball.bbox); 
            computeEdgeDensity(blurred, ball); 
            
            // 2. Classify
            ball.type = classifyBall(ball);

            /*
            // 3. Determine label and color
            std::string label;
            cv::Scalar color;
            switch (ball.type) {
                case BallType::CUE:       label = "CUE";    color = cv::Scalar(255, 255, 255); break; // White
                case BallType::SOLID:     label = "SOLID";  color = cv::Scalar(0, 0, 255);     break; // Red
                case BallType::STRIPE:    label = "STRIPE"; color = cv::Scalar(255, 255, 0);   break; // Cyan
                case BallType::UNCERTAIN: label = "?";      color = cv::Scalar(0, 255, 255);   break; // Yellow
            }*/

            // 3. Determine label and color - modded at DevTrack-4.2
            std::string label;
            cv::Scalar color;
            switch (ball.type) {
                case BallType::CUE:       label = "CUE";    color = cv::Scalar(255, 255, 255); nCue++;       break; // White
                case BallType::SOLID:     label = "SOLID";  color = cv::Scalar(0, 0, 255);     nSolid++;     break; // Red
                case BallType::STRIPE:    label = "STRIPE"; color = cv::Scalar(255, 255, 0);   nStripe++;    break; // Cyan
                case BallType::UNCERTAIN: label = "?";      color = cv::Scalar(0, 255, 255);   nUncertain++; break; // Yellow
            }

            // 4. Debug output (single print)
            std::cout << "frame=" << frameCount
                      << " ball=" << (&ball - &candidates[0])
                      << " wr=" << ball.white_ratio
                      << " ed=" << ball.edge_density
                      << " class=" << label << std::endl;
            

            // 5. Draw on the original frame
            cv::rectangle(frame, ball.bbox, color, 1);
            cv::putText(frame, label, cv::Point(ball.bbox.x, ball.bbox.y - 5), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.5, color, 1);
        }

        // 4.2 SUMMARY log (Tee'd via freopen)
        int64 now = getTickCount();
        double instantFps = getTickFrequency() / (double)(now - prevTick);
        prevTick = now;

        cout << "SUMMARY"
             << " frame=" << frameCount
             << " balls=" << candidates.size()
             << " CUE=" << nCue
             << " SOLID=" << nSolid
             << " STRIPE=" << nStripe
             << " ?=" << nUncertain
             << " fps=" << instantFps << endl;

        // Debug visuals (SHOW THE FRAME!)
        imshow("frame", frame);

        //3.1. Debug visuals
        /*
        Mat overlay = filtered.clone();
        cvtColor(overlay, overlay, COLOR_GRAY2BGR);
        for (size_t i = 0; i < candidates.size(); ++i) {
            char buf[32]; snprintf(buf, sizeof(buf), "%.2f", candidates[i].white_ratio);
            putText(overlay, buf,
                    Point(candidates[i].bbox.x, candidates[i].bbox.y - 4),
                    FONT_HERSHEY_SIMPLEX, 0.4, Scalar(0,255,255), 1);
            rectangle(overlay, candidates[i].bbox, Scalar(0,255,0), 1);
        }
        imshow("filtered", overlay);
        */

        // 4. Debug visuals
        //imshow("filtered", filtered);
        // imshow("hsv", hsv); 

        int k = waitKey(10);
        if (k == 27 || k == 'q') break;
    }

    cap.release();
    destroyAllWindows();
    return 0;
}