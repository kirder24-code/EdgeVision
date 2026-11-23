"""Deterministic moving-rectangle input; not a real-world detection benchmark."""
import argparse
from pathlib import Path
import cv2
import numpy as np


def generate(path, frames=180, width=640, height=480):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 30.0, (width, height))
    if not writer.isOpened():
        raise RuntimeError('Could not create synthetic video')
    try:
        for i in range(frames):
            frame = np.full((height, width, 3), 25, dtype=np.uint8)
            # White rectangle crosses frame; background is static.
            x = 20 + int((width - 95) * (i / max(frames - 1, 1)))
            cv2.rectangle(frame, (x, height // 3), (x + 65, height // 3 + 50), (245, 245, 245), -1)
            writer.write(frame)
    finally:
        writer.release()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='artifacts/synthetic.avi')
    p.add_argument('--frames', type=int, default=180)
    args = p.parse_args()
    generate(args.output, frames=args.frames)
