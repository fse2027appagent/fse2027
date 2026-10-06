"""Standalone PaddleOCR worker.

This module is deliberately invoked in a fresh Python process by Page.  It
prevents PaddlePaddle's native thread runtime from sharing a process with
PyTorch/Ultralytics on Apple Silicon.
"""

import contextlib
import json
import os
import sys

import cv2

from ocr import get_ocr


def main(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    # Third-party model loading is noisy on stdout.  Reserve stdout for the
    # one machine-readable result consumed by the parent process.
    with contextlib.redirect_stdout(sys.stderr):
        ocr = get_ocr()
        text_items = ocr.extract_text_all(image) or []

        results = []
        for item in text_items:
            bounds = item["bounds"]
            h, w = image.shape[:2]
            x1, y1 = max(0, bounds.x1), max(0, bounds.y1)
            x2, y2 = min(w, bounds.x2), min(h, bounds.y2)
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            text, _ = ocr.extract_text_part(crop, x2 - x1, y2 - y1)
            if text:
                results.append({"text": text, "bounds": [x1, y1, x2, y2]})

    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python ocr_worker.py <image-path>")
    main(os.path.abspath(sys.argv[1]))
