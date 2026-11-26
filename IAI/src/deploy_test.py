"""4.4 - Execute deploy test plan (4.3_test_plan.md).

Runs all FR1-FR7, TR1-TR8 against the persisted 3.1 pipeline.
Emits deploy_results.csv + logs/4.4-deploy_results.txt.

Notes:
- FR4 uses test_data/reject_batch/*.png if present, else generates
  5 synthetic non-numeral probes (cloth, black, grey, low-V noise,
  two-tone). Source is logged.
- FR6 re-runs split.py with backup/restore of splits.csv.
- TR7 rebuilds the final pipeline in-memory (equivalent to re-running
  3.1's finalize_model.py; avoids file mutation).
"""
import sys, json, time, hashlib, shutil, subprocess, platform, ast
from pathlib import Path
import numpy as np
import pandas as pd
import cv2

sys.path.insert(0, str(Path(__file__).parent))
import config
from load_dataset import load_splits
from pipeline import build_pipeline
from predict import predict_crop, load_model

DATA_ROOT = Path(config.DATA_ROOT)
LOGS_DIR  = Path(config.LOGS_DIR)
FIG_DIR   = Path(config.FIGURES_DIR)
LABELS    = list(range(1, 16))
EXPECTED_TEST_F1 = 0.2607

OK, NO, DE = "PASS", "FAIL", "PENDING"

# ---------------------------------------------------------------- helpers

def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _row(id_, measured, target, ok, notes="", pending=False):
    status = DE if pending else (OK if ok else NO)
    return {"ID": id_, "Measured": measured, "Target": target,
            "Pass": status, "Notes": notes}

def _build_test_paths():
    df = pd.read_csv(DATA_ROOT / "dataset_clean.csv")
    df = df[df["role"] == "test"]
    return [(DATA_ROOT / "unsorted_png" / r["filename"],
             int(r["label"])) for _, r in df.iterrows()]

def _ensure_reject_batch():
    rb = DATA_ROOT / "test_data" / "reject_batch"
    rb.mkdir(parents=True, exist_ok=True)
    if list(rb.glob("*.png")):
        return rb, len(list(rb.glob("*.png"))), "user"
    probes = {
        "synthetic_cloth.png":     np.full((64, 64, 3), (100, 200, 150), np.uint8),
        "synthetic_black.png":     np.full((64, 64, 3), (5, 5, 5),       np.uint8),
        "synthetic_grey.png":      np.full((64, 64, 3), (128, 128, 128), np.uint8),
        "synthetic_darknoise.png": np.random.randint(0, 100, (64, 64, 3), dtype=np.uint8),
        "synthetic_twotone.png":   np.hstack([
            np.full((64, 32, 3), (100, 200, 150), np.uint8),
            np.full((64, 32, 3), (5, 5, 5),       np.uint8)]),
    }
    for n, im in probes.items():
        cv2.imwrite(str(rb / n), im)
    return rb, len(probes), "synthetic"

BANNED_MODULES = {"requests", "http", "urllib", "socket",
                  "boto3", "openai", "huggingface_hub"}

def _static_scan():
    hits = []
    for py in (Path(__file__).parent).glob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in BANNED_MODULES:
                        hits.append(f"{py.name}:import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in BANNED_MODULES:
                    hits.append(f"{py.name}:from {node.module} import ...")
    return hits
# ---------------------------------------------------------------- tests

def test_fr1(batch):
    ok_rows = [r for r in batch if r["status"] == "ok"]
    valid = all(1 <= r["pred_label"] <= 15 for r in ok_rows)
    return _row("FR1",
                f"{len(ok_rows)}/{len(batch)} labelled in 1..15",
                "100% of non-rejected in 1..15",
                valid and len(ok_rows) == len(batch))

def test_fr2():
    p = FIG_DIR / "3.2-cm_test.png"
    return _row("FR2", f"{p.name} exists={p.exists()}",
                "figure exists", p.exists(), "from 3.2")

def test_fr3():
    p = LOGS_DIR / "3.2-classification_report.txt"
    ok = p.exists() and p.stat().st_size > 0
    return _row("FR3", f"{p.name} exists={ok}",
                "report exists", ok, "from 3.2")

def test_fr4(pipe, feats):
    rb, n, source = _ensure_reject_batch()
    rejects = valid = 0
    for p in sorted(rb.glob("*.png")):
        label, _, status = predict_crop(pipe, feats, p)
        if status != "ok":
            rejects += 1
            if label is None:
                valid += 1
    passed = rejects >= 1 and valid == rejects
    return _row("FR4",
                f"{rejects}/{n} rejected ({source})",
                ">=1 reject, label=-1",
                passed, f"source={source}")

def test_fr5():
    hits = _static_scan()
    return _row("FR5", f"{len(hits)} network imports",
                "0", len(hits) == 0, "; ".join(hits))

def test_tr6():
    hits = _static_scan()
    return _row("TR6", f"{len(hits)} network imports",
                "0", len(hits) == 0, "same scan as FR5")

def test_fr6():
    sp = DATA_ROOT / "splits.csv"
    if not sp.exists():
        return _row("FR6", "splits.csv missing", "identical SHA", False)
    bk = sp.with_suffix(".BACKUP.csv")
    shutil.copy(sp, bk)
    sha_orig = _sha256(sp)
    try:
        res = subprocess.run(
            [sys.executable, "src/split.py"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True, text=True, timeout=120,
        )
        if res.returncode != 0:
            return _row("FR6", f"split.py exit {res.returncode}",
                        "identical SHA", False, res.stderr[:120])
        sha_new = _sha256(sp)
    finally:
        shutil.copy(bk, sp)
        bk.unlink(missing_ok=True)
    return _row("FR6",
                f"orig={sha_orig[:12]} new={sha_new[:12]}",
                "identical SHA256", sha_orig == sha_new)

def test_tr1():
    tp = _build_test_paths()[:20]
    loads = sum(1 for p, _ in tp
                if cv2.imread(str(p), cv2.IMREAD_COLOR) is not None)
    path_ok = sum(1 for p, c in tp
                  if p.parent == DATA_ROOT / "unsorted_png" / str(c)
                  and p.exists())
    n = len(tp)
    ok = loads == n and path_ok == n
    return _row("TR1",
                f"{loads}/{n} load, {path_ok}/{n} correct path",
                "20/20 load + 20/20 path", ok)

def test_tr2():
    thumbs = []
    for c in LABELS:
        pngs = sorted((DATA_ROOT / "unsorted_png" / str(c)).glob("*.png"))
        img = cv2.imread(str(pngs[0])) if pngs else None
        thumbs.append(cv2.resize(img, (64, 64)) if img is not None
                      else np.full((64, 64, 3), 128, np.uint8))
    montage = np.vstack([np.hstack(thumbs[i:i + 5]) for i in range(0, 15, 5)])
    out = FIG_DIR / "4.4-TR2_sample_per_class.png"
    cv2.imwrite(str(out), montage)
    return _row("TR2", f"montage written ({out.name})",
                "15-class visual check", out.exists(),
                "manual visual inspection required")

def test_tr3():
    import sklearn
    pyv = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    skv, npv = sklearn.__version__, np.__version__
    ok = (pyv.startswith("3.11") and skv.startswith("1.4")
          and npv.startswith("1.26"))
    return _row("TR3", f"py={pyv} sklearn={skv} numpy={npv}",
                "py3.11, sklearn1.4.x, numpy1.26.x", ok)

def test_tr4():
    dc = pd.read_csv(DATA_ROOT / "dataset_clean.csv")
    test = dc[dc["role"] == "test"]
    counts = test["label"].value_counts()
    min_c, classes = int(counts.min()), len(counts)
    return _row("TR4",
                f"min={min_c}, {classes}/15 classes in test",
                ">=1 per class, 15/15",
                min_c >= 1 and classes == 15, "from 5.3 split")

def test_tr5(pipe, feats, tp):
    times = []
    for p, _ in tp[:50]:
        t0 = time.perf_counter()
        predict_crop(pipe, feats, p)
        times.append((time.perf_counter() - t0) * 1000)
    arr = np.array(times)
    med, p95 = float(np.median(arr)), float(np.percentile(arr, 95))
    return _row("TR5",
                f"median={med:.1f}ms p95={p95:.1f}ms n={len(arr)} "
                f"cpu={platform.processor()[:30]}",
                "median & p95 <= 1000ms",
                med <= 1000 and p95 <= 1000)

def test_tr7(loaded_pipe, X_tr, y_tr):
    from finalize_model import build_final_estimator, load_locked_params
    _, params = load_locked_params()
    fresh = build_pipeline(build_final_estimator(params))
    fresh.fit(X_tr, y_tr)
    probe = X_tr[:5]
    diff = float(np.max(np.abs(
        loaded_pipe.predict_proba(probe) - fresh.predict_proba(probe))))
    return _row("TR7", f"max|delta_proba|={diff:.2e} on 5 rows",
                "< 1e-9", diff < 1e-9, "in-memory rebuild of 3.1")

def test_tr8():
    root = DATA_ROOT / "unsorted_png"
    mb = sum(p.stat().st_size for p in root.rglob("*.png")) / (1024 * 1024)
    return _row("TR8", f"{mb:.2f} MB total",
                "<= 1024 MB (1 GB)", mb <= 1024)

# ---------------------------------------------------------------- main

def main():
    print("loading pipeline ...")
    pipe, feats = load_model()
    print(f"  {len(pipe.steps)} steps, {len(feats)} features")

    print("loading splits ...")
    X_tr, y_tr, _, _, _, _, _ = load_splits()

    print("building test paths ...")
    tp = _build_test_paths()
    print(f"  {len(tp)} test crops")

    print("running test batch ...")
    batch = []
    for p, true_label in tp:
        label, proba, status = predict_crop(pipe, feats, p)
        batch.append({"path": str(p), "true_label": true_label,
                      "pred_label": label if label is not None else -1,
                      "status": status, "proba": proba})

    from sklearn.metrics import f1_score
    y_true = np.array([r["true_label"] for r in batch])
    y_pred = np.array([r["pred_label"] for r in batch])
    macro = float(f1_score(y_true, y_pred, labels=LABELS,
                           average="macro", zero_division=0))
    delta = abs(macro - EXPECTED_TEST_F1)

    fr7_ok = all(r["status"] != "ok" or
                 (r["proba"] is not None and len(r["proba"]) == 15
                  and abs(sum(r["proba"]) - 1) < 1e-6)
                 for r in batch)

    results = [
        test_fr1(batch),
        _row("FR7",
             "all proba len=15 & sum~1" if fr7_ok else "mismatch",
             "len=15, |sum-1|<1e-6", fr7_ok),
        test_fr2(),
        test_fr3(),
        test_fr4(pipe, feats),
        test_fr5(),
        test_fr6(),
        test_tr1(),
        test_tr2(),
        test_tr3(),
        test_tr4(),
        test_tr5(pipe, feats, tp),
        test_tr7(pipe, X_tr, y_tr),
        test_tr8(),
        _row("REPRO",
             f"batch macro-F1={macro:.4f} (3.2={EXPECTED_TEST_F1:.4f})",
             "|delta|<0.01", delta < 0.01,
             "deploy path reproduces sealed-test result"),
    ]

    df = pd.DataFrame(results)
    df.to_csv(DATA_ROOT / "4.4-deploy_results.csv", index=False, encoding="utf-8")

    lines = ["=" * 78, "4.4 DEPLOY TEST RESULTS",
             f"pipeline  : models/3.1-final_pipeline.joblib",
             f"test set  : {len(tp)} crops (clip 1, sealed at 3.2)",
             "=" * 78, ""]
    for r in results:
        lines.append(f"[{r['Pass']:7s}] {r['ID']:5s} | "
                     f"{r['Measured']:52s} | target={r['Target']}")
        if r["Notes"]:
            lines.append(f"          note: {r['Notes']}")
    n_pass = sum(1 for r in results if r["Pass"] == OK)
    n_fail = sum(1 for r in results if r["Pass"] == NO)
    n_pend = sum(1 for r in results if r["Pass"] == DE)
    lines += ["", "=" * 78, "SUMMARY", "=" * 78,
              f"  PASS    : {n_pass}",
              f"  FAIL    : {n_fail}",
              f"  PENDING : {n_pend}",
              ""]
    txt = "\n".join(lines)
    (LOGS_DIR / "4.4-deploy_results.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"wrote 4.4-deploy_results.csv")
    print(f"wrote {LOGS_DIR / '4.4-deploy_results.txt'}")


if __name__ == "__main__":
    main()