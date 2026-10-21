#!/usr/bin/env python3
"""
Prepare portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. bilateral-smooth away texture while keeping drawn lines sharp
  3. stretch tones over subject only
  4. darken line work
  5. composite onto white with defensive bounds checking and square crop

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Usage: python scripts/prep_photo.py <input.png> [output.png]
"""
import os
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INP = os.path.join(HERE, "..", "source-photo.png")
DEFAULT_OUT = os.path.join(HERE, "..", "source-prepped.png")


def crop_subject_bounds(alpha: Any, out: Any) -> Any:
    """Crop square around subject using alpha mask with defensive bounds checking."""
    import numpy as np

    ys, xs = np.where(alpha > 20)
    if len(xs) == 0 or len(ys) == 0:
        # Safe fallback if no pixels match (transparent image or error)
        return out.copy()

    side = max(int(xs.max()) - int(xs.min()), int(ys.max()) - int(ys.min())) + 60
    cx, cy = (int(xs.min()) + int(xs.max())) // 2, (int(ys.min()) + int(ys.max())) // 2
    canvas = np.full((side, side), 255, dtype=np.uint8)
    x0, y0 = cx - side // 2, cy - side // 2
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, out.shape[1]), min(y0 + side, out.shape[0])

    canvas[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = out[sy0:sy1, sx0:sx1].astype(np.uint8)
    return canvas


def process_photo(inp_path: str = DEFAULT_INP, out_path: str = DEFAULT_OUT) -> None:
    """Run full image preprocessing pipeline."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        from rembg import remove
    except ImportError as e:
        raise ImportError(f"Required image processing library missing: {e}")

    LINE_WEIGHT = 0.6

    cut = remove(Image.open(inp_path).convert("RGBA"))
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    smooth = gray
    for _ in range(3):
        smooth = cv2.bilateralFilter(smooth, 9, 40, 9)

    subject_mask = alpha > 128
    if np.any(subject_mask):
        lo, hi = np.percentile(smooth[subject_mask], [2, 92])
        tone = np.clip((smooth.astype(np.float32) - lo) / (hi - lo), 0, 1) if hi > lo else smooth.astype(np.float32) / 255.0
    else:
        tone = smooth.astype(np.float32) / 255.0

    fine = cv2.GaussianBlur(smooth, (0, 0), 1.5).astype(np.float32)
    coarse = cv2.GaussianBlur(smooth, (0, 0), 6).astype(np.float32)
    lines = np.clip((coarse - fine) / 40.0, 0, 1)
    out = np.clip(tone - LINE_WEIGHT * lines, 0, 1) * 255

    mask = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
    out = out * mask + 255.0 * (1.0 - mask)

    canvas = crop_subject_bounds(alpha, out)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    Image.fromarray(canvas, mode="L").save(out_path)
    print("Wrote", out_path, canvas.shape)


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INP
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    process_photo(inp, out)
