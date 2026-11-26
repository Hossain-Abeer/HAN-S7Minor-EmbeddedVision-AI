"""4.1 - Deployment wrapper: raw crop -> features -> persisted pipeline -> label.

Reuses mask.py + features.py helpers to rebuild the training feature vector
at inference time. Rejects crops where mask_is_usable() is False (FR4).

Outputs:
  <DATA_ROOT>/4.1-batch_output.csv    (default batch mode)
  logs/4.1-predict_smoke.txt          (tee when run via PS wrapper)
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import cv2
import joblib

sys.path.insert(0, str(Path(__file__).parent))
import config
from mask import extract_numeral_mask, mask_is_usable
from features import features_from_mask

DATA_ROOT  = Path(config.DATA_ROOT)
MODELS_DIR = DATA_ROOT / "models"
LOGS_DIR   = Path(config.LOGS_DIR)

MODEL_PATH = MODELS_DIR / "3.1-final_pipeline.joblib"
FEAT_PATH  = MODELS_DIR / "3.1-final_feature_names.json"

USE_FEATURES     = config.USE_FEATURES
PROJ_BINS        = config.PROJ_BINS
KEEP_HU_MOMENTS  = config.KEEP_HU_MOMENTS
MIN_HOLE_AREA_PX = config.MIN_HOLE_AREA_PX

LABELS = list(range(1, 16))


def load_model():
    """Load persisted pipeline + training-time feature order."""
    pipe = joblib.load(MODEL_PATH)
    feat_names = json.loads(FEAT_PATH.read_text())
    assert len(feat_names) == 15, f"expected 15 features, got {len(feat_names)}"
    assert len(pipe.steps) == 2, f"expected 2 steps, got {len(pipe.steps)}"
    return pipe, feat_names


def extract_features_from_crop(crop_bgr, feat_names):
    """Rebuild 15-feature vector at inference time.

    Returns (features_1d_array, status).
    status == 'ok' on success; a reject reason string otherwise.
    """
    mask = extract_numeral_mask(crop_bgr)
    if not mask_is_usable(mask):
        return None, "mask_unusable"

    feat_dict = features_from_mask(
        mask,
        use_features=USE_FEATURES,
        proj_bins=PROJ_BINS,
        keep_hu=KEEP_HU_MOMENTS,
        min_hole_area=MIN_HOLE_AREA_PX,
    )
    missing = [k for k in feat_names if k not in feat_dict]
    if missing:
        return None, f"missing_features:{missing}"
    x = np.array([feat_dict[k] for k in feat_names], dtype=float)
    return x, "ok"


def predict_crop(pipe, feat_names, crop_path):
    """Predict one crop. Returns (label, proba_vector, status)."""
    img = cv2.imread(str(crop_path), cv2.IMREAD_COLOR)
    if img is None:
        return None, None, "imread_failed"
    x, status = extract_features_from_crop(img, feat_names)
    if x is None:
        return None, None, status
    x2 = x.reshape(1, -1)
    label = int(pipe.predict(x2)[0])
    proba = pipe.predict_proba(x2)[0].tolist()
    return label, proba, "ok"


def predict_batch(pipe, feat_names, input_dir, out_csv=None):
    """Predict every PNG in input_dir. Returns DataFrame."""
    input_dir = Path(input_dir)
    rows = []
    for p in sorted(input_dir.glob("*.png")):
        label, proba, status = predict_crop(pipe, feat_names, p)
        row = {"filename": p.name, "status": status,
               "predicted_label": label if label is not None else -1}
        if proba is not None:
            for i, cls in enumerate(LABELS):
                row[f"proba_{cls}"] = round(proba[i], 6)
        rows.append(row)
    df = pd.DataFrame(rows)
    if out_csv is not None:
        df.to_csv(out_csv, index=False)
    return df


if __name__ == "__main__":
    pipe, feat_names = load_model()
    print(f"loaded  : {MODEL_PATH.name}")
    print(f"features: {len(feat_names)}")

    target = Path(sys.argv[1]) if len(sys.argv) > 1 \
             else DATA_ROOT / "unsorted_png" / "1"
    out = DATA_ROOT / "4.1-batch_output.csv"

    df = predict_batch(pipe, feat_names, target, out)
    n_ok = int((df["status"] == "ok").sum())
    n_rej = len(df) - n_ok
    print(f"processed: {len(df)} crops  |  ok: {n_ok}  |  rejected: {n_rej}")
    if n_rej:
        for s, c in df[df["status"] != "ok"]["status"].value_counts().items():
            print(f"  reject[{s}] = {c}")
    print(f"wrote   : {out}")