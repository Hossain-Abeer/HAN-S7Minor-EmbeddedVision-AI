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
N_CLIPS          = 5
FRAME_STRIDE     = 5
BLUR_THRESHOLD   = 100.0
DUP_THRESHOLD    = 5.0
DUP_RESIZE_W     = 160
DUP_RESIZE_H     = 90

# ===== Detection (1.3.1) =====
MIN_BALL_AREA    = 2000
MAX_BALL_AREA    = 20000
MIN_CIRCULARITY  = 0.7
DET_MORPH_KERNEL = 5
DET_MORPH_OPEN   = 2
DET_MORPH_CLOSE  = 2

# ===== Crop (1.3.2) =====
PADDING_PCT      = 0.15

# ===== Mask (1.5.1) =====
MASK_S_MAX        = 60
MASK_V_MIN        = 180
MASK_MORPH_KERNEL = 3
MASK_MORPH_OPEN   = 1
MASK_MORPH_CLOSE  = 0
MIN_MASK_AREA     = 30