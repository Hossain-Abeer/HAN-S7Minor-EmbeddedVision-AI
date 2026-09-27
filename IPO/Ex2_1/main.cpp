#include <iostream>
#include <opencv2/opencv.hpp>

using namespace std;
using namespace cv;

int main()
{
    Mat src = imread("../dark_flower.bmp", IMREAD_COLOR); //src matrix created; image is read & stored in src
    if (!src.data)
    {
        cout << "Could not open image!";
        return -1;
    }

    vector<Mat> channels;
    split(src, channels);

    Mat hsv;                                                //hsv matrix created
    cvtColor(src, hsv, COLOR_BGR2HSV);                      //BGR -> HSV conversion

    vector<Mat> hsvCh;
    split(hsv, hsvCh);

    namedWindow("Original", WINDOW_AUTOSIZE);   moveWindow("Original",   0,  0);
    namedWindow("Blue",     WINDOW_AUTOSIZE);   moveWindow("Blue",     320,  0);
    namedWindow("Green",    WINDOW_AUTOSIZE);   moveWindow("Green",    640,  0);
    namedWindow("Red",      WINDOW_AUTOSIZE);   moveWindow("Red",      960,  0);
    namedWindow("Hue",      WINDOW_AUTOSIZE);   moveWindow("Hue",        0,420);
    namedWindow("Saturation", WINDOW_AUTOSIZE); moveWindow("Saturation",320,420);
    namedWindow("Value",    WINDOW_AUTOSIZE);   moveWindow("Value",    640,420);

    imshow("Original", src);
    imshow("Blue", channels[0]);
    imshow("Green", channels[1]);
    imshow("Red", channels[2]);
    imshow("Hue", hsvCh[0]);
    imshow("Saturation", hsvCh[1]);
    imshow("Value", hsvCh[2]);
    imshow("Original", src);

    while (waitKey(1) != 27); // Wait for ESC key

    return 0;
}