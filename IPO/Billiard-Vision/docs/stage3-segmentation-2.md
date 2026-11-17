# Stage 3 (continued): From "White Blobs" to `std::vector<BallCandidate>`

---

## 0. The State You're Standing On

After the bitwise operations, you have a binary Mat called `ball`:

```
┌────────────────────────────────────────────────────────────┐
│             WHITE (255)            │      BLACK (0)        │
│  ─────────────────────────────────────────────────────────  │
│  • The table rail (a closed ring) │  • The cloth surface  │
│  • The pockets                    │                       │
│  • The cue stick                  │                       │
│  • Any ball in view               │                       │
│  • Noise specks (1–3 px)          │                       │
│  • Shadowed cloth edges           │                       │
└────────────────────────────────────────────────────────────┘
```

**This mask is NOT usable as-is.** Three problems:

| Problem | Cause | Visual |
|---|---|---|
| **Specks** | H.264 compression artifacts, dust, edges of pockets | Isolated 1–3 px white dots |
| **Holes** | Specular highlight on a ball makes the pixel look like cloth → inverted → **black hole inside white ball** | Black spot in middle of a white blob |
| **Jagged edges** | Compression + integer rounding | Non-smooth ball boundaries |

Each problem corrupts a different downstream filter (specks break AREA, holes break CIRCULARITY, jagged edges break ASPECT).

---

## 1. Morphology — The "Shrink-Grow / Grow-Shrink" Trick

Two operations, in this order:

### Step 1a: `MORPH_OPEN` = Erode → Dilate

**Erode:** For each pixel, look at the 3×3 neighborhood. If **any** neighbor is black, make the pixel black. → **White shrinks by 1 px from every edge.**

**Dilate:** For each pixel, look at the 3×3 neighborhood. If **any** neighbor is white, make the pixel white. → **White grows by 1 px from every edge.**

**Net effect of OPEN:** Shrink 1 px, then grow 1 px back.

- A **large blob** (ball, 32 px): shrinks to 30 px, grows back to 32 px. **Survives.**
- A **small speck** (2 px): shrinks to 0 px, **disappears**. Growth can't resurrect what's gone.

**Analogy:** Sandpaper on wood. Small raised bumps get sanded flat; the overall plank survives.

### Step 1b: `MORPH_CLOSE` = Dilate → Erode

**Dilate:** Grow every white region by 1 px. **Black holes shrink** because white grows into them.

**Erode:** Shrink back by 1 px. But the hole was already filled by the dilation. → **Black holes disappear.**

**Net effect of CLOSE:** Grow 1 px, then shrink 1 px back.

- A **glare hole** (4 px across, inside a ball): the white grows 1 px inward from all sides → hole becomes 2 px → then erode pulls back, but the hole can't re-form from 2 px of black (it doesn't have the "mass" to survive erosion).
- **The ball is now solid white.**

### Why THIS order?

| If you did CLOSE first | If you did OPEN first ✅ |
|---|---|
| Dilation would **enlarge** specks before OPEN could remove them → larger kernel needed → erodes ball edges | OPEN removes specks first → CLOSE only has to fill holes in surviving blobs |

**Rule of thumb:** *Open to clean, close to smooth.* This is the standard morphological pipeline in every CV textbook.

### What you're left with

```cpp
cv::Mat morphK = cv::getStructuringElement(cv::MORPH_RECT, Size(3, 3));
cv::morphologyEx(ball, m, cv::MORPH_OPEN,  morphK, Point(-1,-1), 1);
cv::morphologyEx(m,    m, cv::MORPH_CLOSE, morphK, Point(-1,-1), 1);
```

After this: **`m`** is a clean binary mask. White = solid ball-sized blobs + still the rails/stick/pockets (those don't have specks or holes, so morphology doesn't touch them). Black = clean cloth.

---

## 2. `findContours` — Turning Pixels into Shapes

### What it does

`cv::findContours` **walks the binary image** and traces the boundary of every white connected region. Each boundary becomes a `std::vector<cv::Point>` — a list of (x,y) coordinates in order around the perimeter.

**Input:** `m` (binary Mat)
**Output:** `std::vector<std::vector<cv::Point>>` — a list of contours

### Two mode flags you must defend

**`RETR_LIST` (retrieval mode):**

| Mode | Behavior |
|---|---|
| `RETR_EXTERNAL` | Only the **outermost** contour of each connected component |
| `RETR_LIST` | **ALL** contours, flat list, no hierarchy |
| `RETR_TREE` | Full nested hierarchy (parent ↔ child) |

**Why `RETR_EXTERNAL` fails here (the killer bug):**

Look at the ball mask. The **table rail is a white closed ring** wrapping the entire frame. The cloth is black inside. The balls are white blobs floating inside that black cloth.

Hierarchy OpenCV sees:
```
Level 0: Outer boundary of rail ring (perimeter of whole table)
    │
    └─ Level 1: Inner boundary of rail ring (where rail meets cloth)
         │
         └─ Level 2: White balls floating inside the cloth
```

`RETR_EXTERNAL` only returns **Level 0**. The balls are at Level 2 — **invisible to it**.

DevTracker 2.3 measured exactly this: `contours=1 accepted=0` — one giant rail contour (area 908090), zero balls.

`RETR_LIST` returns Levels 0, 1, AND 2. Now the filter has a chance to drop the rail (huge area) and keep the balls (small area).

**`CHAIN_APPROX_SIMPLE` (approximation method):**

- `CHAIN_APPROX_NONE` = every boundary pixel returned (e.g., 100 points for a 32-px ball)
- `CHAIN_APPROX_SIMPLE` = **compresses collinear points** (e.g., a straight edge with 20 collinear pixels → 2 endpoints)

Ball boundary is circular, so not much compression. But for the rail (long straight edges), this reduces ~5000 points to ~50. Savings: memory + downstream `arcLength`/`contourArea` speed.

### One gotcha you must know

```cpp
cv::Mat mCopy = m.clone();  // ← why clone?
cv::findContours(mCopy, contours, cv::RETR_LIST, cv::CHAIN_APPROX_SIMPLE);
```

`findContours` **mutates** its input in OpenCV 4 (historically destroyed it, now still modifies). If we passed `m` directly, `m` would be corrupted for any subsequent use. We `clone()` first, so the original `m` stays intact.

---

## 3. The Filter Cascade — Three Checks, In Order

You now have ~25 contours (rails, pockets, balls, stick, noise). The filter loop iterates over every one and asks: *"Is this a valid ball?"*

```cpp
for (size_t i = 0; i < contours.size(); i++) {
    double area = cv::contourArea(contours[i]);
    cv::Rect bb = cv::boundingRect(contours[i]);

    if (area < MIN_BALL_AREA || area > MAX_BALL_AREA) { reject "area"; continue; }
    
    double peri = cv::arcLength(contours[i], true);
    double circ = (peri > 0) ? (4.0 * CV_PI * area / (peri * peri)) : 0.0;
    if (circ < MIN_CIRCULARITY) { reject "circ"; continue; }
    
    float aspect = (float)bb.width / bb.height;
    if (aspect < ASPECT_MIN || aspect > ASPECT_MAX) { reject "aspect"; continue; }
    
    // ACCEPT
    ...
}
```

### Filter 1: AREA (`[200, 60000]` px²)

**Targets:** Table rail, pockets, noise specks.

| Contour | Typical area | Verdict |
|---|---|---|
| Table rail ring | 900,000+ px² | `> 60000` → reject |
| Cloth+balls blob (rare) | ~740,000 px² | `> 60000` → reject |
| Noise speck | 6–20 px² | `< 200` → reject |
| Valid ball | ~800 px² | PASS |
| Half-occluded ball | ~400 px² | PASS |
| Merged pair | ~1600 px² | PASS (caught by CIRC later) |

**Cheapest filter** — `contourArea` is O(P) but called first because it eliminates the biggest offenders (rail, cloth blob) before we pay for `arcLength`.

### Filter 2: CIRCULARITY (`≥ 0.75`)

**Formula:**
```
circ = (4 × π × area) / (perimeter)²
```

| Shape | circ |
|---|---|
| Perfect circle | 1.00 |
| Square | π/4 ≈ 0.785 |
| Rectangle 2:1 | π/5 ≈ 0.628 |
| Long thin stick | 0.3–0.5 |

**Threshold 0.75** = "must be at least as round as a square."

**Targets:** Cue stick, merged ball pairs, curved highlights.

| Contour | Observed circ | Verdict |
|---|---|---|
| Cue stick | 0.44–0.57 | reject |
| Merged pair | 0.44–0.50 | reject |
| Valid ball | 0.80–0.95 | PASS |
| Slightly occluded ball | 0.78–0.85 | PASS (still above 0.75) |

**Trade-off:** A merged pair is **one missing ball for that frame**. Documented as an accepted limitation. `ABSENCE_TOLERANCE=3` (Stage 7) covers brief drops.

### Filter 3: ASPECT RATIO (`[0.70, 1.40]`)

```cpp
bb = boundingRect(contour);        // smallest axis-aligned rectangle
aspect = bb.width / bb.height;
```

| Shape | aspect | Verdict |
|---|---|---|
| Circle (perfect) | 1.00 | PASS |
| Slightly elliptical ball | 0.85–1.15 | PASS |
| Tilted stick | 3.0–8.0 | reject |
| Vertically merged pair | 0.40–0.55 | reject |
| Squashed blob (shadow+ball) | 0.60 | reject |

**Why 0.7–1.4?** Balls are round under overhead camera, but at edges of the frame with perspective skew, a ball can appear slightly elliptical (up to ~1.2:1). Also slight bounding-box overshoot from antialiasing adds ±10%. `[0.70, 1.40]` captures all real balls, rejects all elongated/tilted shapes.

**Why is CIRC before ASPECT?**
- CIRC catches cue stick and merges (the dominant failure mode).
- ASPECT is a **backup** — it catches cases where CIRC accidentally passed something elongated.
- In practice, ASPECT `rejAspect=0` on most frames — CIRC does the heavy lifting.

### Why cascade instead of one combined score?

```
Combined score: f(area, circ, aspect) — hard to tune, opaque, one bad metric masks the others.
Cascade:                — each filter is independently tunable; reject log tells you exactly which check fired.
```

**Defense line:** *"The cascade makes each rejection reason attributable to exactly one metric. My reject log proves which filter caught which non-ball."*

---

## 4. Accept — Blob → `BallCandidate`

For contours that survive all three filters:

```cpp
nAccepted++;
cv::drawContours(filteredOut, contours, (int)i, cv::Scalar(255), -1);  // debug
cv::rectangle(filteredOut, bb, cv::Scalar(128), 1);                    // debug

cv::Moments mu = cv::moments(contours[i]);
cv::Point2f center(
    (float)(mu.m10 / (mu.m00 + 1e-5)),
    (float)(mu.m01 / (mu.m00 + 1e-5))
);
candidates.push_back({ bb, center, (int)area });
```

### The centroid calculation

**Moments** of a binary shape give you its "center of mass" in one shot:

```
m.m00 = area
m.m10 = Σ(x × pixel) = "first-order x moment"
m.m01 = Σ(y × pixel) = "first-order y moment"

center.x = m.m10 / m.m00
center.y = m.m01 / m.m00
```

**Why moments, not bbox center?**
- **bbox center** = `(x + w/2, y + h/2)` — mathematically the center of the *rectangle*, not the ball.
- **moments centroid** = the actual *pixel-weighted* center of the contour.
- For an **occluded ball** (part cut off), bbox is larger than the visible ball, so bbox center is *shifted*. Moments centroid stays on the visible mass.

**Why does this matter?** Stage 6 builds a **convex hull from these centers**. If each center is off by 1–2 px, 13 balls × 2 px drift = ~5 px hull distortion. `approxPolyDP` at `epsilon=0.035 × perimeter` can flip the vertex count from 3 → 4 → false negative on rack detection.

**Why `+1e-5`?** Division-by-zero guard. A degenerate contour (single pixel, zero area) would give `m00 = 0`. The tiny epsilon keeps the math valid (returns a finite — if nonsense — point) instead of producing `NaN` which would poison the hull.

### Populating the struct

The struct is a **placeholder** at this point:

```cpp
struct BallCandidate {
    cv::Rect    bbox;
    cv::Point2f center;
    int         area;
    float       white_ratio  = 0.0f;   // filled by Stage 4
    float       edge_density = 0.0f;   // filled by Stage 4
    BallType    type         = BallType::UNCERTAIN;  // filled by Stage 5
};
```

- `bbox`, `center`, `area` ← **populated here**
- `white_ratio`, `edge_density` ← **populated in Stage 4**
- `type` ← **populated in Stage 5**

This "fill-as-you-go" design means each stage only touches the fields it owns. Clean layering.

---

## 5. Return + Side Effects

```cpp
std::cout << "contours=" << contours.size()
          << " accepted=" << nAccepted
          << " candidates=" << candidates.size() 
          << " rejArea=" << nRejectArea
          << " rejCirc=" << nRejectCirc
          << " rejAspect=" << nRejectAspect << "\n";

return candidates;
```

Three outputs exit this function:

| Output | Type | Consumer |
|---|---|---|
| **`candidates`** (return value) | `std::vector<BallCandidate>` | Stage 4 |
| **`filteredOut`** (out-param) | `cv::Mat` | Not shown (debug only) |
| **SUMMARY line** | `cout` → log file | Summary log |
| **Rejects file** | Written throughout loop | Reject log |

### The invariant (memorize this)

```
contours.size() = accepted + rejArea + rejCirc + rejAspect
```

Every contour is either **accepted** or **rejected for exactly one reason**. Never both, never neither. If Peter sees this math check out on your log, he knows the filter code is bug-free.

Example from your log:
```
contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0
14 + 10 + 1 + 0 = 25 ✓
```

---

## 6. The Journey in One Diagram

```text
┌────────────────────────────────────────────────────────────────┐
│ ball mask (post-bitwise)                                       │
│ WHITE = balls + rails + pockets + stick + specks               │
│ BLACK = cloth                                                  │
│ Problems: specks, glare holes, jagged edges                    │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ MORPH_OPEN (erode → dilate)                                    │
│ Erode 1 px: every white speck < 3 px vanishes                  │
│ Dilate 1 px: surviving blobs (balls) restore to original size  │
│ Result: specks GONE                                            │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ MORPH_CLOSE (dilate → erode)                                   │
│ Dilate 1 px: white grows into black holes inside balls         │
│ Erode 1 px: blobs shrink back, but holes stay filled           │
│ Result: glare holes GONE                                       │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ m.clone() → findContours(RETR_LIST, CHAIN_APPROX_SIMPLE)       │
│ Walks the binary image → traces every white boundary           │
│ Result: vector<vector<Point>> — one contour per white blob     │
│ (Retrieval mode is critical: RETR_EXTERNAL drops balls nested  │
│  inside the rail ring → black screen → see DevTracker 2.3)     │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ FOR EACH contour:                                              │
│                                                                │
│   ┌─ FILTER 1: contourArea → [200, 60000] ─────────────────┐   │
│   │  Rejects: table rail (919601), noise (20)              │   │
│   │  Accepts: balls (800), occluded balls (400)            │   │
│   └────────────────────────────┬───────────────────────────┘   │
│                                │                               │
│                                ▼ PASS                          │
│   ┌─ FILTER 2: circularity → ≥ 0.75 ───────────────────────┐   │
│   │  Rejects: cue stick (0.57), merged pair (0.44)         │   │
│   │  Accepts: round balls (0.80–0.95)                      │   │
│   └────────────────────────────┬───────────────────────────┘   │
│                                │                               │
│                                ▼ PASS                          │
│   ┌─ FILTER 3: aspect → [0.70, 1.40] ──────────────────────┐   │
│   │  Rejects: tilted/squashed blobs                        │   │
│   │  (mostly redundant, catches stragglers CIRC missed)    │   │
│   └────────────────────────────┬───────────────────────────┘   │
│                                │                               │
│                                ▼ ACCEPT                        │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ moments → centroid (m10/m00, m01/m00)                │    │
│   │ push_back({bbox, center, area})                      │    │
│   │ drawContours + rectangle to filteredOut (debug)      │    │
│   └──────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│ return std::vector<BallCandidate> (size = accepted)            │
│ Side effects:                                                  │
│   • cout << "contours=.. accepted=.. rejArea=.. ..."           │
│   • rej << "area .. | bbox .." (per rejection)                 │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
                       STAGE 4 (features)
```

---

## 7. One-Line Defense Summaries (memorize these)

- **"Morphology OPEN removes specks by shrinking-then-growing — small things die, big things survive."**
- **"Morphology CLOSE fills glare holes by growing-then-shrinking — the hole is filled before the erosion can restore it."**
- **"RETR_EXTERNAL drops balls because they're nested inside the table's rail ring. RETR_LIST returns everything, and the area filter kills the rail."**
- **"The filter cascade is area → circularity → aspect because each catches a different failure mode, and the reject log attributes each rejection to exactly one cause."**
- **"Moments centroid beats bbox center for occluded balls — it stays on the visible mass."**
- **"The invariant `contours = accepted + rejArea + rejCirc + rejAspect` proves the filter code is complete and bug-free."**

---

**Ready for `[stage4]`?** Feature Extraction — where every downstream decision hinges on two numbers: `white_ratio` (primary) and `edge_density` (tie-breaker).