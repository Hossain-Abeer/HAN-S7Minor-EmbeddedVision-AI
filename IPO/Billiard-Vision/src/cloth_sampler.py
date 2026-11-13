"""
0.5 cloth HSV calibration utility.

Calibration ONLY. Not called by the C++ runtime pipeline.
Resolves D-CAVEAT-2: samples mid-cloth pixels from the reference PNG,
excluding the cue-ball and shadow ROIs, and prints min/max/mean per HSV
channel so CLOTH_*_LO/HI can be set in src/config.h with a documented
widening margin (H +-5, S +-10, V +-10).

Writes: DATA_ROOT/IPO/logs/0.5_cloth_samples.txt
"""
import os
import cv2
import numpy as np

DATA_ROOT = "D:/HAN/Semester 7 Minor/billiards-game-clips"
IMG       = f"{DATA_ROOT}/game1/clothColor_noAspectRatio.png"
OUT_LOG   = f"{DATA_ROOT}/IPO/logs/0.5_cloth_samples.txt"

CUE_BALL_BOX = (848, 149, 881, 182)   # x0,y0,x1,y1
SHADOW_BOX   = (79, 558, 87, 575)

SAMPLE_PTS = [(200,200),(500,200),(300,400),(700,400),
              (400,300),(600,500),(900,450)]

def in_box(x, y, box):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1

def main():
    img = cv2.imread(IMG)
    if img is None:
        raise SystemExit(f"cannot read {IMG}")
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    rows = []
    for x, y in SAMPLE_PTS:
        if in_box(x, y, CUE_BALL_BOX) or in_box(x, y, SHADOW_BOX):
            continue
        h, s, v = hsv[y, x]
        rows.append((x, y, int(h), int(s), int(v)))
        print(f"({x},{y}) -> H={h} S={s} V={v}")

    if not rows:
        raise SystemExit("no valid sample points survived exclusions")

    arr = np.array([r[2:] for r in rows])
    lo, hi, mean = arr.min(axis=0), arr.max(axis=0), arr.mean(axis=0)

    summary = (
        f"samples={len(rows)}\n"
        f"H min/max/mean = {lo[0]}/{hi[0]}/{mean[0]:.1f}\n"
        f"S min/max/mean = {lo[1]}/{hi[1]}/{mean[1]:.1f}\n"
        f"V min/max/mean = {lo[2]}/{hi[2]}/{mean[2]:.1f}\n"
        f"widened: H {max(0,lo[0]-5)}..{min(179,hi[0]+5)}  "
        f"S {max(0,lo[1]-10)}..{min(255,hi[1]+10)}  "
        f"V {max(0,lo[2]-10)}..{min(255,hi[2]+10)}\n"
    )
    print(summary)

    os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)
    with open(OUT_LOG, "w") as f:
        f.write(summary)
    print(f"written: {OUT_LOG}")

if __name__ == "__main__":
    main()



    