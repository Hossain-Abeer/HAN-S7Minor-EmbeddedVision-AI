# ===== Paths =====
DATA_ROOT    = r"D:\HAN\Semester 7 Minor\billiards-game-clips"
CLIP_DIR     = DATA_ROOT + r"\game1"
CROP_ROOT    = DATA_ROOT + r"\unsorted_png"
MASK_ROOT    = DATA_ROOT + r"\mask_png"
LOGS_DIR     = DATA_ROOT + r"\logs"
FIGURES_DIR  = DATA_ROOT + r"\figures"
SPLITS_CSV   = DATA_ROOT + r"\splits.csv"
FEATURES_CSV = DATA_ROOT + r"\features.csv"
DATASET_CSV  = DATA_ROOT + r"\dataset.csv"
REJECT_LOG      = LOGS_DIR + r"\rejects_extract.csv"
MASK_REJECT_LOG = LOGS_DIR + r"\rejects_mask.csv"

# ===== Extraction (1.2.3 + 1.2.4) =====
N_CLIPS = 5                          # Number of source clips to process.
FRAME_STRIDE = 1                     # Keep every Nth frame; primary volume knob (5→3 for more crops).
BLUR_THRESHOLD = 75.0                # Reject frames below this Laplacian variance (lower = sharper requirement).
DUP_THRESHOLD = 3.0                  # Reject frames whose mean pixel diff to last-kept is below this.
DUP_RESIZE_W = 160                   # Width to downscale to before computing duplicate diff.
DUP_RESIZE_H = 90                    # Height to downscale to before computing duplicate diff.
MOTION_THRESHOLD = 4.0               # Rejects fast-moving frames. Higher = more strict.

# ===== Detection (1.3.1) =====
MIN_BALL_AREA = 800                  # Reject contours smaller than this (px²): specks, HUD dots.
MAX_BALL_AREA = 6000                 # Reject contours larger than this (px²): merged blobs, border.
MIN_CIRCULARITY = 0.7                # Reject contours less round than this (1.0 = perfect circle).
DET_MORPH_KERNEL = 5                 # Kernel size (px) for detection-stage morphology.
DET_MORPH_OPEN = 2                   # Opening iterations: removes specks from ball mask.
DET_MORPH_CLOSE = 2                  # Closing iterations: fills holes inside ball mask.

# ===== Crop (1.3.2) =====
PADDING_PCT = 0.15                   # Expand each box by this fraction on all sides (preserves numeral + cloth ring).

# ===== Mask (1.5.1) =====
MASK_S_MAX = 60                      # Max saturation for "white" numeral pixels (raise if masks empty).
MASK_V_MIN = 180                     # Min brightness for "white" numeral pixels (lower to 150 if masks empty).
MASK_MORPH_KERNEL = 3                # Kernel size for mask morphology (smaller than detection).
MASK_MORPH_OPEN = 1                  # Opening iterations on mask: removes specks, preserves numeral edges.
MASK_MORPH_CLOSE = 0                 # CRITICAL: must stay 0; closing would fill numeral holes.
MIN_MASK_AREA = 30                   # Reject crops whose mask has fewer than this many pixels.