# src/extract_crop.py
import os
import csv
import cv2
import numpy as np

import config
import constants as C

# Module-level state for duplicate detection
_last_kept_frame = None

def log_reject(reason, clip_id, frame_idx, metric_value):
    """Append one row to the reject log."""
    new_file = not os.path.exists(config.REJECT_LOG)
    with open(config.REJECT_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["reason", "clip_id", "frame_idx", "metric_value"])
        w.writerow([reason, clip_id, frame_idx, f"{metric_value:.4f}"])

def passes_filter(frame, clip_id, frame_idx):
    """Return True if frame survives blur + duplicate gates."""
    global _last_kept_frame

    # (a) Blur gate - Laplacian variance
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if lap_var < config.BLUR_THRESHOLD:
        log_reject("blur", clip_id, frame_idx, lap_var)
        return False

    # (b) Duplicate gate - mean abs diff to last KEPT frame
    if _last_kept_frame is not None:
        a = cv2.resize(frame, (config.DUP_RESIZE_W, config.DUP_RESIZE_H))
        b = cv2.resize(_last_kept_frame, (config.DUP_RESIZE_W, config.DUP_RESIZE_H))
        diff = float(np.mean(cv2.absdiff(a, b)))
        if diff < config.DUP_THRESHOLD:
            log_reject("duplicate", clip_id, frame_idx, diff)
            return False

    _last_kept_frame = frame
    return True

def detect_balls(frame):
    """Return list of (x, y, w, h) bounding boxes for ball candidates."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Pull cloth bounds from constants.py
    cloth_lo = np.array([C.CLOTH_H_LO, C.CLOTH_S_LO, C.CLOTH_V_LO])
    cloth_hi = np.array([C.CLOTH_H_HI, C.CLOTH_S_HI, C.CLOTH_V_HI])
    
    cloth_mask = cv2.inRange(hsv, cloth_lo, cloth_hi)
    ball_mask = cv2.bitwise_not(cloth_mask)

    # Morphology from config.py
    kernel = np.ones((config.DET_MORPH_KERNEL, config.DET_MORPH_KERNEL), np.uint8)
    ball_mask = cv2.morphologyEx(ball_mask, cv2.MORPH_OPEN, kernel,
                                 iterations=config.DET_MORPH_OPEN)
    ball_mask = cv2.morphologyEx(ball_mask, cv2.MORPH_CLOSE, kernel,
                                 iterations=config.DET_MORPH_CLOSE)

    contours, _ = cv2.findContours(ball_mask, cv2.RETR_LIST,
                                   cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (config.MIN_BALL_AREA <= area <= config.MAX_BALL_AREA):
            continue
        perim = cv2.arcLength(c, True)
        if perim == 0:
            continue
        circularity = 4.0 * np.pi * area / (perim ** 2)
        if circularity < config.MIN_CIRCULARITY:
            continue
        
        x, y, w, h = cv2.boundingRect(c)
        regions.append((x, y, w, h))

    return regions

def crop_and_save(frame, regions, clip_id, frame_idx):
    """Write one padded PNG per region."""
    os.makedirs(config.CROP_ROOT, exist_ok=True)
    H, W = frame.shape[:2]
    written = 0

    for k, (x, y, w, h) in enumerate(regions):
        pad_x = int(w * config.PADDING_PCT)
        pad_y = int(h * config.PADDING_PCT)
        
        # Clamp to frame bounds
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(W, x + w + pad_x)
        y1 = min(H, y + h + pad_y)

        crop = frame[y0:y1, x0:x1]
        name = f"clip{clip_id}_frame{frame_idx:06d}_ball{k}.png"
        path = os.path.join(config.CROP_ROOT, name)

        if cv2.imwrite(path, crop):
            written += 1
        else:
            print(f"[WARN] imwrite failed: {path}")

    return written

def main():
    global _last_kept_frame

    # Truncate reject log at the start of each run
    if os.path.exists(config.REJECT_LOG):
        os.remove(config.REJECT_LOG)

    dry_frames = int(os.environ.get("EVML_DRY_RUN_FRAMES", "0"))
    dry_clips  = int(os.environ.get("EVML_DRY_RUN_CLIPS",  "0"))

    total_kept = 0
    total_crops = 0

    clip_range = range(1, config.N_CLIPS + 1)
    if dry_clips > 0:
        clip_range = range(1, min(dry_clips, config.N_CLIPS) + 1)

    for clip_id in clip_range:
        path = os.path.join(config.CLIP_DIR, f"billiards-game-clip{clip_id}.mp4")
        if not os.path.exists(path):
            print(f"[WARN] missing clip: {path}")
            continue

        print(f"[INFO] Processing clip {clip_id}...")
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"[WARN] cannot open clip {clip_id}")
            continue

        _last_kept_frame = None
        
        # State machine variables
        prev_gray_small = None
        is_moving = True # Assume moving at start
        frames_since_move = 0

        frame_idx = 0
        kept = 0
        crops = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if dry_frames and frame_idx >= dry_frames:
                break

            # 1. Calculate Motion (Downscaled for speed and robustness)
            gray_small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (160, 90))
            
            if prev_gray_small is not None:
                motion_diff = cv2.absdiff(gray_small, prev_gray_small).mean()
            else:
                motion_diff = 999.0
                
            prev_gray_small = gray_small

            # 2. Update Motion State
            if motion_diff > config.MOTION_THRESHOLD:
                frames_since_move = 0
            else:
                frames_since_move += 1

            # 3. Trigger Extraction
            if frame_idx % config.FRAME_STRIDE == 0:
                # We check if the scene has been still for AT LEAST 3 frames
                if frames_since_move >= 3:
                    # passes_filter will reject if it's a duplicate (cooldown)
                    # or if it's blurry.
                    if passes_filter(frame, clip_id, frame_idx):
                        kept += 1
                        regions = detect_balls(frame)
                        crops += crop_and_save(frame, regions, clip_id, frame_idx)

            frame_idx += 1

        cap.release()
        print(f"[INFO] clip {clip_id}: frames={frame_idx} kept={kept} crops={crops}")
        total_kept  += kept
        total_crops += crops

    print(f"[DONE] total kept frames={total_kept} total crops={total_crops}")

if __name__ == "__main__":
    main()