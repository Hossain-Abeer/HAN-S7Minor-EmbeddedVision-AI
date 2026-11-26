"""2.5 - Evaluate tuned candidates on the validation set.

Reads best_params_{svc,knn,rf}.json from 2.4, rebuilds each pipeline,
fits on full train, predicts on val, emits confusion matrix +
classification_report + summary row per model.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (confusion_matrix, classification_report,
                             f1_score, accuracy_score,
                             ConfusionMatrixDisplay)

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import build_pipeline
from load_dataset import load_splits
from train_models import CANDIDATES, SEED

DATA_ROOT   = Path(config.DATA_ROOT)
FIG_DIR     = Path(config.FIGURES_DIR)
LOGS_DIR    = Path(config.LOGS_DIR)
MODELS_DIR  = DATA_ROOT / "models"

FIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LABELS = list(range(1, 16))


def load_best_params(name):
    """Read best_params_<name>.json from 2.4."""
    p = MODELS_DIR / f"best_params_{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"missing {p} - run 2.4 first")
    return json.loads(p.read_text())


def rebuild_model(name):
    """Instantiate base estimator with best_params applied."""
    params = load_best_params(name)
    est = CANDIDATES[name].__class__(**{**CANDIDATES[name].get_params(),
                                        **params})
    return est, params


def evaluate_one(name, X_tr, y_tr, X_va, y_va):
    """Fit one model, predict val, emit artefacts, return summary row."""
    est, params = rebuild_model(name)
    pipe = build_pipeline(est)
    pipe.fit(X_tr, y_tr)
    y_pred = pipe.predict(X_va)

    cm = confusion_matrix(y_va, y_pred, labels=LABELS)
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay(cm, display_labels=LABELS).plot(
        ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.set_title(f"val confusion - {name}")
    plt.tight_layout()
    fig.savefig(FIG_DIR / f"cm_val_{name}.png", dpi=150)
    plt.close(fig)

    report = classification_report(
        y_va, y_pred, labels=LABELS, zero_division=0, digits=3)
    (LOGS_DIR / f"classification_report_{name}.txt").write_text(
        f"model: {name}\nparams: {params}\n\n{report}\n")

    per_class_f1 = f1_score(y_va, y_pred, labels=LABELS,
                            average=None, zero_division=0)
    return {
        "model":         name,
        "macro_f1":      float(f1_score(y_va, y_pred,
                                        average="macro", zero_division=0)),
        "accuracy":      float(accuracy_score(y_va, y_pred)),
        "min_class_f1":  float(np.min(per_class_f1)),
        "n_zero_f1":     int(np.sum(per_class_f1 == 0)),
        "best_params":   json.dumps(params),
    }


def main():
    X_tr, y_tr, X_va, y_va, *_ = load_splits()
    print(f"train {X_tr.shape}  val {X_va.shape}")

    rows = []
    for name in CANDIDATES:
        print(f"[VAL] {name} ...", flush=True)
        rows.append(evaluate_one(name, X_tr, y_tr, X_va, y_va))

    df = pd.DataFrame(rows).set_index("model")
    print()
    print(df[["macro_f1", "accuracy", "min_class_f1", "n_zero_f1"]]
          .to_string(float_format=lambda v: f"{v:.4f}"))

    df.to_csv(DATA_ROOT / "val_summary.csv")
    print(f"\nwrote {DATA_ROOT / 'val_summary.csv'}")


if __name__ == "__main__":
    main()