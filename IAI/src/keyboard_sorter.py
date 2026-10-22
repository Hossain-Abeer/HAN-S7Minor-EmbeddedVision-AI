"""
4.2 KEYBOARD SORTER

Opens each crop left in unsorted_png, shows it, waits for a key.
Moves the crop into the matching class folder (1-15) or deletes it.

KEYS:
  1 2 3 4 5 6 7 8 9  -> classes 1 to 9
  q                  -> class 10
  w                  -> class 11
  e                  -> class 12
  a                  -> class 13
  s                  -> class 14
  d                  -> class 15
  x                  -> DELETE this crop (junk)
  space              -> SKIP (leave for a later session)
  ESC                -> quit

Run from repo root:
  python src/keyboard_sorter.py
"""

import os
import shutil
import tkinter as tk
from PIL import Image, ImageTk

CROP_ROOT = r"D:\HAN\Semester 7 Minor\billiards-game-clips\unsorted_png"
DISPLAY_SIZE = 320

KEY_TO_CLASS = {
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
    '6': 6, '7': 7, '8': 8, '9': 9,
    'q': 10, 'w': 11, 'e': 12,
    'a': 13, 's': 14, 'd': 15,
}


class Sorter:
    def __init__(self, root):
        self.root = root
        self.root.title("4.2 Sorter")

        self.files = sorted(
            f for f in os.listdir(CROP_ROOT)
            if f.lower().endswith('.png')
            and os.path.isfile(os.path.join(CROP_ROOT, f))
        )
        self.idx = 0
        self.moved = 0
        self.deleted = 0
        self.skipped = 0
        self._tk_img = None

        self.img_label = tk.Label(root)
        self.img_label.pack()

        self.info = tk.Label(root, font=("Courier", 11), justify="left")
        self.info.pack(fill="x", padx=8, pady=4)

        self.keys = tk.Label(root, font=("Courier", 9), justify="left", fg="#555555")
        self.keys.pack(fill="x", padx=8, pady=2)
        self.keys.config(
            text="1-9 classes 1-9 | q,w,e 10,11,12 | a,s,d 13,14,15 "
                 "| x delete | space skip | ESC quit"
        )

        self._show_current()
        self.root.focus_force()
        self.root.bind("<Key>", self._on_key)

    def _show_current(self):
        while self.idx < len(self.files):
            path = os.path.join(CROP_ROOT, self.files[self.idx])
            if os.path.isfile(path):
                try:
                    img = Image.open(path).convert("RGB")
                except Exception as exc:
                    self._set_info(f"READ FAIL: {self.files[self.idx]}  ({exc})")
                    self.idx += 1
                    continue
                img.thumbnail((DISPLAY_SIZE, DISPLAY_SIZE))
                self._tk_img = ImageTk.PhotoImage(img)
                self.img_label.config(image=self._tk_img)
                self._set_info(
                    f"[{self.idx + 1}/{len(self.files)}]  {self.files[self.idx]}\n"
                    f"moved={self.moved}  deleted={self.deleted}  skipped={self.skipped}"
                )
                return
            self.idx += 1

        self.img_label.config(image="")
        self._set_info(
            f"DONE\nmoved={self.moved}  deleted={self.deleted}  skipped={self.skipped}"
        )

    def _set_info(self, text):
        self.info.config(text=text)

    def _on_key(self, event):
        k = event.keysym.lower()
        if k == "escape":
            self.root.quit()
            return
        if self.idx >= len(self.files):
            return

        fname = self.files[self.idx]
        path = os.path.join(CROP_ROOT, fname)

        if k == "space":
            self.skipped += 1
        elif k == "x":
            try:
                os.remove(path)
                self.deleted += 1
            except Exception:
                pass
        elif k in KEY_TO_CLASS:
            cls = KEY_TO_CLASS[k]
            dest_dir = os.path.join(CROP_ROOT, str(cls))
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.move(path, os.path.join(dest_dir, fname))
                self.moved += 1
            except Exception:
                pass
        else:
            return  # ignore unmapped keys, don't advance

        self.idx += 1
        self._show_current()


if __name__ == "__main__":
    if not os.path.isdir(CROP_ROOT):
        raise SystemExit(f"ERROR: {CROP_ROOT} not found")
    r = tk.Tk()
    Sorter(r)
    r.mainloop()