"""
9.2 FEATURE SCALING

Loads dataset_clean.csv and retained_features.txt. Fits StandardScaler on
train rows only, transforms all roles. Saves before/after histograms and
scaled CSVs for inspection.

Design reference: designtracker-1.7.2
Run from repo root:
    python src/scale.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

import config

# Paths
DATASET_CSV  = os.path.join(config.DATA_ROOT, "dataset_clean.csv")
RETAINED_TXT = os.path.join(config.DATA_ROOT, "retained_features_correlations.txt")
OUT_DIR      = config.DATA_ROOT
FIG_DIR      = os.path.join(config.FIGURES_DIR, "scaling")
LOG_PATH     = os.path.join(config.LOGS_DIR, "1.7.2_scaling_report.txt")

SAVE_SCALED_CSV = True  # Design B1: persist for inspection, do not re-feed


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


def scale_data():
    df = pd.read_csv(DATASET_CSV)
    with open(RETAINED_TXT, "r") as f:
        feats = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"[INFO] Scaling {len(feats)} retained feature columns.")

    train = df[df["role"] == "train"]
    val   = df[df["role"] == "val"]
    test  = df[df["role"] == "test"]

    X_train = train[feats]
    X_val   = val[feats]
    X_test  = test[feats]

    print(f"[INFO] Train rows: {len(X_train)}")
    print(f"[INFO] Val rows:   {len(X_val)}")
    print(f"[INFO] Test rows:  {len(X_test)}")

    # ========================================================================
    # FIT ON TRAIN ONLY
    # ========================================================================
    scaler = StandardScaler()
    scaler.fit(X_train)

    X_train_s = scaler.transform(X_train)
    X_val_s   = scaler.transform(X_val)
    X_test_s  = scaler.transform(X_test)

    # ========================================================================
    # REPORT LEARNED PARAMETERS
    # ========================================================================
    print("\nLearned per-feature mean and std (from train):")
    for f, mu, sd in zip(feats, scaler.mean_, scaler.scale_):
        print(f"  {f:30s}  mean={mu:+.4f}  std={sd:.4f}")

    # ========================================================================
    # BEFORE / AFTER HISTOGRAMS
    # ========================================================================
    os.makedirs(FIG_DIR, exist_ok=True)
    for i, f in enumerate(feats):
        fig, ax = plt.subplots(1, 2, figsize=(10, 3))

        ax[0].hist(X_train[f], bins=20, color="steelblue")
        ax[0].set_title(f"BEFORE: {f}")
        ax[0].set_xlabel("raw value")

        ax[1].hist(X_train_s[:, i], bins=20, color="darkorange")
        ax[1].set_title(f"AFTER: {f} (standard)")
        ax[1].set_xlabel("scaled value")

        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, f"scaling_{f}.png"), dpi=150)
        plt.close(fig)

    print(f"\n[INFO] Wrote before/after figures to {FIG_DIR}")

    # ========================================================================
    # OPTIONAL PERSIST (INSPECTION ONLY)
    # ========================================================================
    if SAVE_SCALED_CSV:
        for role_name, X_s in [("train", X_train_s), ("val", X_val_s), ("test", X_test_s)]:
            sub = df[df["role"] == role_name][["filename", "label", "role"]].copy()
            for j, f in enumerate(feats):
                sub[f] = X_s[:, j]
            
            out_path = os.path.join(OUT_DIR, f"dataset_{role_name}_scaled.csv")
            sub.to_csv(out_path, index=False)
            print(f"[INFO] Wrote {out_path}")
    else:
        print("[INFO] Scaled matrices kept in memory only.")


def main():
    _tee_stdout(LOG_PATH)
    scale_data()
    print(f"\n[INFO] log: {LOG_PATH}")


if __name__ == "__main__":
    main()