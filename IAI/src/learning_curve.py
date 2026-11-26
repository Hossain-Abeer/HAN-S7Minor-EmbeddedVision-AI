"""2.7 - Learning curves for rf (selected) and svc (runner-up).

Train/CV only. Val ignored (L16: distribution shift).
Emits one figure per model + numeric log.
"""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold, learning_curve

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import build_pipeline
from load_dataset import load_splits
from train_models import CANDIDATES, SEED

DATA_ROOT  = Path(config.DATA_ROOT)
FIG_DIR    = Path(config.FIGURES_DIR)
LOGS_DIR   = Path(config.LOGS_DIR)
MODELS_DIR = DATA_ROOT / "models"

FIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = ["rf", "svc"]
SIZES = np.linspace(0.1, 1.0, 8)
CV    = 5
SCORING = "f1_macro"


def load_params(name):
    return json.loads(
        (MODELS_DIR / f"best_params_{name}.json").read_text())


def rebuild(name):
    base = CANDIDATES[name]
    params = load_params(name)
    return base.__class__(**{**base.get_params(), **params})


def curve_for(name, X, y):
    est  = rebuild(name)
    pipe = build_pipeline(est)
    skf  = StratifiedKFold(n_splits=CV, shuffle=True, random_state=SEED)
    sizes, tr_scores, cv_scores = learning_curve(
        pipe, X, y,
        train_sizes=SIZES,
        cv=skf,
        scoring=SCORING,
        n_jobs=-1,
        shuffle=True,
        random_state=SEED,
    )
    return (sizes,
            tr_scores.mean(axis=1), tr_scores.std(axis=1),
            cv_scores.mean(axis=1), cv_scores.std(axis=1))


def plot(name, sizes, tr_m, tr_s, cv_m, cv_s):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(sizes, tr_m, "o-", color="tab:blue",  label="train")
    ax.fill_between(sizes, tr_m - tr_s, tr_m + tr_s,
                    alpha=0.2, color="tab:blue")
    ax.plot(sizes, cv_m, "s-", color="tab:orange", label="CV")
    ax.fill_between(sizes, cv_m - cv_s, cv_m + cv_s,
                    alpha=0.2, color="tab:orange")
    ax.set_xlabel("training size")
    ax.set_ylabel(f"{SCORING}")
    ax.set_title(f"learning curve - {name}")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(0, 1)
    plt.tight_layout()
    fig.savefig(FIG_DIR / f"2.7-lc_{name}.png", dpi=150)
    plt.close(fig)


def verdict(name, sizes, tr_m, cv_m):
    gap_final = tr_m[-1] - cv_m[-1]
    slope_cv  = cv_m[-1] - cv_m[-2]
    if gap_final > 0.15 and slope_cv > 0.02:
        return "OVERFITTING (widening gap, CV still rising)"
    if gap_final > 0.15 and slope_cv <= 0.02:
        return "OVERFITTING (gap persisted, CV plateaued)"
    if tr_m[-1] < 0.80 and cv_m[-1] < 0.80 and gap_final < 0.10:
        return "UNDERFITTING (both low, converged)"
    if gap_final < 0.10 and slope_cv < 0.03:
        return "CONVERGED (small gap, CV flat)"
    return "WELL-FIT (small gap, CV still rising)"


def main():
    X_tr, y_tr, *_ = load_splits()
    print(f"train {X_tr.shape}")

    log_lines = []
    for name in PAIRS:
        print(f"[LC] {name} ...", flush=True)
        sizes, tr_m, tr_s, cv_m, cv_s = curve_for(name, X_tr, y_tr)
        plot(name, sizes, tr_m, tr_s, cv_m, cv_s)

        v = verdict(name, sizes, tr_m, cv_m)
        print(f"  verdict: {v}")
        for s, a, b in zip(sizes, tr_m, cv_m):
            print(f"  n={int(s):3d}  train={a:.3f}  cv={b:.3f}  gap={a-b:+.3f}")

        log_lines.append(f"\n[{name}]  verdict: {v}")
        for s, a, b in zip(sizes, tr_m, cv_m):
            log_lines.append(
                f"  n={int(s):3d}  train={a:.4f}  cv={b:.4f}  gap={a-b:+.4f}")

    (LOGS_DIR / "2.7-learning_curves.txt").write_text("\n".join(log_lines))
    print(f"\nwrote {LOGS_DIR / '2.7-learning_curves.txt'}")


if __name__ == "__main__":
    main()