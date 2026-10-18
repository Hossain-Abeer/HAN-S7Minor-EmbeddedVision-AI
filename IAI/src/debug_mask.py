# src/debug_mask.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import config
import constants as C

def main():
    # Path to the video (update if testing a different clip)
    video_path = r'D:\HAN\Semester 7 Minor\billiards-game-clips\game1\billiards-game-clip1.mp4'
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print('Failed to read frame from video.')
        return

    # --- HSV Cloth Mask Logic ---
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    cloth_lo = np.array([C.CLOTH_H_LO, C.CLOTH_S_LO, C.CLOTH_V_LO])
    cloth_hi = np.array([C.CLOTH_H_HI, C.CLOTH_S_HI, C.CLOTH_V_HI])
    
    cloth_mask = cv2.inRange(hsv, cloth_lo, cloth_hi)
    ball_mask = cv2.bitwise_not(cloth_mask)

    # --- Morphology ---
    kernel = np.ones((config.DET_MORPH_KERNEL, config.DET_MORPH_KERNEL), np.uint8)
    ball_mask = cv2.morphologyEx(ball_mask, cv2.MORPH_OPEN, kernel, iterations=config.DET_MORPH_OPEN)
    ball_mask = cv2.morphologyEx(ball_mask, cv2.MORPH_CLOSE, kernel, iterations=config.DET_MORPH_CLOSE)

    # --- Save to logs folder ---
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    out_path = os.path.join(config.LOGS_DIR, 'debug_mask.png')
    cv2.imwrite(out_path, ball_mask)
    print(f"Saved mask to: {out_path}")

    # --- Find Contours ---
    contours, _ = cv2.findContours(ball_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    print(f'Found {len(contours)} raw contours.')
    
    for i, c in enumerate(contours[:10]):
        area = cv2.contourArea(c)
        perim = cv2.arcLength(c, True)
        circ = 4 * np.pi * area / (perim**2) if perim > 0 else 0
        x, y, w, h = cv2.boundingRect(c)
        print(f'Contour {i}: Area={area:.1f}, Circularity={circ:.2f}, WxH={w}x{h}')

if __name__ == "__main__":
    main()