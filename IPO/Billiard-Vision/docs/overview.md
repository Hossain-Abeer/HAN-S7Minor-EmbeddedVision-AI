# Billiard-Vision: Pipeline Overview

This document provides a high-level overview of the data flow through the Billiard-Vision pipeline. Each stage is detailed with its inputs, processing logic, outputs, relevant codebase, and observability (windows/logs).

---

### Stage 1: Acquisition (`main.cpp`)
* **Data In:** Video source (`.mp4`). Passed via CLI argument or defaults to `billiards-game-clip1.mp4`. Read frame-by-frame via `cv::VideoCapture`.
* **Process:** 
    1. Check if the frame is empty (end of video).
    2. Calculate new height to maintain aspect ratio.
    3. Resize frame to `PROCESS_WIDTH` (1280px) using `cv::resize` with `INTER_AREA` interpolation (best for downscaling).
* **Data Out:** `cv::Mat frame` (BGR color space, 1280xH resolution). Piped to Stage 2.
* **Codebase / Libraries:** `main.cpp`, `<opencv2/opencv.hpp>`, `cv::VideoCapture`, `cv::resize`.
* **Windows:** The resized frame is eventually shown in the `imshow("frame", frame)` window at the end of the loop, but with overlays drawn on it.
* **Logs:** 
    * Log Snippet: `source=1388x772 -> 1280px wide`
    * Interpretation: Confirms the original video resolution and verifies the resize operation was applied to the target width.

---

### Stage 2: Enhancement (`preprocess.cpp`)
* **Data In:** `cv::Mat frame` (BGR) from Stage 1.
* **Process:** 
    1. Apply `cv::GaussianBlur` (5x5 kernel, sigma 0) to the BGR frame to reduce noise.
    2. Convert the *blurred* BGR image to HSV using `cv::cvtColor`.
    *Note: Blurring is done BEFORE HSV conversion to prevent hue-wrap artifacts (blurring HSV causes colors at the 0/179 boundary to average incorrectly).*
* **Data Out:** Two `cv::Mat` objects: `blurred` (BGR) and `hsv` (HSV). Both are piped to Stages 3 and 4.
* **Codebase / Libraries:** `preprocess.cpp`, `cv::GaussianBlur`, `cv::cvtColor`, `COLOR_BGR2HSV`.
* **Windows:** None. (Debug windows for H, S, V channels exist in code comments but are disabled to preserve FPS).
* **Logs:** None directly.

---

### Stage 3: Segmentation (`segment.cpp`)
* **Data In:** `cv::Mat hsv` from Stage 2.
* **Process:** 
    1. `cv::inRange` creates a mask of the green cloth using `CLOTH_H/S/V` bounds from `config.h`.
    2. `cv::bitwise_not` inverts the mask to isolate balls/rails/pockets.
    3. `greenBall` patch: ORs a specific HSV mask to prevent the solid green 6-ball from being absorbed into the cloth mask.
    4. `cv::morphologyEx`: OPEN (removes specks) then CLOSE (fills holes) using a 3x3 kernel.
    5. `cv::findContours` using `RETR_LIST` (extracts all contours, unlike `RETR_EXTERNAL` which missed balls inside the table rail).
    6. Filter loop: Drops contours based on Area (200-60000), Circularity (>0.75), and Aspect Ratio (0.7-1.4).
    7. `cv::moments`: Calculates the center `(x,y)` of accepted contours.
* **Data Out:** `std::vector<BallCandidate>` (structs containing `bbox`, `center`, `area`). Piped to Stage 4.
* **Codebase / Libraries:** `segment.cpp`, `cv::inRange`, `cv::findContours`, `cv::moments`.
* **Windows:** None in production. A `filtered` window exists for debug (shows black background with white accepted blobs).
* **Logs:** 
    * Log Snippet: `contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0`
    * Interpretation: 25 shapes found; 10 rejected for being too small/large, 1 rejected for not being round enough; 14 valid balls passed.

---

### Stage 4: Feature Extraction (`features.cpp`)
* **Data In:** `std::vector<BallCandidate>` from Stage 3, plus the `hsv` and `blurred` Mats from Stage 2.
* **Process:** Loops through each candidate:
    1. `computeWhiteRatio`: Crops the ball's bounding box (inset by 2px to avoid edges). Applies `cv::inRange` for white pixels (S < 40, V > 200). Divides white pixel count by total bbox area.
    2. `computeEdgeDensity`: Crops the bbox, converts to grayscale, applies `cv::Canny` (50, 150). Divides edge pixel count by total bbox area.
* **Data Out:** Updated `std::vector<BallCandidate>` with `white_ratio` and `edge_density` populated.
* **Codebase / Libraries:** `features.cpp`, `cv::Canny`, `cv::countNonZero`.
* **Windows:** `imshow("frame")` draws green boxes with `wr|ed` text for debug.
* **Logs:** 
    * Log Snippet: `frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE`
    * Interpretation: Ball #1 has 49.3% white pixels and 20.0% edge pixels. (This is a stripe ball).

---

### Stage 5: Classification (`classify.cpp`)
* **Data In:** `std::vector<BallCandidate>` with features from Stage 4.
* **Process:** `classifyBall()` function applies deterministic `if/else` rules:
    1. `wr > RATIO_CUE` (0.65) -> CUE.
    2. `wr > UNCERTAIN_WHITE_HI` (0.60) -> UNCERTAIN (extreme glare).
    3. `wr >= RATIO_STRIPE_LO` (0.15) -> STRIPE.
    4. `wr >= SOLID_WHITE_LO` (0.05) AND `ed > EDGE_SOLID_MIN` (0.10) -> SOLID.
    5. `else` -> SOLID (catches dark 8-ball).
* **Data Out:** Updated `std::vector<BallCandidate>` with `BallType type` populated.
* **Codebase / Libraries:** `classify.cpp`, `config.h`.
* **Windows:** `imshow("frame")` draws colored boxes and labels (White=CUE, Red=SOLID, Cyan=STRIPE, Yellow=?).
* **Logs:** 
    * Log Snippet: `frame=4251 ball=1 ... class=STRIPE`
    * Interpretation: The final class assigned to that ball based on the thresholds.

---

### Stage 6: Rack Detection (`rack-detection.cpp`)
* **Data In:** `std::vector<BallCandidate>` from Stage 5.
* **Process:** 
    1. Check `size() >= RACK_MIN_BALLS` (13).
    2. Extract centers into a `std::vector<cv::Point>`.
    3. `cv::convexHull`: Finds the outermost points of the cluster.
    4. `cv::approxPolyDP`: Simplifies the hull using epsilon ratio 0.035.
    5. Check if `approx.size() == 3` (triangle) AND `cv::contourArea > RACK_MIN_AREA` (12000).
* **Data Out:** `bool rackDetected` (true/false).
* **Codebase / Libraries:** `rack-detection.cpp`.
* **Windows:** `imshow("frame")` draws red text "RACK DETECTED" at (50,50) if true.
* **Logs:** 
    * Log Snippet: `... rack=1 fps=30.32`
    * Interpretation: Appended to the SUMMARY line. `1` means a triangular hull was detected this frame.

---

### Stage 7: Counter Logic (`game-counter.cpp`)
* **Data In:** `bool rackDetected` from Stage 6.
* **Process:** `GameCounter::update()` runs a State Machine:
    1. If `true`: increments `m_rackStreak`, resets absence/cooldown. If streak >= `DEBOUNCE_FRAMES` (10) and state is IDLE -> state becomes COUNTED, increments `m_count`, logs event, returns `true` once.
    2. If `false`: increments absence/cooldown. If absence > `ABSENCE_TOLERANCE` (3), resets rack streak. If cooldown >= `COOLDOWN_FRAMES` (45), state resets to IDLE.
* **Data Out:** `bool counted` (true for exactly one frame). Increments internal `m_count`.
* **Codebase / Libraries:** `game-counter.cpp`, `<fstream>`, `<ctime>`.
* **Windows:** `imshow("frame")` draws yellow text "COUNT: X" at (50,100).
* **Logs:** 
    * Log Snippet: `COUNTER EVENT: count=3 at frame=4281`
    * Also writes to `log-counted-[clip].txt`: `2026-11-15T11:03:51,4,billiards-game-clip7`
    * Interpretation: A new game was confirmed. The state machine successfully debounced the rack and fired the event exactly once.