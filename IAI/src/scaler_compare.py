"""2.8 - Alternative scaler comparison: StandardScaler vs MinMaxScaler on RF.

RF is scale-invariant by construction. Expectation: delta = 0.000.
Satisfies Jeroen's feedback S6 (preprocessing level 3 -> 4).
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import StratifiedKFold, cross_validate

sys.path.insert(0, str(Path(__file__).parent))
import config
from load_dataset import load_splits
from train_models import CANDIDATES, SEED

DATA_ROOT = Path(config.DATA_ROOT)
FIG_DIR   = Path(config.FIGURES_DIR)
LOGS_DIR  = Path(config.LOGS_DIR)

FIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

SCALERS = {
    "StandardScaler": StandardScaler(),
    "MinMaxScaler":   MinMaxScaler(),
}

SCORING = {"f1_macro": "f1_macro", "accuracy": "accuracy"}


def load_rf():
    """Load rf estimator with best params from 2.4."""
    params = json.loads(
        (DATA_ROOT / "models" / "best_params_rf.json").read_text())
    base = CANDIDATES["rf"]
    return base.__class__(**{**base.get_params(), **params})


def compare(X, y):
    """Run 5-fold CV under each scaler; return DataFrame indexed by scaler."""
    rows = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for name, scaler in SCALERS.items():
        pipe = Pipeline([("scaler", scaler), ("clf", load_rf())])
        res = cross_validate(pipe, X, y, cv=skf, scoring=SCORING, n_jobs=-1)
        row = {"scaler": name}
        for m in SCORING:
            row[f"{m}_mean"] = float(np.mean(res[f"test_{m}"]))
            row[f"{m}_std"]  = float(np.std(res[f"test_{m}"]))
        rows.append(row)
    return pd.DataFrame(rows).set_index("scaler")


def plot_bar(df):
    """Two-bar comparison with error bars."""
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(df))
    w = 0.35
    ax.bar(x - w/2, df["f1_macro_mean"], w, yerr=df["f1_macro_std"],
           capsize=4, label="macro-F1")
    ax.bar(x + w/2, df["accuracy_mean"], w, yerr=df["accuracy_std"],
           capsize=4, label="accuracy")
    ax.set_xticks(x)
    ax.set_xticklabels(df.index)
    ax.set_ylabel("score")
    ax.set_ylim(0, 1)
    ax.set_title("scaler comparison - rf")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "2.8_scaler_compare.png", dpi=150)
    plt.close(fig)


def main():
    X_tr, y_tr, *_ = load_splits()
    print(f"train {X_tr.shape}")
    df = compare(X_tr, y_tr)
    print(df.to_string(float_format=lambda v: f"{v:.4f}"))

    delta = (df.loc["StandardScaler", "f1_macro_mean"]
             - df.loc["MinMaxScaler",   "f1_macro_mean"])
    print(f"\ndelta (Std - MinMax) on macro-F1: {delta:+.6f}")

    plot_bar(df)
    df.to_csv(DATA_ROOT / "scaler_compare.csv")
    print(f"\nwrote {DATA_ROOT / 'scaler_compare.csv'}")
    print(f"wrote {FIG_DIR / '2.8_scaler_compare.png'}")


if __name__ == "__main__":
    main()