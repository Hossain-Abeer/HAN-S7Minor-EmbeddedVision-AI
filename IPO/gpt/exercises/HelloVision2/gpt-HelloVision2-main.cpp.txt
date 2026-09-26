#include <iostream>
#include <opencv2/opencv.hpp>
#include <thread>  // for the sleep

using namespace std;
using namespace cv;

int main()
{
   VideoCapture Img;
   Img.open(0);

   if (!Img.isOpened()) {
      cout << "Could not take a snapshot, probably no camera connected!";
   }
   else {
      Mat Cam;
      // Take first snapshot
      Img >> Cam;
      
      if (!Cam.data) { // there is no frame
         cout << "Snapshot taken but could not be converted to image!";
      }
      else {
         while (waitKey(10)!=27)
         {
              // Create images
            Mat src,dst,Edge;

            // Take snapshot
            Img >> Cam;
            this_thread::sleep_for(chrono::milliseconds(5));
            // Convert to grayscale
            cvtColor(Cam,src,COLOR_BGR2GRAY);
            // Threshold
            threshold(src,dst,130,255,THRESH_BINARY);
            // Edge detection
            Canny(src,Edge,150,255,3);

            // Create Windows
            namedWindow("Snapshot",WINDOW_AUTOSIZE);
            moveWindow("Snapshot",100,5);
            namedWindow("GrayScale",WINDOW_AUTOSIZE);
            moveWindow("GrayScale",650,5);
            namedWindow("Threshold",WINDOW_AUTOSIZE);
            moveWindow("Threshold",100,500);
            namedWindow("Edge",WINDOW_AUTOSIZE);
            moveWindow("Edge",650,500);

            // Show images
            imshow("Snapshot",Cam);        
            imshow("GrayScale", src);
            imshow("Threshold",dst);
            imshow("Edge",Edge);
         }
      }
   }

}
