import argparse
import json
import os
from pathlib import Path
import statistics
import time

import cv2
import psutil

from .pipeline import MotionPipeline
from .capture import CaptureWorker
from .recorder import percentile_nearest_rank, validate_output_paths


def run(source, output, metrics, *, max_frames=0, width=640, height=480, min_area=350,
        capture_mode="sync", queue_capacity=3):
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or max_frames < 0:
        raise ValueError("max_frames must be a nonnegative integer")
    validate_output_paths(output, metrics)
    if not str(source).isdigit():
        source_path = Path(source).resolve()
        if source_path == Path(output).resolve() or source_path == Path(metrics).resolve():
            raise ValueError("output and metrics paths must be different from input")
    if capture_mode not in ("sync", "buffered"):
        raise ValueError("capture_mode must be sync or buffered")
    if capture_mode == "buffered" and (not isinstance(queue_capacity, int) or queue_capacity <= 0):
        raise ValueError("queue_capacity must be positive")
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
    worker = None
    queue_wait_samples = []
    if capture_mode == "buffered":
        worker = CaptureWorker(cap, capacity=queue_capacity).start()

    def next_frames():
        if worker is not None:
            yield from worker.frames()
        else:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                yield frame

    try:
        for item in next_frames():
            if max_frames and frame_count >= max_frames:
                break
            if worker is not None:
                frame = item.frame
                queue_wait_samples.append(item.queue_wait_ms())
            else:
                frame = item
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
        try:
            if worker is not None:
                worker.stop()
            else:
                cap.release()
        finally:
            pipe.close()
            if writer:
                writer.release()
    wall = time.perf_counter() - started
    if not samples:
        raise RuntimeError('No frames decoded')
    s = sorted(samples)
    pct = lambda p: percentile_nearest_rank(s, p)
    report = {
        'source': str(source), 'output': str(output), 'frames_processed': frame_count,
        'detections_total': detections, 'source_fps': fps_source,
        'processing_fps_excluding_io': round(1000 * frame_count / sum(samples), 2),
        'end_to_end_fps_including_io': round(frame_count / wall, 2),
        'processing_latency_ms': {'p50': round(statistics.median(samples), 3),
                                  'p95': round(pct(0.95), 3), 'max': round(max(samples), 3)},
        'peak_process_rss_mb': round(peak_rss / 2**20, 2),
        'duration_seconds': round(wall, 3),
        'latency_percentile_definition': 'nearest rank (ceil(p * n))',
        'limitations': 'CPU/file benchmark; no camera latency or dropped-frame accounting; MOG2 motion, not semantic object recognition'
    }
    if worker is not None:
        wait_sorted = sorted(queue_wait_samples)
        report.update({
            'capture_mode': 'buffered',
            'capture_frames_read': worker.frames_read,
            'frames_dropped_overflow': worker.dropped_overflow,
            'frames_unprocessed': worker.frames_read - frame_count - worker.dropped_overflow,
            'queue_max_depth': worker.queue.max_depth,
            'queue_capacity': queue_capacity,
            'queue_wait_ms': {
                'p50': round(statistics.median(wait_sorted), 3),
                'p95': round(percentile_nearest_rank(wait_sorted, .95), 3),
                'max': round(max(wait_sorted), 3),
            },
            'timestamp_scope': 'monotonic clock after VideoCapture.read, NOT sensor exposure time',
        })
        report['limitations'] = ('CPU capture-to-consumer queue age, not glass-to-glass latency; '
                                 'software queue drops only; hardware/driver drops unknown; MOG2 motion, not semantic object recognition')
    metrics_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description='EdgeVision CPU motion detection + native C++ tracking')
    parser.add_argument('--source', required=True, help='File path or camera index (e.g. 0)')
    parser.add_argument('--output', default='artifacts/annotated.avi')
    parser.add_argument('--metrics', default='artifacts/metrics.json')
    parser.add_argument('--max-frames', type=int, default=0)
    parser.add_argument('--min-area', type=int, default=350)
    parser.add_argument('--capture-mode', choices=['sync', 'buffered'], default='sync')
    parser.add_argument('--queue-capacity', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.metrics, max_frames=args.max_frames,
                         min_area=args.min_area, capture_mode=args.capture_mode,
                         queue_capacity=args.queue_capacity), indent=2))


if __name__ == '__main__':
    main()
