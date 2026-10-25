"""
8.1 CHECK CLASS BALANCE

Loads dataset.csv, prints per-class counts and per-role/per-class matrix,
computes train-only max/min imbalance ratio, branches verdict, saves
class_balance.png and logs/1.6.1_balance_report.txt.

Design reference: designtracker-1.6.1
Run from repo root:
    python src/balance.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import config
import constants as C


MODERATE_RATIO = 1.5
SEVERE_RATIO   = 3.0
ROLES          = ("train", "val", "test")


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


def check_balance(dataset_csv, fig_dir):
    df = pd.read_csv(dataset_csv)

    overall = df["label"].value_counts().sort_index()
    print("Class counts (overall):")
    print(overall.to_string())

    pivot = (df.groupby(["role", "label"])
               .size()
               .unstack(fill_value=0))
    for r in ROLES:
        if r not in pivot.index:
            pivot.loc[r] = 0
    for cid in C.CLASS_IDS:
        if cid not in pivot.columns:
            pivot[cid] = 0
    pivot = pivot[sorted(pivot.columns)]
    pivot = pivot.loc[[r for r in ROLES if r in pivot.index]]

    print("\nPer-role / per-class counts:")
    print(pivot.to_string())

    train_counts = (df[df["role"] == "train"]["label"]
                    .value_counts()
                    .reindex(C.CLASS_IDS, fill_value=0)
                    .sort_index())
    min_c = int(train_counts.min())
    max_c = int(train_counts.max())
    ratio = max_c / max(min_c, 1)

    print(f"\nTRAIN imbalance:")
    print(f"  min class count = {min_c}")
    print(f"  max class count = {max_c}")
    print(f"  max/min ratio   = {ratio:.2f}")

    if ratio >= SEVERE_RATIO:
        verdict = "SEVERE"
        action  = ("Apply class_weight='balanced' in Phase 2 for SVC and RF. "
                   "Do not resample unless weighting proves insufficient.")
    elif ratio >= MODERATE_RATIO:
        verdict = "MODERATE"
        action  = "Document ratio in report §3. No correction applied."
    else:
        verdict = "BALANCED"
        action  = "Document ratio in report §3. No correction needed."

    print(f"  verdict         = {verdict}")
    print(f"  action          = {action}")

    os.makedirs(fig_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.countplot(data=df, x="label", hue="role", ax=ax)
    ax.set_title(f"Class balance per role (train max/min = {ratio:.2f})")
    ax.set_xlabel("Class (ball number)")
    ax.set_ylabel("Sample count")
    plt.tight_layout()
    out_png = os.path.join(fig_dir, "class_balance.png")
    plt.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"\n[INFO] wrote {out_png}")

    return {"overall": overall, "pivot": pivot,
            "ratio": ratio, "verdict": verdict, "action": action}


def main():
    log_path = os.path.join(config.LOGS_DIR, "1.6.1_balance_report.txt")
    _tee_stdout(log_path)

    check_balance(config.DATASET_CSV, config.FIGURES_DIR)
    print(f"\n[INFO] log: {log_path}")


if __name__ == "__main__":
    main()