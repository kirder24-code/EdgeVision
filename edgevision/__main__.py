import argparse
import json
import os
from pathlib import Path
import statistics
import time

import cv2
import psutil

from .pipeline import MotionPipeline


def run(source, output, metrics, *, max_frames=0, width=640, height=480, min_area=350):
    source_arg = int(source) if str(source).isdigit() else str(source)
    cap = cv2.VideoCapture(source_arg)
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open video source: {source}')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    fps_source = cap.get(cv2.CAP_PROP_FPS)
    fps_source = fps_source if 0 < fps_source <= 240 else 25.0
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path = Path(metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    samples = []
    frame_count = 0
    detections = 0
    peak_rss = psutil.Process(os.getpid()).memory_info().rss
    started = time.perf_counter()
    pipe = MotionPipeline(min_area=min_area)
    try:
        while not max_frames or frame_count < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*'MJPG'), fps_source, (w, h))
                if not writer.isOpened():
                    raise RuntimeError(f'Cannot create output video: {output}')
            t0 = time.perf_counter_ns()
            rendered, tracks, n = pipe.process(frame)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            samples.append(elapsed_ms)
            detections += n
            writer.write(rendered)
            frame_count += 1
            peak_rss = max(peak_rss, psutil.Process(os.getpid()).memory_info().rss)
    finally:
        cap.release()
        pipe.close()
        if writer:
            writer.release()
    wall = time.perf_counter() - started
    if not samples:
        raise RuntimeError('No frames decoded')
    s = sorted(samples)
    pct = lambda p: s[min(len(s) - 1, max(0, int((len(s) - 1) * p)))]
    report = {
        'source': str(source), 'output': str(output), 'frames_processed': frame_count,
        'detections_total': detections, 'source_fps': fps_source,
        'processing_fps_excluding_io': round(1000 * frame_count / sum(samples), 2),
        'end_to_end_fps_including_io': round(frame_count / wall, 2),
        'processing_latency_ms': {'p50': round(statistics.median(samples), 3),
                                  'p95': round(pct(0.95), 3), 'max': round(max(samples), 3)},
        'peak_process_rss_mb': round(peak_rss / 2**20, 2),
        'duration_seconds': round(wall, 3),
        'limitations': 'CPU/file benchmark; no camera latency or dropped-frame accounting; MOG2 motion, not semantic object recognition'
    }
    metrics_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description='EdgeVision CPU motion detection + native C++ tracking')
    parser.add_argument('--source', required=True, help='File path or camera index (e.g. 0)')
    parser.add_argument('--output', default='artifacts/annotated.avi')
    parser.add_argument('--metrics', default='artifacts/metrics.json')
    parser.add_argument('--max-frames', type=int, default=0)
    parser.add_argument('--min-area', type=int, default=350)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.metrics, max_frames=args.max_frames,
                         min_area=args.min_area), indent=2))


if __name__ == '__main__':
    main()
