"""
6.1 EXTRACT NUMERAL-REGION MASK PER CROP

For each crop in CROP_ROOT/<class>/, extract a binary mask that isolates
the numeral region:
  - HSV high-V, low-S threshold  (whitish pixels)
  - intersect with non-cloth     (reuse CLOTH_* bounds from constants.py)
  - morphology OPEN only         (CLOSE must stay 0 to preserve holes)

Output: parallel tree under MASK_ROOT/<class>/<name>_mask.png
Rejects (mask too small): logged to MASK_REJECT_LOG, skipped.

Design reference: designtracker-1.5.1
Run from repo root:
    python src/mask.py

Dry run (caps total crops processed to N):
    PowerShell:
        $env:EVML_DRY_RUN_CROPS="20"; python src/mask.py; Remove-Item Env:EVML_DRY_RUN_CROPS
"""

import os
import csv
import cv2
import numpy as np

import config
import constants as C


def extract_numeral_mask(crop_bgr):
    """
    Return a uint8 binary mask (0/255).
    Isolates bright, low-saturation pixels (the white patch bearing the
    numeral) while excluding cloth-coloured pixels.
    """
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)

    # (a) high-V, low-S: the whitish patch that carries the numeral
    white_lo = np.array([0,   0,           config.MASK_V_MIN])
    white_hi = np.array([179, config.MASK_S_MAX, 255])
    mask = cv2.inRange(hsv, white_lo, white_hi)

    # (b) intersect with non-cloth pixels
    cloth_lo = np.array([C.CLOTH_H_LO, C.CLOTH_S_LO, C.CLOTH_V_LO])
    cloth_hi = np.array([C.CLOTH_H_HI, C.CLOTH_S_HI, C.CLOTH_V_HI])
    cloth    = cv2.inRange(hsv, cloth_lo, cloth_hi)
    valid    = cv2.bitwise_not(cloth)
    mask     = cv2.bitwise_and(mask, valid)

    # (c) morphology: OPEN only. CLOSE must stay 0 (would fill numeral holes).
    if config.MASK_MORPH_KERNEL > 0:
        k = np.ones((config.MASK_MORPH_KERNEL, config.MASK_MORPH_KERNEL),
                    np.uint8)
        if config.MASK_MORPH_OPEN > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k,
                                    iterations=config.MASK_MORPH_OPEN)
        if config.MASK_MORPH_CLOSE > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k,
                                    iterations=config.MASK_MORPH_CLOSE)

    return mask


def mask_is_usable(mask):
    return int(np.count_nonzero(mask)) >= config.MIN_MASK_AREA


def log_reject(class_id, filename, n_pixels):
    new_file = not os.path.exists(config.MASK_REJECT_LOG)
    with open(config.MASK_REJECT_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["reason", "class_id", "filename", "n_pixels"])
        w.writerow(["small_mask", class_id, filename, n_pixels])


def build_masks(crop_root, mask_root, class_ids, dry_run_crops=0):
    total = 0
    written = 0
    rejected = 0

    for cid in class_ids:
        src_dir = os.path.join(crop_root, str(cid))
        if not os.path.isdir(src_dir):
            continue
        out_dir = os.path.join(mask_root, str(cid))
        os.makedirs(out_dir, exist_ok=True)

        for fname in sorted(os.listdir(src_dir)):
            if not fname.lower().endswith(".png"):
                continue
            if fname.endswith("_mask.png"):
                continue
            if dry_run_crops and total >= dry_run_crops:
                return total, written, rejected

            crop = cv2.imread(os.path.join(src_dir, fname))
            total += 1

            if crop is None:
                print(f"[WARN] read fail: {cid}/{fname}")
                rejected += 1
                continue

            mask = extract_numeral_mask(crop)

            if not mask_is_usable(mask):
                log_reject(cid, fname, int(np.count_nonzero(mask)))
                rejected += 1
                continue

            base, _ = os.path.splitext(fname)
            out_path = os.path.join(out_dir, f"{base}_mask.png")
            if cv2.imwrite(out_path, mask):
                written += 1
            else:
                print(f"[WARN] imwrite fail: {out_path}")
                rejected += 1

    return total, written, rejected


def main():
    # Truncate reject log at start of each run
    if os.path.exists(config.MASK_REJECT_LOG):
        os.remove(config.MASK_REJECT_LOG)

    dry_run_crops = int(os.environ.get("EVML_DRY_RUN_CROPS", "0"))

    total, written, rejected = build_masks(
        config.CROP_ROOT, config.MASK_ROOT, C.CLASS_IDS,
        dry_run_crops=dry_run_crops,
    )
    print(f"[DONE] total={total} written={written} rejected={rejected}")


if __name__ == "__main__":
    main()