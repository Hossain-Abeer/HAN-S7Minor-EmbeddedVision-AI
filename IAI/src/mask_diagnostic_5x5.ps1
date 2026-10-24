python -c "
import cv2, numpy as np
p = r'D:\HAN\Semester 7 Minor\billiards-game-clips\mask_png\8\clip1_frame000084_ball6_mask.png'
m = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
k = np.ones((5,5), np.uint8)
closed = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
cv2.imwrite('closed_test.png', closed)
n_before = cv2.connectedComponentsWithStats(m, 8)[0] - 1
n_after  = cv2.connectedComponentsWithStats(closed, 8)[0] - 1
print(f'CC before: {n_before}, CC after close: {n_after}')
inv = cv2.bitwise_not(closed)
n_h, _, stats_h, _ = cv2.connectedComponentsWithStats(inv, 8)
h, w = closed.shape
holes = [i for i in range(1, n_h) if not (stats_h[i][0]==0 or stats_h[i][1]==0 or stats_h[i][0]+stats_h[i][2]==w or stats_h[i][1]+stats_h[i][3]==h) and stats_h[i][4]>=5]
print(f'holes after close: {len(holes)}')
"