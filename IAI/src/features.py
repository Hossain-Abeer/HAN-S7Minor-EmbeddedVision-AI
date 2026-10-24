"""
7.1 EXTRACT SHAPE FEATURES FROM NUMERAL-REGION MASK

For each mask in MASK_ROOT/<class>/, derive a fixed-length feature vector
describing the numeral geometry (hole_count, ratios, projections, ...).
Writes features.csv with one row per surviving mask.

Default feature set (7 categories = 23 sub-features):
  (a) hole_count                  1
  (b) connected_component_count   1
  (c) blob_area_ratio             1
  (f) hole_area_ratio             1
  (g) hole_aspect                 1
  (h) hole_centroid_dx, _dy       2
  (i) proj_x_0..7, proj_y_0..7   16
  --------------------------------
  Total                          23

Fallback features (toggled via USE_FEATURES in config.py):
  (d) blob_circularity
  (e) blob_aspect
  (j) hu_moments

Design reference: designtracker-1.5.2
Run from repo root:
    python src/features.py

Output:
    config.FEATURES_CSV  (~/features.csv)
    columns: filename | <features...>
    filename is the CROP name (mask-suffix stripped) so that 1.5.3's
    inner join against splits.csv succeeds.
"""

import os
import csv
import cv2
import numpy as np

import config
import constants as C


KNOWN_FEATURES = {
    "hole_count",
    "connected_component_count",
    "blob_area_ratio",
    "blob_circularity",
    "blob_aspect",
    "hole_area_ratio",
    "hole_aspect",
    "hole_centroid",
    "projections",
    "hu_moments",
}


def check_use_features(use_features):
    """Warn on unknown feature names; return list of unknowns."""
    unknown = [f for f in use_features if f not in KNOWN_FEATURES]
    if unknown:
        print(f"[WARN] Unknown features in USE_FEATURES: {unknown}")
        print(f"[WARN] Known: {sorted(KNOWN_FEATURES)}")
    return unknown


def largest_blob(mask):
    """Return (blob_mask_uint8, stats_row) for the largest non-background component."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return None, None
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    blob = (labels == idx).astype(np.uint8) * 255
    return blob, stats[idx]


def find_holes(blob_mask, min_area_px):
    """Return list of stats rows for holes (background components NOT touching border)."""
    inv = cv2.bitwise_not(blob_mask)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, 8)
    h, w = blob_mask.shape
    holes = []
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        if x == 0 or y == 0 or x + ww == w or y + hh == h:
            continue
        if area < min_area_px:
            continue
        holes.append(stats[i])
    return holes


def projections_binned(blob_mask, n_bins, blob_area):
    """Return (x_bins, y_bins), each length n_bins, normalised by blob_area."""
    col_sums = (blob_mask > 0).sum(axis=0).astype(float)
    row_sums = (blob_mask > 0).sum(axis=1).astype(float)
    x_chunks = np.array_split(col_sums, n_bins)
    y_chunks = np.array_split(row_sums, n_bins)
    x_bins = np.array([c.sum() for c in x_chunks]) / max(1.0, blob_area)
    y_bins = np.array([c.sum() for c in y_chunks]) / max(1.0, blob_area)
    return x_bins, y_bins


def features_from_mask(mask, use_features, proj_bins, keep_hu, min_hole_area):
    """Return dict of {feature_name: value}, or None if mask unusable."""
    blob, blob_stat = largest_blob(mask)
    if blob is None:
        return None

    h, w = mask.shape
    crop_area = float(h * w)
    blob_area = float(blob_stat[cv2.CC_STAT_AREA])
    bw = float(blob_stat[cv2.CC_STAT_WIDTH])
    bh = float(blob_stat[cv2.CC_STAT_HEIGHT])

    feats = {}

    # (a) hole_count
    holes = find_holes(blob, min_hole_area)
    if "hole_count" in use_features:
        feats["hole_count"] = len(holes)

    # (b) connected_component_count on the full mask
    if "connected_component_count" in use_features:
        n_cc, _, _, _ = cv2.connectedComponentsWithStats(mask, 8)
        feats["connected_component_count"] = n_cc - 1

    # (c) blob_area_ratio
    if "blob_area_ratio" in use_features:
        feats["blob_area_ratio"] = blob_area / crop_area

    # (d) blob_circularity (fallback)
    if "blob_circularity" in use_features:
        contours, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        per = cv2.arcLength(contours[0], True) if contours else 0.0
        feats["blob_circularity"] = (
            4.0 * np.pi * blob_area / (per ** 2) if per > 0 else 0.0
        )

    # (e) blob_aspect (fallback)
    if "blob_aspect" in use_features:
        feats["blob_aspect"] = bw / max(1.0, bh)

    # (f)-(h) hole-derived
    if holes:
        hx, hy, hw, hh, harea = max(holes, key=lambda s: s[cv2.CC_STAT_AREA])

        if "hole_area_ratio" in use_features:
            feats["hole_area_ratio"] = float(harea) / blob_area
        if "hole_aspect" in use_features:
            feats["hole_aspect"] = float(hw) / max(1.0, hh)
        if "hole_centroid" in use_features:
            blob_cx = blob_stat[cv2.CC_STAT_LEFT] + bw / 2.0
            blob_cy = blob_stat[cv2.CC_STAT_TOP] + bh / 2.0
            hole_cx = hx + hw / 2.0
            hole_cy = hy + hh / 2.0
            feats["hole_centroid_dx"] = (hole_cx - blob_cx) / max(1.0, bw)
            feats["hole_centroid_dy"] = (hole_cy - blob_cy) / max(1.0, bh)
    else:
        if "hole_area_ratio" in use_features:
            feats["hole_area_ratio"] = 0.0
        if "hole_aspect" in use_features:
            feats["hole_aspect"] = 0.0
        if "hole_centroid" in use_features:
            feats["hole_centroid_dx"] = 0.0
            feats["hole_centroid_dy"] = 0.0

    # (i) projections
    if "projections" in use_features:
        xb, yb = projections_binned(blob, proj_bins, blob_area)
        for i, v in enumerate(xb):
            feats[f"proj_x_{i}"] = float(v)
        for i, v in enumerate(yb):
            feats[f"proj_y_{i}"] = float(v)

    # (j) Hu moments on the largest hole (fallback; OFF by default)
    if keep_hu and "hu_moments" in use_features and holes:
        hx, hy, hw, hh, harea = max(holes, key=lambda s: s[cv2.CC_STAT_AREA])
        inv = cv2.bitwise_not(blob)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, 8)
        hole_label = None
        for i in range(1, n):
            x, y, ww, hh2, area = stats[i]
            if (x, y, ww, hh2, area) == (hx, hy, hw, hh, harea):
                hole_label = i
                break
        if hole_label is not None:
            hole_mask = (labels == hole_label).astype(np.uint8) * 255
            hu = cv2.HuMoments(cv2.moments(hole_mask)).flatten()
            hu_scaled = -np.sign(hu) * np.log10(np.abs(hu) + 1e-12)
            for i, v in enumerate(hu_scaled):
                feats[f"hu_{i}"] = float(v)
        else:
            for i in range(7):
                feats[f"hu_{i}"] = 0.0

    return feats


def build_features(mask_root, class_ids, out_csv,
                   use_features, proj_bins, keep_hu, min_hole_area):
    """Walk mask folders, extract features per mask, write features.csv."""
    rows = []

    for cid in class_ids:
        folder = os.path.join(mask_root, str(cid))
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.lower().endswith(".png"):
                continue
            mask = cv2.imread(os.path.join(folder, fname),
                              cv2.IMREAD_GRAYSCALE)
            if mask is None:
                continue
            mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]

            feats = features_from_mask(mask, use_features, proj_bins,
                                       keep_hu, min_hole_area)
            if feats is None:
                continue

            # Strip the _mask suffix so filename matches splits.csv
            # (which uses the original crop filename). Required for the
            # inner join at 1.5.3.
            if fname.endswith("_mask.png"):
                base = fname[:-len("_mask.png")]
            else:
                base = fname
            row = {"filename": f"{cid}/{base}.png"}
            row.update(feats)
            rows.append(row)

    if not rows:
        print("[WARN] no feature rows produced; check config.MASK_ROOT")
        with open(out_csv, "w", newline="") as f:
            f.write("filename\n")
        return 0

    fieldnames = ["filename"] + sorted(
        k for k in rows[0].keys() if k != "filename"
    )

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    return len(rows)


def main():
    unknown = check_use_features(config.USE_FEATURES)
    if unknown:
        print("[WARN] Proceeding with known subset only.")

    n = build_features(
        config.MASK_ROOT,
        C.CLASS_IDS,
        config.FEATURES_CSV,
        config.USE_FEATURES,
        config.PROJ_BINS,
        config.KEEP_HU_MOMENTS,
        config.MIN_HOLE_AREA_PX,
    )
    print(f"[DONE] wrote {n} rows to {config.FEATURES_CSV}")


if __name__ == "__main__":
    main()