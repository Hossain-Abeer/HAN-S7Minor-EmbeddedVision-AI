"""
4.3 AUDIT CLASS BALANCE

Reads class folders under unsorted_png/, counts PNGs per class, prints a
fixed-width table, and flags any class below MIN_CROPS_PER_CLASS.

Imports:
    config    -> CROP_ROOT, LOGS_DIR
    constants -> CLASS_IDS, MIN_CROPS_PER_CLASS

Run from repo root:
    python src/audit.py

Output:
    Console table
    logs/1.3.5_class_count.txt (via Tee, always written)
"""

import os
import sys

import config
import constants as C


def count_per_class(crop_root, class_ids):
    """
    Return dict {class_id: file_count} for PNG files in each class folder.
    Missing folder -> count 0 (does not raise).
    """
    counts = {}
    for cid in class_ids:
        folder = os.path.join(crop_root, str(cid))
        if not os.path.isdir(folder):
            counts[cid] = 0
            continue
        n = sum(
            1
            for f in os.listdir(folder)
            if f.lower().endswith(".png")
        )
        counts[cid] = n
    return counts


def report_counts(counts, min_per_class):
    """
    Print a fixed-width table and flag under-delivering classes.
    Returns the list of SHORT class ids.
    """
    print(f"{'class':>6} | {'count':>6} | status")
    print("-" * 30)

    short_classes = []
    for cid in sorted(counts):
        n = counts[cid]
        flag = "OK" if n >= min_per_class else "SHORT"
        if flag == "SHORT":
            short_classes.append(cid)
        print(f"{cid:>6} | {n:>6} | {flag}")

    total = sum(counts.values())
    mn = min(counts.values())
    mx = max(counts.values())

    print("-" * 30)
    print(
        f"total = {total} | min = {mn} | max = {mx} | "
        f"threshold = {min_per_class}"
    )

    if short_classes:
        print(f"\nSHORT classes ({len(short_classes)}/{len(counts)}): "
              f"{short_classes}")
        print("Note: FRAME_STRIDE is already 1; further stride-tightening")
        print("is a non-lever under the motion-gated architecture.")
        print("Document as limitation and proceed to 5.1.")
    else:
        print("\nAll classes meet threshold. Proceed to 5.1.")

    return short_classes


def _tee_stdout(log_path):
    """
    Mirror stdout to both the console and a log file.
    Creates parent dirs if absent.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    log_file = open(log_path, "w")

    class _Tee:
        def write(self, s):
            log_file.write(s)
            sys.__stdout__.write(s)

        def flush(self):
            log_file.flush()
            sys.__stdout__.flush()

    sys.stdout = _Tee()


def main():
    log_path = os.path.join(config.LOGS_DIR, "audit_class_count.txt")
    _tee_stdout(log_path)

    counts = count_per_class(config.CROP_ROOT, C.CLASS_IDS)
    report_counts(counts, C.MIN_CROPS_PER_CLASS)


if __name__ == "__main__":
    main()