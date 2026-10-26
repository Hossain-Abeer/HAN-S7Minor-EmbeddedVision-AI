"""
9.3 BUILD PREPROCESSING PIPELINE

Factory that returns an sklearn Pipeline: scaler -> classifier.

Why a Pipeline instead of a pre-scaled dataset:
    When a Pipeline sits inside cross_val_score / GridSearchCV, sklearn
    RE-FITS the entire pipeline -- including the scaler -- inside each CV
    fold, using only that fold's training portion. The held-out fold is
    transformed using scaler parameters derived only from the training
    portion. No leakage. Val/test statistics never touch the scaler.

Design reference: designtracker-1.7.3 (R1 addendum applied)

Run from repo root:
    python src/pipeline.py        # smoke test
"""

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================================
# [PARAMETERS - FILL IN BEFORE RUN]
# ============================================================================
SCALER_CLASS          = StandardScaler     # from 9.2 decision
FEATURE_STEP_NAME     = "scaler"           # routes scaler params as scaler__*
CLASSIFIER_STEP_NAME  = "clf"              # routes classifier params as clf__*


# ============================================================================
# FACTORY
# ============================================================================
def build_pipeline(classifier):
    """
    Return an sklearn Pipeline: scaler -> classifier.

    PRECONDITIONS (caller's responsibility):
      * X must contain NUMERIC FEATURE COLUMNS ONLY.
        Do NOT pass filename, label, or role columns. StandardScaler
        will raise ValueError at fit time with a message that points at
        the scaler, not at the actual mistake.
      * X must contain the same 15 retained feature columns used at 8.3.
        Column order does not matter to the scaler, but consistency
        across train/val/test is required.

    DO NOT:
      * Pass a pre-fitted scaler. The Pipeline must own it, so that
        GridSearchCV / cross_val_score can refit per fold.
      * Pass a pre-fitted classifier. The Pipeline must own both steps
        in an unfitted state; refit-per-fold requires this.

    Arguments:
        classifier : an UNFITTED sklearn classifier
                     (SVC(), KNeighborsClassifier(), RandomForestClassifier())

    Returns:
        sklearn.pipeline.Pipeline with two steps:
            ("scaler", StandardScaler())
            ("clf",    classifier)
    """
    return Pipeline([
        (FEATURE_STEP_NAME,    SCALER_CLASS()),
        (CLASSIFIER_STEP_NAME, classifier),
    ])


# ============================================================================
# SMOKE TEST (run once before Phase 2 commits)
# ============================================================================
if __name__ == "__main__":
    from sklearn.dummy import DummyClassifier

    pipe = build_pipeline(DummyClassifier())
    print(pipe)
    # Expect:
    #   Pipeline(steps=[('scaler', StandardScaler()),
    #                   ('clf',    DummyClassifier())])

    # Also print the param-grid keys Phase 2 will use
    print("\nHyperparameter grid keys for Phase 2:")
    print("  clf__C, clf__gamma          (for SVC)")
    print("  clf__n_neighbors, clf__weights   (for KNeighborsClassifier)")
    print("  clf__n_estimators, clf__max_depth (for RandomForestClassifier)")