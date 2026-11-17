# Stage 1: Acquisition — Defense Prep

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **Source type** | `.mp4` video file (H.264 encoded) |
| **Location** | `D:/HAN/Semester 7 Minor/billiards-game-clips/game1/` |
| **How fed in** | `argv[1]` via CLI, or default `billiards-game-clip1.mp4` |
| **Native resolution** | 1388 x 772 (test clips) |
| **Container read by** | `cv::VideoCapture` (FFMPEG backend on Windows) |
| **Data type produced** | `cv::Mat frame` in BGR, `CV_8UC3` |

### Process (Sequence of Actions)
1. **`main(int argc, char** argv)`** — accept CLI argument.
2. **Path resolution** — if no slash in `argv[1]`, prepend `DATA_ROOT + "/game1/"`.
3. **Open** — `cv::VideoCapture cap(clipPath)`.
4. **Fail-safe** — `if (!cap.isOpened())` → `cerr` + `return -1`.
5. **Diagnostic** — `cout << "source=...x... -> 1280px wide"` (goes to terminal, **before** freopen).
6. **Logging setup** — `freopen(logPath, "w", stdout)` (all subsequent `cout` → log file).
7. **Loop:**
   - `cap >> frame` — decode next frame.
   - `if (frame.empty()) break` — end-of-video detection.
   - `newH = (int)(frame.rows * 1280 / (double)frame.cols)` — aspect-preserving height.
   - `cv::resize(frame, frame, Size(1280, newH), 0, 0, INTER_AREA)` — downscale.
   - `if (frameCount % 30 == 0)` — rolling FPS calculation.

### Data Out
| Aspect | Detail |
|---|---|
| **Type** | `cv::Mat frame` (BGR, `CV_8UC3`, 1280 x 711 for the test clips) |
| **Piped to** | `applyPreprocessing(frame, blurred, hsv)` in `preprocess.cpp` (Stage 2) |
| **Ownership** | Frame is reused per iteration (no deep copy until Stage 3 bbox cropping) |

---

## 2. Codebase, Libraries, Imports

**File:** `src/main.cpp`

```cpp
#include <opencv2/opencv.hpp>   // VideoCapture, Mat, resize, INTER_AREA, getTickCount
#include <iostream>             // cout, cerr
#include <string>               // std::string
#include <ctime>                // time(), strftime
#include "config.h"             // DATA_ROOT, PROCESS_WIDTH
```

**Core Code Blocks:**

**CLI + Path Resolution:**
```cpp
int main(int argc, char** argv) {
    string clipName = "billiards-game-clip1.mp4"; 
    if (argc > 1) clipName = argv[1]; 

    string clipPath = clipName;
    if (clipName.find("/") == string::npos && clipName.find("\\") == string::npos) {
        clipPath = string(DATA_ROOT) + "/game1/" + clipName;
    }
```

**Open + Fail-Safe:**
```cpp
    VideoCapture cap(clipPath);
    if (!cap.isOpened()) {
        cerr << "Failed to open: " << clipPath << endl;
        return -1;
    }
```

**Resize (Aspect-Preserving):**
```cpp
    int newH = (int)(frame.rows * PROCESS_WIDTH / (double)frame.cols);
    resize(frame, frame, Size(PROCESS_WIDTH, newH), 0, 0, INTER_AREA);
```

**FPS Rolling Average:**
```cpp
    if (frameCount % FPS_PRINT_EVERY == 0) {
        int64 now = getTickCount();
        double fps = FPS_PRINT_EVERY * getTickFrequency() / (double)(now - prevTick);
        prevTick = now;
        cout << "frame=" << frameCount << " size=" << frame.cols << "x" << frame.rows
             << " fps=" << fps << endl;
    }
```

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Content |
|---|---|---|
| **Terminal (stdout)** | ✅ | `source=1388x772 -> 1280px wide` — **before** freopen |
| **Terminal (after freopen)** | ❌ | Goes blank; all `cout` redirected to log file |
| **`imshow("frame", frame)`** | ✅ | The resized frame, rendered at end of loop **with overlays from Stages 3–7** |
| **Stage-1-specific debug window** | ❌ | No dedicated Stage 1 window exists |
| **H/S/V channel windows** | ❌ | Commented out in Stage 2 (they were debug-only) |

**Key nuance:** The frame is shown, but by the time it hits `imshow`, it has bounding boxes, class labels, `RACK DETECTED`, and `COUNT: X` painted onto it from Stages 3–7. The "raw" Stage-1 resized frame is never displayed in isolation.

---

## 4. Logs

**Log file:** `DATA_ROOT/IPO/logs/4.2-log-consol_out_YYYYMMDD_HHMMSS.txt`

**Two types of output:**

**Startup (goes to terminal, NOT file):**
```
source=1388x772 -> 1280px wide
```

**FPS + size (goes to file, every 30 frames):**
```
frame=30   size=1280x711 fps=28.747
frame=60   size=1280x711 fps=30.9103
frame=90   size=1280x711 fps=30.8814
frame=120  size=1280x711 fps=31.2415
...
frame=780  size=1280x711 fps=32.2555
```

### Interpretation
- `frame=30` → 30th frame processed since start.
- `size=1280x711` → aspect-preserved: `1280/1388 = 0.9222`, `772 × 0.9222 = 711.6` → floor = **711**.
- `fps=28.747` → 30 frames in 1.044 s = 28.75 FPS.
- **Target (TR4): ≥15 FPS.** Observed: 25–32 FPS → **~2× headroom**.

### Known cosmetic bug (defend proactively)
At `frameCount % 30 == 0`, the SUMMARY block **also** calls `getTickCount()` on the same frame (added in DevTracker 4.2). Both blocks compete for `prevTick`, so SUMMARY measures `now − prevTick ≈ 0 ms` → prints a spike like `fps=1274.68`.  
**Effect:** Cosmetic only. Self-corrects next frame. Documented in DevTracker 4.2 (D2). **Not a defect.**

---

## 5. Skeletal + Parameters + Effects

### Skeletal (Stage 1 only)
```cpp
int main(int argc, char** argv) {
    // 1. Parse CLI
    string clipName = (argc > 1) ? argv[1] : "billiards-game-clip1.mp4";

    // 2. Resolve relative → absolute path
    string clipPath = clipName;
    if (clipName.find_first_of("/\\") == string::npos) {
        clipPath = string(DATA_ROOT) + "/game1/" + clipName;
    }

    // 3. Open + fail-safe
    VideoCapture cap(clipPath);
    if (!cap.isOpened()) { cerr << "Failed: " << clipPath; return -1; }

    // 4. Setup timing
    int64 prevTick = getTickCount();
    int frameCount = 0;
    const int FPS_PRINT_EVERY = 30;
    Mat frame;

    // 5. Main loop
    while (true) {
        cap >> frame;
        if (frame.empty()) break;

        // Resize
        int newH = (int)(frame.rows * PROCESS_WIDTH / (double)frame.cols);
        resize(frame, frame, Size(PROCESS_WIDTH, newH), 0, 0, INTER_AREA);

        // FPS (every 30 frames)
        frameCount++;
        if (frameCount % FPS_PRINT_EVERY == 0) { /* compute + cout */ }

        // → frame piped to Stage 2
    }

    cap.release();
    destroyAllWindows();
    return 0;
}
```

### Parameter Table

| Param | Value | Location | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| `PROCESS_WIDTH` | **1280** | `config.h` | More px per ball → better classification & Canny edges. But CPU cost ↑, FPS ↓. | Faster FPS but balls shrink below ~22 px → classification unreliable, contours noisy. |
| `FPS_PRINT_EVERY` | 30 | `main.cpp` (const) | Fewer log lines, longer averaging window (smoother). | Noisier FPS reporting, more log spam. |
| `INTER_AREA` | fixed | `main.cpp` | Best for **downscale** — averages pixels, no aliasing. | Using `INTER_LINEAR` instead → aliasing → fake Canny edges in Stage 4 edge_density. |

### PROCESS_WIDTH justification (defend with DevTracker 1.3 evidence)
- **960** → ~30 FPS, ball ≈ 22 px, classification less stable.
- **1280** → ~30 FPS, ball ≈ 32 px, **chosen** (no FPS penalty vs 960).
- **1920** → untested; FPS headroom exists but diminishing return (32 px is already comfortably above MIN_BALL_AREA-derived diameter).
- **Decision rule (DevTracker 1.3):** `960 default; 1280 if FPS > 15`. Measured ~29.8 FPS at 1280 → keep 1280.
- **Why not OCR at 1280?** Ball ≈ 32 px diameter. Numeral occupies ~10–12 px. Tesseract/OCR requires ≥ 64 px per character minimum for reliable recognition. **OCR is a 4K-only feature.**

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ TERMINAL                                                             │
│ $ ./Billiard-Vision.exe billiards-game-clip2.mp4                     │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ main(argc, argv)                       [main.cpp, lines ~24–38]     │
│ ├─ clipName = argv[1]  (or default clip1)                            │
│ ├─ if no "/" → clipPath = DATA_ROOT + "/game1/" + clipName           │
│ └─ clipPath = ".../billiards-game-clip2.mp4"                         │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ cv::VideoCapture cap(clipPath)         [main.cpp, line ~41]          │
│ ├─ FFMPEG opens .mp4                                                 │
│ ├─ if (!cap.isOpened()) → cerr + return -1                           │
│ └─ cout << "source=1388x772 -> 1280px wide"  [TERMINAL]              │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ freopen(logPath, "w", stdout)          [main.cpp, line ~62]          │
│ └─ all subsequent cout → 4.2-log-consol_out_YYYYMMDD.txt             │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
       ┌──────────── while(true) ────────────┐
       │                                     │
       ▼                                     │
┌──────────────────────────────────┐         │
│ cap >> frame                     │         │
│ if (frame.empty()) break;        │         │
└──────────────┬───────────────────┘         │
               │                             │
               ▼                             │
┌──────────────────────────────────┐         │
│ newH = frame.rows × 1280 / cols  │         │
│ resize(frame, 1280×newH,         │         │
│        INTER_AREA)               │         │
└──────────────┬───────────────────┘         │
               │                             │
               ▼                             │
┌──────────────────────────────────┐         │
│ frameCount++                     │         │
│ if (frameCount % 30 == 0):       │         │
│   fps = 30 × tickFreq / (t - t₀) │         │
│   cout << "frame=30 ... fps=..." │         │
└──────────────┬───────────────────┘         │
               │                             │
               │  ┌──────────────────────┐   │
               ├──│ cv::Mat frame        │   │
               │  │ BGR, 1280×711        │   │
               │  └──────────┬───────────┘   │
               │             │               │
               │             ▼               │
               │  ┌──────────────────────┐   │
               │  │ STAGE 2              │   │
               │  │ applyPreprocessing() │   │
               │  │ (preprocess.cpp)     │   │
               │  └──────────────────────┘   │
               │                             │
               └───────── (next frame) ──────┘
                                  │
                                  ▼ (on break)
┌──────────────────────────────────────────────────────────────────────┐
│ cap.release();  destroyAllWindows();  return 0;                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why `INTER_AREA` specifically?"** | It averages pixels when shrinking. `INTER_LINEAR`/`INTER_NEAREST` alias on downscale → fake edges → corrupt Stage 4's `edge_density`. Future-proof: 4K→1280 is a 3× downscale where this matters most. |
| **"Why 1280 and not the native 1388?"** | Normalisation. All `config.h` thresholds (`RACK_MIN_AREA=12000`, `MIN_BALL_AREA=200`) are pixel-calibrated. A fixed `PROCESS_WIDTH` guarantees the same pixel metrics regardless of source. Different cameras (1080p, 4K) → same pipeline. |
| **"What if source is smaller than 1280?"** | We'd upscale (bad). Assumed minimum: 1280. Documented assumption. Commercial deployment = 4K minimum per Section 4.3. |
| **"Why `VideoCapture` and not a live camera?"** | Reproducibility for empirical tuning. The same clip can be replayed identically across DevTracker experiments. For deployment: `VideoCapture(0)` or RTSP URL works — no code change. |
| **"What's the `fps=1274` spike?"** | Two `getTickCount()` blocks on `frameCount % 30` collide. SUMMARY measures `now − prevTick ≈ 0`. Cosmetic, self-corrects. Documented in DevTracker 4.2 D2. |
| **"What does `frame.empty()` catch?"** | End-of-video: FFMPEG returns a 0-row Mat. Also catches corrupt frame. Break → `cap.release()` → clean exit. |
| **"Why the aspect-ratio formula?"** | `newH = rows × 1280 / cols` uses a single division → preserves ratio. Example: 772 × 1280 / 1388 = 711.6 → floor(711). Rounding delta 0.28 px ≈ 0.1% — negligible vs ball diameter ~32 px. |
| **"How do you handle a corrupted / unsupported codec?"** | `cap.isOpened()` returns false → `cerr` + `return -1`. No crash. Exit code visible to caller. |

---

**Stage 1 complete.** When ready, prompt `[stage2]` and I'll detail Enhancement (`preprocess.cpp`) — Blur-Before-HSV ordering, hue-wrap reasoning, and the `BLUR_KSIZE` tuning decision.