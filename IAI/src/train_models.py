"""2.1 - Candidate estimators + baseline cross-validation.

Three untuned candidates, each wrapped via build_pipeline().
cv_report() returns mean/std of macro-F1 and accuracy over StratifiedKFold.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import build_pipeline
from load_dataset import load_splits

SEED = 42

CANDIDATES = {
    "svc": SVC(kernel="rbf", class_weight="balanced",
               probability=True, random_state=SEED),
    "knn": KNeighborsClassifier(),
    "rf":  RandomForestClassifier(n_estimators=300,
                                  class_weight="balanced",
                                  random_state=SEED, n_jobs=-1),
}

SCORING = {"f1_macro": "f1_macro", "accuracy": "accuracy"}


def cv_report(name, estimator, X, y, cv=5):
    """Run stratified CV; return dict of mean/std for each metric."""
    pipe = build_pipeline(estimator)
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=SEED)
    res = cross_validate(pipe, X, y, cv=skf, scoring=SCORING, n_jobs=-1)
    row = {"model": name}
    for m in SCORING:
        row[f"{m}_mean"] = float(np.mean(res[f"test_{m}"]))
        row[f"{m}_std"]  = float(np.std(res[f"test_{m}"]))
    return row


def main():
    X_tr, y_tr, *_ = load_splits()
    rows = []
    for name, est in CANDIDATES.items():
        print(f"[CV] {name} ...", flush=True)
        rows.append(cv_report(name, est, X_tr, y_tr))
    df = pd.DataFrame(rows).set_index("model")
    print(df.to_string(float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    main()