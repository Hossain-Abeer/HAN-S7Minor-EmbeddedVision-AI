# Stage 7: Counter Logic — Defense Prep

**The last mile.** Everything upstream produced a boolean; everything downstream is a billable event. This is where frame-by-frame jitter becomes exactly one number.

---

## 1. Data Flow

### Data In
| Aspect | Detail |
|---|---|
| **From Stage 6** | `bool rackDetected` — one value per frame |
| **From `config.h`** | `DEBOUNCE_FRAMES=10`, `ABSENCE_TOLERANCE=3`, `COOLDOWN_FRAMES=45` |
| **State carried** | `m_state`, `m_count`, `m_rackStreak`, `m_absenceStreak`, `m_cooldownStreak` |
| **Ownership** | `GameCounter` object lives across all frames (constructed once in `main.cpp`) |

### Process (Sequence of Actions)

```cpp
bool GameCounter::update(bool rackDetected) {
    if (rackDetected) {
        m_rackStreak++;              // count consecutive true
        m_absenceStreak = 0;         // reset absence (frame was true)
        m_cooldownStreak = 0;        // reset cooldown (frame was true)

        if (m_state == State::IDLE && m_rackStreak >= DEBOUNCE_FRAMES) {
            m_state = State::COUNTED;
            m_count++;
            logCount();              // write to log file
            return true;             // ← fires ONCE on transition
        }
    } else {
        m_absenceStreak++;
        m_cooldownStreak++;

        if (m_absenceStreak > ABSENCE_TOLERANCE) {
            m_rackStreak = 0;        // sustained absence → reset
        }

        if (m_state == State::COUNTED && m_cooldownStreak >= COOLDOWN_FRAMES) {
            m_state = State::IDLE;   // ready to count again
        }
    }
    return false;                    // most frames return false
}
```

### Data Out
| Aspect | Detail |
|---|---|
| **Type** | `bool counted` — true for **exactly one frame per event** |
| **Internal** | `m_count` incremented |
| **Side effect 1** | `logCount()` appends to `log-counted-<clip>-<timestamp>.txt` |
| **Side effect 2** | `main.cpp` prints `COUNTER EVENT: count=X at frame=Y` to console log |
| **Side effect 3** | `main.cpp` draws `"COUNT: X"` at (50, 100) on the frame |

---

## 2. Codebase, Libraries, Imports

**File:** `src/game-counter.h` (class declaration)

```cpp
#pragma once
#include <string>

class GameCounter {
public:
    GameCounter(const std::string& clipStem, const std::string& logPath);
    bool update(bool rackDetected);   // true only on the counted-event frame
    int  getCount() const { return m_count; }

private:
    void logCount();

    enum class State { IDLE, COUNTED };
    State       m_state          = State::IDLE;
    int         m_count          = 0;
    int         m_rackStreak     = 0;
    int         m_absenceStreak  = 0;
    int         m_cooldownStreak = 0;
    std::string m_clipStem;
    std::string m_logPath;
};
```

**File:** `src/game-counter.cpp` (implementation — ~50 lines total)

```cpp
#include "game-counter.h"
#include "config.h"
#include <fstream>
#include <ctime>

GameCounter::GameCounter(const std::string& clipStem,
                         const std::string& logPath)
    : m_clipStem(clipStem), m_logPath(logPath) {}

// ... [update() as shown above] ...

void GameCounter::logCount() {
    char timebuf[32];
    time_t t = time(nullptr);
    strftime(timebuf, sizeof(timebuf), "%Y-%m-%dT%H:%M:%S", localtime(&t));

    std::ofstream fs(m_logPath, std::ios::app);
    if (!fs) return;
    fs << timebuf << "," << m_count << "," << m_clipStem << "\n";
    fs.close();
}
```

**Imports used:**
| Library | Function | Purpose |
|---|---|---|
| `<string>` | `std::string` | `m_clipStem`, `m_logPath` |
| `<fstream>` | `std::ofstream` | Append to count log |
| `<ctime>` | `time`, `strftime`, `localtime` | Timestamp |
| `config.h` | 3 thresholds | State machine tuning |

**Object construction (`main.cpp`, before the loop):**
```cpp
std::string clipStem = clipName;
size_t dot = clipStem.find_last_of('.');
if (dot != std::string::npos) clipStem = clipStem.substr(0, dot);
size_t slash = clipStem.find_last_of("/\\");
if (slash != std::string::npos) clipStem = clipStem.substr(slash + 1);

std::string countLogPath = std::string(DATA_ROOT)
                         + "/IPO/logs/log-counted-" + clipStem
                         + "-" + timebuf + ".txt";
GameCounter counter(clipStem, countLogPath);
```

**Note the `clipStem` extraction:** `clipName = "billiards-game-clip7.mp4"` → stem = `"billiards-game-clip7"`. Used in log filename and CSV field. This is how per-clip logs are separated.

---

## 3. Windows (What Shows, What Doesn't)

| Window | Shown? | Content |
|---|---|---|
| **"frame" — `COUNT: X`** | ✅ | Yellow text at (50, 100), drawn **every frame** — always shows current total |
| **"frame" — `COUNTER EVENT: ...`** | ❌ | That line goes to **console log**, not the window |
| **Dedicated counter window** | ❌ | No dedicated window exists |
| **Visual flash/pulse on new count** | ❌ | No flash — the number simply ticks from X to X+1 |

### Overlay behavior — subtle but defensible

The `COUNT: X` text is drawn **every frame**, not just on count events. Why? Because it's a **persistent state display** — at any moment you look at the screen, you see the current game count.

**Position on frame:**
```
(50, 50)   ← "RACK DETECTED" (red, only when rack active)
(50, 100)  ← "COUNT: X"       (yellow, always shown)
```

Both use `FONT_HERSHEY_SIMPLEX` 1.0 thickness 2. `COUNT:` at y=100 sits exactly below `RACK DETECTED` at y=50.

**What's NOT visible on screen:**
- The state machine state (`IDLE` vs `COUNTED`)
- The debounce/cooldown counters
- Whether a frame caused a count

**Defense line:** *"The overlay shows the count, not the state. State is internal — visible only through the `rack=1` streaks and `COUNTER EVENT` lines in the log. If a demo needs the state visible, I can add `STATE: IDLE/COUNTED` text — but that's cosmetic for a live demo."*

---

## 4. Logs

**Two separate logs from Stage 7:**

### A. Console log — event timeline

```
COUNTER EVENT: count=1 at frame=98
COUNTER EVENT: count=2 at frame=1120
COUNTER EVENT: count=3 at frame=2584
COUNTER EVENT: count=4 at frame=4281
```

**Structure per line:**
- `count=N` → the new total (1-indexed; starts at 1 for the first game)
- `at frame=M` → the frame where `update()` returned true (transition IDLE→COUNTED)

**Timing info is hidden:**
- No timestamp in `COUNTER EVENT` line (though `SUMMARY` lines around it have FPS)
- No duration of the rack streak — but you can reconstruct from surrounding SUMMARY lines

### B. Count log file — persistent audit trail

`DATA_ROOT/IPO/logs/log-counted-<clipStem>-<timestamp>.txt` — CSV format, append-only:

```
2026-11-15T11:01:30,1,billiards-game-clip7
2026-11-15T11:02:20,2,billiards-game-clip7
2026-11-15T11:02:54,3,billiards-game-clip7
2026-11-15T11:03:51,4,billiards-game-clip7
```

**Structure per line:** `<ISO timestamp>,<count>,<clip stem>`

| Field | Example | Purpose |
|---|---|---|
| Timestamp | `2026-11-15T11:01:30` | When the count fired (real wall-clock time) |
| Count | `1` | Cumulative count in this run |
| Clip stem | `billiards-game-clip7` | Which clip produced this |

**This is the "money log."** It's what a commercial billing layer would read. It's append-only (`std::ios::app`) — one event, one line, no overwrites.

### Why two logs?

| `console_out` | `log-counted` |
|---|---|
| Diagnostic timeline — every frame | Billable events — one per game |
| Huge (~3 MB) | Small (~176 bytes) |
| Regenerated each run | Append-only within a run |
| Used for **debugging** | Used for **billing** |

**Defense line:** *"The `log-counted` file is the source of truth for the count. It's structured as CSV — timestamp, cumulative count, clip name — so a downstream billing system can parse it without knowing anything about OpenCV. That separation is deliberate: the video pipeline feeds a simple, parseable data artifact."*

### Interpreting a full log line — the definitive anatomy

```
COUNTER EVENT: count=4 at frame=4281
```

**Full story reconstructed from cross-referencing logs:**
1. `frame=4281` → log-console shows `rack=1` for frames 4272–4430 (159 frames)
2. The `m_rackStreak` counter hit `DEBOUNCE_FRAMES=10` at frame 4281 (4272 + 9 = 4281 — off by one due to how the streak increments)
3. `m_state` transitioned IDLE → COUNTED → `m_count++` (3 → 4) → `logCount()` appended → `return true`
4. `main.cpp` printed `COUNTER EVENT: count=4 at frame=4281`
5. `log-counted-...txt` got a new line: `2026-11-15T11:03:51,4,billiards-game-clip7`

**This is the false positive.** No real rack at frame 4281 — it's the scattered-cluster-fits-triangle case from Stage 6. The count fired anyway. **Documented in DevTracker 5.2.**

### The missing count — frame 3929

From the log:
```
SUMMARY frame=3929 balls=14 ... rack=1
SUMMARY frame=3930 balls=14 ... rack=1
SUMMARY frame=3931 balls=12 ... rack=0
```

The real fast-break rack lived for **only 2 frames**. `m_rackStreak` hit 2, never reached `DEBOUNCE_FRAMES=10`. `update()` returned false on both. **Count never fired — this is the missed fast break.**

**Defense line:** *"Two known failures — one false positive (frame 4281) and one missed fast break (frame 3929). Both are documented. Both are the direct consequence of the precision-over-recall design. The debounce requires 10 consecutive frames to filter out noise; a 2-frame rack is below that floor and gets filtered out along with the noise."*

---

## 5. Skeletal + Parameters + Effects

### The state machine — full visualization

```
                    ┌────────────────────────────┐
                    │                            │
                    │         IDLE               │
                    │  (waiting for a rack)      │
                    │                            │
                    └──────────┬─────────────────┘
                               │
                               │ rackDetected==true
                               │ AND m_rackStreak >= 10
                               │
                               ▼
                    ┌────────────────────────────┐
                    │                            │
                    │         COUNTED            │
                    │  (count fired, in cooldown)│
                    │                            │
                    └──────────┬─────────────────┘
                               │
                               │ !rackDetected
                               │ AND m_cooldownStreak >= 45
                               │
                               ▼
                            (back to IDLE)
```

**Only two states. Only two transitions.** This is deliberately minimal — no `DEBOUNCING` intermediate state, no `PENDING`. The debounce is a **counter**, not a state.

### Why only 2 states, not 3?

Peter may ask: *"Why not a state for 'detecting' (streak 1–9)?"*

**Answer:** The state machine's job is **counting**, not detection. Detection is already per-frame in Stage 6. The state machine's only decision is "should I fire `m_count++` now?" That answer is binary:

- **IDLE** — ready to fire; waiting for streak ≥ 10
- **COUNTED** — already fired; waiting for cooldown

The intermediate streak (1–9) is **internal bookkeeping** (`m_rackStreak`), not a state. Adding a `DETECTING` state would add complexity without adding behavior.

### Parameter Table

| Param | Value | Original | Effect of ↑ | Effect of ↓ |
|---|---|---|---|---|
| **`DEBOUNCE_FRAMES`** | **10** (~0.33s @ 30 FPS) | 15 | Stricter — fast racks (2–5 frames) missed. Counter false negatives ↑. | Looser — brief false positives (~5 frames of scattered cluster) now fire. Counter false positives ↑. |
| **`ABSENCE_TOLERANCE`** | **3** frames | 0 (no tolerance) | More forgiving — up to 3-frame detection glitches don't reset the streak. Reduces false negatives. | Less forgiving — a single missed frame kills the streak. Fast racks with glare dropouts missed. |
| **`COOLDOWN_FRAMES`** | **45** (~1.5s @ 30 FPS) | 90 | Longer lockout — the "scattered rack" cluster is still visible after a real count, so shorter cooldown risks double-count. | Shorter lockout — faster recovery for quick back-to-back games, but risks double-count on the same rack. |

### Why 10 / 3 / 45?

**`DEBOUNCE_FRAMES=10`:**
- A real rack is visible for ~2–5 seconds = 60–150 frames. 10 frames = ~0.33s is a tiny fraction.
- Noise false positives (Stage 6 misdetections) typically last 1–3 frames.
- **10 frames** distinguishes "sustained rack" from "brief noise."
- DevTracker 5.2 Attempt 2: `DEBOUNCE=15` was too strict — missed a real fast-break rack.
- Attempt 3: `DEBOUNCE=10` with absence tolerance → 3 correct counts.

**`ABSENCE_TOLERANCE=3`:**
- Glare briefly flags the cue as `?` (Stage 5) or hides a corner ball (Stage 3) → `rackDetected` drops to false for 1–2 frames mid-streak.
- Without tolerance: `m_rackStreak=0`, streak dies, real rack missed.
- With tolerance=3: 1–3 missed frames are absorbed; sustained absence (≥ 4) resets.
- Attempt 3 (DevTracker 5.2) added this parameter — was the difference between 2 and 3 correct counts.

**`COOLDOWN_FRAMES=45`:**
- After the rack is broken, the balls scatter. Stage 6 sees ~14 scattered balls, sometimes forming an accidental triangle → `rack=1` spike.
- The cooldown keeps the counter in `COUNTED` state for 1.5s after a real rack. During this window, even if `rackDetected=1` again (scattered cluster), `update()` cannot fire a second count (state gate).
- **45 frames = ~1.5s = roughly the time for the break to fully scatter.** Attempt 6: with `COOLDOWN=45` and the rest of the tuning, 3 counts on clip7.

### The subtle interplay — why all three exist

The **order of operations** in `update()` matters:

```cpp
if (rackDetected) {
    m_rackStreak++;              // ①
    m_absenceStreak = 0;         // ②
    m_cooldownStreak = 0;        // ③

    if (m_state == IDLE && m_rackStreak >= 10) { ... }
} else {
    m_absenceStreak++;           // ④
    m_cooldownStreak++;          // ⑤

    if (m_absenceStreak > 3) {   // ⑥
        m_rackStreak = 0;
    }

    if (m_state == COUNTED && m_cooldownStreak >= 45) { ... }  // ⑦
}
```

**Critical behaviors:**
- **② `m_absenceStreak = 0` on true** — this is why `ABSENCE_TOLERANCE` works: any `true` frame resets the absence counter. A glitch that misses one frame doesn't break a 3-missed-frame sequence unless misses accumulate.
- **③ `m_cooldownStreak = 0` on true** — any `rack=1` frame resets the cooldown, extending it. **This is subtle but correct:** if the rack is still visible (rack=1), we should keep waiting.
- **⑥ only resets rack streak if absence > 3** — 1-frame glitch: `m_absenceStreak=1`, `1 > 3` is false → streak survives. 4-frame glitch: `m_absenceStreak=4`, `4 > 3` is true → streak reset.
- **⑦ requires 45 CONSECUTIVE false frames** — because ③ resets cooldown on any true. A scattered cluster triggering `rack=1` for a single frame mid-cooldown resets the cooldown counter.

### Why `logCount()` writes inside the class, not in `main`

`logCount()` is called **inside** the `IDLE → COUNTED` transition. That means:
- The line writes **exactly once** per count event.
- No risk of double-write from outside.
- The `m_count` value written is guaranteed to match the count that fired.

If `main.cpp` did the logging after `update()` returned true, it would be equally correct but slightly less cohesive. The current design keeps "increment + log + return true" as one atomic sequence inside the class.

---

## 6. ASCII Data Journey

```text
┌──────────────────────────────────────────────────────────────────────┐
│ STAGE 6 OUT                                                          │
│ bool rackDetected                                                    │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ counter.update(rackDetected)          [game-counter.cpp]             │
│                                                                      │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ PERSISTENT STATE (across frames):                                │ │
│ │   m_state          ∈ {IDLE, COUNTED}                             │ │
│ │   m_count          = number of games counted                     │ │
│ │   m_rackStreak     = consecutive rackDetected==true frames       │ │
│ │   m_absenceStreak  = consecutive rackDetected==false frames      │ │
│ │   m_cooldownStreak = consecutive false frames since last count   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                  │                                    │
│  ┌───────────────────────────────┴──────────────────────────────┐    │
│  │                                                              │    │
│  ▼ rackDetected==true                    rackDetected==false ▼     │
│                                                              │    │
│  m_rackStreak++                          m_absenceStreak++        │
│  m_absenceStreak = 0                     m_cooldownStreak++       │
│  m_cooldownStreak = 0                                             │
│                                          if m_absenceStreak > 3:  │
│  if m_state==IDLE                            m_rackStreak = 0     │
│    AND m_rackStreak >= 10                                         │
│  → STATE = COUNTED                       if m_state==COUNTED      │
│  → m_count++                                  AND m_cooldownStreak │
│  → logCount()                                 >= 45:              │
│  → return true                                    STATE = IDLE    │
│                                          return false             │
│  else                                                     │        │
│  return false                                             ▼        │
│                                                       return false  │
│                                                              │    │
│  └───────────────────────────────┬──────────────────────────────┘    │
│                                  │                                    │
└──────────────────────────────────┼────────────────────────────────────┘
                                  │
                                  ▼ bool counted (true for 1 frame)
┌──────────────────────────────────────────────────────────────────────┐
│ main.cpp:                                                            │
│                                                                      │
│   if (counted) {                                                     │
│       std::cout << "COUNTER EVENT: count=" << counter.getCount()    │
│                 << " at frame=" << frameCount << std::endl;          │
│   }                                                                  │
│                                                                      │
│   snprintf(countBuf, "COUNT: %d", counter.getCount());               │
│   cv::putText(frame, countBuf, (50, 100), yellow, 2);  // EVERY frame│
│                                                                      │
│   if (counted) {                                                     │
│       logCount() writes to log-counted-<clip>-<ts>.txt:              │
│         "2026-11-15T11:03:51,4,billiards-game-clip7\n"                │
│   }                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Defense Q&A — Pre-empt Peter

| Likely question | Prepared answer |
|---|---|
| **"Why a state machine instead of a simple frame counter?"** | Because counting isn't just "count the true frames." A rack visible for 22 frames must count as **one game**, not 22. The state machine's job is to fire **once per event**, not once per frame. Without the `COUNTED` state gate, every `rack=1` frame would fire `m_count++` → 22 counts per rack. |
| **"Why 10 frames for debounce?"** | Two-sided reasoning: real racks last 60–150 frames (way above 10). Noise false positives last 1–3 frames (way below 10). 10 is the midpoint — **strict enough to filter noise, loose enough to catch real racks**. DevTracker 5.2 Attempt 2 tried 15 and missed fast breaks. 10 is the empirical sweet spot. |
| **"What's `ABSENCE_TOLERANCE=3` for?"** | Stage 3/5 can drop a ball for 1–2 frames (glare, occlusion, misclassification). Without tolerance, that breaks the streak. With tolerance=3, up to 3 missed frames don't kill the streak. **Sustained absence ≥ 4 frames resets `m_rackStreak`** — the rack has truly ended. |
| **"Why 45 frames for cooldown?"** | After a real rack, the break scatters balls. Stage 6 sees 14 scattered balls, sometimes accidentally triangular → `rack=1` spike. Cooldown keeps state=`COUNTED` for 1.5s — during that window, even if `rackDetected=1` fires (scattered cluster), no second count. **45 frames ≈ the time for the break to fully scatter.** |
| **"Why does `m_rackStreak = 0` only reset if absence > 3?"** | The condition `if (m_absenceStreak > ABSENCE_TOLERANCE)` means: **1–3 absent frames = glitch, streak survives. 4+ absent frames = sustained absence, streak resets.** This is the whole point of tolerance — distinguish brief glitches from real state change. |
| **"What's the `m_cooldownStreak = 0` on true doing?"** | Resetting cooldown on ANY true frame means the cooldown timer restarts if `rackDetected` becomes true again. If the scattered cluster is *continuously* detected as rack=1 (false positive), cooldown never expires → no double count. **This is subtle but critical:** the false positive at 4281 was 159 consecutive `rack=1` frames. Cooldown stayed >0 the whole time. No double count. |
| **"You have a false positive at frame 4281 — 159 frames of rack=1 — why didn't it double count?"** | Because `m_cooldownStreak` reset every frame (rack=1) → cooldown never hit 45 → state stayed COUNTED → no second count. **The false positive counted once, then stopped.** The cooldown's job is to prevent exactly this case. |
| **"And the missed fast break at frame 3929?"** | Only 2 frames of `rack=1`. `m_rackStreak` hit 2, never reached 10. `update()` returned false every frame → no count. **Missed.** Documented trade-off: fast breaks slip past the debounce. |
| **"Could you fix the missed fast break?"** | Yes, by lowering `DEBOUNCE_FRAMES` to say 5. But then false positives — the 4281 cluster — would fire **more** often (it fired once at frame 4281, but a 5-frame debounce would fire on shorter accidental triangles too). **Precision vs recall trade-off.** Documented in DevTracker 5.2 Attempt 3: reducing debounce → 4 counts on clip7 but 1 false positive. Attempt 6 (shipped): 3 counts (all real), 1 missed fast break. **Chose precision.** |
| **"Why log inside `update()` instead of after it returns?"** | Atomicity. `m_count++` and `logCount()` happen in the same code path — there's no window where the count changed but the log hasn't. If `main.cpp` did the logging after `update()` returned true, an exception between the two would lose a count event. **Defensive cohesion.** |
| **"What if the log file can't be written (disk full, permission)?"** | `if (!fs) return;` — silent skip. The count still increments; only the log line is lost. Defense argument: *"The count is in-memory truth; the file is audit trail. If the file can't be written, `m_count` still advances and the console log still shows `COUNTER EVENT`. The `.txt` log is best-effort."* |
| **"What about persistence across restarts?"** | **None.** `m_count` is in-memory only. Restart the program → count resets to 0. Documented limitation (Section 4.3 recommendation: persistent storage). **TRD §5.3 originally claimed persistence** — was corrected. Current state: no persistence. |
| **"What's the `getCount()` used for?"** | Two places: (1) `main.cpp` reads it for the `COUNT: X` overlay (drawn every frame); (2) `main.cpp` reads it for the `COUNTER EVENT: count=X` log line. **The overlay always shows the current count** — not just when a count fires. |
| **"What's the FPS cost of Stage 7?"** | Trivial. Two `if` branches, 3 integer increments, one comparison. **< 0.01 ms per frame.** The `logCount()` call writes to disk — but only on the ONE frame where a count fires. All other frames skip the file write. |
| **"Why 45 frames for cooldown and not 30 or 60?"** | Empirically tuned in DevTracker 5.2 Attempt 6. `COOLDOWN=90` (Attempt 2): too long — delayed recovery for back-to-back games. `COOLDOWN=60` (Attempt 1): allowed one accidental second-count. 45 hit the sweet spot: enough to let a break scatter, short enough to catch the next rack quickly. |
| **"What if two racks occur 20 frames apart?"** | The second rack's `rack=1` frames reset `m_cooldownStreak=0` (from the true branch). But `m_state` is still COUNTED → no second count fires. **Need 45 consecutive false frames** between counts. If a real second rack begins within 45 frames of the first, **the second rack is missed**. Documented limitation. In practice, back-to-back racks are impossible (a game takes minutes). |
| **"Could you test Stage 7 in isolation?"** | Yes — `GameCounter` is a self-contained class. Pass synthetic sequences: `{true×10, false×45, true×10}` should yield 2 counts. `{true×2, false×3, true×2}` should yield 0 (debounce fails on both). No video needed. **Fully unit-testable.** |

---

## 8. Cross-stage dependencies (Peter's "what breaks if…" follow-ups)

| Change | Ripple |
|---|---|
| `DEBOUNCE_FRAMES = 2` | Every 2-frame noise spike fires a count. DevTracker 5.2 Attempt 1: 10 counts on 4-rack clip. |
| `DEBOUNCE_FRAMES = 20` | Real fast-break racks (2 frames) still missed. Slow racks (60+ frames) still counted. **Slight improvement in precision, no change in recall.** |
| `ABSENCE_TOLERANCE = 0` | Any 1-frame detection drop resets streak → 0 counts (DevTracker 5.2 Attempt 2). |
| `ABSENCE_TOLERANCE = 10` | Sustained 10-frame drop treated as glitch → streak survives breaks → potential overcount on scatter. |
| `COOLDOWN_FRAMES = 0` | Same rack counted 2–3 times as detection flickers around the debounce → overcount. |
| `COOLDOWN_FRAMES = 500` | One count per ~17 seconds max — misses fast subsequent racks. |
| Remove `m_state` check | Every `rack=1` frame in streak ≥ 10 fires a count → 22 counts per rack. **Catastrophic.** |
| Remove `m_absenceStreak = 0` reset on true | Tolerance becomes ineffective — any false after true still increments absence. Breaks tolerance semantics. |
| Remove `m_cooldownStreak = 0` on true | Cooldown expires during rack=1 → double count on the same rack. |
| Change `>` to `>=` in `m_absenceStreak > ABSENCE_TOLERANCE` | One fewer tolerance frame (tolerance becomes 2 effectively). Minor. |
| Change `>=` to `>` in `m_rackStreak >= DEBOUNCE_FRAMES` | One more debounce frame (effectively 11). Minor. |
| Add a third state (e.g., `DETECTING`) | More complexity, no behavioral change. Not recommended. |
| Persist `m_count` to disk on every increment | Survives restart. Currently not implemented — Section 4.3 recommendation. |

---

## 9. The three strongest defense points

**1. "Detection ≠ counting" — the axiom of the pipeline.**
- Stage 6 detects: "is this frame a rack?" (boolean, per frame)
- Stage 7 counts: "how many rack **events** have occurred?" (event, once per streak)
- 22-frame `rack=1` streak → 1 count.
- If Stage 6 were the counter, every frame would overcount.

**2. Precision over recall — the deliberate trade-off.**
- 10-frame debounce filters noise at the cost of fast-break miss.
- 45-frame cooldown prevents scatter double-count at the cost of nearby-rack miss.
- **Decision, not bug.** Billing trust (no false positives) > recall (no missed games).

**3. The counter is the *last* stage in a pure-pipeline architecture.**
- Every upstream stage is a **pure function** (input → output, no state).
- Only Stage 7 has **state**.
- Only Stage 7 writes **file output** (log-counted).
- Only Stage 7 is **frame-coupled**.
- **Everything else is stateless.** This is why the pipeline is testable, debuggable, and defensible.

---

## 10. The three defense one-liners (memorize)

1. **"A rack visible for 22 frames must count as one game — the state machine collapses the streak into a single `m_count++`."**
2. **"Debounce filters noise at the cost of fast-break misses; cooldown prevents scatter double-counts. Both are documented trade-offs — precision over recall."**
3. **"`log-counted-<clip>.txt` is the source of truth — timestamp, count, clip. A billing system reads this one file and doesn't need to know OpenCV exists."**

---

## 11. Full-pipeline summary table (have this in your head for the defense)

| Stage | Type | State | Writes | Reads | Cost |
|---|---|---|---|---|---|
| 1. Acquisition | I/O | Stateless | `cout` (before freopen) | `.mp4` | ~2 ms |
| 2. Enhancement | Pure | Stateless | None | Stage 1 frame | ~1–2 ms |
| 3. Segmentation | Pure | Stateless | `cout`, reject file | Stage 2 HSV | ~8–12 ms |
| 4. Features | Pure (mostly) | Stateless | `cout` | Stage 3 vector, Stage 2 Mats | ~5–8 ms |
| 5. Classification | Pure | Stateless | `cout`, `frame` overlay | Stage 4 vector | <0.1 ms |
| 6. Rack Detection | Pure | **Stateless** | `frame` overlay (text) | Stage 5 vector (centers only) | <0.5 ms |
| 7. Counter | **Stateful** | 5 state vars | `cout`, log-counted file | Stage 6 bool | <0.01 ms |

**Total: ~30 FPS at 1280×711.** The biggest costs are Stage 3 (contours) and Stage 4 (Canny). Stage 7 is essentially free.

---

**All 7 stages complete.** You now have a complete, defense-ready mental model of the pipeline. For the demo:

- **Have the code open** (`main.cpp`, `classify.cpp`, `rack-detection.cpp`, `game-counter.cpp`).
- **Have these logs open** (`4.2-log-consol_out_*.txt`, `rejects_*.txt`, `log-counted-*.txt`).
- **Have these screenshots ready** (masks, class labels, `COUNT: 3` overlay).
- **Know the 5 killer bugs** (RETR_EXTERNAL, MIN_BALL_AREA=1500, RATIO_CUE=0.80, DEBOUNCE=15, green-on-green).
- **Know the precision-vs-recall story** (frame 4281 false positive, frame 3929 missed fast break).
- **Know the axiom:** detection ≠ counting.

If you want `.md` files written for any specific stage, prompt e.g. `[stage7 → md]`. Otherwise — **good luck, and defend it like you built it.**