"""2.3 - Grid search over small hyperparameter grids per candidate.

Grids anchored to CV noise floor (~0.07 macro-F1, per 2.2 B.6).
refit=False: no full-train fit here. Refit happens at 3.1.
"""
import sys, json
from pathlib import Path
import pandas as pd
from sklearn.model_selection import GridSearchCV, StratifiedKFold

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import build_pipeline
from load_dataset import load_splits
from train_models import CANDIDATES, SEED

MODELS_DIR = Path(config.DATA_ROOT) / "models"
LOGS_DIR   = Path(config.LOGS_DIR)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

PARAM_GRIDS = {
    "svc": {
        "clf__C":      [1, 10, 100],
        "clf__gamma":  ["scale", 0.01],
        "clf__kernel": ["rbf"],
    },
    "knn": {
        "clf__n_neighbors": [3, 5, 7, 11],
        "clf__weights":     ["uniform", "distance"],
    },
    "rf": {
        "clf__n_estimators":     [300],
        "clf__max_depth":        [None, 10, 20],
        "clf__min_samples_leaf": [1, 2],
    },
}

SCORING = "f1_macro"


def run_grid(name, estimator, X, y):
    """Run GridSearchCV for one model; return fitted GridSearchCV object."""
    pipe = build_pipeline(estimator)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    gs = GridSearchCV(
        pipe, PARAM_GRIDS[name],
        scoring=SCORING, cv=skf, n_jobs=-1,
        refit=False, return_train_score=False, verbose=0,
    )
    gs.fit(X, y)
    return gs


def main():
    X_tr, y_tr, *_ = load_splits()
    summary = []
    for name, est in CANDIDATES.items():
        print(f"[GRID] {name} ...", flush=True)
        gs = run_grid(name, est, X_tr, y_tr)

        best_params = {k.replace("clf__", ""): v
                       for k, v in gs.best_params_.items()}
        (MODELS_DIR / f"best_params_{name}.json").write_text(
            json.dumps(best_params, indent=2))

        res_df = pd.DataFrame(gs.cv_results_)
        res_df.to_csv(LOGS_DIR / f"2.4_cv_results_{name}.csv", index=False)

        summary.append({
            "model":     name,
            "best_f1":   float(gs.best_score_),
            "baseline_f1": None,   # filled by caller from 2.2
            "best_params": str(best_params),
        })
        print(f"  best macro-F1 = {gs.best_score_:.4f}")
        print(f"  best params   = {best_params}")

    df = pd.DataFrame(summary).set_index("model")
    print()
    print(df.to_string(float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    main()