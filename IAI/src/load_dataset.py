"""1.2 - Load dataset_clean.csv into role-split arrays.

Returns numeric-only X (15 retained features), y labels (1..15),
and feature names in retained-file order.
"""
import sys
from pathlib import Path
import pandas as pd
from sklearn.utils.multiclass import unique_labels

sys.path.insert(0, str(Path(__file__).parent))
import config


def load_retained_features(path=None):
    """Read retained_features_correlations.txt. Skip blank/comment lines."""
    path = Path(path) if path else Path(config.DATA_ROOT) / "retained_features_correlations.txt"
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            names.append(s)
    assert len(names) == 15, f"expected 15 retained features, got {len(names)}"
    return names


def load_splits(dataset_csv=None, retained_txt=None):
    """Return (X_train, X_val, X_test, y_train, y_val, y_test, feature_names)."""
    dataset_csv = Path(dataset_csv) if dataset_csv else Path(config.DATA_ROOT) / "dataset_clean.csv"
    df = pd.read_csv(dataset_csv)
    feature_names = load_retained_features(retained_txt)

    missing = [c for c in feature_names if c not in df.columns]
    assert not missing, f"features missing from CSV: {missing}"

    out = {}
    for role in ("train", "val", "test"):
        sub = df[df["role"] == role]
        out[role] = (sub[feature_names].to_numpy(dtype=float),
                     sub["label"].to_numpy(dtype=int))
    return (*out["train"], *out["val"], *out["test"], feature_names)


if __name__ == "__main__":
    X_tr, y_tr, X_va, y_va, X_te, y_te, feats = load_splits()
    print(f"features: {len(feats)}")
    print(f"train   : {X_tr.shape}  classes={len(unique_labels(y_tr))}")
    print(f"val     : {X_va.shape}  classes={len(unique_labels(y_va))}")
    print(f"test    : {X_te.shape}  classes={len(unique_labels(y_te))}")