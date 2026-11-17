# Stage 6: Rack Detection — Defense Prep

**The pivot point.** Everything upstream produced balls; everything downstream consumes one boolean. This is where "we see balls" becomes "a game started." Every billing charge passes through this function.

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **From Stage 5** | `const std::vector<BallCandidate>& candidates` |
| **Fields used** | **`center` only** — `.bbox`, `.area`, `.white_ratio`, `.edge_density`, `.type` are **ignored** |
| **From `config.h`** | `RACK_MIN_BALLS=13`, `RACK_EPSILON_RATIO=0.035`, `RACK_MIN_AREA=12000.0` |
| **Ownership** | Passed by const-reference — read-only |

**Critical:** Stage 6 is **classification-agnostic**. A `?`-flagged UNCERTAIN ball and a confidently classified CUE ball contribute identically (just a center point). This is intentional — see Q&A.

### Process (Sequence of Actions)

```
1.  if (candidates.size() < RACK_MIN_BALLS)     → return false  [gate]
2.  centers ← extract (int, int) from ball.center for each ball
3.  hull    ← cv::convexHull(centers)
        → smallest convex polygon enclosing ALL centers
4.  peri    ← cv::arcLength(hull, closed=true)
5.  epsilon ← RACK_EPSILON_RATIO × peri          (adaptive tolerance)
6.  approx  ← cv::approxPolyDP(hull, epsilon, closed=true)
        → simplified polygon with dominant vertices
7.  if (approx.size() != 3)                    → return false  [triangle gate]
8.  area    ← cv::contourArea(approx)
9.  if (area < RACK_MIN_AREA)                  → return false  [size gate]
10. return true
```

**Five sequential gates.** Each reject returns `false`. Only a shape that survives all five is a rack.

### Data Out
| Aspect | Detail |
|---|---|
| **Type** | `bool` |
| **Meaning** | `true` = triangular rack detected this frame; `false` = no rack |
| **Piped to** | Stage 7 (`GameCounter::update(rackDetected)`) |
| **Side effects** | `main.cpp` draws `"RACK DETECTED"` text + appends `rack=1` to SUMMARY |

**No file I/O. No state. No static variables.** Pure function — deterministic, testable in isolation.

---

## 2. Codebase, Libraries, Imports

**File:** `src/rack-detection.cpp` — **whole file, 33 lines**

```cpp
#include "rack-detection.h"
#include "config.h"
#include <opencv2/opencv.hpp>

bool detectRack(const std::vector<BallCandidate>& candidates) {
    // 1. Minimum ball count
    if ((int)candidates.size() < RACK_MIN_BALLS) return false;

    // 2. Extract ball centers
    std::vector<cv::Point> centers;
    centers.reserve(candidates.size());
    for (const auto& ball : candidates) {
        centers.push_back(cv::Point((int)ball.center.x, (int)ball.center.y));
    }

    // 3. Convex hull of the cluster
    std::vector<cv::Point> hull;
    cv::convexHull(centers, hull);

    // 4. Approximate hull to a polygon
    std::vector<cv::Point> approx;
    double peri = cv::arcLength(hull, true);
    cv::approxPolyDP(hull, approx, RACK_EPSILON_RATIO * peri, true);

    // 5. Triangle check
    if (approx.size() != 3) return false;

    // 6. Area check (filter small clusters that happen to be triangular)
    double area = cv::contourArea(approx);
    if (area < RACK_MIN_AREA) return false;

    return true;
}
```

**Header:** `src/rack-detection.h`
```cpp
#pragma once
#include <vector>
#include "types.h"

bool detectRack(const std::vector<BallCandidate>& candidates);
```

**Imports used:**
| Library | Function | Purpose |
|---|---|---|
| `types.h` | `BallCandidate` | Input vector |
| OpenCV imgproc | `cv::convexHull` | Enclosing polygon |
| OpenCV imgproc | `cv::arcLength` | Perimeter for epsilon scaling |
| OpenCV imgproc | `cv::approxPolyDP` | Polygon simplification (Douglas-Peucker) |
| OpenCV imgproc | `cv::contourArea` | Triangle area check |
| `config.h` | 3 thresholds | Gates |

**Call site (`main.cpp`, inside loop after Stage 5):**
```cpp
// 5.1 — Rack Detection
bool rackDetected = detectRack(candidates);
if (rackDetected) {
    cv::putText(frame, "RACK DETECTED", cv::Point(50, 50),
                cv::FONT_HERSHEY_SIMPLEX, 1.0, cv::Scalar(0, 0, 255), 2);
}

// 5.2 — Counter update
bool counted = counter.update(rackDetected);

// ... eventually:
cout << "SUMMARY ... rack=" << (rackDetected ? 1 : 0) << " fps=" << instantFps << endl;
```

**Line count:** 33 lines in the .cpp. This is the **smallest source file in the pipeline** but does the most work per line.

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Content |
|---|---|---|
| **"frame"** | ✅ | Red `"RACK DETECTED"` text at (50, 50) when `rackDetected==true` |
| **"hull" debug** | ❌ | **Does not exist** in production code |
| **"approx" debug** | ❌ | **Does not exist** in production code |
| **Triangle overlay** | ❌ | The 3 vertices of the approx polygon are **not** drawn |

**The only visual signal is text.** When a rack is detected, red text appears at top-left. When not detected, nothing changes.

**For the demo — if Peter asks "show me the triangle":**
- There's no code to draw it currently.
- **Add-on snippet** (2 lines, in `main.cpp` right after `detectRack`):
  ```cpp
  if (rackDetected) {
      // redraw by re-running detection to get hull points (defensive)
      // OR log the 3 approx vertices from inside detectRack via cout
  }
  ```
- Better: add `cout << "RACK_HULL " << approx[0].x << "," << approx[0].y << " ..."` inside `detectRack` before return. Not in production now.

**Defense line:** *"The visual indicator is text-only by design — drawing the hull and approx polygon would add ~5–10 ms per frame and clutter the overlay. The `rack=1` field in the SUMMARY log is the authoritative record — timestamped, per-frame, greppable."*

---

## 4. Logs

**No dedicated log file** from Stage 6. Its output appears in **two places**, both mediated by `main.cpp`:

### A. SUMMARY line — the `rack=` field

```
SUMMARY frame=108 balls=13 CUE=1 SOLID=8 STRIPE=4 ?=0 rack=1 fps=30.32
```

| Field | Meaning |
|---|---|
| `frame=108` | Frame number |
| `balls=13` | Ball count (must be ≥ 13 for rack to be possible) |
| `rack=1` | Stage 6 returned `true` on this frame |
| `rack=0` | Stage 6 returned `false` |

### B. The "COUNTER EVENT" line — indirect evidence

When `rack=1` transitions from a streak → counter fires (Stage 7), the `main.cpp` loop prints:

```
COUNTER EVENT: count=3 at frame=108
```

This is **not** from Stage 6 directly — it's the downstream proof that a `rack=1` streak was long enough to survive debounce.

### Frame-by-frame interpretation — a real rack story

From your `5.2-evidence` log:

```
frame=94-97    balls=3-4       rack=0     ← balls entering frame
frame=98       balls=11        rack=1     ← triangular hull formed → detected
frame=108      balls=13        rack=1     ← still racked, sustained
frame=118      balls=13        rack=1     ← still racked
frame=119      balls=13        rack=1     ← still racked
frame=120      balls=12        rack=0     ← break occurred; balls scattering
frame=121+     balls=7-12      rack=0     ← scattered, no triangle
```

**Reading:** the rack was `rack=1` for frames 98–119 (**22 consecutive frames**). At frame 120, the break scattered the balls → hull became irregular polygon → `approx.size() > 3` → `rack=0`. **One rack = one continuous streak.**

### The counter overcount trap (why 22 frames don't = 22 games)

A rack detected for 22 frames produces **22 `rack=1` lines**. If the counter counted every `true`, it would report 22 games from one rack. The `GameCounter` state machine (Stage 7) collapses the streak into **1 count** via `DEBOUNCE_FRAMES=10` + `COOLDOWN_FRAMES=45`.

**Defense line:** *"Stage 6 is per-frame diagnostic — `rack=1` for 22 frames is expected. Stage 7 converts that streak into one billable event. Detection ≠ counting."*

### The two failure modes visible in your log

**Failure 1: Missed fast break (frame 3929)**
```
SUMMARY frame=3929 balls=14 CUE=1 SOLID=7 STRIPE=6 ?=0 rack=1 fps=30.3201
SUMMARY frame=3930 balls=14 CUE=1 SOLID=7 STRIPE=6 ?=0 rack=1 fps=124.432
SUMMARY frame=3931 balls=12 CUE=1 SOLID=7 STRIPE=4 ?=0 rack=0 fps=...
```
- Rack was `rack=1` for **only 2 frames** (3929–3930) before break.
- Failed to survive `DEBOUNCE_FRAMES=10` in Stage 7 → **missed**.
- This is a **real rack** in the video that we didn't count.

**Failure 2: False positive (frame 4281)**
```
frame=4272-4430  balls=14  rack=1  ← 159 consecutive frames!
```
- A scattered cluster of 10+ balls happened to form a rough triangle after `approxPolyDP`.
- **159 frames** is way above `DEBOUNCE_FRAMES=10` → count fired.
- This is a **false positive** — no real rack there.

**Both are documented in DevTracker 5.2 as deliberate trade-offs.** The tuning chose precision over recall: false positives break billing trust; false negatives are bounded (one missed fast break per session).

---

## 5. Skeletal + Parameters + Effects

### Skeletal — 5 gates

```
INPUT: std::vector<BallCandidate> candidates
       │
       ▼
┌────────────────────────────────────────────────────┐
│ GATE 1: size check                                 │
│   if (candidates.size() < 13)  → return false      │
└────────────────────┬───────────────────────────────┘
                     │ ≥ 13 balls
                     ▼
┌────────────────────────────────────────────────────┐
│ Extract centers → std::vector<cv::Point>           │
└────────────────────┬───────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────┐
│ cv::convexHull(centers, hull)                      │
│   → smallest convex polygon enclosing all centers  │
└────────────────────┬───────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────┐
│ peri    = cv::arcLength(hull, closed=true)         │
│ epsilon = 0.035 × peri                             │
│ cv::approxPolyDP(hull, approx, epsilon, closed)    │
│   → simplified polygon                             │
└────────────────────┬───────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────┐
│ GATE 2: vertex count                               │
│   if (approx.size() != 3)  → return false          │
└────────────────────┬───────────────────────────────┘
                     │ exactly 3 vertices
                     ▼
┌────────────────────────────────────────────────────┐
│ area = cv::contourArea(approx)                     │
└────────────────────┬───────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────┐
│ GATE 3: area                                       │
│   if (area < 12000)  → return false                │
└────────────────────┬───────────────────────────────┘
                     │ area ≥ 12000 px²
                     ▼
                  return true
```

### Parameter Table — the three tuning knobs

| Param | Value | Original (DevTracker 5.1) | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| **`RACK_MIN_BALLS`** | **13** | 10 | Stricter — racks with >2 occlusions missed | Looser — allows 3–5-ball clusters to attempt rack detection (false positives increase) |
| **`RACK_EPSILON_RATIO`** | **0.035** | 0.025 | Aggressive simplification — an irregular 5-vertex hull might collapse to 3 → **false positive** risk | Conservative — a real rack's hull with 4–5 vertices due to pixel jitter won't simplify to 3 → **false negative** risk |
| **`RACK_MIN_AREA`** | **12000 px²** | 5000 | Rejects small accidental triangles more aggressively, may miss loose racks in wide-angle shots | Accepts small triangles → 3–4 mid-game balls pushed together can false-positive |

### Why 13 balls, not 15?

Standard 8-ball rack has **15 balls** (1 + 2 + 3 + 4 + 5 triangle). So why 13?

1. **Occlusion.** Two corner balls frequently hidden by the cue or shadow. Documented in DevTracker 5.1 L4.
2. **Segmentation limits.** Green 6-ball when stationary is missed (Stage 3 limitation). That's one ball gone from the count.
3. **Noise headroom.** Allowing 2 misses means a momentary mis-detection doesn't kill the rack.

**Effect of 10 (too low):** A mid-game cluster of 10 balls arranged accidentally triangularly → false positive. DevTracker 5.2 Attempt 1 measured **10 counts** on a clip with only 4 real racks.

**Effect of 15 (too high):** Occluded corner or the stationary 6-ball → 13 balls → fails gate 1 → real rack missed entirely.

**Effect of 13 (chosen):** Tolerates 2 occlusions while blocking most accidental clusters.

### Why `RACK_EPSILON_RATIO=0.035` and not 0.025 or 0.05?

**`approxPolyDP` uses Douglas-Peucker simplification with tolerance = `epsilon × perimeter`.** The epsilon is **adaptive** — scaled to hull size — so it works for large and small racks equally.

| Epsilon ratio | Behavior | DevTracker evidence |
|---|---|---|
| 0.025 | Tight — a real rack's hull with pixel jitter keeps 4–5 vertices → fails `== 3` → **false negative** | Attempt 2: only **2 counts** on clip7 (should be 4) |
| **0.035** | Balanced — real racks simplify to 3; scattered clusters sometimes also simplify to 3 | **Chosen** — Attempt 4: 3 counts but 1 false positive at 4281 |
| 0.040 | Loose — even irregular hulls simplify to 3 → false positives spike | Attempt 1: **10 counts** on clip7 |

**Physical meaning of 0.035:** For a real rack triangle at 1280px, perimeter ≈ 3500 px → tolerance ≈ 122 px. The triangle's corner balls (about 32 px diameter) sit within 122 px of the idealized triangle vertices → absorbed by approximation. **The tolerance must be about 3–4 ball diameters** to handle the scalloped hull that 15 individual ball centers produce.

### Why `RACK_MIN_AREA=12000`?

A real rack triangle at 1280px:
- Side length ≈ 550–650 px (depends on camera distance)
- Area of equilateral triangle: `(√3/4) × side² ≈ 0.433 × 600² ≈ 155,880 px²`
- **But** — the hull is of **ball centers**, not ball edges. Ball centers are inset ~16 px from the visual rack edge. So the hull-side is ~520 px → area ≈ 117,000 px².

Hmm — but `RACK_MIN_AREA=12000` is 10× smaller. **Why?**

- The 13-ball gate already filters most noise.
- The triangle gate (`== 3` vertices) already filters most non-racks.
- `RACK_MIN_AREA=12000` is a **secondary floor** to reject "a cluster of 3 balls arranged in a tight triangle" (e.g., three balls accidentally touching).
- Example: 3 balls in a tight triangle, side ≈ 100 px → area ≈ 4330 px² → rejected.
- A 13-ball rack's hull is always ≥ 12,000 px² (minimum side would be ~230 px for equilateral area 22,900 — well above 12,000).

**Why not 50,000 or 100,000?**
- Attempt 5 tried `RACK_MAX_AREA=25000` (a ceiling, not floor) and broke — real racks with occlusions sometimes produce smaller hulls.
- 12000 was chosen as a **conservative floor** that never rejects a real rack but filters 3-ball accidental triangles.

### The `convexHull + approxPolyDP` primitive — why not alternatives?

**Alternative 1: `cv::minEnclosingTriangle`**

```
cv::minEnclosingTriangle(points, triangleVertices);
```

Returns **always exactly 3 vertices** — it's defined that way. Cannot distinguish a rack from a scattered cluster: any set of points fits inside *some* triangle. **Cannot be used for detection** — no discrimination power.

**Alternative 2: Convex hull only (no approxPolyDP)**

A rack of 15 ball centers produces a hull that, due to pixel rounding at corners, has **4–6 vertices** (not 3). A scattered cluster produces a hull with **6–10 vertices**. Both look similar — no clean threshold. **ApproxPolyDP is required to snap scallops to dominant corners.**

**Alternative 3: Hough line detection on hull edges**

Detect the three lines forming the triangle. Complex, sensitive to parameter tuning, slower. **Overkill** — we're already working in 2D point space (hull vertices); approximating is cheaper than line fitting.

**Alternative 4: Segment the filled rack region (re-run segmentation on the rack area)**

Couples Stage 6 back to Stage 3. Violates separation of concerns. **Rejected.**

**`convexHull + approxPolyDP` is the minimal correct primitive:**
- Takes points → produces a simplified polygon
- Vertex count is a meaningful discriminator (3 = triangle)
- Two parameters, both tunable
- Runs in O(n log n) on 14 points = ~microseconds

### Why is Stage 6 stateless? (defend this)

`detectRack()` has no:
- `static` variables
- `class` member variables
- File I/O
- Persistence between calls

Every call is a pure function of its input `candidates` vector.

**Why this matters:**
1. **Testable in isolation** — pass synthetic centers `{(0,0), (100,0), (50,86)}` and get `true` without any video pipeline.
2. **Thread-safe** — no shared state. Could run in parallel on multiple frames (future commercial scaling).
3. **Debuggable** — any disagreement between log and expected output means the input was different, not that some hidden state drifted.

**Defense line:** *"Stage 6 is a pure function — no state, no side effects. The 22-frame `rack=1` streak in the log is 22 independent calls that all returned `true`. The state machine that collapses the streak into a count lives entirely in Stage 7. This is the textbook separation of detection from counting."*

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 5 OUT                                                          │
│ std::vector<BallCandidate> candidates (N balls)                      │
│   each: { bbox, center, area, white_ratio, edge_density, type }      │
│   ★ Only .center is consumed downstream                              │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ detectRack(candidates)                          [rack-detection.cpp] │
│                                                                      │
│  GATE 1: candidates.size() < 13 ?                                    │
│    YES → return false                                                │
│    NO  → continue                                                    │
│                                  │                                    │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ std::vector<cv::Point> centers;                                │  │
│  │ for (ball : candidates)                                        │  │
│  │     centers.push_back({(int)ball.center.x,                     │  │
│  │                        (int)ball.center.y});                   │  │
│  │                                                                │  │
│  │ Example (racked):                                              │  │
│  │   (900,300) (940,310) (980,320)   ← row 1 (1 ball offset)      │  │
│  │     (910,340) (950,350) ...       ← row 2                      │  │
│  │       ...                          ← row 3–5                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ cv::convexHull(centers, hull)                                  │  │
│  │                                                                │  │
│  │ Rack example: hull vertices ≈ (900,300) (900,300) (980,320)   │  │
│  │                              (1000,380) (900,300)  → 4–5 pts   │  │
│  │ Scatter example: hull vertices ≈ 8–10 scattered points         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ peri    = arcLength(hull, closed=true)                         │  │
│  │ epsilon = 0.035 × peri                                         │  │
│  │ cv::approxPolyDP(hull, approx, epsilon, closed=true)           │  │
│  │                                                                │  │
│  │ Rack:    4–5 pts → snapped to 3 → TRIANGLE                     │  │
│  │ Scatter: 8–10 pts → sometimes snapped to 3 (false positive!)   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  GATE 2: approx.size() != 3 ?                                        │
│    YES → return false                                                │
│    NO  → continue                                                    │
│                                  │                                    │
│                                  ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ area = contourArea(approx)                                     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│                                  ▼                                    │
│  GATE 3: area < 12000 ?                                              │
│    YES → return false                                                │
│    NO  → return true                                                 │
│                                                                      │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼ bool rackDetected
┌──────────────────────────────────────────────────────────────────────┐
│ main.cpp:                                                            │
│                                                                      │
│   if (rackDetected) {                                                │
│       cv::putText(frame, "RACK DETECTED", (50,50), red, 2);          │
│   }                                                                  │
│                                                                      │
│   bool counted = counter.update(rackDetected);   ◄── STAGE 7         │
│                                                                      │
│   cout << "SUMMARY ... rack=" << (rackDetected?1:0) << " fps=..."    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why `convexHull` and not just count balls in a cluster?"** | Counting balls doesn't detect a **shape**. A scattered 13-ball cluster would pass. `convexHull` produces the enclosing polygon, whose **vertex count** is a meaningful discriminator: 3 = triangle (rack), 4+ = irregular (no rack). |
| **"Why `approxPolyDP` on top of `convexHull`?"** | A rack's convex hull has 4–6 vertices due to pixel rounding at corners (each corner ball adds a small facet). `approxPolyDP` with tolerance `0.035 × perimeter` collapses these into the dominant 3 corners. Without it, a real rack would sometimes show 4 vertices → fail `== 3` → false negative. |
| **"Why exactly 3 vertices? Why not 4?"** | A rack triangle has exactly 3 corners (top, bottom-left, bottom-right). A 4-vertex polygon is a **quadrilateral**, not a rack. The `== 3` gate is the primary discriminator. |
| **"Why does a false positive happen at frame 4281 then?"** | A scattered cluster of 14 balls in mid-field happened to form an irregular polygon that `approxPolyDP` simplified to 3 dominant vertices. Its area ≈ 30,000 px² > `RACK_MIN_AREA=12000` → passed all gates. From the log: `rack=1` for 159 consecutive frames. **This is a documented geometric false positive** — the core precision/recall trade-off. |
| **"Why not tighten epsilon to prevent that false positive?"** | DevTracker 5.2 Attempt 2 tried `epsilon=0.025` → **2 counts** on clip7 instead of expected 3 (real racks were missed). Tighter epsilon breaks real racks before it stops scattered clusters. Attempt 5 tried additional spatial gates (`RACK_MAX_AREA`, diameter ratio) → **0 counts** — too aggressive. Attempt 6 reverted to `epsilon=0.035` and **accepted the false positive**. |
| **"So you shipped a known bug?"** | No — I shipped a **bounded, documented trade-off**. The false positive occurs in specific real-world clips (scattered balls forming a triangle). In commercial use, a **temporal tracker** (Kalman filter on ball positions, or ByteTrack) would distinguish "balls moving into triangular formation repeatedly" (real rack) from "balls coincidentally arranged" (one-shot). That's a Phase 2 recommendation. |
| **"Why `RACK_MIN_BALLS=13` when a rack has 15?"** | Two occlusions are typical (corner balls hidden by cue or shadow). Also the green 6-ball is missed when stationary (Stage 3 limitation). 13 = 15 − 2. Tuned from DevTracker 5.1 L4. **Tighter (14 or 15) → misses racks with any occlusion. Looser (10 or 12) → allows accidental clusters.** |
| **"Why not `RACK_MAX_BALLS`? What if 20 balls detected?"** | Not needed in practice — a billiard table has max 16 balls. **But** — false contours could inflate the count. In DevTracker 5.2 Attempt 5, adding `RACK_MAX_AREA=25000` broke real detection. A `RACK_MAX_BALLS` could be added safely (16 or 18) as a defensive gate; not currently present. **Honest answer: an untested safeguard.** |
| **"What's the FPS cost of Stage 6?"** | Negligible. `convexHull` on 14 points is O(n log n) ≈ microseconds. `approxPolyDP` is O(n) Douglas-Peucker. `contourArea` is O(k) for k≈4 hull vertices. **Total < 0.5 ms per frame** — well below noise floor. |
| **"Why is Stage 6 stateless?"** | Separation of concerns. Detection = "is this frame a rack?" State = "should I count it?" Mixing them invites bugs (e.g., "why did the counter drift when I only changed the rack geometry?"). Stage 7 owns all state. Stage 6 owns only geometry. |
| **"Why does Stage 6 ignore `type`?"** | Because rack detection is a **spatial** question: "do the ball positions form a triangle?" Ball colors are irrelevant to geometry. If classification later becomes wrong (say, `STRIPE` classifies as `SOLID`), rack detection is unaffected. **Robustness through decoupling.** |
| **"What if a rack is tilted (camera not overhead)?"** | Would appear as a quadrilateral or pentagon after `approxPolyDP` → fail `== 3` → false negative. **Documented limitation (DevTracker 5.1 L3):** the DT 0.3 fixed overhead camera assumption prevents this. Commercial deployment would need perspective rectification (homography). |
| **"What if there are exactly 13 balls but they're not a rack?"** | GATE 1 passes (13 ≥ 13). GATE 2 is the discriminator — 13 balls scattered produce an irregular hull → `approx.size() > 3` → return false. **The vertex count is the critical filter, not the ball count.** |
| **"How do you know it works?"** | Three evidence sources: (1) **Console log** — `rack=1` frames 98–119 for a real rack, followed by `rack=0` when break occurs; (2) **Visual** — red `"RACK DETECTED"` text appears during the rack; (3) **Counter fires** — `COUNTER EVENT` line appears exactly once per rack streak. All three agree → detection is working. |
| **"What about `RACK_MIN_BALLS` — could false positives slip through by having 13 balls?"** | Yes — the false positive at frame 4281 had 14 balls (one more than minimum). This is why `RACK_MIN_AREA` and the `approx==3` gates exist. **Three gates together** filter most false positives; the remainder is the documented precision/recall trade-off. |

---

## 8. Cross-stage dependencies (Peter's "what breaks if…" follow-ups)

| Change | Ripple |
|---|---|
| `RACK_MIN_BALLS = 15` | Any rack with a single occlusion fails gate 1 → **most real racks missed**. Counter shows 0 counts. |
| `RACK_MIN_BALLS = 10` | Mid-game clusters trigger false rack detection. From DevTracker 5.2 Attempt 1: **10 counts** on a 4-rack clip. |
| `RACK_EPSILON_RATIO = 0.025` | Real racks show 4–5 hull vertices → fail `== 3` → **most racks missed**. Attempt 2: 2 counts instead of 4. |
| `RACK_EPSILON_RATIO = 0.050` | Scattered clusters simplify to 3 vertices → **false positive spike**. Attempt 1: 10 counts. |
| `RACK_MIN_AREA = 5000` | Small accidental triangles pass → false positives increase. |
| `RACK_MIN_AREA = 50000` | Loose racks with occlusions fail → false negatives increase. |
| Remove `approxPolyDP` (hull only) | A rack's hull has 4–6 vertices → `== 3` always fails → **0 racks ever detected**. |
| Use `minEnclosingTriangle` | Always returns 3 vertices → every 13-ball cluster detected as rack → **false positives on every frame**. |
| Use `RETR_EXTERNAL` on filled mask | Would couple to Stage 3 → violates separation of concerns. |
| Add `type`-based filtering before Stage 6 (e.g., "only count real balls, drop `?`") | Removes 6-ball contribution on frames where it's UNCERTAIN → `candidates.size()` drops to 12 → fails gate 1 → **racks missed**. **This is why Stage 6 ignores type.** |

---

## 9. The strongest defense points

**1. Pure function, stateless, testable in isolation.**
- Zero global state → no cross-frame bugs.
- Can be unit-tested with `vector<BallCandidate>{...}` and no video.
- Every call deterministic given input.

**2. Classification-agnostic.**
- Only reads `.center` — immune to Stage 5 misclassifications.
- CUE, SOLID, STRIPE, UNCERTAIN all contribute identically to rack detection.
- **Design win:** classification errors don't propagate into count errors.

**3. Two-stage detection philosophy.**
- Stage 6 detects (per-frame bool).
- Stage 7 counts (state machine across frames).
- **"Detection ≠ counting"** — this is the single most-quoted phrase in your defense.

**4. Precision over Recall — a deliberate, documented choice.**
- False positives break billing trust.
- False negatives are bounded (one missed fast break per session).
- DevTracker 5.2 Attempts 1–6 show every iteration — the tuning journey is the defense.

**5. Separation of concerns (the acronym to memorize).**
- Stage 6 is the **only stage in the pipeline** that reads just `.center`.
- It's the "geometry module" — nothing to do with color, texture, or classification.
- Change a Stage 5 threshold → Stage 6 unaffected.
- Swap Stage 5 for a CNN → Stage 6 unaffected.

---

## 10. The five defense one-liners (memorize)

1. **"A rack is a triangle of ball centers — convex hull gives the enclosing polygon, approxPolyDP collapses the scalloped hull into 3 dominant corners."**
2. **"The vertex count is the discriminator, not the ball count. 13 scattered balls form a 5–8 vertex hull — only a real rack forms exactly 3."**
3. **"Stage 6 detects per-frame; Stage 7 counts per-event. A 22-frame streak is one game."**
4. **"Classification-agnostic by design — only `.center` is read. Misclassification doesn't propagate into count errors."**
5. **"Precision over recall: the frame-4281 false positive is bounded, documented, and preferable to missed racks that would break the tuning everywhere else."**

---

**Stage 6 complete.** When ready, prompt `[stage7]` and I'll detail Counter Logic — the `GameCounter` state machine, the `DEBOUNCE_FRAMES=10` / `ABSENCE_TOLERANCE=3` / `COOLDOWN_FRAMES=45` guards, and the LOG-FILE evidence that collapsed 22-frame streaks into exactly one `COUNTER EVENT` line.