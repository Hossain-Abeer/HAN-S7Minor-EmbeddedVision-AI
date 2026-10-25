"""
7.3 ASSEMBLE FEATURE MATRIX + LABELS + ROLES

Inner-joins features.csv (from 7.2) with splits.csv (from 5.2) on filename,
extracts label from the filename prefix, and writes dataset.csv.

Design reference: designtracker-1.5.3

Run from repo root:
    python src/assemble.py

Output:
    config.DATASET_CSV  (~/dataset.csv)
      columns: filename | label | role | <23 features>
    logs/1.5.3_join_report.txt (via Tee)
"""

import os
import sys
import pandas as pd

import config
import constants as C

FEATURE_COLUMNS = [
    "hole_count",
    "connected_component_count",
    "blob_area_ratio",
    "hole_area_ratio",
    "hole_aspect",
    "hole_centroid_dx",
    "hole_centroid_dy",
    "proj_x_0", "proj_x_1", "proj_x_2", "proj_x_3",
    "proj_x_4", "proj_x_5", "proj_x_6", "proj_x_7",
    "proj_y_0", "proj_y_1", "proj_y_2", "proj_y_3",
    "proj_y_4", "proj_y_5", "proj_y_6", "proj_y_7",
]

ROLES = ("train", "val", "test")


def _tee_stdout(log_path):
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


def assemble_dataset(features_csv, splits_csv, dataset_csv, feature_columns):
    df_feat   = pd.read_csv(features_csv)
    df_splits = pd.read_csv(splits_csv)

    n_feat   = len(df_feat)
    n_splits = len(df_splits)

    df = df_feat.merge(df_splits, on="filename", how="inner")
    n_merged = len(df)

    df["label"] = df["filename"].str.split("/").str[0].astype(int)

    cols    = ["filename", "label", "role"] + feature_columns
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns after merge: {missing}")
    df = df[cols]

    df.to_csv(dataset_csv, index=False)

    print(f"[INFO] features.csv rows:   {n_feat}")
    print(f"[INFO] splits.csv rows:     {n_splits}")
    print(f"[INFO] merged (inner join): {n_merged}")
    print(f"[INFO] dropped:             {n_splits - n_merged}")
    print(f"[INFO] dataset.csv columns: {len(df.columns)} "
          f"(3 meta + {len(feature_columns)} features)")

    pivot = df.groupby(["role", "label"]).size().unstack(fill_value=0)
    for r in ROLES:
        if r not in pivot.index:
            pivot.loc[r] = 0
    for cid in C.CLASS_IDS:
        if cid not in pivot.columns:
            pivot[cid] = 0
    pivot = pivot[sorted(pivot.columns)]
    pivot = pivot.loc[[r for r in ROLES if r in pivot.index]]

    print("\nPer-role / per-class counts (post-join):")
    print(pivot.to_string())

    totals = pivot.sum(axis=0)
    print(f"\ntotal per class: {dict(totals)}")
    print(f"total samples:   {int(totals.sum())}")

    zero_cells = []
    for role in ROLES:
        if role not in pivot.index:
            continue
        for cid in C.CLASS_IDS:
            if pivot.loc[role, cid] == 0:
                zero_cells.append((role, cid))

    if zero_cells:
        print("\n[HARD] zero cells post-join (role, class):")
        for role, cid in zero_cells:
            print(f"  {role} class {cid}: n=0")
        print("Action: 1.5.1 reject log may have hit thin classes. "
              "Consider 5.2 fallback or scope narrowing.")
    else:
        print("\n[OK] no zero cells post-join. Dataset integrity intact.")

    return df


def main():
    log_path = os.path.join(config.LOGS_DIR, "1.5.3_join_report.txt")
    _tee_stdout(log_path)

    assemble_dataset(
        config.FEATURES_CSV,
        config.SPLITS_CSV,
        config.DATASET_CSV,
        FEATURE_COLUMNS,
    )
    print(f"\n[INFO] wrote {config.DATASET_CSV}")


if __name__ == "__main__":
    main()