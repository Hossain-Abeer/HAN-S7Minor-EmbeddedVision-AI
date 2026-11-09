    // src/config.h — scope lock (0.4)
#pragma once

constexpr const char* DATA_ROOT =
    "D:/HAN/Semester 7 Minor/billiards-game-clips";

enum class BallType { CUE, SOLID, STRIPE, UNCERTAIN };
// 8-ball -> SOLID. Three game classes only. No text-recognition class.
// No live-capture source class.

constexpr int NUM_GAME_CLASSES = 3;   // CUE, SOLID, STRIPE
constexpr int NUM_LABELS       = 4;   // + UNCERTAIN

// --- Enhancement (2.1) ---
constexpr int    BLUR_KSIZE  = 5;
constexpr double BLUR_SIGMA  = 0.0;

// --- Segmentation: cloth HSV (3.1, widened for F3 lighting) ---
// Sampled from game1/clothColor_noAspectRatio.png (7 mid-cloth points,
// cue-ball + shadow ROIs excluded). Source: 0.5_cloth_samples.txt.
// Raw min/max: H 90..91 | S 253..255 | V 121..156.
// Widened per designTracker 3.1: H +-5, S +-10, V +-10.
constexpr int CLOTH_H_LO = 35,  CLOTH_H_HI = 100;  // widened H
constexpr int CLOTH_S_LO = 50,  CLOTH_S_HI = 255;  // widened S (lowered 243 -> 50)
constexpr int CLOTH_V_LO = 50,  CLOTH_V_HI = 220;  // widened V (raised 166 -> 220)

constexpr int MORPH_KERNEL_SIZE = 3;
constexpr int MORPH_ITER        = 1;

// --- Contour filter (3.4) ---
constexpr int    MIN_BALL_AREA   = 1500;
constexpr int    MAX_BALL_AREA   = 60000;
constexpr double MIN_CIRCULARITY = 0.75;
constexpr double ASPECT_MIN      = 0.70;
constexpr double ASPECT_MAX      = 1.40;

// --- Feature extraction (4.1, 4.2) ---
constexpr int WHITE_S_MAX = 40;
constexpr int WHITE_V_MIN = 200;
constexpr int CANNY_LO    = 50;
constexpr int CANNY_HI    = 150;

// --- Classification rules (5.2) ---
constexpr double RATIO_CUE          = 0.80;
constexpr double UNCERTAIN_WHITE_HI = 0.60;
constexpr double RATIO_STRIPE_LO    = 0.15;
constexpr double SOLID_WHITE_LO     = 0.05;
constexpr double UNCERTAIN_WHITE_LO = 0.05;
constexpr double EDGE_SOLID_MIN     = 0.10;
constexpr double EDGE_CUE_MAX       = 0.04;

// --- Acquisition (1.3) ---
constexpr int PROCESS_WIDTH = 1280;