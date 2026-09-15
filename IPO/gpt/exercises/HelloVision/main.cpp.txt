// ============================================================
// HelloVision — main.cpp
// Loads a grayscale image, thresholds it, shows both windows.
// ============================================================

#include <iostream>              // for cout (console output)
#include <opencv2/opencv.hpp>    // umbrella header: core, imgproc, highgui, imgcodecs

using namespace std;             // so we can write cout instead of std::cout
using namespace cv;              // so we can write Mat instead of cv::Mat

int main()                       // entry point, runs top-to-bottom
{
    Mat src;                     // declare OpenCV image/matrix container (empty for now)

    // Read image from disk, force grayscale (1 channel, 8-bit)
    // "../" = one folder up from the .exe (which lives in build/)
    src = imread("../circles.bmp", IMREAD_GRAYSCALE);

    if(!src.data) {              // src.data is the raw pixel pointer; null = load failed
       cout << "Could not open image!";   // report failure (no window shown)
    }
    else {                       // only run the vision pipeline if image loaded

       int height = src.rows, width = src.cols;   // rows = height (y), cols = width (x)

       // --- Window 1: show original ---
       namedWindow("Original image", WINDOW_AUTOSIZE);  // create GUI window, auto-fit image
       moveWindow("Original image", 100, 100);          // place it at screen (100,100)

       imshow("Original image",src);                    // render src into that window

       // --- Prepare destination image ---
       // NOTE: constructor is (rows, cols, type) — here width/height are swapped.
       // Harmless for a square image, a bug for non-square ones.
       Mat dst(width,height,CV_8UC1);   // empty Mat: 8-bit unsigned, 1 channel

       // --- Threshold ---
       // For each pixel: >120 -> 255, else -> 0  (binary black/white)
       threshold(src,dst,120,255,THRESH_BINARY);

       // --- Window 2: show threshold result ---
       namedWindow("Threshold", WINDOW_AUTOSIZE);       // second GUI window
       moveWindow("Threshold", 450, 100);               // place to the right of window 1

       imshow("Threshold",dst);                         // render binary result

       // --- Keep windows alive until ESC (27) is pressed ---
       // waitKey(10) waits 10 ms, pumps GUI events, returns key code (or -1).
       // Without waitKey, imshow windows won't render/refresh.
       while (waitKey(10)!=27);
    }
}                            // returns 0 implicitly; windows close on exit