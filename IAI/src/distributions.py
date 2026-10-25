"""
8.2 PLOT FEATURE DISTRIBUTIONS

Loads dataset.csv, filters to role=='train', and saves a boxplot per feature
(feature vs class 1-15) plus a grid overview.

Design reference: designtracker-1.6.2
Run from repo root:
    python src/distributions.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import config


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

GRID_COLS = 4
FIG_DPI   = 150


def plot_distributions(dataset_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(dataset_csv)
    df = df[df["role"] == "train"]

    # 1. Individual figures
    for feat in FEATURE_COLUMNS:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.boxplot(data=df, x="label", y=feat, ax=ax)
        ax.set_title(f"Distribution of '{feat}' per class (train)")
        ax.set_xlabel("Class (ball number)")
        ax.set_ylabel(feat)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"feature_dist_{feat}.png"), dpi=FIG_DPI)
        plt.close(fig)

    # 2. Grid overview
    n = len(FEATURE_COLUMNS)
    ncols = GRID_COLS
    nrows = (n + ncols - 1) // ncols
    
    fig, axes = plt.subplots(nrows, ncols, figsize=(4*ncols, 3*nrows))
    axes = axes.ravel()

    for ax, feat in zip(axes, FEATURE_COLUMNS):
        sns.boxplot(data=df, x="label", y=feat, ax=ax)
        ax.set_title(feat, fontsize=9)
        ax.set_xlabel("")
        ax.set_ylabel("")

    for ax in axes[n:]:
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "feature_dist_GRID.png"), dpi=FIG_DPI)
    plt.close(fig)
    
    print(f"[INFO] wrote 23 individual plots + 1 grid to {out_dir}")


def main():
    out_dir = os.path.join(config.FIGURES_DIR, "feature_dist")
    plot_distributions(config.DATASET_CSV, out_dir)


if __name__ == "__main__":
    main()