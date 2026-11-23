"""Deterministic labelled *synthetic* detector fixture; NOT real-world validation."""
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgevision.evaluation import evaluate_sequence
from edgevision.pipeline import MotionPipeline


def run(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    # Ground truth comes from geometric scene specification, not detections.
    # Warmup and scored phases are explicit to prevent false accuracy claims.
    with_tracker = MotionPipeline(min_area=75, history=200)
    try:
        for step in range(100):
            frame = np.full((240, 320, 3), 30, dtype=np.uint8)
            gt = []
            if step >= 20:
                x = 10 + (step - 20) * 2
                y = 90
                gt = [(x, y, 30, 24)]
                cv2.rectangle(frame, (x, y), (x + 29, y + 23), (230, 230, 230), -1)
            _, tracks, _ = with_tracker.process(frame)
            # Includes only visible detections: missed C++ tracks are excluded.
            predictions = [t['box'] for t in tracks if t['missed'] == 0]
            if step >= 20:
                frames.append((gt, predictions))
    finally:
        with_tracker.close()
    report = evaluate_sequence(frames)
    report.update({'dataset': 'synthetic_single_moving_rectangle', 'scored_frames': len(frames),
                   'warmup_frames': 20, 'source': 'deterministically rendered synthetic geometry',
                   'limitations': 'Not real footage. Single object, clean background, no occlusion or class labels.'})
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else 'artifacts/v04_synthetic_evaluation.json'), indent=2))
