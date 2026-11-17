# Stage 4: Feature Extraction — Defense Prep

**Two numbers per ball. Every downstream decision depends on them.** If `white_ratio` is wrong, every class label is wrong, and every rack count is wrong.

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **From Stage 3** | `std::vector<BallCandidate>& candidates` — each has `bbox`, `center`, `area` populated |
| **From Stage 2** | `const cv::Mat& hsv` — for `white_ratio` (needs H, S, V channels) |
| **From Stage 2** | `const cv::Mat& blurred` — for `edge_density` (needs grayscale-able BGR) |
| **Ownership** | `hsv` and `blurred` read-only; `candidates` **mutated in place** |

### Process (Sequence of Actions)
Per candidate, in `main.cpp`'s loop:
```
for (auto& ball : candidates) {
    1. ball.white_ratio  = computeWhiteRatio(hsv, ball.bbox);
    2. computeEdgeDensity(blurred, ball);        // writes ball.edge_density
}
```

### Inside `computeWhiteRatio(hsv, bbox)`
```
1. Inset bbox by 2 px on all sides  →  (x+2, y+2, w-4, h-4)
2. If width < 4 OR height < 4  →  return 0.0f          [degenerate guard]
3. Clamp to image bounds  →  r &= cv::Rect(0, 0, hsv.cols, hsv.rows)
4. If width < 4 OR height < 4 after clamp  →  return 0.0f
5. cv::inRange(roi, (0, 0, 200), (179, 40, 255), white)
       → white mask: low saturation (S ≤ 40) AND high value (V ≥ 200)
6. count = countNonZero(white)
7. return count / (width × height)
```

### Inside `computeEdgeDensity(blurred, ball)`
```
1. Inset bbox by 2 px  →  (x+2, y+2, w-4, h-4)
2. If width < 4 OR height < 4  →  return               [degenerate guard]
3. Clamp to image bounds
4. If width < 4 OR height < 4 after clamp  →  return
5. cv::cvtColor(roi_bgr, gray, COLOR_BGR2GRAY)
6. cv::Canny(gray, edges, 50, 150)
7. ball.edge_density = countNonZero(edges) / edges.total()
```

### Data Out
| Aspect | Detail |
|---|---|
| **Type** | Same `std::vector<BallCandidate>` — two fields filled |
| **Field 1** | `float white_ratio` — range [0.0, 1.0] |
| **Field 2** | `float edge_density` — range [0.0, 1.0] |
| **Piped to** | Stage 5 (`classifyBall`) consumes both |

---

## 2. Codebase, Libraries, Imports

**File:** `src/features.cpp` (~50 lines)

```cpp
#include "features.h"
#include "config.h"

float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox);
void  computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball);
```

**Imports used:**
| Library | Function | Purpose |
|---|---|---|
| OpenCV core | `cv::Rect::operator&=` | Clamp to image bounds |
| OpenCV core | `cv::inRange` | HSV white mask |
| OpenCV core | `cv::countNonZero` | Count mask pixels |
| OpenCV imgproc | `cv::cvtColor` | BGR → GRAY |
| OpenCV imgproc | `cv::Canny` | Edge detection |
| `config.h` | `WHITE_S_MAX`, `WHITE_V_MIN`, `CANNY_LO`, `CANNY_HI` | Threshold constants |

**Full code, both functions:**

```cpp
float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox) {
    cv::Rect r(bbox.x + 2, bbox.y + 2, bbox.width - 4, bbox.height - 4);
    if (r.width < 4 || r.height < 4) return 0.0f;

    r &= cv::Rect(0, 0, hsv.cols, hsv.rows);
    if (r.width < 4 || r.height < 4) return 0.0f;

    cv::Mat roi = hsv(r);
    cv::Mat white;
    cv::inRange(roi,
        cv::Scalar(0,   0,          WHITE_V_MIN),   // H 0, S 0, V 200
        cv::Scalar(179, WHITE_S_MAX, 255),          // H 179, S 40, V 255
        white);

    int cnt = cv::countNonZero(white);
    return (float)cnt / (float)(r.width * r.height);
}

void computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball) {
    cv::Rect r = ball.bbox;
    r.x += 2; r.y += 2; r.width -= 4; r.height -= 4;
    if (r.width < 4 || r.height < 4) return;

    r &= cv::Rect(0, 0, blurred.cols, blurred.rows);
    if (r.width < 4 || r.height < 4) return;

    cv::Mat roi_bgr = blurred(r);
    cv::Mat gray, edges;
    cv::cvtColor(roi_bgr, gray, cv::COLOR_BGR2GRAY);
    cv::Canny(gray, edges, CANNY_LO, CANNY_HI);

    ball.edge_density = cv::countNonZero(edges) / (float)edges.total();
}
```

**Header (`features.h`):**
```cpp
#pragma once
#include <opencv2/opencv.hpp>
#include "types.h"

float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox);
void  computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball);
```

**Note the asymmetry in the signature:**
- `computeWhiteRatio` **returns** a `float` (pure function)
- `computeEdgeDensity` **mutates** `BallCandidate&` (impure)

Why? Historical — before DevTracker 3.3, both were going to return floats, but `edge_density` needs the ball object anyway (to access `.bbox`). Passing `BallCandidate&` saves one `bbox` copy. Cosmetic inconsistency, not a bug.

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Notes |
|---|---|---|
| **"frame" with `wr|ed` text** | 🟡 Shown in DevTracker 3.1/3.2 **during tuning**, but **removed in production** | See `main.cpp`: current overlay draws **class label** ("CUE"/"SOLID"/"STRIPE"), not `wr/ed` |
| **Overlay format** | `label` (e.g., "STRIPE") | Replaced `wr|ed` in DevTracker 3.5 |
| **"filtered"** | ❌ | Commented out |
| **No dedicated "features" window** | ❌ | Features are numbers, not visual |

**What the current overlay shows for each accepted ball:**
- Bounding box in **class color** (white=cue, red=solid, cyan=stripe, yellow=?)
- Text label above the box

**What you *can* recover for a demo:**
- **Per-ball feature values are in the console log**, one line each:
  ```
  frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE
  ```
- If Peter asks **"show me the wr/ed on screen"**: uncomment the DevTracker 3.1 `snprintf("%.2f|%.2f", wr, ed)` block in `main.cpp`. The code is still there, commented out.

---

## 4. Logs

### Per-ball line (written from `main.cpp`, not `features.cpp`)
```
frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE
```

**Breakdown:**
| Field | Meaning | Typical range |
|---|---|---|
| `frame=4251` | Frame number | — |
| `ball=1` | Index in this frame's `candidates` vector (0-indexed) | 0–14 |
| `wr=0.493827` | `white_ratio` | 0.00–0.72 observed |
| `ed=0.200274` | `edge_density` | 0.09–0.25 observed |
| `class=STRIPE` | Stage 5 output | CUE/SOLID/STRIPE/? |

### Empirical ranges (from DevTracker 3.4, 400+ frames)

| Feature | Min | Max | Distribution |
|---|---|---|---|
| `wr` | 0.00 | 0.72 | Bimodal: CUE at 0.62–0.72, SOLID at 0.00–0.10, STRIPE at 0.20–0.55 |
| `ed` | 0.09 | 0.25 | Overlapping — no clean split between classes |

**Interpretation of one log line:**
> `wr=0.493827 ed=0.200274` — this ball is 49.4% white pixels and 20.0% edge pixels. `wr > 0.15` and `wr < 0.60` → STRIPE. Confirmed by `class=STRIPE`.

### What you can prove from these numbers

**Proof 1 — separation is clean:**
- CUE: `wr` clusters at 0.62–0.72 (all > `RATIO_CUE=0.65` minus shadow, some at 0.62–0.65 → UNCERTAIN)
- SOLID: `wr < 0.10`
- STRIPE: `wr` between 0.20 and 0.55

**Proof 2 — `ed` is a tie-breaker, not a primary:**
- `ed` ranges overlap heavily (solids 0.10–0.22, stripes 0.13–0.25, cue 0.10–0.16).
- If `ed` were the primary metric, you couldn't separate classes.
- But as a **secondary check** (does a "solid-looking" ball have at least 0.10 edge density?), it works — because a totally flat dark ball (say, a black 8-ball with the numeral worn off) would have `ed < 0.10` and be a candidate for misclassification. `ed ≥ 0.10` confirms edges exist.

### Known "wr=0" cases — read the log like a pro

```
frame=4251 ball=0 wr=0 ed=0.121173 class=SOLID
```
- `wr=0` — **no white pixels at all** inside the bbox (dark solid ball or heavy shadow).
- `ed=0.12` — edges present (numeral, specular reflection).
- `class=SOLID` — correct.

If you *ever* see `wr=0 ed=0 class=SOLID` → suspicious. Could be a completely dark blob misclassified. Filter it mentally as "needs verification."

---

## 5. Skeletal + Parameters + Effects

### Skeletal — `computeWhiteRatio`
```cpp
float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox) {
    // 1. Inset by 2 px to avoid antialiased boundary pixels
    cv::Rect r(bbox.x + 2, bbox.y + 2, bbox.width - 4, bbox.height - 4);
    if (r.width < 4 || r.height < 4) return 0.0f;

    // 2. Clamp to image bounds (bbox may extend past frame edge)
    r &= cv::Rect(0, 0, hsv.cols, hsv.rows);
    if (r.width < 4 || r.height < 4) return 0.0f;

    // 3. White mask: low saturation, high brightness
    cv::Mat roi = hsv(r);
    cv::Mat white;
    cv::inRange(roi,
        cv::Scalar(0,   0,           WHITE_V_MIN),  // (H_min, S_min, V_min)
        cv::Scalar(179, WHITE_S_MAX, 255),          // (H_max, S_max, V_max)
        white);

    // 4. Ratio = white pixels / total pixels
    int cnt = cv::countNonZero(white);
    return (float)cnt / (float)(r.width * r.height);
}
```

### Skeletal — `computeEdgeDensity`
```cpp
void computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball) {
    // 1. Inset by 2 px
    cv::Rect r = ball.bbox;
    r.x += 2; r.y += 2; r.width -= 4; r.height -= 4;
    if (r.width < 4 || r.height < 4) return;

    // 2. Clamp to image bounds
    r &= cv::Rect(0, 0, blurred.cols, blurred.rows);
    if (r.width < 4 || r.height < 4) return;

    // 3. BGR → gray → Canny
    cv::Mat roi_bgr = blurred(r);
    cv::Mat gray, edges;
    cv::cvtColor(roi_bgr, gray, cv::COLOR_BGR2GRAY);
    cv::Canny(gray, edges, CANNY_LO, CANNY_HI);

    // 4. Ratio = edge pixels / total pixels
    ball.edge_density = cv::countNonZero(edges) / (float)edges.total();
}
```

### Parameter Table

| Param | Value | Location | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| **Bbox inset** | **2 px** | `features.cpp` (hardcoded) | More interior pixels ignored → safer from boundary artifacts, but wastes ~12% of bbox area for a 32-px ball | Less inset → ball edge (which is dark vs bright cloth) may leak into `white_ratio` or create false Canny edges at the border |
| `WHITE_S_MAX` | **40** | `config.h` | More saturated pixels counted as white → pink/light-blue balls miscounted as CUE | Fewer pixels counted as white → even slightly shadowed cue ball drops below `RATIO_CUE=0.65` |
| `WHITE_V_MIN` | **200** | `config.h` | Darker pixels included in "white" → shadowed cue ball still counted | Only very bright pixels → cue ball under shadow completely missed |
| `CANNY_LO` | **50** | `config.h` | More edges detected (weaker gradients count) → noisy `edge_density` | Fewer edges → real edges missed |
| `CANNY_HI` | **150** | `config.h` | Fewer edges (only strong gradients) | More edges |
| `CANNY_LO/HI ratio` | **1:3** | Standard | Canny's recommended ratio for hysteresis | — |

### Why these specific values?

**`WHITE_S_MAX=40, WHITE_V_MIN=200`:**
- **S** (saturation): white has low saturation by definition. S ≤ 40 excludes any colored pixel.
- **V** (value): white has high brightness. V ≥ 200 ensures dark pixels (shadow, table edge) aren't white.
- Together: **the mathematical definition of "white-ish"** — low color, high brightness.
- Tuned via DevTracker 3.1: shadowed cue ball `wr` drops to ~0.62 (was expected 0.80). This is why `RATIO_CUE` was lowered to 0.65 — not because `WHITE_S_MAX/V_MIN` are wrong, but because shadows reduce the pixel count that *is* white.

**`CANNY_LO=50, CANNY_HI=150`:**
- This 1:3 ratio is **Canny's own recommendation** (John Canny, 1986).
- Empirically: 50/150 catches ball numbers (thin dark strokes on bright bands) at 1280px resolution.
- Lower thresholds (30/90) → noise edges from H.264 compression. Higher (80/240) → misses thin numeral edges.

**2-px bbox inset:**
- **White ratio:** boundary pixels are antialiased ball-vs-cloth mixtures. A pixel 50% ball + 50% cloth would score as non-white even if the ball is cue. Inset skips them.
- **Edge density:** the bbox edge itself creates a hard rectangular gradient → Canny would detect it as 4 fake edges spanning the bbox perimeter. For a 32×32 bbox, that's 128 pixels of fake edges ≈ 12% spurious `edge_density`. Inset kills them.
- **Cost:** loses 4×2×32 − 16 = ~240 boundary pixels ≈ 23% of bbox area for a 32-px ball. But it prevents ~12% spurious edges. Trade-off favors the inset.

**Division by `(width × height)`, not by "non-black pixels":**
- We want to know the **fraction of white pixels**, not "white among visible pixels."
- If you divided by non-black pixels, a cue ball with a shadow half would show 100% white — because the shadow pixels are black and would be excluded from the denominator.
- By dividing by **total bbox area**, shadows correctly reduce `white_ratio` (cue ball with half shadow → `wr ≈ 0.5`).

**Clamp to image bounds:**
- Balls near frame edges have bboxes that extend past `[0, 0, cols, rows]`.
- `Rect & Rect` performs intersection — returns clipped rectangle.
- Without clamp: `hsv(r)` with out-of-bounds coords would throw or crash.
- DevTracker 3.2 log mentions "0-width bbox crash — clamping from Dev 3.2 works" — this was a **real crash fixed by clamping**.

### Why two features? (defend this)

| Feature | Purpose | Primary or tie-breaker |
|---|---|---|
| `white_ratio` | Discriminates CUE (high), STRIPE (medium), SOLID (low) | **Primary** |
| `edge_density` | Detects numeral presence + distinguishes dark solids from empty blobs | **Tie-breaker** |

**If you only had `white_ratio`:**
- Every dark solid (8-ball, 7-ball, 3-ball) would score `wr < 0.05` → all classified SOLID. ✓
- But an **empty ball-like blob** (e.g., a glare patch that passed segmentation) would also score `wr ≈ 0` → classified SOLID. ✗ False positive.
- `edge_density ≥ 0.10` proves the blob has internal structure (numeral or texture) → it's a real ball.

**If you only had `edge_density`:**
- CUE: `ed ≈ 0.13` (smooth sphere, few edges)
- SOLID red: `ed ≈ 0.15` (numeral + edges)
- STRIPE: `ed ≈ 0.20` (bands create many edges)
- Overlap is too heavy — cannot classify.

**Together:** `white_ratio` handles 95% of decisions; `edge_density` catches the last 5% (dark solid vs empty blob).

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 3 OUT                                                          │
│ std::vector<BallCandidate> candidates  (N balls)                     │
│   each: { bbox, center, area, white_ratio=0, edge_density=0 }        │
│                                                                      │
│ hsv      (HSV, 8UC3, 1280×H)  from Stage 2                           │
│ blurred  (BGR, 8UC3, 1280×H)  from Stage 2                           │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ main.cpp unified loop:                                               │
│                                                                      │
│   for (auto& ball : candidates) {                                    │
│       ball.white_ratio  = computeWhiteRatio(hsv, ball.bbox);         │
│       computeEdgeDensity(blurred, ball);                             │
│       ball.type = classifyBall(ball);                                │
│   }                                                                  │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
              ▼                                       ▼
┌─────────────────────────────┐         ┌──────────────────────────────┐
│ computeWhiteRatio(hsv,bbox) │         │ computeEdgeDensity(blurred,  │
│   [features.cpp]            │         │                    ball)     │
│                             │         │   [features.cpp]             │
│                             │         │                              │
│ 1. r = bbox inset by 2 px   │         │ 1. r = bbox inset by 2 px    │
│                             │         │                              │
│ 2. if w<4 or h<4 → return 0 │         │ 2. if w<4 or h<4 → return    │
│                             │         │                              │
│ 3. clamp to image bounds    │         │ 3. clamp to image bounds     │
│                             │         │                              │
│ 4. roi = hsv(r)             │         │ 4. roi_bgr = blurred(r)      │
│                             │         │                              │
│ 5. inRange(roi,             │         │ 5. cvtColor(BGR → GRAY)      │
│       (0,0,200),            │         │                              │
│       (179,40,255), white)  │         │ 6. Canny(gray, edges,        │
│     → white mask            │         │           50, 150)           │
│                             │         │     → edge mask              │
│ 6. count = countNonZero     │         │                              │
│     / (w·h)                 │         │ 7. count = countNonZero     │
│                             │         │     / edges.total()          │
│ 7. return float             │         │                              │
│                             │         │ 8. ball.edge_density = float │
│                             │         │                              │
└──────────────┬──────────────┘         └──────────────┬───────────────┘
               │                                       │
               ▼                                       ▼
       ball.white_ratio                       ball.edge_density
       [0.0 ... 1.0]                          [0.0 ... 1.0]
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ candidates (with BOTH features populated)                            │
│                                                                      │
│   each: { bbox, center, area,                                        │
│           white_ratio, edge_density,                                 │
│           type=UNCERTAIN }                                           │
│                                                                      │
│ Side effect: cout << "frame=.. ball=.. wr=.. ed=.. class=.."         │
│              (one line per ball per frame → console_out log)         │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
                       STAGE 5 (classify)
```

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why 2-px inset?"** | Two reasons. (1) **White ratio:** bbox boundary pixels are antialiased ball-vs-cloth mixtures — including them adds noise. (2) **Edge density:** the bbox rectangle itself creates a hard gradient; Canny detects the bbox edges as 4 fake lines around the perimeter. For a 32×32 bbox that's ~128 spurious edge pixels ≈ 12% inflated `edge_density`. Inset skips both. |
| **"Why is the inset hardcoded and not a `config.h` constant?"** | It's a **structural property of the bbox**, not a tunable. Every bbox from `cv::boundingRect` has the same antialiasing at its perimeter. Making it tunable invites misconfiguration. Contrast: `MIN_BALL_AREA` is tunable because the ball diameter varies by camera/resolution. |
| **"Why `S ≤ 40` and `V ≥ 200`?"** | The mathematical definition of "white": low saturation, high brightness. S=40 excludes any saturated color (red, blue, green balls). V=200 excludes darker pixels (shadow, numeral digits). Together they capture cue ball + stripe bands + cue-side edges. Tuned empirically — DevTracker 3.1 baseline. |
| **"Why not just use brightness (V) alone?"** | Brightness alone can't distinguish white from light-colored balls. A very bright yellow ball would have V ≈ 240 — high. But S ≈ 200 — highly saturated. White requires **both** low S **and** high V. |
| **"Why ratio over absolute pixel count?"** | Because balls are **similar size but not identical** (due to perspective). Absolute white pixel count would vary with ball size. Ratio normalizes — a cue ball at 32 px diameter and 30 px diameter both show `wr ≈ 0.65`, but absolute counts would differ by ~10%. |
| **"Why divide by total bbox area, not by non-shadow area?"** | Because a shadowed cue ball **should** score lower `wr`. Its actual white fraction is reduced by the shadow. If we excluded shadows from the denominator, a 50%-shadowed cue ball would score 100% white → `wr = 1.0` → indistinguishable from a full-white pixel-filled region. Shadows must dilute the ratio for honest measurement. |
| **"Why Canny (50, 150)?"** | Canny's own recommended 1:3 hysteresis ratio. 50 = low threshold (weak edges still followed if connected to strong edges). 150 = high threshold (only strong gradients start an edge). Tuned: lower (30/90) picks up H.264 blockiness noise, higher (80/240) misses thin numeral strokes. |
| **"Why Canny on BGR→GRAY, not on HSV?"** | Canny works on a single-channel image whose gradients have meaning. BGR→GRAY gives luminance (perceptual brightness), which is exactly the channel that shows numeral strokes and stripe band edges. HSV doesn't have a single "brightness-like" channel — H is circular (wraps at 179), S is saturation, V is brightness but Canny on V alone loses color boundaries. Grayscale is the standard Canny input. |
| **"What's the crash that DevTracker 3.2 fixed?"** | The `r &= cv::Rect(0, 0, cols, rows)` clamp. Without it, a bbox at (1270, 700, 40, 40) on a 1280×720 image extends past the frame boundary. `hsv(r)` or `blurred(r)` with out-of-bounds coordinates would either throw or return garbage. The clamp intersection shrinks the ROI to what's actually visible. |
| **"Why does `edge_density` sometimes read 0.09 (the minimum)?"** | Smooth, untextured balls — typically cue ball under direct light, or 8-ball face-on with worn numeral. Canny detects the ball outline (which is inside the 2-px inset) as edges, but no interior texture. `ed ≈ 0.09` still passes `EDGE_SOLID_MIN=0.10` marginally — if it dips below 0.10, that's why `EDGE_CUE_MAX=0.15` is a *ceiling* not a requirement. |
| **"Why does `edge_density` max out at 0.25, not 1.0?"** | Because even a maximally textured ball (say, the 15-ball with complex stripe) has at most ~25% of its bbox as Canny edge pixels. A `ed = 1.0` would mean every pixel is an edge — impossible for a 2D region (edges are 1-D structures, so 2-D regions have edges only at boundaries). Typical realistic upper bound: 0.20–0.25. |
| **"What if a ball is partially occluded?"** | The bbox is slightly smaller than a full ball's, but `wr` and `ed` are computed over the visible pixels only (via inset+clamp). A half-ball with the other half behind another ball would show only the visible half → `wr` and `ed` both shift → classification may flip to `?`. **This is why `ABSENCE_TOLERANCE=3` in Stage 7 exists** — brief misclassifications don't kill a rack. |
| **"What's the FPS cost of Stage 4?"** | ~5–8 ms per frame for 14 balls. Canny is O(W·H) per ball bbox: 32×32 × 14 ≈ 14,336 pixels — negligible. `inRange` similarly. Dominant cost is `cvtColor` (BGR→GRAY) per ball. Total pipeline ~30 FPS. |

---

## 8. Cross-stage dependencies (Peter's "what breaks if…" follow-ups)

| Change | Ripple |
|---|---|
| `WHITE_S_MAX` → 10 | Shadowed cue ball drops to `wr ≈ 0.4`. `RATIO_CUE=0.65` fails → CUE classified as STRIPE. Counts wrong. |
| `WHITE_V_MIN` → 180 | Darker shade pixels counted as white. Shadow on solid red might push `wr` to 0.20 → SOLID classified as STRIPE. |
| `CANNY_LO/HI` → 20/60 | H.264 blockiness noise → `ed` on every ball climbs to 0.30+ → tie-breaker useless. |
| `CANNY_LO/HI` → 100/300 | Thin numeral strokes missed → `ed` drops to 0.08 → dark solids get rejected by `EDGE_SOLID_MIN=0.10` → fall to `?` (UNCERTAIN). |
| Bbox inset → 0 px | Boundary artifacts leak: `edge_density` inflated by ~12% → the `EDGE_CUE_MAX=0.15` threshold for CUE would misfire. |
| Bbox inset → 4 px | Loses ~44% of ball area. `wr` on cue ball drops sharply. Misclassification. |
| Remove clamp | Crash on edge balls. `Rect(1270, 700, 40, 40)` → out-of-bounds → `hsv(r)` segfault. |
| Swap Canny for Sobel | Sobel produces edge magnitude, not binary edges. `countNonZero` would need thresholding → different parameter tuning → not worth it for consistency. |
| Return `count` instead of `count / area` | Ball size varies 800–1000 px² → absolute counts vary widely → thresholds would need per-frame tuning. Normalization is essential. |

---

**Stage 4 complete.** When ready, prompt `[stage5]` and I'll detail Classification — the if/else cascade whose thresholds (`RATIO_CUE=0.65`, `UNCERTAIN_WHITE_HI=0.60`, `RATIO_STRIPE_LO=0.15`) were empirically tuned from these exact log lines, plus the `UNCERTAIN` glare-band design that prevents false billing.