"""
8.3 COMPUTE CORRELATIONS

Computes feature-feature Pearson correlation and feature-label relevance
(ANOVA F + mutual info). Flags highly correlated pairs.
Saves corr_heatmap.png and feature_label_relevance.csv.

Design reference: designtracker-1.6.3
Run from repo root:
    python src/correlations.py
"""

import os
import sys
from turtle import clear
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_selection import f_classif, mutual_info_classif

import config
import constants as C

FEATURE_COLUMNS = [
    "hole_count", "connected_component_count", "blob_area_ratio",
    "hole_area_ratio", "hole_aspect", "hole_centroid_dx", "hole_centroid_dy",
    "proj_x_0", "proj_x_1", "proj_x_2", "proj_x_3", "proj_x_4", "proj_x_5", "proj_x_6", "proj_x_7",
    "proj_y_0", "proj_y_1", "proj_y_2", "proj_y_3", "proj_y_4", "proj_y_5", "proj_y_6", "proj_y_7",
]

REDUNDANCY_THR = 0.9
FIG_DPI = 150

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


def compute_correlations(dataset_csv, fig_dir, root_dir):
    df = pd.read_csv(dataset_csv)
    df = df[df["role"] == "train"]

    # 1. Feature-Feature Pearson Correlation
    corr = df[FEATURE_COLUMNS].corr(method="pearson")

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, square=True, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_title("Feature-feature correlation (train)")
    plt.tight_layout()
    out_png = os.path.join(fig_dir, "corr_heatmap.png")
    plt.savefig(out_png, dpi=FIG_DPI)
    plt.close(fig)
    print(f"[INFO] wrote {out_png}")

    # Flag redundant pairs
    flagged = []
    for i, a in enumerate(FEATURE_COLUMNS):
        for b in FEATURE_COLUMNS[i+1:]:
            if abs(corr.loc[a, b]) >= REDUNDANCY_THR:
                flagged.append((a, b, round(corr.loc[a, b], 3)))

    print(f"\nRedundant pairs (|r| >= {REDUNDANCY_THR}):")
    for a, b, r in flagged:
        print(f"  {a} <-> {b} : r = {r}")
    if not flagged:
        print("  (none)")

    # 2. Feature-Label Relevance
    X = df[FEATURE_COLUMNS].values
    y = df["label"].values

    f_scores, p_vals = f_classif(X, y)
    mi_scores       = mutual_info_classif(X, y, random_state=42)

    relevance = pd.DataFrame({
        "feature":   FEATURE_COLUMNS,
        "anova_F":   f_scores,
        "anova_p":   p_vals,
        "mut_info":  mi_scores,
    }).sort_values("mut_info", ascending=False)

    print("\nFeature-label relevance (sorted by mutual information):")
    print(relevance.to_string(index=False))

    out_csv = os.path.join(root_dir, "feature_label_relevance.csv")
    relevance.to_csv(out_csv, index=False)
    print(f"\n[INFO] wrote {out_csv}")

    return corr, relevance


def main():
    log_path = os.path.join(config.LOGS_DIR, "1.6.3_redundancy_flags.txt")
    _tee_stdout(log_path)

    compute_correlations(config.DATASET_CSV, config.FIGURES_DIR, config.DATA_ROOT)
    print(f"\n[INFO] log: {log_path}")


if __name__ == "__main__":
    main()