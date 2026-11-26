"""3.3 - Per-class error analysis of the 3.2 test confusion matrix.

Reloads 3.1 joblib (deterministic, identical to 3.2 predictions).
Ranks off-diagonal cells, tags known ambiguous pairs, separates
structural failures (fail on val AND test) from shift-induced failures.

Outputs:
  3.3-error_pairs.csv
  figures/3.3-error_pairs.png
  logs/3.3-error_analysis.txt
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.metrics import confusion_matrix, f1_score

sys.path.insert(0, str(Path(__file__).parent))
import config
from load_dataset import load_splits

DATA_ROOT  = Path(config.DATA_ROOT)
FIG_DIR    = Path(config.FIGURES_DIR)
LOGS_DIR   = Path(config.LOGS_DIR)
MODELS_DIR = DATA_ROOT / "models"

FIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH  = MODELS_DIR / "3.1-final_pipeline.joblib"
FEAT_PATH   = MODELS_DIR / "3.1-final_feature_names.json"
CSV_PATH    = DATA_ROOT  / "3.3-error_pairs.csv"
PNG_PATH    = FIG_DIR    / "3.3-error_pairs.png"
LOG_PATH    = LOGS_DIR   / "3.3-error_analysis.txt"

LABELS       = list(range(1, 16))
EXPECTED_F1  = 0.2607     # from 3.2; used as seal-integrity check
TOP_N        = 20

# Known ambiguous pairs from L6 / L7 plus observed val errors from 2.5.
# Unordered - match either direction.
KNOWN_PAIRS = {
    frozenset({6, 9}):   "L6: 6/9 rotation ambiguity",
    frozenset({4, 9}):   "L7: 4/9 shape overlap",
    frozenset({11, 1}):  "L7: 11/1 shape overlap",
    frozenset({2, 5}):   "L7: 2/5 shape overlap",
    frozenset({3, 4}):   "val 2.5: 4->3 dominant",
    frozenset({9, 14}):  "val 2.5: 9->14 dominant",
    frozenset({12, 13}): "test 3.2: 13->12 magnet",
    frozenset({10, 12}): "test 3.2: 10->12 magnet",
}


def load_pipeline():
    pipe = joblib.load(MODEL_PATH)
    feats = json.loads(FEAT_PATH.read_text())
    return pipe, feats


def predict_va_te(pipe, X_va, X_te):
    """Deterministic re-predict. Identical to 3.2 due to 3.1 reload check."""
    return pipe.predict(X_va), pipe.predict(X_te)


def build_offdiag_df(y_te, y_pred_te):
    """Every (true, pred) pair with count > 0 and true != pred."""
    cm = confusion_matrix(y_te, y_pred_te, labels=LABELS)
    support = cm.sum(axis=1)
    rows = []
    for i, t in enumerate(LABELS):
        for j, p in enumerate(LABELS):
            if t == p:
                continue
            c = int(cm[i, j])
            if c == 0:
                continue
            rows.append({
                "true_class":      t,
                "pred_class":      p,
                "count":           c,
                "support_true":    int(support[i]),
                "pct_of_true":     round(c / support[i], 3) if support[i] else 0,
                "known_pair":      KNOWN_PAIRS.get(frozenset({t, p}), ""),
            })
    df = pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)
    return df, cm


def classify_failures(y_va, y_pred_va, y_te, y_pred_te):
    """Per class: F1 on val, F1 on test, structural flag."""
    f1_va = f1_score(y_va, y_pred_va, labels=LABELS, average=None, zero_division=0)
    f1_te = f1_score(y_te, y_pred_te, labels=LABELS, average=None, zero_division=0)
    rows = []
    for i, c in enumerate(LABELS):
        if f1_te[i] == 0 and f1_va[i] == 0:
            verdict = "STRUCTURAL (fail both)"
        elif f1_te[i] == 0:
            verdict = "SHIFT-INDUCED (test only)"
        elif f1_va[i] == 0:
            verdict = "VAL-ONLY (test survives)"
        else:
            verdict = "survives"
        rows.append({
            "class":  c,
            "f1_val": round(float(f1_va[i]), 3),
            "f1_test": round(float(f1_te[i]), 3),
            "verdict": verdict,
        })
    return pd.DataFrame(rows)


def plot_top_errors(df, top_n, path):
    top = df.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 7))
    labels = [f"{r.true_class}->{r.pred_class}" for r in top.itertuples()]
    colors = ["tab:red" if r.known_pair else "tab:blue" for r in top.itertuples()]
    ax.barh(labels, top["count"], color=colors)
    ax.set_xlabel("count")
    ax.set_title(f"Top {top_n} test confusions (red = known pair)")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    log = []
    def emit(s):
        print(s); log.append(s)

    X_tr, y_tr, X_va, y_va, X_te, y_te, _ = load_splits()
    pipe, _ = load_pipeline()

    y_va_pred = pipe.predict(X_va)
    y_te_pred = pipe.predict(X_te)

    # Seal-integrity check: reproduce 3.2 macro-F1 exactly
    f1_te = float(f1_score(y_te, y_te_pred, average="macro", zero_division=0))
    emit(f"test macro-F1 reproduced : {f1_te:.4f} (expected {EXPECTED_F1:.4f})")
    assert abs(f1_te - EXPECTED_F1) < 1e-3, "seal broken: predictions differ from 3.2"
    emit("seal check               : PASS (identical to 3.2)")

    df, cm = build_offdiag_df(y_te, y_te_pred)
    df.to_csv(CSV_PATH, index=False)
    emit(f"wrote                    : {CSV_PATH}")

    plot_top_errors(df, TOP_N, PNG_PATH)
    emit(f"wrote                    : {PNG_PATH}")

    fail = classify_failures(y_va, y_va_pred, y_te, y_te_pred)

    emit("")
    emit("=" * 72)
    emit(f"TOP {TOP_N} OFF-DIAGONAL (test)")
    emit("=" * 72)
    emit(df.head(TOP_N).to_string(index=False))

    emit("")
    emit("=" * 72)
    emit("KNOWN-PAIR VERDICTS")
    emit("=" * 72)
    for pair, reason in KNOWN_PAIRS.items():
        t, p = sorted(pair)
        c_tp = int(cm[LABELS.index(t), LABELS.index(p)])
        c_pt = int(cm[LABELS.index(p), LABELS.index(t)])
        total = c_tp + c_pt
        verdict = "CONFIRMED" if total >= 2 else "NOT OBSERVED"
        emit(f"  {t}<->{p} : {c_tp}+{c_pt} = {total:3d}  [{verdict}]  {reason}")

    emit("")
    emit("=" * 72)
    emit("PER-CLASS FAILURE CLASSIFICATION")
    emit("=" * 72)
    emit(fail.to_string(index=False))

    structural = fail[fail["verdict"] == "STRUCTURAL (fail both)"]["class"].tolist()
    shift_only = fail[fail["verdict"] == "SHIFT-INDUCED (test only)"]["class"].tolist()
    emit("")
    emit(f"STRUCTURAL failures (L5/L6/L7 ceiling): {structural}")
    emit(f"SHIFT-INDUCED failures (test only):     {shift_only}")

    # Class-12 magnet
    idx12 = LABELS.index(12)
    col12 = cm[:, idx12]
    row12 = cm[idx12, :]
    emit("")
    emit("CLASS-12 MAGNET")
    emit(f"  predictions of '12' : {int(col12.sum())}")
    emit(f"  correct             : {int(row12[idx12])}")
    emit(f"  precision on 12     : {row12[idx12] / col12.sum():.3f}"
         if col12.sum() else "  precision on 12     : n/a")

    LOG_PATH.write_text("\n".join(log))
    print(f"\nwrote {LOG_PATH}")


if __name__ == "__main__":
    main()