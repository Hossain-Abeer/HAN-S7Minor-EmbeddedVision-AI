"""
5.1 SPLIT INTO TRAIN / VALIDATION / TEST

Group-by-clip split: whole clips assigned to roles.
  - Method: group-by-clip (not file-level random)
  - Ratio:  3 train / 1 val / 1 test
  - Rule:   best-coverage clip -> val, second -> test, rest -> train
  - Output: config.SPLITS_CSV with columns filename, role

Design reference: designtracker-1.4.1

Run from repo root:
    python src/split.py
"""

import os
import csv
import re
from collections import defaultdict

import config
import constants as C

# Filename convention from 1.3.2:
#   clip{id}_frame{idx:06d}_ball{k}.png
CLIP_ID_REGEX = re.compile(r"clip(\d+)_frame(\d+)_ball(\d+)")


def scan_crops(crop_root, class_ids):
    """
    Walk each class folder and return a list of
    (relative_filename, label, clip_id) tuples.

    relative_filename format: "<class>/<fname>.png"
    """
    records = []
    for cid in class_ids:
        folder = os.path.join(crop_root, str(cid))
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.lower().endswith(".png"):
                continue
            match = CLIP_ID_REGEX.search(fname)
            if not match:
                continue  # malformed filename; skip
            clip_id = int(match.group(1))
            rel_path = f"{cid}/{fname}"
            records.append((rel_path, cid, clip_id))
    return records


def score_clips_by_coverage(records):
    """
    Return {clip_id: (classes_covered, min_count_across_covered)}.

    Higher tuple = better coverage.
    Sorting on this tuple ranks clips by how many classes they can
    contribute and how thinly the rarest such class is represented.
    """
    counts = defaultdict(lambda: defaultdict(int))  # clip -> class -> count
    for _, label, clip_id in records:
        counts[clip_id][label] += 1

    scores = {}
    for clip_id, per_class in counts.items():
        covered = len(per_class)
        min_count = min(per_class.values()) if per_class else 0
        scores[clip_id] = (covered, min_count)
    return scores


def assign_roles(scores):
    """
    Rank clips by (classes_covered, min_count) descending.
    Rank 0 -> val, rank 1 -> test, ranks 2+ -> train.

    Tie-break: clip_id ascending (deterministic; no random seed).
    """
    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]),
    )
    roles = {}
    for rank, (clip_id, _) in enumerate(ranked):
        if rank == 0:
            roles[clip_id] = "val"
        elif rank == 1:
            roles[clip_id] = "test"
        else:
            roles[clip_id] = "train"
    return roles


def write_splits_csv(records, roles, out_path):
    """
    Write splits CSV: header + one row per crop.
    Columns: filename, role.
    """
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "role"])
        for rel_path, _label, clip_id in records:
            writer.writerow([rel_path, roles[clip_id]])


def coverage_matrix(records):
    """
    Diagnostic helper: {clip_id: {class_id: count}}.
    Used only by main() to pre-warn about zero cells before 5.3.
    """
    matrix = defaultdict(lambda: defaultdict(int))
    for _, label, clip_id in records:
        matrix[clip_id][label] += 1
    return matrix


def main():
    records = scan_crops(config.CROP_ROOT, C.CLASS_IDS)
    print(f"[INFO] scanned {len(records)} crops across {len(C.CLASS_IDS)} classes")

    if not records:
        print("[WARN] no crops found; check config.CROP_ROOT")
        return

    scores = score_clips_by_coverage(records)
    roles = assign_roles(scores)

    # --- Diagnostic: ranked clip coverage scores ---
    print("\nClip coverage scores (ranked):")
    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]),
    )
    for clip_id, (covered, min_count) in ranked:
        print(
            f"  clip {clip_id}: classes_covered={covered:>2}, "
            f"min_count={min_count:>2}, role={roles[clip_id]}"
        )

    # --- Diagnostic: pre-5.3 zero-cell warning ---
    cm = coverage_matrix(records)
    role_classes = {"train": set(), "val": set(), "test": set()}
    for clip_id, role in roles.items():
        for cls, n in cm[clip_id].items():
            if n > 0:
                role_classes[role].add(cls)

    print("\nPer-role class coverage (pre-5.3 check):")
    any_missing = False
    for role in ("train", "val", "test"):
        covered = role_classes[role]
        missing = [c for c in C.CLASS_IDS if c not in covered]
        if missing:
            any_missing = True
            print(f"  {role}: {len(covered)}/{len(C.CLASS_IDS)} classes "
                  f"(MISSING: {missing})")
        else:
            print(f"  {role}: all {len(C.CLASS_IDS)} classes covered")
    if any_missing:
        print("  [NOTE] 5.3 will flag these as zero cells. "
              "If unrecoverable, document as limitation and scope the "
              "classifier to the fully-covered classes.")

    # --- Write CSV ---
    write_splits_csv(records, roles, config.SPLITS_CSV)
    print(f"\n[INFO] wrote {config.SPLITS_CSV}")


if __name__ == "__main__":
    main()