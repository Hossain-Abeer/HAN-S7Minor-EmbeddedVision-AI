#include <iostream>
#include <opencv2/opencv.hpp>

using namespace std;
using namespace cv;

int main()
{
    Mat src;

    src = imread("../circles.bmp",IMREAD_GRAYSCALE);
    if(!src.data) {
       cout << "Could not open image!";
    }
    else {

       int height = src.rows; 
       int width = src.cols;

       // Create a window
       namedWindow("Original image", WINDOW_AUTOSIZE);
       moveWindow("Original image", 100, 100);

       // Show the image
       imshow("Original image", src);


       // Create bit image
       Mat dst(width, height, CV_8UC1);
       //new mat container named 'dst' created, memory allocated
       //assigned dimesnsions: widht, height, CV_8UC1
       //'width' and 'height' were previously defined
       //CV_8UC1 → a label representing greyscale (8-bit, 1 channel) 

       // Threshold
       threshold(src,dst,120,255,THRESH_BINARY);
       /*
       src → input grayscale.
       dst → output Mat (same size/type).
       thresh = 120 → cutoff value.
       maxval = 255 → value assigned when condition true.
       threshold() → function.
       THRESH_BINARY → enum.
       Function scans every pixel, applies rule, writes to dst.
       */

       // Create a window
       namedWindow("Threshold", WINDOW_AUTOSIZE);
       moveWindow("Threshold", 450, 100);

       // Show the image into window
       imshow("Threshold",dst);
      
       while (waitKey(10)!=27); 
    }  
}
