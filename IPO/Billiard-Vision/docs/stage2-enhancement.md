# Stage 2: Enhancement — Defense Prep

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **Type** | `const cv::Mat& frame` — BGR, `CV_8UC3`, 1280 × H |
| **From** | Stage 1 (`main.cpp` main loop, after `resize`) |
| **Ownership** | Passed by const-reference — **read-only**, original frame untouched |
| **Format** | 8-bit unsigned, 3 channels (Blue, Green, Red order) |

### Process (Sequence of Actions)
1. **`applyPreprocessing(frame, blurred, hsv)`** — single function call, two output Mats.
2. **`cv::GaussianBlur(frame, blurred, Size(BLUR_KSIZE, BLUR_KSIZE), BLUR_SIGMA)`** — smooth **BGR**.
3. **`cv::cvtColor(blurred, hsv, COLOR_BGR2HSV)`** — convert the **blurred** BGR → HSV.

That's it. **Two lines.** But those two lines and their order are the two most defensible decisions in this stage.

### Data Out
| Aspect | Detail |
|---|---|
| **`blurred`** | BGR, `CV_8UC3`, 1280 × H (smoothed) |
| **`hsv`** | HSV, `CV_8UC3`, 1280 × H (H: 0–179, S: 0–255, V: 0–255) |
| **Piped to** | `blurred` → Stage 3 (greenBall patch is BGR? no — see below) & Stage 4 `computeEdgeDensity` |
| **Piped to** | `hsv` → Stage 3 `extractCandidates` (cloth mask), Stage 4 `computeWhiteRatio` |
| **Neither** is destroyed after the loop iteration; both re-allocated each frame (OpenCV handles Mat reuse internally) |

---

## 2. Codebase, Libraries, Imports

**File:** `src/preprocess.cpp` (the entire file — 7 lines)

```cpp
#include "preprocess.h"
#include "config.h"

void applyPreprocessing(const cv::Mat& frame, cv::Mat& blurred, cv::Mat& hsv) {
    // 1.4 — BGR -> Blur -> HSV (order matters)
    cv::GaussianBlur(frame, blurred, cv::Size(BLUR_KSIZE, BLUR_KSIZE), BLUR_SIGMA);
    cv::cvtColor(blurred, hsv, cv::COLOR_BGR2HSV);
}
```

**Header:** `src/preprocess.h`
```cpp
#pragma once
#include <opencv2/opencv.hpp>

void applyPreprocessing(const cv::Mat& frame, cv::Mat& blurred, cv::Mat& hsv);
```

**Imports used:**
| Library | Function | Purpose |
|---|---|---|
| OpenCV `imgproc` | `cv::GaussianBlur` | Smooth BGR frame |
| OpenCV `imgproc` | `cv::cvtColor` | BGR → HSV |
| OpenCV core | `cv::Size` | Kernel dimension (5×5) |
| OpenCV core | `cv::Mat` | Container |
| `config.h` | `BLUR_KSIZE`, `BLUR_SIGMA` | Tuning constants |

**Call site (`main.cpp`):**
```cpp
Mat blurred, hsv;
applyPreprocessing(frame, blurred, hsv);
```

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Notes |
|---|---|---|
| **"blurred"** | ❌ | Debug window in DevTracker 1.4 — **removed in production** to save FPS |
| **"H"** | ❌ | Hue channel debug window — commented out |
| **"S"** | ❌ | Saturation channel — commented out |
| **"V"** | ❌ | Value channel — commented out |
| **"frame"** | ✅ | Shown at end of `main` loop — but frame is **unmodified by this stage** (Blur and HSV are separate Mats). The frame displayed still has original BGR pixels + overlays drawn from later stages |

**Critical clarity for Peter:**  
Stage 2 does **not** modify `frame`. It produces **new** Mats (`blurred`, `hsv`) derived from `frame`. If Peter asks "why don't I see the blur?" — the answer is: it's applied to a *copy*, not the display frame. Debug windows were closed after empirical tuning.

**Why are debug windows gone?** DevTracker 1.4 measured FPS with 5 windows open: **~26 FPS with dips to 6.25**. Without: **~30 FPS**. Verified as GUI blit overhead, not code overhead. Deliberately removed for production (DevTracker 1.4 E3).

---

## 4. Logs

**Direct log output from Stage 2:** **None.**  
`preprocess.cpp` doesn't `cout` anything. It's a pure function.

**Indirect evidence in the log** — visible through Stage 3 and 4 results:

```
SUMMARY frame=4251 balls=13 CUE=1 SOLID=7 STRIPE=5 ?=0 rack=0 fps=29.49
```

**Interpretation of "why Stage 2 matters at all here":**
- `balls=13` — if Stage 2 had failed (e.g., no blur → noise → false contours), this number would be inflated.
- `?=0` — if HSV were corrupted by hue-wrap, the `white_ratio` would be noisy → more `?` flags. Zero `?` = clean HSV input.
- `fps=29.49` — near 30 FPS proves blur + cvtColor are not a bottleneck (they're SIMD-optimized).

**FPS contribution from Stage 2:** ~1–2 ms per frame at 1280×711. Negligible.

---

## 5. Skeletal + Parameters + Effects

### Skeletal
```cpp
void applyPreprocessing(const cv::Mat& frame, cv::Mat& blurred, cv::Mat& hsv) {
    // Step 1: Smooth BGR FIRST
    cv::GaussianBlur(
        frame,                                  // src (const-ref)
        blurred,                                // dst (BGR)
        cv::Size(BLUR_KSIZE, BLUR_KSIZE),       // 5×5 kernel
        BLUR_SIGMA                              // 0.0 → auto σ from ksize
    );

    // Step 2: Convert the SMOOTHED BGR to HSV
    cv::cvtColor(blurred, hsv, cv::COLOR_BGR2HSV);
}
```

### Parameter Table

| Param | Value | Location | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| `BLUR_KSIZE` | **5** | `config.h` | Smoother (less noise) BUT Canny edges soften → `edge_density` drops → weakens SOLID vs STRIPE distinction. Also blurs ball boundaries → `cv::moments` center drifts by 1–2 px → rack triangle perturbs. | Less smoothing → salt-pepper noise survives → false contours → `rejArea`/`rejCirc` counts inflate → FPS hits & classification noise. |
| `BLUR_SIGMA` | **0.0** | `config.h` | Sigma=0 → OpenCV **auto-derives** σ from ksize: σ ≈ 0.3·((k−1)/2−1)+0.8 = **~1.1** for k=5. This is textbook Gaussian. | N/A — σ=0 means "auto", not "no blur". Explicitly setting σ>0 would decouple σ from ksize; here we deliberately let ksize drive σ. |
| Order (Blur → HSV) | **fixed** | `preprocess.cpp` | Correct — hue computed from smoothed BGR. | **WRONG** — blurring HSV directly causes hue-wrap (0° and 180° are the same red, but a 5-px blur averages 179 and 2 → ~90 → cyan artifact). |

### Why 5×5 / σ≈1.1? (empirical reasoning)

| Kernel | Behavior |
|---|---|
| 3×3 | Too little — DevTracker 1.4 showed residual noise survives → false contours |
| **5×5** | **Chosen** — removes H.264 compression blockiness + camera noise, preserves ball edges (~32 px diameter; 5-px blur is < ⅙ of ball) |
| 7×7, 9×9 | Over-smoothing — ball edges lose definition; `edge_density` on striped balls collapses |

Also: ksize must be **odd** (OpenCV requirement for Gaussian — odd kernel = single center pixel). 5 satisfies this.

### Why not Median or Bilateral?

| Filter | Verdict |
|---|---|
| **Gaussian** ✅ | Fast, cheap, linear — ideal for H.264 blockiness which is *additive white noise* (Gaussian's sweet spot). |
| **Median** ❌ | Better for salt-pepper, slower (O(k²) per pixel but with sort). Slows FPS. Not needed — H.264 artifacts aren't salt-pepper. |
| **Bilateral** ❌ | Preserves edges but ~10× slower. Would tank FPS. Edge preservation is *irrelevant* here because we want smoothed BGR for Canny (Canny needs pre-smoothed input per its spec). |

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 1 OUT                                                          │
│ cv::Mat frame   (BGR, 1280×711, 8UC3)                                │
│ ├─ NO modification from Stage 1 resize                              │
│ └─ Passed by const-ref to applyPreprocessing()                       │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ applyPreprocessing(frame, blurred, hsv)         [preprocess.cpp]    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ cv::GaussianBlur(frame, blurred, Size(5,5), 0.0)               │  │
│  │                                                                │  │
│  │ • Uses 5×5 kernel (BLUR_KSIZE)                                 │  │
│  │ • σ auto-derived ≈ 1.1 (BLUR_SIGMA=0)                          │  │
│  │ • Removes H.264 blockiness + sensor noise                      │  │
│  │ • BORDER_REFLECT_101 (default) → no zero-padding artifacts     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ blurred (BGR, 8UC3)               │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ cv::cvtColor(blurred, hsv, COLOR_BGR2HSV)                      │  │
│  │                                                                │  │
│  │ • Standard OpenCV formula:                                     │  │
│  │   V = max(R,G,B)                                               │  │
│  │   S = (V − min) / V  if V>0 else 0                             │  │
│  │   H = 60·(G−B)/(V−min) → normalized to 0..179                  │  │
│  │ • Input is BLURRED — prevents hue-wrap at 0/179 boundary       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
└──────────────────────────────────┼────────────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          │                                               │
          ▼ blurred (BGR)                                 ▼ hsv (HSV)
┌──────────────────────────────┐         ┌────────────────────────────────┐
│ STAGE 4:                     │         │ STAGE 3:                       │
│ computeEdgeDensity(blurred,  │         │ extractCandidates(hsv, ...)    │
│   ball)                      │         │ → inRange cloth mask           │
│ (Canny on blurred BGR)       │         │                                │
│                              │         │ STAGE 4:                       │
│                              │         │ computeWhiteRatio(hsv, bbox)   │
│                              │         │ → inRange white mask           │
└──────────────────────────────┘         └────────────────────────────────┘
```

**Notice the fan-out:** one entry point → two output Mats → each consumed by **two different downstream stages**. This is the **only stage in the pipeline that multiplies data flow**. Every other stage is 1-in-1-out.

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why blur at all?"** | H.264 compression introduces 8×8 DCT blockiness + Mosquito noise. Unblurred, `Canny` in Stage 4 picks these as fake edges → `edge_density` inflates by 30–50% → STRIPE vs SOLID distinction collapses. Blur is a prerequisite for reliable Canny. |
| **"Why blur BGR and not HSV directly?"** | HSV's H channel is circular: 0° and 179° both represent red. A 5-px Gaussian blur on H would average values like 179 and 3 → 91 → **cyan**. This is *hue wrap*. Blurring BGR first avoids the wrap entirely because BGR is a linear vector space. |
| **"But is that really a problem?"** | Yes — and DevTracker 1.4 explicitly closed DT 2.3 on this. If Peter probes further, point him to the **red ball's edge** in an HSV-blurred image: you'd see a cyan halo. Blurring BGR → no halo. |
| **"Why 5×5 and not 3×3 or 7×7?"** | Empirically tuned in DevTracker 1.4. 3×3 left residual noise; 7×7 softened ball edges enough to degrade `edge_density`. 5×5 is the sweet spot for 1280px resolution — visually confirmed in the debug "blurred" window (before it was removed). |
| **"Why σ=0?"** | In OpenCV, `sigma=0` is a sentinel meaning "auto-derive σ from ksize." Formula: σ ≈ 0.3·((k−1)/2 − 1) + 0.8. For k=5: **σ ≈ 1.1**. This is the textbook Gaussian. Explicitly setting σ would decouple it from kernel size — not desirable here. |
| **"Why not Median or Bilateral?"** | Median targets salt-pepper (not our problem). Bilateral preserves edges (irrelevant — we *want* to soften edges so Canny detects real ball/numeral edges, not noise). Both are slower. Gaussian is the right tool. |
| **"Doesn't blur hurt small details?"** | Ball diameter ≈ 32 px. 5-px kernel blur radius ≈ 2.5 px = **~8% of ball diameter**. Still leaves ample edge definition for `edge_density` on striped bands (~10–15 px wide). Verified in DevTracker 1.4: `edge_density` on stripes still 0.13–0.25. |
| **"What's the FPS cost of this stage?"** | ~1–2 ms per frame at 1280×711. Measured via DevTracker 1.3: 30 FPS sustained → this stage contributes ~3–6% of frame budget. |
| **"What happens if I feed a non-BGR frame?"** | `cvtColor(..., COLOR_BGR2HSV)` assumes 3-channel 8-bit. If input were grayscale or float, it would throw. Our pipeline guarantees BGR via `VideoCapture` + `resize` with default `INTER_AREA` preserving dtype. Contract enforced by types. |
| **"Can this stage be bypassed?"** | In principle yes — `applyPreprocessing(frame, frame, hsv)` would blur the display frame too. But it would corrupt the visual overlay (Stage 7 draws text on `frame`). We deliberately keep `frame` unmodified for the display path. |

---

## 8. Cross-stage dependencies (for Peter's likely "what breaks if…" questions)

| If you change… | Ripple effect |
|---|---|
| `BLUR_KSIZE` ↑ | Canny edges soften → `edge_density` ↓ → SOLID vs STRIPE confusion. Also `cv::moments` center drifts → triangle hull distorts → **rack detection false negatives**. |
| `BLUR_KSIZE` ↓ | Noise survives → false contours → `rejArea`/`rejCirc` inflate → `balls=` count noisy → SUMMARY logs unstable. |
| Blur HSV instead of BGR | Hue-wrap → `white_ratio` inaccurate → CUE/STRIPE misclassification → false `?` flags → counter over-counts (glare triggers). |
| Remove blur entirely | Canny false edges → `edge_density` on every ball spikes → all SOLIDs flagged as CUE? No — but STRIPE/SOLID line gets fuzzy. Already covered in DevTracker 1.4 defect log. |

---

**Stage 2 complete.** When ready, prompt `[stage3]` and I'll detail Segmentation — the **most code-heavy** stage (HSV mask + green-ball patch + morphology + `RETR_LIST` + 3-filter pipeline), and the one Peter is most likely to probe (it's where the original `RETR_EXTERNAL` black-screen bug lived).