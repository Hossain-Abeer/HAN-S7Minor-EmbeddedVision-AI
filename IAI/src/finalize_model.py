"""3.1 - Retrain final RF pipeline on full train set, persist to joblib.

Locked params from 2.6. StandardScaler inside pipeline (per 2.8).
Reload check: predict 5 fixed rows before save and after load; must match.

Outputs (all tagged 3.1-):
  models/3.1-final_pipeline.joblib
  models/3.1-final_feature_names.json
  logs/3.1-finalize.txt
"""
import sys, json
from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import build_pipeline
from load_dataset import load_splits, load_retained_features

DATA_ROOT  = Path(config.DATA_ROOT)
MODELS_DIR = DATA_ROOT / "models"
LOGS_DIR   = Path(config.LOGS_DIR)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42

MODEL_PATH  = MODELS_DIR / "3.1-final_pipeline.joblib"
FEAT_PATH   = MODELS_DIR / "3.1-final_feature_names.json"
LOG_PATH    = LOGS_DIR   / "3.1-finalize.txt"


def load_locked_params():
    """Read model name + params from 2.6_selected_model.json."""
    p = MODELS_DIR / "2.6_selected_model.json"
    data = json.loads(p.read_text())
    return data["model"], data["params"]


def build_final_estimator(params):
    """Instantiate RF with locked params + seed."""
    return RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_leaf=params["min_samples_leaf"],
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )


def main():
    log = []
    def emit(s):
        print(s)
        log.append(s)

    # 1. Load
    X_tr, y_tr, *_ = load_splits()
    feat_names = list(load_retained_features())
    emit(f"train shape  : {X_tr.shape}")
    emit(f"features     : {len(feat_names)}")

    # 2. Locked params
    name, params = load_locked_params()
    emit(f"locked model : {name}")
    emit(f"locked params: {params}")
    assert name == "rf", f"expected rf, got {name}"

    # 3. Build + fit
    pipe = build_pipeline(build_final_estimator(params))
    pipe.fit(X_tr, y_tr)
    emit(f"pipeline fit : OK")

    # 4. Reload check (pre-save)
    probe = X_tr[:5]
    pred_before = pipe.predict_proba(probe)

    # 5. Persist
    joblib.dump(pipe, MODEL_PATH, compress=3)
    FEAT_PATH.write_text(json.dumps(feat_names, indent=2))
    emit(f"wrote        : {MODEL_PATH}")
    emit(f"wrote        : {FEAT_PATH}")

    # 6. Reload check (post-load)
    pipe2 = joblib.load(MODEL_PATH)
    pred_after = pipe2.predict_proba(probe)
    diff = float(np.max(np.abs(pred_before - pred_after)))
    emit(f"reload delta : {diff:.2e}")
    assert diff < 1e-12, f"reload mismatch: {diff}"
    emit("reload check : PASS")

    # 7. Sanity: predict full train, report train macro-F1
    from sklearn.metrics import f1_score
    train_f1 = f1_score(y_tr, pipe.predict(X_tr), average="macro")
    emit(f"train f1     : {train_f1:.4f}  (expected near 1.0, per 2.7)")

    LOG_PATH.write_text("\n".join(log))
    print(f"\nwrote        : {LOG_PATH}")


if __name__ == "__main__":
    main()