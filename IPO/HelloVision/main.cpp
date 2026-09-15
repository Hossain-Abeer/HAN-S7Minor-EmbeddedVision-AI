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

       int height = src.rows, width = src.cols;

       // Create a window
       namedWindow("Original image", WINDOW_AUTOSIZE);
       moveWindow("Original image", 100, 100);

       // Show the image
       imshow("Original image",src);


       // Create bit image
       Mat dst(width,height,CV_8UC1);

       // Threshold
       threshold(src,dst,120,255,THRESH_BINARY);

       // Create a window
       namedWindow("Threshold", WINDOW_AUTOSIZE);
       moveWindow("Threshold", 450, 100);

       // Show the image
       imshow("Threshold",dst);
      
       while (waitKey(10)!=27); 
    }  
}
