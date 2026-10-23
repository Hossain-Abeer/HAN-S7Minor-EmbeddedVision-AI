"""
5.3 VERIFY STRATIFIED SPLITTING

Reads splits.csv. Prints a per-role / per-class count matrix.
Flags:
  - Zero cells (hard failure for val/test)
  - Below hard floor: train < 5, val/test < 1
  - Below soft target: val/test < 3

Design reference: designtracker-1.4.2

Run from repo root:
    python src/verify_split.py

Output:
  Console matrix
  logs/1.4.2_stratification.txt (via Tee)
"""

import os
import csv
import sys

import config
import constants as C

HARD_FLOOR_TRAIN   = 5
HARD_FLOOR_VALTEST = 1
SOFT_TARGET_VALTEST = 3
ROLES = ("train", "val", "test")


def _tee_stdout(log_path):
    """Mirror stdout to log file and console. Same pattern as 1.7.1/4.3."""
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


def load_splits(splits_csv):
    """Return list of (relative_filename, role)."""
    rows = []
    with open(splits_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((r["filename"], r["role"]))
    return rows


def class_from_filename(rel_path):
    """
    Extract class id from the 'cid/fname.png' prefix.
    Returns int or None if malformed.
    """
    prefix = rel_path.split("/")[0]
    try:
        return int(prefix)
    except ValueError:
        return None


def build_matrix(rows, class_ids):
    """
    Return {role: {class_id: count}} with all cells initialized to 0.
    Roles missing from splits.csv appear as all-zero rows.
    """
    matrix = {role: {cid: 0 for cid in class_ids} for role in ROLES}
    for rel_path, role in rows:
        cid = class_from_filename(rel_path)
        if cid is None or cid not in class_ids:
            continue
        if role not in matrix:
            continue
        matrix[role][cid] += 1
    return matrix


def print_matrix(matrix, class_ids):
    """Print the 15-row x 3-role count matrix, with totals."""
    header = f"{'class':>6} | " + " | ".join(f"{r:>6}" for r in ROLES)
    print(header)
    print("-" * len(header))
    for cid in class_ids:
        line = f"{cid:>6} | " + " | ".join(
            f"{matrix[r][cid]:>6}" for r in ROLES
        )
        print(line)
    print("-" * len(header))
    totals = {r: sum(matrix[r].values()) for r in ROLES}
    print(f"{'total':>6} | " + " | ".join(f"{totals[r]:>6}" for r in ROLES))


def check_floors(matrix, class_ids):
    """
    Return (hard_failures, soft_failures).

    Each failure is a tuple (role, class_id, count, reason_str).
    """
    hard_failures = []
    soft_failures = []
    for role in ROLES:
        for cid in class_ids:
            n = matrix[role][cid]
            if role == "train":
                if n < HARD_FLOOR_TRAIN:
                    hard_failures.append(
                        (role, cid, n, f"train < {HARD_FLOOR_TRAIN}")
                    )
            else:
                if n < HARD_FLOOR_VALTEST:
                    hard_failures.append(
                        (role, cid, n,
                         f"{role} < {HARD_FLOOR_VALTEST} (zero cell)")
                    )
                elif n < SOFT_TARGET_VALTEST:
                    soft_failures.append(
                        (role, cid, n,
                         f"{role} < {SOFT_TARGET_VALTEST} (soft target)")
                    )
    return hard_failures, soft_failures


def report_failures(hard_failures, soft_failures):
    print()
    if not hard_failures and not soft_failures:
        print("All roles meet hard floors and soft targets. "
              "Proceed to 6.1.")
        return

    if hard_failures:
        print(f"HARD FAILURES ({len(hard_failures)}):")
        for role, cid, n, reason in hard_failures:
            print(f"  {role:>6} class {cid:>2}: n={n:>2} ({reason})")
        print()
        print("Note: FRAME_STRIDE is already 1 under the motion-gated")
        print("architecture. Standard escalation (stride 5->3) is a")
        print("non-lever. Options:")
        print("  1. Re-run assign_roles with rare-class preference.")
        print("  2. Narrow classifier scope to fully-covered classes.")
        print("  3. Document as limitation and proceed.")

    if soft_failures:
        print()
        print(f"SOFT TARGET MISSES ({len(soft_failures)}):")
        for role, cid, n, reason in soft_failures:
            print(f"  {role:>6} class {cid:>2}: n={n:>2} ({reason})")
        print()
        print("Soft misses are NON-BLOCKING. Document in Preliminary ML §3")
        print("as a known limitation (thin val/test cells for those classes).")


def main():
    log_path = os.path.join(config.LOGS_DIR, "verify_split_log.txt")
    _tee_stdout(log_path)

    rows = load_splits(config.SPLITS_CSV)
    print(f"[INFO] read {len(rows)} rows from {config.SPLITS_CSV}")

    matrix = build_matrix(rows, C.CLASS_IDS)
    print("\nPer-role / per-class count matrix:")
    print_matrix(matrix, C.CLASS_IDS)

    hard_failures, soft_failures = check_floors(matrix, C.CLASS_IDS)
    report_failures(hard_failures, soft_failures)


if __name__ == "__main__":
    main()