# Clear Answer: No — it's unrelated to Stage 3's output

`cv::Rect::operator&=` is **rectangle intersection**, not a data-pipe from Stage 3. It has nothing to do with `filteredOut` (Stage 3's binary debug Mat).

---

## What `operator&=` actually does

```cpp
r &= cv::Rect(0, 0, hsv.cols, hsv.rows);
// equivalent to:
r = r & cv::Rect(0, 0, hsv.cols, hsv.rows);
// = intersection of two rectangles
```

**`cv::Rect` = `{ x, y, width, height }`.** Intersecting two rectangles returns the overlapping region.

```
Image bounds:  Rect(0, 0, 1280, 720)   ← the whole frame
bbox from S3:  Rect(1270, 700, 40, 40) ← ball near bottom-right corner

Intersection:  Rect(1270, 700, 10, 20) ← what actually fits inside the image
```

Because the second operand is always the full image rect, the result is **"the bbox, cropped to whatever lies inside the image."** Pure geometry. Nothing to do with Stage 3's content.

---

## Why the clamp is needed — the actual crash case

`cv::boundingRect(contour)` in Stage 3 can return a rect **partially outside the image**. Example: a ball whose left edge is at x=1270, but the frame is only 1280 wide and the ball is 32 px wide.

```
bbox = { x=1270, y=700, width=32, height=32 }
       → right edge = 1270 + 32 = 1302 > 1280 (frame width)
       → bottom edge = 700 + 32 = 732 > 720 (frame height)
```

Then in Stage 4:
```cpp
cv::Mat roi = hsv(r);   // r extends past hsv's bounds
```

OpenCV's `Mat::operator()(Rect)` **asserts** `0 <= r.x && 0 <= r.width && r.x + r.width <= m.cols` (same for y/height). Out-of-bounds → **assert failure → crash** in debug, **undefined behavior** in release.

The clamp prevents this by shrinking `r` to `{ x=1270, y=700, width=10, height=20 }` — the portion actually inside the frame.

**DevTracker 3.2 log confirms this was a real crash**:  
> *"No 0-width bbox crash (clamping from Dev 3.2 works)"*

---

## How Stage 4 *actually* links to Stage 3

The linkage is **only via the `candidates` vector**, not via `filteredOut` or the clamp.

| What Stage 3 passes to Stage 4 | Purpose |
|---|---|
| **`std::vector<BallCandidate>` return value** | The list of accepted balls; each has `bbox`, `center`, `area` |
| ❌ `filteredOut` | **NOT passed.** Debug-only Mat. Never enters Stage 4. |
| ❌ `rejects` file | **NOT passed.** Audit log. |
| ❌ `contours` vector | **NOT passed.** Discarded after Stage 3. |

Stage 4 iterates the `candidates` vector and uses **`ball.bbox`** as the region of interest, but the pixel data is pulled from **Stage 2's outputs** (`hsv` and `blurred`), not from `filteredOut`:

```cpp
// features.cpp
float computeWhiteRatio(const cv::Mat& hsv, const cv::Rect& bbox) {
    cv::Rect r(bbox.x + 2, ...);        // ← bbox comes from Stage 3 via candidates
    r &= cv::Rect(0, 0, hsv.cols, ...); // ← clamp to hsv (Stage 2), not filteredOut
    cv::Mat roi = hsv(r);               // ← sample HSV pixels, not filteredOut
    ...
}

void computeEdgeDensity(const cv::Mat& blurred, BallCandidate& ball) {
    cv::Rect r = ball.bbox;             // ← bbox from Stage 3
    r &= cv::Rect(0, 0, blurred.cols, ...); // ← clamp to blurred (Stage 2), not filteredOut
    cv::Mat roi_bgr = blurred(r);       // ← sample BGR pixels, not filteredOut
    ...
}
```

---

## The correct mental model

```
Stage 3 produces TWO things:
  ┌──────────────────────────────────┐
  │ candidates (vector of structs)   │ ← the bboxes and centroids
  │ filteredOut (binary Mat)         │ ← DEBUG ONLY, never read again
  └──────────────────────────────────┘

Stage 4 consumes:
  ┌──────────────────────────────────┐
  │ candidates (from Stage 3)        │ ← WHICH balls to measure
  │ hsv (from Stage 2)               │ ← WHERE to read HSV pixel values
  │ blurred (from Stage 2)           │ ← WHERE to read BGR pixel values
  └──────────────────────────────────┘
```

**Analogy:** Stage 3 hands Stage 4 a **list of addresses** (`bbox`) where balls are, but Stage 4 reads the **actual pixel data** from Stage 2's output Mats (`hsv`, `blurred`). `filteredOut` is just Stage 3's private notebook — never handed forward.

The `operator&=` is a **safety belt**, unrelated to any inter-stage data flow.

---

## One-line defense

> *"`cv::Rect::operator&=` is rectangle intersection — it clamps a bbox to the image boundary so `hsv(r)` doesn't assert when a ball straddles the frame edge. Stage 4's link to Stage 3 is purely the `candidates` vector; the pixel data comes from Stage 2's Mats, not from `filteredOut`."*

---

**Ready for `[stage5]`?**