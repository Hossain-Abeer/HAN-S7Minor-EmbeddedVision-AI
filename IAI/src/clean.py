"""
9.1 DATA CLEANING (MISSING VALUES, OUTLIERS)

Loads dataset.csv and retained_features_correlations.txt.
Checks for NaN. Computes IQR bounds on TRAIN only. Clips outliers.
Verifies projection sum-to-1 invariant.
Saves dataset_clean.csv and logs/1.7.1_cleaning_report.txt.

Design reference: designtracker-1.7.1 (R1 corrections applied)
"""

import os
import sys
import pandas as pd
import numpy as np

import config

# ============================================================================
# [PARAMETERS - FILL IN BEFORE RUN]
# ============================================================================
DATASET_CSV      = config.DATASET_CSV
RETAINED_TXT     = os.path.join(config.DATA_ROOT, "retained_features_correlations.txt")
OUT_DIR          = config.DATA_ROOT
LOG_PATH         = os.path.join(config.LOGS_DIR, "1.7.1_cleaning_report.txt")

CLIP_OR_REMOVE   = "clip"   # "clip" | "remove" | "keep"
MIN_IQR_FLOOR    = 1e-6
IQR_K            = 1.5

# EXCLUDE discrete features and structural bounded-sum features
EXCLUDED_FEATURES = [
    "connected_component_count",
    "proj_x_0", "proj_x_1", "proj_x_2", "proj_x_3", "proj_x_4", "proj_x_5", "proj_x_6",
    "proj_y_1", "proj_y_2", "proj_y_3", "proj_y_4", "proj_y_5", "proj_y_6",
]

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

def clean_data():
    df = pd.read_csv(DATASET_CSV)
    
    # Load retained features
    if not os.path.exists(RETAINED_TXT):
        raise FileNotFoundError(f"Missing {RETAINED_TXT}. Run 8.3 first.")
    with open(RETAINED_TXT, "r") as f:
        retained = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
    feats = [f for f in retained if f in df.columns]
    missing_cols = [f for f in retained if f not in df.columns]
    if missing_cols:
        print(f"[WARNING] retained_features.txt lists absent columns: {missing_cols}")
        
    print(f"[INFO] Cleaning {len(feats)} retained feature columns.")

    # 1. Missing values check
    nan_counts = df[feats].isna().sum()
    print("\nMissing values per column (retained set):")
    print(nan_counts.to_string())

    # 2. Outlier detection setup
    cleanable = [f for f in feats if f not in EXCLUDED_FEATURES]
    print(f"\n[INFO] Cleanable features ({len(cleanable)}): {cleanable}")
    print(f"[INFO] Excluded from outlier detection ({len(EXCLUDED_FEATURES)}): {EXCLUDED_FEATURES}")

    if not cleanable:
        print("[INFO] No features to clean.")
        return

    # Derive thresholds from TRAIN only
    train_df = df[df["role"] == "train"]
    q1 = train_df[cleanable].quantile(0.25)
    q3 = train_df[cleanable].quantile(0.75)
    iqr = q3 - q1
    
    # Guard against IQR = 0
    iqr_safe = iqr.clip(lower=MIN_IQR_FLOOR)
    if (iqr < MIN_IQR_FLOOR).any():
        warned = list(iqr[iqr < MIN_IQR_FLOOR].index)
        print(f"\n[WARNING] IQR near zero for: {warned}. Widened to floor {MIN_IQR_FLOOR}.")

    lower = q1 - IQR_K * iqr_safe
    upper = q3 + IQR_K * iqr_safe

    # Apply bounds to all roles
    outlier_mask = (df[cleanable] < lower) | (df[cleanable] > upper)
    print("\nOutliers per cleanable column (bounds from train):")
    print(outlier_mask.sum().to_string())

    # 3. Handle outliers
    if CLIP_OR_REMOVE == "clip":
        df[cleanable] = df[cleanable].clip(lower=lower, upper=upper, axis=1)
        
        # Verify invariant explicitly per axis
        proj_x_cols = [c for c in feats if c.startswith("proj_x_")]
        proj_y_cols = [c for c in feats if c.startswith("proj_y_")]
        
        if proj_x_cols:
            sx = df[proj_x_cols].sum(axis=1)
            assert np.allclose(sx, 1.0, atol=1e-3), f"proj_x sum broken. Min: {sx.min()}, Max: {sx.max()}"
        if proj_y_cols:
            sy = df[proj_y_cols].sum(axis=1)
            assert np.allclose(sy, 1.0, atol=1e-3), f"proj_y sum broken. Min: {sy.min()}, Max: {sy.max()}"
            
        print("[OK] Projection sum-to-1 invariants hold.")
            
        out_path = os.path.join(OUT_DIR, "dataset_clean.csv")
        df.to_csv(out_path, index=False)
        print(f"\n[INFO] Clipped columns. Wrote {out_path}")

    elif CLIP_OR_REMOVE == "remove":
        keep = ~outlier_mask.any(axis=1)
        out_path = os.path.join(OUT_DIR, "dataset_clean.csv")
        df[keep].to_csv(out_path, index=False)
        print(f"\n[INFO] Removed {int((~keep).sum())} rows. Wrote {out_path}")

    else:
        print("\n[INFO] Outliers kept. dataset.csv continues unchanged.")

def main():
    _tee_stdout(LOG_PATH)
    clean_data()
    print(f"\n[INFO] log: {LOG_PATH}")

if __name__ == "__main__":
    main()