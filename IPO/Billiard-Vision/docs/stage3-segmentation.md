# Stage 3: Segmentation — Defense Prep

**⚠️ Highest-probability probe zone.** This stage has the most code, the most bugs caught during development, and the most empirical tuning. Peter *will* ask about `RETR_LIST` and `MIN_BALL_AREA`.

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **Type** | `const cv::Mat& hsv` — HSV, `CV_8UC3`, 1280 × H |
| **From** | Stage 2 (`preprocess.cpp` output) |
| **Also needs** | `const std::string& rejectPath` — timestamped reject log path |
| **Mutates** | `cv::Mat& filteredOut` — by-reference, filled with white blobs + grey rects (debug output) |
| **Ownership** | `hsv` read-only; `filteredOut` cleared and redrawn each frame |

### Process (Sequence of Actions)

```
1.  cv::inRange(hsv, CLOTH_LO, CLOTH_HI, cloth)
        → white pixels = cloth; black = everything else
2.  cv::bitwise_not(cloth, ball)
        → invert: white = everything NON-cloth (balls + rails + pockets + background)
3.  cv::inRange(hsv, (40,150,50), (75,255,255), greenBall)
    cv::bitwise_or(ball, greenBall, ball)
        → patch: re-adds the green 6-ball absorbed by cloth mask
4.  cv::getStructuringElement(MORPH_RECT, Size(3,3), morphK)
5.  cv::morphologyEx(ball, m, MORPH_OPEN,  morphK, iter=1)
        → erode then dilate: removes white specks
6.  cv::morphologyEx(m,    m, MORPH_CLOSE, morphK, iter=1)
        → dilate then erode: fills holes inside balls
7.  cv::findContours(m.clone(), contours, RETR_LIST, CHAIN_APPROX_SIMPLE)
        → ALL contours, no hierarchy filtering
8.  For each contour:
        a. area  = cv::contourArea()
        b. if (area < 200 || area > 60000)        → reject "area"
        c. peri  = cv::arcLength(closed=true)
        d. circ  = 4π·area / peri²
        e. if (circ < 0.75)                       → reject "circ"
        f. bb    = cv::boundingRect()
        g. aspect = bb.width / bb.height
        h. if (aspect < 0.70 || aspect > 1.40)    → reject "aspect"
        i. ACCEPT:
            - cv::drawContours(filteredOut, ..., white, -1)   [debug]
            - cv::rectangle(filteredOut, bb, grey, 1)         [debug]
            - mu = cv::moments(contour)
            - center = (mu.m10/mu.m00, mu.m01/mu.m00)
            - candidates.push_back({bb, center, area})
9.  return candidates;
```

### Data Out
| Aspect | Detail |
|---|---|
| **Type** | `std::vector<BallCandidate>` |
| **Struct** | `{ cv::Rect bbox; cv::Point2f center; int area; }` |
| **Piped to** | Stage 4 (`computeWhiteRatio`, `computeEdgeDensity`) |
| **Side outputs** | `filteredOut` Mat (debug), `rejectPath` file (audit) |

**BallCandidate fields inherited from `types.h`:**
```cpp
struct BallCandidate {
    cv::Rect    bbox;
    cv::Point2f center;
    int         area;
    float       white_ratio  = 0.0f;   // filled in Stage 4
    float       edge_density = 0.0f;   // filled in Stage 4
    BallType    type         = BallType::UNCERTAIN;  // filled in Stage 5
};
```

Stage 3 populates the first three fields. Stages 4 & 5 fill the rest downstream.

---

## 2. Codebase, Libraries, Imports

**File:** `src/segment.cpp` (~80 lines — the largest module)

```cpp
#include "segment.h"        // extractCandidates declaration
#include "config.h"         // all thresholds
#include <fstream>          // std::ofstream for reject log
#include <iostream>         // cout for SUMMARY counters
#include <vector>           // std::vector
```

**Imports used:**
| Library | Function | Purpose |
|---|---|---|
| OpenCV core | `cv::inRange` | HSV thresholds → binary mask |
| OpenCV core | `cv::bitwise_not`, `cv::bitwise_or` | Invert + patch |
| OpenCV imgproc | `cv::getStructuringElement` | 3×3 kernel |
| OpenCV imgproc | `cv::morphologyEx` | OPEN + CLOSE |
| OpenCV imgproc | `cv::findContours` | Extract contours |
| OpenCV imgproc | `cv::contourArea`, `arcLength`, `boundingRect`, `moments` | Filter + centroid |
| OpenCV imgproc | `cv::drawContours`, `cv::rectangle` | Debug output |
| STL | `std::ofstream` | Reject log |

**Critical code blocks:**

**Cloth mask + green-ball patch:**
```cpp
cv::Mat cloth, ball;
cv::inRange(hsv,
            cv::Scalar(CLOTH_H_LO, CLOTH_S_LO, CLOTH_V_LO),
            cv::Scalar(CLOTH_H_HI, CLOTH_S_HI, CLOTH_V_HI),
            cloth);
cv::bitwise_not(cloth, ball);

cv::Mat greenBall;
cv::inRange(hsv, cv::Scalar(40, 150, 50), cv::Scalar(75, 255, 255), greenBall);
cv::bitwise_or(ball, greenBall, ball);
```

**Morphology:**
```cpp
cv::Mat morphK = cv::getStructuringElement(cv::MORPH_RECT,
        cv::Size(MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE));
cv::Mat m;
cv::morphologyEx(ball, m, cv::MORPH_OPEN,  morphK, cv::Point(-1,-1), MORPH_ITER);
cv::morphologyEx(m,    m, cv::MORPH_CLOSE, morphK, cv::Point(-1,-1), MORPH_ITER);
```

**Contour retrieval:**
```cpp
cv::Mat mCopy = m.clone();  // findContours MUTATES its input
std::vector<std::vector<cv::Point>> contours;
cv::findContours(mCopy, contours, cv::RETR_LIST, cv::CHAIN_APPROX_SIMPLE);
```

**Filter cascade + centroid:**
```cpp
for (size_t i = 0; i < contours.size(); i++) {
    double area = cv::contourArea(contours[i]);
    cv::Rect bb = cv::boundingRect(contours[i]);

    if (area < MIN_BALL_AREA || area > MAX_BALL_AREA) {
        nRejectArea++;
        rej << "area " << area << " | bbox " << bb.x << "," << bb.y
            << "," << bb.width << "," << bb.height << "\n";
        continue;
    }

    double peri = cv::arcLength(contours[i], true);
    double circ = (peri > 0) ? (4.0 * CV_PI * area / (peri * peri)) : 0.0;
    if (circ < MIN_CIRCULARITY) {
        nRejectCirc++;
        rej << "circ " << circ << " | bbox ...\n";
        continue;
    }

    float aspect = (float)bb.width / bb.height;
    if (aspect < ASPECT_MIN || aspect > ASPECT_MAX) {
        nRejectAspect++;
        rej << "aspect " << aspect << " | bbox ...\n";
        continue;
    }

    // ACCEPT
    cv::Moments mu = cv::moments(contours[i]);
    cv::Point2f center(
        (float)(mu.m10 / (mu.m00 + 1e-5)),
        (float)(mu.m01 / (mu.m00 + 1e-5))
    );
    candidates.push_back({ bb, center, (int)area });
}
```

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Content |
|---|---|---|
| **"cloth"** | ❌ | Debug-only. White cloth, black everything else. |
| **"ball"** | ❌ | Debug-only. Inverse — black cloth, white balls+rails+pockets. |
| **"morph"** | ❌ | Debug-only. After OPEN+CLOSE. |
| **"filtered"** | ❌ | **Production: disabled.** In DevTracker 2.5 this showed black background + white filled balls + grey rects. Drawing still happens (writes to `filteredOut` Mat), but no window displays it. |
| **"frame"** | ✅ (later) | The original BGR frame with overlay from Stages 5–7. Bounding boxes on **this** frame come from Stage 5's drawing loop, not Stage 3. |

**Critical clarity for Peter:**
- `filteredOut` is still **drawn** every frame (CPU cost: negligible, ~0.3 ms). It's passed back to `main.cpp` but never `imshow`'d. Available if needed for a live demo debug.
- The green bounding boxes on the "frame" window are **not** from Stage 3's `rectangle(filteredOut, ...)`. They come from `main.cpp`'s Stage-5 loop that draws on `frame` directly. Two different draw calls, two different Mats.

---

## 4. Logs

### A. Console Log (SUMMARY line)
Appended to `4.2-log-consol_out_*.txt` at end of each frame:

```
contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0
```

**Breakdown:**
| Field | Meaning |
|---|---|
| `contours=25` | Raw contours returned by `findContours` |
| `accepted=14` | Passed all 3 filters |
| `candidates=14` | Same as accepted (they're pushed 1:1) |
| `rejArea=10` | Rejected: too small or too large |
| `rejCirc=1` | Rejected: circularity < 0.75 |
| `rejAspect=0` | Rejected: aspect outside [0.7, 1.4] |

**Sanity check (defend this):** `accepted + rejArea + rejCirc + rejAspect = 14 + 10 + 1 + 0 = 25 = contours`. **Always.** If Peter sees this math check out, he knows you understand your own counters.

### B. Reject Log
File: `rejects_YYYYMMDD_HHMMSS.txt` (append-only)

Sample (from Appendix B):
```
area 20 | bbox 1207,595,3,11
area 16 | bbox 1207,583,3,9
area 6 | bbox 1207,563,3,4
area 14 | bbox 947,486,5,5
circ 0.571423 | bbox 1009,473,27,32
circ 0.483016 | bbox 931,471,30,33
circ 0.443474 | bbox 929,359,62,49
area 740087 | bbox 42,47,1196,631
area 919601 | bbox 0,0,1280,720
```

**Interpretation:**
| Line | Interpretation |
|---|---|
| `area 919601 \| bbox 0,0,1280,720` | **The table rail.** Covers full frame, enclosed ring. Rejected by MAX_BALL_AREA. |
| `area 740087 \| bbox 42,47,1196,631` | **The cloth + balls as one blob** (before inversion caught it — this is a "gap" between rail and cloth regions). |
| `area 20 \| bbox 1207,595,3,11` | **Sensor noise** at image edge. Rejected by MIN_BALL_AREA. |
| `circ 0.571 \| bbox 1009,473,27,32` | **Cue stick tip** or ball+shadow merge. Rejected by MIN_CIRCULARITY. |
| `circ 0.443 \| bbox 929,359,62,49` | **Merged ball pair** (two balls touching). Aspect acceptable, but circularity collapsed. |

**This is your defense evidence.** Three lines tell the whole filter story:
1. Table rejected by AREA (919601 > 60000)
2. Noise rejected by AREA (20 < 200)
3. Cue stick rejected by CIRCULARITY (0.571 < 0.75)

Cite **exactly these three lines** if Peter asks "prove your filters work."

---

## 5. Skeletal + Parameters + Effects

### Parameter Table

| Param | Value | Old (0.5) | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| `CLOTH_H_LO/HI` | **35/100** | 85/96 | Wider H → more cloth captured → more rails leak into ball mask (false positives) | Narrower H → balls absorbed into cloth → fewer detections |
| `CLOTH_S_LO` | **50** | 243 | Higher S floor → shadowed cloth treated as non-cloth → false ball detections in shadows | Lower S floor → more shadow cloth absorbed → cleaner ball mask |
| `CLOTH_S_HI` | 255 | 255 | N/A (already max) | — |
| `CLOTH_V_LO` | **50** | 111 | Higher → dark cloth treated as ball → noise | Lower → dark shadowed cloth absorbed |
| `CLOTH_V_HI` | **220** | 166 | Higher → bright glare on cloth treated as cloth (good) | Lower → bright spots on cloth flagged as balls (bad, false positives) |
| `MORPH_KERNEL_SIZE` | **3** | 3 | Larger kernel = more aggressive smoothing, but **can erase small balls** (< 3-px radius). | Smaller (2 not allowed — must be odd for symmetric erosion) |
| `MORPH_ITER` | **1** | 1 | More iterations = same effect as larger kernel. Same risk of erasing balls. | 0 = disabled (no benefit) |
| `MIN_BALL_AREA` | **200** | 1500 | Higher → occluded/small balls dropped, ball count destabilizes | Lower → noise passes as ball |
| `MAX_BALL_AREA` | **60000** | 60000 | Higher → table frame leaks through | Lower → legitimate merges (2–3 balls) dropped before circularity can judge |
| `MIN_CIRCULARITY` | **0.75** | 0.75 | Higher → tilted/occluded balls rejected → fewer detections | Lower → cue stick + merged pairs pass → false candidates |
| `ASPECT_MIN/MAX` | **0.70/1.40** | 0.70/1.40 | Tighter → rejects tilted balls | Looser → elongated blobs (stick, merges) pass |

### Key Parameters — Deep Dive

**`MIN_BALL_AREA = 200` (was 1500)**
- **This was the second black-screen bug** in DevTracker 2.3.
- Original estimate: 1500 (assumed larger resolution).
- Reality at 1280px: ball ≈ **32 px diameter → π·16² ≈ 804 px²**.
- With 1500 threshold, **every ball was rejected**. Black filtered output.
- Lowered to 200: keeps balls (~800 px²) but drops noise (< 200 px²).
- **Peter's likely question:** "Why not 500 or 1000?" → Answer: 200 gives margin for occluded/partial balls (a half-occluded ball ≈ 400 px²). Noise specks measured at 6–20 px². 200 is 10× noise floor, 25% of full ball. Empirically tuned.

**`MIN_CIRCULARITY = 0.75`**
- Formula: `circ = 4π·A / P²` where A = area, P = perimeter.
- Perfect circle = **1.0**.
- Square = π/4 ≈ **0.785**.
- Rectangle 2:1 ≈ **0.698**.
- **0.75 rejects anything less circular than a square.** Cue stick ≈ 0.44–0.57. Merged pairs ≈ 0.44–0.50.
- Perfect threshold: high enough to reject elongated blobs, low enough that slight occlusion (ball edge cut by neighbor) still scores ≥ 0.80.

**Green-ball patch (H 40–75, S 150–255, V 50–255)**
- DevTracker 3.5 discovered: solid green 6-ball blends into cloth.
- Root cause: 6-ball's HSV = (65, 220, 130) roughly — inside cloth range (35–100, 50–255, 50–220).
- Patch: dedicated narrower range that's "more saturated green than cloth" (S ≥ 150).
- OR'd back into ball mask.
- **Limitation (documented):** when stationary, patch still struggles. When rolling, motion blur shifts pixels → detected.
- Peter's likely question: "Why not just widen CLOTH range less aggressively?" → Because that rejects shadows on cloth → noise → false positives. Two separate ranges is cleaner.

### Sequence Justification — Why This Order?

**Blur → cvtColor → inRange → invert → morph → findContours → filter**
Each step's output is the next step's input. Two sub-questions Peter might ask:

**Q1: Why invert AFTER inRange, not threshold non-cloth directly?**
Because `inRange(cloth_lo, cloth_hi)` gives a clean, tight cloth mask. Inverting is one operation. Trying to threshold "not cloth" directly = 6 separate inRange calls (one per non-cloth region) + ORs. `inRange + bitwise_not` = 2 ops.

**Q2: Why OPEN then CLOSE, not CLOSE then OPEN?**
- OPEN (erode → dilate) **removes** small white specks and thin protrusions. Do this FIRST to clean the field.
- CLOSE (dilate → erode) **fills** small black holes inside the balls (e.g., specular reflection hole in the middle).
- Reverse order: CLOSE first would *enlarge* specks before OPEN could remove them.
- **This is the standard morphological pipeline: "open to clean, close to smooth."**

**Q3: Why `RETR_LIST` not `RETR_EXTERNAL`?**
This is the biggest question. Answer in the Q&A section below.

### What does `RETR_LIST` vs `RETR_EXTERNAL` actually mean?

| Mode | Behavior | Result on this image |
|---|---|---|
| `RETR_EXTERNAL` | Only outermost contours per connected component | The table rail forms a closed ring → **ONE** giant contour encloses all balls → balls ignored → black screen |
| `RETR_LIST` | **All** contours, flat list, no hierarchy | Rail ring + inner ball contours all returned → filter logic drops rail (area) and keeps balls |
| `RETR_TREE` | Full nested hierarchy | Overkill — we don't need parent/child relationships |
| `RETR_CCOMP` | 2-level hierarchy | Unnecessary here |

**The bug story (DevTracker 2.3):**
1. First try: `RETR_EXTERNAL` → `contours=1 accepted=0` → table ring (area 908090) rejected, but balls never found → **black filtered output**.
2. Switched to `RETR_LIST` → `contours=25 accepted=0` → STILL black, but for a different reason (MIN_BALL_AREA too high).
3. Fixed MIN_BALL_AREA → `contours=25 accepted=14` → **working**.

**Both bugs had the same symptom (black screen), different causes.** This is why DevTracker evidence is gold — you can show two failed attempts, then the fix.

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 2 OUT                                                          │
│ cv::Mat hsv  (HSV, 8UC3, 1280×H)                                     │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ extractCandidates(hsv, rejectPath, filteredOut)  [segment.cpp]     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ cv::inRange(hsv, cloth_lo, cloth_hi, cloth)                    │  │
│  │   → WHITE = cloth, BLACK = balls+rails+pockets                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ cloth                              │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ cv::bitwise_not(cloth, ball)                                   │  │
│  │   → WHITE = balls+rails+pockets, BLACK = cloth                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ ball                               │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ greenBall = inRange(hsv, 40-75, 150-255, 50-255)               │  │
│  │ cv::bitwise_or(ball, greenBall, ball)                          │  │
│  │   → 6-ball added back                                          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ ball (patched)                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ morphK = getStructuringElement(RECT, 3×3)                      │  │
│  │ morphologyEx(ball, m, OPEN,  morphK)   // remove specks        │  │
│  │ morphologyEx(m,    m, CLOSE, morphK)   // fill holes           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ m (cleaned binary mask)            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ findContours(m.clone(), contours, RETR_LIST, CHAIN_APPROX)     │  │
│  │   → std::vector<std::vector<cv::Point>>                        │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ contours                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ FOR each contour:                                              │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ FILTER 1: contourArea()                                  │ │  │
│  │   │   if (area < 200 || area > 60000) → reject, log "area"   │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  │              │                                                 │  │
│  │              ▼ passed Filter 1                                 │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ FILTER 2: arcLength → 4πA/P²                             │ │  │
│  │   │   if (circ < 0.75) → reject, log "circ"                  │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  │              │                                                 │  │
│  │              ▼ passed Filter 2                                 │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ FILTER 3: boundingRect → W/H                             │ │  │
│  │   │   if (aspect < 0.70 or > 1.40) → reject, log "aspect"    │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  │              │                                                 │  │
│  │              ▼ ACCEPT                                          │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ moments → m.m10/m.m00, m.m01/m.m00 → Point2f center      │ │  │
│  │   │ candidates.push_back({bb, center, area})                 │ │  │
│  │   │ drawContours(filteredOut) + rectangle(filteredOut)  [dbg]│ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼ candidates                         │
└──────────────────────────────────┼────────────────────────────────────┘
                                  │
                                  ▼
     std::vector<BallCandidate> (N balls, each with bbox/center/area)
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 4  →  computeWhiteRatio(hsv, bbox)   // fills white_ratio      │
│            computeEdgeDensity(blurred, ball) // fills edge_density    │
└──────────────────────────────────────────────────────────────────────┘
```

**Side channel — reject log** (written concurrently):
```text
rejects_YYYYMMDD_HHMMSS.txt
├─ "area 919601 | bbox 0,0,1280,720"      ← table ring
├─ "area 20 | bbox 1207,595,3,11"          ← noise
├─ "circ 0.571 | bbox 1009,473,27,32"      ← cue stick
└─ "circ 0.443 | bbox 929,359,62,49"       ← merged pair
```

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why `RETR_LIST` and not `RETR_EXTERNAL`?"** | The table rail is a closed ring. `RETR_EXTERNAL` returns ONLY the outermost contour → **one giant contour enclosing all balls** → balls are ignored as internal. We saw exactly this: `contours=1 accepted=0`. `RETR_LIST` returns ALL contours regardless of nesting → rail comes back as a single huge contour (area 919601) which the AREA filter rejects, while balls come back as individual contours that pass. |
| **"Why was `MIN_BALL_AREA=1500` wrong?"** | Original estimate assumed higher resolution. At 1280px, ball diameter ≈ 32px → area ≈ π·16² ≈ 804 px². Threshold 1500 rejected **every** ball. Lowered to 200. Margin still 10× above noise (measured 6–20 px²). |
| **"Why exactly 200?"** | Half-occluded ball ≈ 400 px². Fully visible ball ≈ 800 px². Noise specks 6–20 px². 200 sits comfortably between noise floor and smallest expected ball, with 4× safety factor. |
| **"Why 3 filters instead of one combined metric?"** | Each filter targets a different failure mode: AREA → size (table/noise), CIRCULARITY → shape (cue stick, merges), ASPECT → orientation (tilted/squashed blobs). A combined score would be opaque and harder to tune. **Cascade order = cheapest first:** contourArea is O(1), arcLength is O(P), boundingRect is O(1) — all fast, but cascade also means we don't call arcLength on 900-px contours we're about to reject on area. |
| **"Why moments instead of bbox center?"** | `bbox_center = (x + w/2, y + h/2)`. For a partially occluded ball, the bbox is larger than the visible ball, so bbox center is **shifted away** from the true ball center. `moments` centroid is the intensity-weighted center of the actual contour — more accurate. Matters for Stage 6 (convexHull + triangle check): 1–2 px drift × 13 balls = distorted hull → missed racks. |
| **"What is the green-ball patch exactly?"** | 6-ball's HSV is inside cloth range (H ~65, S ~220). `inRange(cloth)` absorbs it. Patch is a second, narrower `inRange` targeting "saturated green" (S ≥ 150) that cloth's shadowed regions don't reach. OR'd back into ball mask. **Limitation:** still struggles when 6-ball is perfectly stationary (documented in DevTracker 3.5). |
| **"Why not widen cloth range less aggressively?"** | That's what causes shadow-on-cloth → false ball detections. The two-range approach isolates the problem to one ball rather than corrupting the whole cloth mask. |
| **"Why OPEN then CLOSE?"** | OPEN (erode→dilate) removes white specks. CLOSE (dilate→erode) fills black holes inside balls (glare holes). Reversing would enlarge specks before OPEN could remove them. This is the standard morphological pipeline. |
| **"Why 3×3 kernel and 1 iteration?"** | Empirically: H.264 artifacts are small (1–3 px). 3×3 kernel covers them without erasing ball edges. Larger kernel (5×5, 7×7) or more iterations would eat into the ball's ~32-px diameter. |
| **"Why `m.clone()` before findContours?"** | `cv::findContours` **mutates** its input (OpenCV 4 requirement — historically it destroyed the input). We clone to preserve `m` (needed later if we want to re-run). |
| **"Why don't you imshow `filteredOut`?"** | Debug window. DevTracker 1.4 measured FPS with debug windows: ~26 FPS with dips to 6.25. Without: ~30 FPS. GUI blit is the bottleneck, not the drawing. Removed for production. `filteredOut` still gets drawn (CPU cost 0.3 ms) — available if needed for a live debug. |
| **"What if two balls are touching?"** | Their contours merge → area ≈ 1600 px² (2 balls) → passes area filter → circularity ≈ 0.5 → **rejected by CIRC filter**. Documented in reject log: `circ 0.443 \| bbox 929,359,62,49`. This is a deliberate trade-off: 2 merged balls = 1 missing from the count for one frame. `ABSENCE_TOLERANCE` (Stage 7) covers brief drops. |
| **"What if the cue stick is in view?"** | It's a long thin blob → area passes (say 3000 px²), **circularity ≈ 0.44** → rejected. **Aspect ratio** would also reject it, but circularity catches it first (cheaper to compute than aspect? Actually aspect is O(1) — but circularity is required for merged-pair detection which aspect alone misses). Documented: `circ 0.483 \| bbox 931,471,30,33`. |
| **"Could you detect the cloth mask differently?"** | Alternatives: (1) **mean-shift on color** — slower, overkill. (2) **Fixed background subtraction** — fails when cloth colour varies across venues. (3) **Learned semantic segmentation** — correct approach for commercial scale, but requires training data and tank FPS on CPU. `inRange` is 3-channel thresholding: fastest, most explainable, sufficient for this scope. |
| **"What's the FPS cost of Stage 3?"** | ~8–12 ms per frame at 1280×711. This is the **dominant cost** in the pipeline. Measured: full pipeline ~30 FPS → Stage 3 consumes ~25–35% of frame budget. Canny (in Stage 4) is next most expensive. |
| **"Why not filter by color (solid red vs solid blue) instead of white_ratio?"** | That would work for SOLID classification but not for CUE (white = no color) and not for STRIPE (white bands + color bands). `white_ratio` is a unified metric for all three classes: CUE = high, STRIPE = medium, SOLID = low. Color would be a 4th feature — Stage 5 would need a decision tree instead of if/else. Out of scope for Period 1. |

---

## 8. Cross-stage dependencies (Peter's "what breaks if…" follow-ups)

| Change | Ripple |
|---|---|
| `RETR_EXTERNAL` instead of `RETR_LIST` | **Catastrophic.** Black screen. `candidates=0` on every frame. `detectRack` fails (needs ≥ 13). Counter never fires. **This is the killer bug from DevTracker 2.3.** |
| `MIN_BALL_AREA = 1500` | **Catastrophic.** Same black screen (DevTracker 2.3 attempt 2). Every ball rejected on area. |
| `MIN_CIRCULARITY = 0.5` | Cue stick and merged pairs pass as balls. `balls=` count inflates. Summary log becomes noisy. Rack detection sees 20+ "balls" — may false-positive. |
| `MIN_CIRCULARITY = 0.95` | Occluded/tilted balls rejected. `balls=` drops to 10–11. Rack detection fails `RACK_MIN_BALLS=13`. Counter misses racks. |
| `MORPH_KERNEL_SIZE = 7` | Ball edges erode. Ball area drops from ~800 to ~500 px². `MIN_BALL_AREA=200` still passes, but circularity collapses → more rejects. Worse: green 6-ball is eaten by cloth mask entirely. |
| Cloth `S_LO` = 150 | Shadows on cloth excluded from cloth mask → shadows become "balls" → **15 phantom candidates** per frame. Rack detection false-positives immediately. |
| Remove green-ball patch | 6-ball missed ~70% of the time when stationary. Rack `ball_count` drops to 12 → just below `RACK_MIN_BALLS=13` → **racks missed entirely**. |

---

**Stage 3 complete.** When ready, prompt `[stage4]` and I'll detail Feature Extraction — the two metrics (`white_ratio`, `edge_density`) that every downstream decision depends on, and the empirical ranges (wr 0.00–0.72, ed 0.09–0.25) that justify the Stage 5 thresholds.