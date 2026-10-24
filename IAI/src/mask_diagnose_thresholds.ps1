"""
whiteness_diagnose.py

Diagnostic for 7.2 failure: hole_count=0 across all 492 rows.

Root-cause hypothesis: MASK_V_MIN=180 / MASK_S_MAX=60 is too strict.
The ball's white patch fragments into specks. Numerals become notches
(open to background) rather than enclosed holes. find_holes() rejects
them correctly.

This script tests six (V_MIN, S_MAX) threshold pairs across five
representative crops and reports pixel survival, connected-component
count, and hole count. Saves current and loose_C masks for visual
inspection.

Usage:
    python src/whiteness_diagnose.py

Reads:  config, constants, CROP_ROOT
Writes: logs/whiteness_diag/*.png
"""

import os
import cv2
import numpy as np

import config
import constants as C

# One crop per class archetype. Chosen from splits.csv (test/val roles
# for representativeness), covering: black solid, yellow solid, green
# solid, striped blue, striped purple.
TEST_CROPS = [
    ("8",  "clip1_frame000084_ball6.png",  "black solid, digit 8 (2 holes expected)"),
    ("1",  "clip1_frame000003_ball1.png",  "yellow solid, digit 1 (0 holes, thin)"),
    ("6",  "clip1_frame000090_ball2.png",  "green solid, digit 6 (1 hole expected)"),
    ("10", "clip1_frame000029_ball10.png", "striped blue, digit 10 (1 hole in the 0)"),
    ("12", "clip1_frame000058_ball7.png",  "striped purple, digit 12 (0 holes)"),
]

THRESHOLDS = [
    ("current",  180,  60),
    ("loose_A",  150,  80),
    ("loose_B",  140,  80),
    ("loose_C",  120,  90),
    ("loose_D",  120, 100),
    ("loose_E",  100, 120),
]

CLOTH_LO = np.array([C.CLOTH_H_LO, C.CLOTH_S_LO, C.CLOTH_V_LO], np.uint8)
CLOTH_HI = np.array([C.CLOTH_H_HI, C.CLOTH_S_HI, C.CLOTH_V_HI], np.uint8)


def apply_pipeline(img, v_min, s_max):
    """Mimics 6.1: threshold + cloth intersect + open. Returns mask."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mask = ((v >= v_min) & (s <= s_max)).astype(np.uint8) * 255
    cloth = cv2.inRange(hsv, CLOTH_LO, CLOTH_HI)
    mask = cv2.bitwise_and(mask, cv2.bitwise_not(cloth))
    k = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    return mask


def count_holes(mask, min_hole_area=5):
    """Mimics 6.1's find_holes(). Returns (cc_count, hole_count)."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return 0, 0
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    blob = (labels == idx).astype(np.uint8) * 255
    inv = cv2.bitwise_not(blob)
    nn, ll, ss, _ = cv2.connectedComponentsWithStats(inv, 8)
    h, w = blob.shape
    holes = 0
    for i in range(1, nn):
        x, y, cw, ch, area = ss[i]
        if x == 0 or y == 0 or x + cw == w or y + ch == h:
            continue
        if area < min_hole_area:
            continue
        holes += 1
    return n - 1, holes


def main():
    out_dir = os.path.join(config.LOGS_DIR, "whiteness_diag")
    os.makedirs(out_dir, exist_ok=True)

    print(f"{'cls':>3} | {'file':<32} | {'name':<8} | {'V':>4} | {'S':>4} | "
          f"{'pix':>7} | {'frac':>6} | {'cc':>3} | {'holes':>5}")
    print("-" * 110)

    for cls, fname, note in TEST_CROPS:
        path = os.path.join(config.CROP_ROOT, cls, fname)
        img = cv2.imread(path)
        if img is None:
            print(f"[WARN] missing {path}")
            continue
        total = img.shape[0] * img.shape[1]
        print(f"# {note}")

        for name, v, s in THRESHOLDS:
            mask = apply_pipeline(img, v, s)
            n_pix = int(np.count_nonzero(mask))
            frac = n_pix / total
            cc, holes = count_holes(mask)
            print(f"{cls:>3} | {fname:<32} | {name:<8} | {v:>4} | {s:>4} | "
                  f"{n_pix:>7} | {frac:>6.3f} | {cc:>3} | {holes:>5}")

            if name in ("current", "loose_C"):
                outname = f"cls{cls}_{fname.replace('.png', '')}_{name}.png"
                cv2.imwrite(os.path.join(out_dir, outname), mask)

        print("-" * 110)

    print(f"\nMasks written to: {out_dir}")
    print("Visual check targets:")
    print("  1. Holes visible inside numerals (8 → 2 holes, 6 → 1 hole)")
    print("  2. Patch is ONE contiguous disk, not fragments")
    print("  3. No coloured ball surface leaking (no sphere visible)")
    print("  4. No cloth leakage (no teal patches at corners)")


if __name__ == "__main__":
    main()