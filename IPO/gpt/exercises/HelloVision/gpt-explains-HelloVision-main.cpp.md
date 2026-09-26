FOCUS: main.cpp — HelloVision
================================

HEADERS
-------
#include <iostream>
    Pulls in cout (console output).

#include <opencv2/opencv.hpp>
    Umbrella header: loads core, imgproc, highgui, etc.
    One include gives all OpenCV.

NAMESPACES
----------
using namespace std;
    cout instead of std::cout.

using namespace cv;
    Mat, imread instead of cv::Mat, cv::imread.

INT MAIN()
----------
Entry point. Returns int to OS.
All code runs sequentially.

MAT SRC
-------
Mat src;
    Declares a cv::Mat — OpenCV's image/matrix container.
    Empty until assigned.
    Holds: data pointer, rows, cols, type, refcount.

IMREAD
------
src = imread("../circles.bmp", IMREAD_GRAYSCALE);
    imread -> highgui/imgcodecs. Reads image from disk.
    "../" -> one folder up from exe (build dir).
    IMREAD_GRAYSCALE -> force 1-channel, 8-bit (CV_8UC1).
    Produces: src filled with pixel data, or empty if fail.

LOAD GUARD
----------
if(!src.data)
    Checks src has pixel data. src.data is raw pointer.
    Null -> load failed. (Modern style: src.empty().)

else { ... }
    Everything below only runs if image loaded.

DIMENSIONS
----------
int height = src.rows, width = src.cols;
    rows = height (y). cols = width (x).
    Grabs dimensions for later.

WINDOW 1 — ORIGINAL
-------------------
namedWindow("Original image", WINDOW_AUTOSIZE);
    namedWindow -> highgui. Creates GUI window on screen.
    WINDOW_AUTOSIZE -> auto-fits image, no manual resize.
    Produces: empty window registered as "Original image".

moveWindow("Original image", 100, 100);
    Moves window to screen coord (100,100). Purely placement.

imshow("Original image", src);
    imshow -> highgui. Renders src into named window.
    CV_8UC1 -> displayed as grayscale.
    Produces: visible image on screen.

DESTINATION MAT
---------------
Mat dst(width,height,CV_8UC1);
    Creates empty Mat. Constructor: (rows, cols, type).
    Passed width as rows, height as cols -> SWAPPED.
    Harmless for square image; bug for non-square.
    CV_8UC1 -> 8-bit unsigned, 1 channel (binary/gray).

THRESHOLD
---------
threshold(src,dst,120,255,THRESH_BINARY);
    threshold -> imgproc.
    Args: source, destination, threshold (120), maxval (255), type.
    THRESH_BINARY: pixel > 120 -> 255, else -> 0.
    Produces: dst = binary image (pure black/white).

WINDOW 2 — THRESHOLD
--------------------
namedWindow("Threshold", WINDOW_AUTOSIZE);
    Second window, same behavior as first.

moveWindow("Threshold", 450, 100);
    Placed to the right of the first window.

imshow("Threshold", dst);
    Shows binary result. Visually compare against src.

EVENT LOOP
----------
while (waitKey(10)!=27);
    waitKey(10) -> highgui. Waits 10 ms for keypress,
    returns key code (or -1).
    27 = ESC key.
    Loop runs until ESC pressed.
    Side effect: pumps GUI event loop — without waitKey,
    imshow windows won't render/refresh.

END OF MAIN
-----------
Returns 0 implicitly. Windows destroyed automatically on exit.

================================
MAT CONCEPT
================================
Mat is the fundamental container class for images and matrices
in OpenCV. Just as an int variable holds a number, a cv::Mat
object holds all the data and metadata for an image.

Think of it as a smart box containing:
    - The pixel data (a grid of numbers, like a 2D array).
    - Metadata: size (rows, cols), data type (e.g. CV_8UC1),
      number of channels, and memory layout.





      



==================================================
HELLOVISION - main.cpp WALKTHROUGH
==================================================

INPUT
-----
File: circles.bmp
Loaded as: src (grayscale, CV_8UC1)


STEP 1 - LOAD
-------------
Code:   src = imread("../circles.bmp", IMREAD_GRAYSCALE);
Check:  if(!src.data) -> "Could not open image!"
Result: src = pixel data, or empty


STEP 2 - DIMENSIONS
-------------------
Code:   height = src.rows;  width = src.cols;
Result: dimensions stored for later


STEP 3 - SHOW ORIGINAL
----------------------
Code:   namedWindow("Original image", WINDOW_AUTOSIZE);
        moveWindow("Original image", 100, 100);
        imshow("Original image", src);

Result: window at (100,100)
        shows dark circle + X/lines
              light circle
              faint background


STEP 4 - CREATE DESTINATION
---------------------------
Code:   Mat dst(width, height, CV_8UC1);
Note:   (width,height) swapped -> harmless (square image)
Result: empty 1-channel 8-bit Mat


STEP 5 - THRESHOLD
------------------
Code:   threshold(src, dst, 120, 255, THRESH_BINARY);

Rule:   pixel > 120  -> 255 (white)
        pixel <= 120 -> 0   (black)

Result: dark pixels  -> black
        light pixels -> white


STEP 6 - SHOW THRESHOLD
-----------------------
Code:   namedWindow("Threshold", WINDOW_AUTOSIZE);
        moveWindow("Threshold", 450, 100);
        imshow("Threshold", dst);

Result: window at (450,100)
        dark circle + X/lines -> black
        light circle + bg     -> white


STEP 7 - HOLD
-------------
Code:   while (waitKey(10) != 27);

Effect: waits 10 ms per loop
        runs until ESC (key code 27)
        also pumps GUI event loop
        (without waitKey, windows won't render)


SEQUENCE
--------
load -> show original -> threshold -> show binary -> wait ESC


FINAL OUTPUT
------------
Window 1: original grayscale image
Window 2: binary image, dark shapes isolated on white
==================================================