"""2.6 - Select best model and write decision note.

Reads:
  logs/cv_results_{svc,knn,rf}.csv  OR  logs/2.4_cv_results_{svc,knn,rf}.csv
  models/best_params_{svc,knn,rf}.json
  val_summary.csv

Writes:
  logs/2.6_selection_note.txt
  models/2.6_selected_model.json
"""
import sys, json
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config

DATA_ROOT   = Path(config.DATA_ROOT)
LOGS_DIR    = Path(config.LOGS_DIR)
MODELS_DIR  = DATA_ROOT / "models"

NOISE_FLOOR = 0.087
MODELS = ["svc", "knn", "rf"]
COMPLEXITY = {"knn": 1, "svc": 2, "rf": 3}

MANUAL_OVERRIDE = "rf"
OVERRIDE_REASON = (
    "Val rank preservation (rf>svc>knn) corroborates the CV ordering. "
    "Tuning sensitivity differs: RF gain vs baseline = +0.0002 (default-robust); "
    "SVC gain = +0.1004 (tuning-dependent). At deployment, RF's default robustness "
    "and its leading val score under distribution shift (L16) outweigh the small "
    "0.0166 CV gap. Complexity tie-break rule 3 is overridden with this rationale."
)

CV_RESULT_CANDIDATES = [
    "cv_results_{model}.csv",
    "2.4_cv_results_{model}.csv",
]


def read_cv_best(model):
    """Return best mean_test_score from cv_results_<model>.csv (2.4 output)."""
    for pattern in CV_RESULT_CANDIDATES:
        p = LOGS_DIR / pattern.format(model=model)
        if p.exists():
            df = pd.read_csv(p)
            best = df.sort_values("mean_test_score", ascending=False).iloc[0]
            return float(best["mean_test_score"]), float(best["std_test_score"])
    raise FileNotFoundError(
        f"no CV results for {model} in {LOGS_DIR}; "
        f"tried: {[pat.format(model=model) for pat in CV_RESULT_CANDIDATES]}"
    )


def read_val(model):
    df = pd.read_csv(DATA_ROOT / "val_summary.csv").set_index("model")
    row = df.loc[model]
    return float(row["macro_f1"]), int(row["n_zero_f1"]), float(row["min_class_f1"])


def rank(df, col, higher_better=True):
    order = df.sort_values(col, ascending=not higher_better).index
    return {m: i + 1 for i, m in enumerate(order)}


def apply_tiebreak(candidates, val_df):
    trail = []
    remaining = list(candidates)
    min_zeros = min(val_df.loc[m, "n_zero_f1"] for m in remaining)
    survivors = [m for m in remaining if val_df.loc[m, "n_zero_f1"] == min_zeros]
    trail.append(f"Rule a (fewer val F1 zeros): min={min_zeros}, survivors={survivors}")
    if len(survivors) == 1:
        return survivors[0], trail

    remaining = survivors
    max_min = max(val_df.loc[m, "min_class_f1"] for m in remaining)
    survivors = [m for m in remaining if val_df.loc[m, "min_class_f1"] == max_min]
    trail.append(f"Rule b (higher val min_class_f1): max={max_min}, survivors={survivors}")
    if len(survivors) == 1:
        return survivors[0], trail

    remaining = survivors
    min_c = min(COMPLEXITY[m] for m in remaining)
    survivors = [m for m in remaining if COMPLEXITY[m] == min_c]
    trail.append(f"Rule c (lower complexity): min={min_c}, survivors={survivors}")
    return survivors[0], trail


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    cv = {m: read_cv_best(m) for m in MODELS}
    val_df = pd.read_csv(DATA_ROOT / "val_summary.csv").set_index("model")

    cv_df = pd.DataFrame(
        {m: {"cv_f1": cv[m][0], "cv_std": cv[m][1]} for m in MODELS}
    ).T
    cv_df = cv_df.join(val_df[["macro_f1", "n_zero_f1", "min_class_f1"]])

    cv_rank  = rank(cv_df, "cv_f1",  higher_better=True)
    val_rank = rank(cv_df, "macro_f1", higher_better=True)

    cv_sorted  = sorted(MODELS, key=lambda m: cv_df.loc[m, "cv_f1"],  reverse=True)
    val_sorted = sorted(MODELS, key=lambda m: cv_df.loc[m, "macro_f1"], reverse=True)
    rank_preserved = cv_sorted == val_sorted

    top1, top2 = cv_sorted[0], cv_sorted[1]
    gap = cv_df.loc[top1, "cv_f1"] - cv_df.loc[top2, "cv_f1"]
    tied = gap < NOISE_FLOOR
    tiebreak_trail = []

    if tied:
        tied_set = [m for m in MODELS if
                    cv_df.loc[top1, "cv_f1"] - cv_df.loc[m, "cv_f1"] < NOISE_FLOOR]
        winner, tiebreak_trail = apply_tiebreak(tied_set, cv_df)
        mode = "tie-break"
    else:
        winner = top1
        mode = "clear primary"

    mechanical = winner
    final = MANUAL_OVERRIDE if MANUAL_OVERRIDE else mechanical

    params = json.loads((MODELS_DIR / f"best_params_{final}.json").read_text())

    lines = []
    lines.append("=" * 76)
    lines.append("2.6 - MODEL SELECTION NOTE")
    lines.append("=" * 76)
    lines.append(f"CV noise floor          : {NOISE_FLOOR}")
    lines.append(f"Primary metric          : CV macro-F1 (grid search best)")
    lines.append(f"Corroboration           : val rank preservation")
    lines.append(f"Rank preservation       : {'YES' if rank_preserved else 'NO'}")
    lines.append(f"  CV rank  : {cv_sorted}")
    lines.append(f"  Val rank : {val_sorted}")
    lines.append("")
    lines.append("Decision table")
    lines.append("-" * 76)
    lines.append(f"{'model':<6} {'cv_f1':>8} {'cv_std':>8} "
                 f"{'val_f1':>8} {'n_zero':>7} {'min_f1':>8}")
    for m in MODELS:
        r = cv_df.loc[m]
        lines.append(f"{m:<6} {r.cv_f1:>8.4f} {r.cv_std:>8.4f} "
                     f"{r.macro_f1:>8.4f} {int(r.n_zero_f1):>7d} "
                     f"{r.min_class_f1:>8.4f}")
    lines.append("")
    lines.append(f"Top-2 CV gap            : {gap:.4f}")
    lines.append(f"Noise-floor verdict     : "
                 f"{'TIE (gap < noise)' if tied else 'CLEAR (gap >= noise)'}")
    lines.append(f"Decision mode           : {mode}")
    if tiebreak_trail:
        lines.append("Tie-break trail:")
        for t in tiebreak_trail:
            lines.append(f"  {t}")
    lines.append("")
    lines.append(f"Mechanical winner       : {mechanical}")
    if MANUAL_OVERRIDE:
        lines.append(f"MANUAL OVERRIDE         : {final}")
        lines.append(f"Override rationale      : {OVERRIDE_REASON}")
    lines.append(f"FINAL SELECTED MODEL    : {final}")
    lines.append(f"Locked hyperparameters  : {params}")
    lines.append("=" * 76)

    note = "\n".join(lines)
    (LOGS_DIR / "2.6_selection_note.txt").write_text(note)
    print(note)

    (MODELS_DIR / "2.6_selected_model.json").write_text(json.dumps({
        "step": "2.6",
        "model": final,
        "params": params,
        "cv_f1": float(cv_df.loc[final, "cv_f1"]),
        "val_f1": float(cv_df.loc[final, "macro_f1"]),
        "override": bool(MANUAL_OVERRIDE),
    }, indent=2))
    print(f"\nwrote {MODELS_DIR / '2.6_selected_model.json'}")


if __name__ == "__main__":
    main()