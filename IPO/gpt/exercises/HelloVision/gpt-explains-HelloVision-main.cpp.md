Focus: main.cpp.

Headers

#include <iostream> → pulls in cout (console output).

#include <opencv2/opencv.hpp> → umbrella header: loads core, imgproc, highgui, etc. One include gives all OpenCV.

Namespaces

using namespace std; → cout instead of std::cout.

using namespace cv; → Mat, imread instead of cv::Mat, cv::imread.

int main()
Entry point. Returns int to OS. All code runs sequentially.

Mat src;
Declares a cv::Mat — OpenCV's image/matrix container. Empty until assigned. Holds: data pointer, rows, cols, type, refcount.

src = imread("../circles.bmp", IMREAD_GRAYSCALE);

imread → highgui/imgcodecs function. Reads image from disk.

../ → one folder up from exe (build dir).

IMREAD_GRAYSCALE → force 1-channel, 8-bit (CV_8UC1).

Produces: src filled with pixel data, or empty if fail.

if(!src.data)
Checks if src has pixel data. src.data is the raw pointer. Null → load failed. (Modern style: src.empty().)

else { ... }
Everything below only runs if image loaded.

int height = src.rows, width = src.cols;

rows = height (y).

cols = width (x).
Grabs dimensions for later.

namedWindow("Original image", WINDOW_AUTOSIZE);

namedWindow → highgui. Creates a GUI window on screen.

WINDOW_AUTOSIZE → window auto-fits image, no manual resize.

Produces: an empty window registered under name "Original image".

moveWindow("Original image", 100, 100);
Moves that window to screen coordinate (100,100). Purely placement.

imshow("Original image", src);

imshow → highgui. Renders src into the named window.

CV_8UC1 → displayed as grayscale.

Produces: visible image on screen.

Mat dst(width,height,CV_8UC1);
Creates empty Mat. Constructor: (rows, cols, type).

Passed width as rows, height as cols → swapped.

Harmless for square image; bug for non-square.

CV_8UC1 → 8-bit unsigned, 1 channel (binary/gray).

threshold(src,dst,120,255,THRESH_BINARY);

threshold → imgproc.

Args: source, destination, threshold (120), maxval (255), type.

THRESH_BINARY: if pixel > 120 → 255, else → 0.

Produces: dst = binary image (pure black/white).

namedWindow("Threshold", WINDOW_AUTOSIZE);
Second window, same behavior as first.

moveWindow("Threshold", 450, 100);
Placed to the right of the first window.

imshow("Threshold", dst);
Shows binary result. Visually compare against src.

while (waitKey(10)!=27);

waitKey(10) → highgui. Waits 10 ms for a keypress, returns key code (or -1).

27 = ESC key.

Loop runs until ESC pressed.

Side effect: pumps GUI event loop — without waitKey, imshow windows won't render/refresh.

End of main
Returns 0 implicitly. Windows destroyed automatically on exit.




Mat is the fundamental container class for images and matrices in OpenCV. Just as an int variable holds a number, a cv::Mat object holds all the data and metadata for an image.

Think of it like a smart box that contains:

The pixel data (a grid of numbers, like a 2D array).

Metadata describing that data: its size (rows, cols), data type (e.g., CV_8UC1), number of channels, and how it's stored in memory.