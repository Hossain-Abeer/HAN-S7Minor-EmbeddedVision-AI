"""3.2 - One-shot test set evaluation of the persisted final pipeline.

Loads models/3.1-final_pipeline.joblib and predicts on the 119-row test
set exactly ONCE. No re-tune, no re-fit, no re-open.

Emits (all tagged 3.2-):
  figures/3.2-cm_test.png
  logs/3.2-classification_report.txt
  logs/3.2-test_report.txt
  3.2-test_summary.csv
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.metrics import (confusion_matrix, classification_report,
                             f1_score, accuracy_score,
                             ConfusionMatrixDisplay)

sys.path.insert(0, str(Path(__file__).parent))
import config
from load_dataset import load_splits, load_retained_features

DATA_ROOT  = Path(config.DATA_ROOT)
FIG_DIR    = Path(config.FIGURES_DIR)
LOGS_DIR   = Path(config.LOGS_DIR)
MODELS_DIR = DATA_ROOT / "models"

FIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH  = MODELS_DIR / "3.1-final_pipeline.joblib"
FEAT_PATH   = MODELS_DIR / "3.1-final_feature_names.json"

CM_PATH      = FIG_DIR  / "3.2-cm_test.png"
REPORT_PATH  = LOGS_DIR / "3.2-classification_report.txt"
LOG_PATH     = LOGS_DIR / "3.2-test_report.txt"
SUMMARY_PATH = DATA_ROOT / "3.2-test_summary.csv"

LABELS       = list(range(1, 16))
SMART_TARGET = 0.50


def load_final_pipeline():
    """Load persisted pipeline + training-time feature order."""
    pipe       = joblib.load(MODEL_PATH)
    feat_names = json.loads(FEAT_PATH.read_text())
    assert len(feat_names) == 15, f"expected 15 features, got {len(feat_names)}"
    assert len(pipe.steps) == 2, f"expected 2 pipeline steps, got {len(pipe.steps)}"
    return pipe, feat_names


def check_feature_alignment(model_names, data_names):
    """Deploy-time feature order must match training-time order exactly."""
    if list(model_names) != list(data_names):
        raise ValueError(
            f"feature order mismatch:\n"
            f"  model: {list(model_names)}\n"
            f"  data : {list(data_names)}")


def evaluate_once(pipe, X_te, y_te):
    """One prediction pass. Returns dict of all metrics."""
    y_pred = pipe.predict(X_te)
    cm     = confusion_matrix(y_te, y_pred, labels=LABELS)
    per_class_f1 = f1_score(y_te, y_pred, labels=LABELS,
                            average=None, zero_division=0)
    return {
        "y_pred":       y_pred,
        "cm":           cm,
        "per_class_f1": per_class_f1,
        "macro_f1":     float(f1_score(y_te, y_pred, average="macro",
                                       zero_division=0)),
        "accuracy":     float(accuracy_score(y_te, y_pred)),
        "min_class_f1": float(np.min(per_class_f1)),
        "n_zero_f1":    int(np.sum(per_class_f1 == 0)),
    }


def plot_cm(cm, path):
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay(cm, display_labels=LABELS).plot(
        ax=ax, cmap="Blues", colorbar=False, values_format="d")
    ax.set_title("test confusion - final pipeline (rf)")
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_classification_report(y_te, y_pred, path):
    rep = classification_report(y_te, y_pred, labels=LABELS,
                                zero_division=0, digits=3)
    path.write_text("model: rf (persisted 3.1-final_pipeline.joblib)\n"
                    "metric: one-shot test set (clip 1, 119 rows)\n\n"
                    f"{rep}\n")


def main():
    log = []
    def emit(s):
        print(s); log.append(s)

    X_tr, y_tr, X_va, y_va, X_te, y_te, data_feat_names = load_splits()
    pipe, model_feat_names = load_final_pipeline()
    emit(f"test shape    : {X_te.shape}")
    emit(f"features      : {len(model_feat_names)}")
    emit(f"pipeline      : {type(pipe).__name__} ({len(pipe.steps)} steps)")
    emit(f"scaler        : {type(pipe.steps[0][1]).__name__}")
    emit(f"clf           : {type(pipe.steps[1][1]).__name__}")

    check_feature_alignment(model_feat_names, data_feat_names)
    emit("feature order : OK")

    emit(f"one-shot predict on {len(y_te)} rows ...")
    r = evaluate_once(pipe, X_te, y_te)
    emit("done. no further prediction passes.")

    plot_cm(r["cm"], CM_PATH)
    emit(f"wrote         : {CM_PATH}")

    write_classification_report(y_te, r["y_pred"], REPORT_PATH)
    emit(f"wrote         : {REPORT_PATH}")

    summary = pd.DataFrame([{
        "model":         "rf",
        "macro_f1":      r["macro_f1"],
        "accuracy":      r["accuracy"],
        "min_class_f1":  r["min_class_f1"],
        "n_zero_f1":     r["n_zero_f1"],
        "smart_target":  SMART_TARGET,
        "smart_pass":    r["macro_f1"] >= SMART_TARGET,
    }])
    summary.to_csv(SUMMARY_PATH, index=False)
    emit(f"wrote         : {SUMMARY_PATH}")

    emit("")
    emit("=" * 60)
    emit(f"TEST macro-F1 : {r['macro_f1']:.4f}")
    emit(f"TEST accuracy : {r['accuracy']:.4f}")
    emit(f"min class F1  : {r['min_class_f1']:.4f}")
    emit(f"F1=0 classes  : {r['n_zero_f1']}")
    emit(f"SMART target  : >= {SMART_TARGET}")
    emit(f"SMART verdict : "
         f"{'PASS' if r['macro_f1'] >= SMART_TARGET else 'FAIL'}")
    emit("=" * 60)

    emit("")
    emit("Comparative:")
    emit("  CV macro-F1  (2.2) : 0.7193   reference")
    emit("  val macro-F1 (2.5) : 0.3425   L16 anomaly, not selection")
    emit(f"  test macro-F1      : {r['macro_f1']:.4f}")
    emit("")
    if r["macro_f1"] >= 0.55:
        emit("Interpretation: test tracks CV. L16 is clip-5 specific.")
    elif r["macro_f1"] >= 0.40:
        emit("Interpretation: test between CV and val. Partial shift. Document.")
    else:
        emit("Interpretation: test tracks val. Shift is broader. Document, "
             "do NOT retune.")

    LOG_PATH.write_text("\n".join(log))
    print(f"\nwrote         : {LOG_PATH}")


if __name__ == "__main__":
    main()