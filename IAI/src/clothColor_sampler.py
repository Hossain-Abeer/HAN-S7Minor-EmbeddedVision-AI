import cv2
import numpy as np

# ==============================================================================
# DATA PATH (Absolute path to maintain data/src separation)
# ==============================================================================
IMG_PATH = r"D:\HAN\Semester 7 Minor\billiards-game-clips\game1\clothColor_noAspectRatio.png"

# ==============================================================================
# INTERACTION LOGIC
# ==============================================================================
image = cv2.imread(IMG_PATH)
if image is None:
    print(f"Error: Image not found at {IMG_PATH}")
    exit()

hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
img_display = image.copy()

print("Instructions:")
print("  - LEFT CLICK (without moving): Sample a single pixel (great for cue ball or pockets)")
print("  - LEFT CLICK + DRAG: Draw a box to get regional min/max (great for the whole cloth)")
print("  - Press 'q' or 'ESC' to quit.")

drawing = False
ix, iy = -1, -1

def print_pixel(x, y):
    h, s, v = hsv[y, x]
    print(f"\n[Single Pixel] X:{x} Y:{y} -> H:{h}, S:{s}, V:{v}")

def print_region(x1, y1, x2, y2):
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    
    roi_hsv = hsv[y_min:y_max, x_min:x_max]
    if roi_hsv.size == 0:
        return
        
    flat_roi = roi_hsv.reshape(-1, 3)
    
    h_min, h_max = np.min(flat_roi[:, 0]), np.max(flat_roi[:, 0])
    s_min, s_max = np.min(flat_roi[:, 1]), np.max(flat_roi[:, 1])
    v_min, v_max = np.min(flat_roi[:, 2]), np.max(flat_roi[:, 2])

    print(f"\n[Region] Bounds from box ({x_min},{y_min}) to ({x_max},{y_max}):")
    print(f"  RAW H: {h_min} to {h_max}")
    print(f"  RAW S: {s_min} to {s_max}")
    print(f"  RAW V: {v_min} to {v_max}")
    print("-" * 40)

def draw_rect(event, x, y, flags, param):
    global ix, iy, drawing, img_display
    
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
        img_display = image.copy()
        
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = image.copy()
            cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
            cv2.imshow("Cloth Sampler", img_copy)
            
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.rectangle(img_display, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.imshow("Cloth Sampler", img_display)
        
        # Check if it was just a click (no drag) or a drag
        if abs(x - ix) < 3 and abs(y - iy) < 3:
            print_pixel(x, y)
        else:
            print_region(ix, iy, x, y)

# CHANGED: Using WINDOW_NORMAL instead of WINDOW_AUTOSIZE to allow resizing large 1080p images
cv2.namedWindow("Cloth Sampler", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Cloth Sampler", draw_rect)
cv2.imshow("Cloth Sampler", image)

while True:
    k = cv2.waitKey(1) & 0xFF
    if k == ord('q') or k == 27:
        break

cv2.destroyAllWindows()