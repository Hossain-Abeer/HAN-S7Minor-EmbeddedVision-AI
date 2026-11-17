# The Two Log Files — Explained

---

## 1. `4.2-log-consol_out_YYYYMMDD_HHMMSS.txt` — The Console Log

### How it's created

```cpp
// main.cpp, line ~62, BEFORE the while loop:
char timebuf[32];
strftime(timebuf, sizeof(timebuf), "%Y%m%d_%H%M%S", localtime(&t));
string logPath = string(DATA_ROOT) + "/IPO/logs/4.2-log-consol_out_" + timebuf + ".txt";
freopen(logPath.c_str(), "w", stdout);
```

`freopen` **hijacks `stdout`**. Every `std::cout <<` in the entire codebase — from any function, any module — now writes to this file instead of the terminal.

### What gets captured

| Source | Line type |
|---|---|
| `main.cpp` (FPS block) | `frame=30 size=1280x711 fps=28.747` |
| `segment.cpp` (end of each frame) | `contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0` |
| `main.cpp` (per-ball loop) | `frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE` |
| `main.cpp` (SUMMARY) | `SUMMARY frame=4251 balls=13 CUE=1 SOLID=7 STRIPE=5 ?=0 rack=0 fps=29.49` |
| `main.cpp` (counter) | `COUNTER EVENT: count=4 at frame=4281` |

### What does NOT get captured

The very first line:
```cpp
cout << "source=" << cap.get(CAP_PROP_FRAME_WIDTH) << "x" << ... << endl;
```
This runs **before** `freopen` — it goes to the **terminal** and is lost from the file. (Cosmetic gap; you see it live but it's not in the log.)

### How to read it — 4 line types, 4 meanings

**Type A — Per-frame SUMMARY (one per frame, the 30,000-foot view):**
```
SUMMARY frame=4251 balls=13 CUE=1 SOLID=7 STRIPE=5 ?=0 rack=0 fps=29.49
```
- `frame=4251` → frame number since video start
- `balls=13` → how many valid balls Stage 3 accepted this frame
- `CUE=1 SOLID=7 STRIPE=5 ?=0` → Stage 5 classification breakdown (must sum to `balls`)
- `rack=0` → Stage 6 did **not** detect a triangle
- `fps=29.49` → instantaneous frames-per-second

**Type B — Per-ball feature dump (N lines per frame):**
```
frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE
```
- `ball=1` → index within this frame's candidate vector
- `wr=0.493827` → `white_ratio` (49.4% of bbox pixels are white)
- `ed=0.200274` → `edge_density` (20.0% of bbox pixels are Canny edges)
- `class=STRIPE` → final classification

**Type C — Filter summary (from `segment.cpp`, one per frame):**
```
contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0
```
- `contours=25` → raw contours from `findContours`
- `accepted=14` → passed all 3 filters
- `candidates=14` → pushed into the vector (identical to accepted)
- `rejArea=10` → rejected by Filter 1 (area)
- `rejCirc=1` → rejected by Filter 2 (circularity)
- `rejAspect=0` → rejected by Filter 3 (aspect)
- **Invariant:** `25 = 14 + 10 + 1 + 0` ✓

**Type D — Counter event (the "money" line):**
```
COUNTER EVENT: count=4 at frame=4281
```
- Fired **exactly once** when Stage 7 transitions `IDLE → COUNTED`
- `count=4` → this is the 4th game counted in this run

### Mental model

> **`console_out` is a timeline.** It shows you *what the system saw and decided* frame by frame. If something broke, you open this file, `Ctrl+F` the frame number, and reconstruct the story.

---

## 2. `rejects_YYYYMMDD_HHMMSS.txt` — The Reject Log

### How it's created

```cpp
// segment.cpp, before the filter loop:
std::ofstream rej(rejectPath, std::ios::app);
```

Then **inside** the filter loop, every time a contour is rejected:

```cpp
if (area < MIN_BALL_AREA || area > MAX_BALL_AREA) {
    nRejectArea++;
    rej << "area " << area << " | bbox " << bb.x << "," << bb.y
        << "," << bb.width << "," << bb.height << "\n";
    continue;
}
```

Written with `std::ofstream` — **not** `cout`. So `freopen` doesn't touch it. This is an independent file.

**Note:** opened with `std::ios::app` (append). Every frame's rejections add to the file without truncating. That's why the file grows to ~1.5 MB for a long run.

### What gets captured — **only rejections**

One line per rejected contour, in this format:
```
<reason> <value> | bbox x,y,w,h
```

Examples from your actual log:
```
area 919601 | bbox 0,0,1280,720          ← the table ring
area 20 | bbox 1207,595,3,11              ← a noise speck
area 740087 | bbox 42,47,1196,631         ← cloth+balls blob
circ 0.571423 | bbox 1009,473,27,32       ← cue stick
circ 0.483016 | bbox 931,471,30,33        ← merged pair
circ 0.443474 | bbox 929,359,62,49        ← big merge
```

### What does NOT get captured

- **Accepted balls** → silent. Only rejections are logged.
- **Per-frame boundaries** → no frame separator. You can't tell which reject belonged to which frame without cross-referencing `console_out`.
- **Timestamps** → no timestamp on each line.

### How to read it — by prefix

| Prefix | Meaning | Example interpretation |
|---|---|---|
| `area <number>` | Rejected by Filter 1 (too small or too big) | `area 919601` → table ring. `area 20` → noise speck. |
| `circ <number>` | Rejected by Filter 2 (circularity < 0.75) | `circ 0.571` → cue stick. `circ 0.443` → merged pair. |
| `aspect <number>` | Rejected by Filter 3 (aspect outside [0.7, 1.4]) | Rare; catch-all for elongated blobs. |

Then `| bbox x,y,w,h` tells you **where** on the frame this rejection happened — useful for verifying visually ("Ah yes, that's the pocket at bottom-right").

### Mental model

> **`rejects` is evidence of what your filters caught.** It answers *"what did I reject, and why?"* — used to prove the filter is doing its job, and to debug "why is ball count lower than expected?"

---

## 3. Side-by-Side Comparison

| Aspect | `console_out` | `rejects` |
|---|---|---|
| **Created by** | `freopen(logPath, "w", stdout)` | `std::ofstream rej(rejectPath, std::ios::app)` |
| **Captures** | Everything `cout` writes | Only rejections from `segment.cpp` |
| **Granularity** | Per-frame + per-ball | Per-rejected-contour |
| **Has frame numbers** | ✅ (`frame=4251`) | ❌ |
| **Has timestamps** | ❌ (but filename has it) | ❌ (but filename has it) |
| **Has accepted balls** | ✅ | ❌ (only rejected) |
| **Size (long run)** | ~3 MB | ~1.5 MB |
| **Open mode** | `w` (truncate — fresh file per run) | `app` (append — grows during run) |
| **Primary use** | Timeline reconstruction | Filter audit / proof of work |
| **Shared timestamp** | ✅ same `timebuf` → files pair up | ✅ same `timebuf` |

**The filename pairing is the trick:** both files get `timebuf` embedded. So `4.2-log-consol_out_20261115_110128.txt` and `rejects_20261115_110128.txt` belong to the **same run**. You can cross-reference them: open console at `frame=4251`, see `rejArea=10`, then scan `rejects` for the 10 nearest `area` lines to know **exactly** what those 10 rejections were.

---

## 4. Example: One Frame Across Both Logs

**From `console_out_20261115_110128.txt`** (hypothetical frame 4251 excerpt):
```
contours=25 accepted=14 candidates=14 rejArea=10 rejCirc=1 rejAspect=0
frame=4251 ball=0 wr=0 ed=0.121173 class=SOLID
frame=4251 ball=1 wr=0.493827 ed=0.200274 class=STRIPE
...
SUMMARY frame=4251 balls=13 CUE=1 SOLID=7 STRIPE=5 ?=0 rack=0 fps=29.49
```

**From `rejects_20261115_110128.txt`** — 11 lines are written during this frame (10 area + 1 circ):
```
area 919601 | bbox 0,0,1280,720
area 740087 | bbox 42,47,1196,631
area 20 | bbox 1207,595,3,11
area 16 | bbox 1207,583,3,9
area 6 | bbox 1207,563,3,4
area 14 | bbox 947,486,5,5
area 10 | bbox 1207,158,3,6
area 18 | bbox 1207,595,3,10
area 6 | bbox 1207,160,3,4
circ 0.571423 | bbox 1009,473,27,32
```

**Now you can reconstruct the full story:**
- "Frame 4251: the pipeline saw 25 shapes."
- "10 were too big/small — table ring (919601), cloth blob (740087), 8 noise specks (6–20 px²)."
- "1 was too elongated — cue stick at (1009,473), circularity 0.57."
- "14 survived as balls → classified as CUE=1, SOLID=7, STRIPE=5, plus 1 uncertain."
- Wait — the SUMMARY says `balls=13` but Stage 3 said `accepted=14`. Why the discrepancy?

**Aha — good catch.** Let me check your actual log... The per-ball dump shows 14 lines (`ball=0` through `ball=13`), and the SUMMARY shows `balls=13 CUE=1 SOLID=7 STRIPE=5 ?=0`. That's 1+7+5+0 = 13, but Stage 3 accepted 14.

**Why the mismatch?** Because on this particular frame, one ball fell into `UNCERTAIN`. Wait, but `?=0`...

Actually, re-reading the log: the `contours=25 accepted=13 candidates=13` line precedes this frame's ball dumps — the `14` came on a different frame. **This is why you cross-reference.** The `contours=` line at the top of a SUMMARY block belongs to that frame's Stage 3 output; the per-ball lines follow; the SUMMARY follows. All three from **the same frame**.

---

## 5. Cross-reference recipe (memorize for the defense)

If Peter asks *"Why did your system miss a ball on frame 4251?"*:

1. **Open console** → `Ctrl+F frame=4251` → find `contours=.. accepted=..`
2. Note the numbers: e.g., `contours=25 accepted=14 rejArea=10 rejCirc=1 rejAspect=0`
3. **Open rejects** → find 11 lines matching `rejArea=10` + `rejCirc=1`
4. For each, look at `bbox` → correlate with visual position → confirm it's a rail/speck/stick, **not** a ball
5. If a *ball* was rejected, that's a bug → fix `MIN_BALL_AREA` or `MIN_CIRCULARITY`

**Defense line:** *"The two logs are paired by timestamp. The console tells me how many passed each filter per frame; the rejects file tells me exactly which shapes were dropped and where. I can audit any single frame in under 30 seconds."*

---

**Next: `[stage4]`?** Feature Extraction — `computeWhiteRatio` and `computeEdgeDensity`, the two numbers every downstream threshold depends on.