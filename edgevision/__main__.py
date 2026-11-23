import argparse
import json
import hashlib
import os
from pathlib import Path
import statistics
import time

import cv2
import psutil

from .pipeline import MotionPipeline, SemanticPipeline
from .capture import CaptureWorker
from .recorder import percentile_nearest_rank, validate_output_paths


def run(source, output, metrics, *, max_frames=0, width=640, height=480, min_area=350,
        capture_mode="sync", queue_capacity=3, tracks_jsonl=None,
        detector="motion", model=None, semantic_detector=None, confidence=0.25, nms_iou=0.45):
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or max_frames < 0:
        raise ValueError("max_frames must be a nonnegative integer")
    validate_output_paths(output, metrics)
    if not str(source).isdigit():
        source_path = Path(source).resolve()
        if source_path == Path(output).resolve() or source_path == Path(metrics).resolve():
            raise ValueError("output and metrics paths must be different from input")
    if tracks_jsonl is not None:
        trace_path = Path(tracks_jsonl).resolve()
        if trace_path in (Path(output).resolve(), Path(metrics).resolve()):
            raise ValueError("track trace path must differ from video and metrics outputs")
        if not str(source).isdigit() and trace_path == Path(source).resolve():
            raise ValueError("track trace path must differ from input")
    if capture_mode not in ("sync", "buffered"):
        raise ValueError("capture_mode must be sync or buffered")
    if capture_mode == "buffered" and (not isinstance(queue_capacity, int) or queue_capacity <= 0):
        raise ValueError("queue_capacity must be positive")
    if detector not in ('motion', 'onnx'):
        raise ValueError('detector must be motion or onnx')
    if detector == 'onnx':
        from .onnx_detector import YoloRawDetector
        if semantic_detector is None and not model:
            raise ValueError('ONNX detector requires --model path.onnx')
        # Validate before creating an inference session or touching a video output.
        # The ONNX weights may represent the user's only local model copy.
        if model is not None:
            model_file = Path(model).resolve()
            reserved = {Path(output).resolve(), Path(metrics).resolve()}
            if tracks_jsonl is not None:
                reserved.add(Path(tracks_jsonl).resolve())
            if model_file in reserved:
                raise ValueError('Output paths must not overwrite the ONNX model')
            if not model_file.is_file():
                raise FileNotFoundError(f'ONNX model not found: {model_file}')
        if semantic_detector is None:
            semantic_detector = YoloRawDetector(model_path=model, confidence=confidence, iou=nms_iou)
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
    onnx_stages = {'preprocess': [], 'inference': [], 'postprocess': []}
    frame_count = 0
    detections = 0
    peak_rss = psutil.Process(os.getpid()).memory_info().rss
    started = time.perf_counter()
    pipe = MotionPipeline(min_area=min_area) if detector == 'motion' else SemanticPipeline(semantic_detector)
    worker = None
    queue_wait_samples = []
    trace_file = None
    if tracks_jsonl is not None:
        Path(tracks_jsonl).parent.mkdir(parents=True, exist_ok=True)
        trace_file = open(tracks_jsonl, 'w', encoding='utf-8')
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
            source_sequence = item.sequence if worker is not None else frame_count
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
            if detector == 'onnx' and hasattr(semantic_detector, 'last_timing_ms'):
                for stage in onnx_stages:
                    onnx_stages[stage].append(semantic_detector.last_timing_ms[stage])
            detections += n
            if trace_file is not None:
                trace_file.write(json.dumps({
                    'source_sequence': source_sequence,
                    'processing_latency_ms': round(elapsed_ms, 4),
                    'tracks': tracks,
                }) + '\n')
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
            if trace_file is not None:
                trace_file.close()
            if writer:
                writer.release()
    wall = time.perf_counter() - started
    if not samples:
        raise RuntimeError('No frames decoded')
    s = sorted(samples)
    pct = lambda p: percentile_nearest_rank(s, p)
    report = {
        'source': str(source), 'output': str(output), 'frames_processed': frame_count,
        'detector': detector,
        'inference': ('none_motion_only' if detector == 'motion' else
                      ('onnxruntime_cpu' if getattr(semantic_detector, 'loaded_from_file', False) else 'mock_session_not_real_model')),
        'detections_total': detections, 'source_fps': fps_source,
        'processing_fps_excluding_io': round(1000 * frame_count / sum(samples), 2),
        'end_to_end_fps_including_io': round(frame_count / wall, 2),
        'processing_latency_ms': {'p50': round(statistics.median(samples), 3),
                                  'p95': round(pct(0.95), 3), 'max': round(max(samples), 3)},
        'peak_process_rss_mb': round(peak_rss / 2**20, 2),
        'duration_seconds': round(wall, 3),
        'latency_percentile_definition': 'nearest rank (ceil(p * n))',
        'limitations': 'No camera latency or glass-to-glass measurement; host processing timing only; offline CPU benchmark' 
    }
    if detector == 'onnx' and all(onnx_stages.values()):
        report['onnx_stage_latency_ms'] = {
            stage: {'p50': round(statistics.median(values), 3),
                    'p95': round(percentile_nearest_rank(sorted(values), .95), 3),
                    'max': round(max(values), 3)}
            for stage, values in onnx_stages.items()
        }
    if detector == 'onnx' and model is not None:
        report['model_path'] = str(Path(model).resolve())
        report['model_sha256'] = hashlib.sha256(Path(model).read_bytes()).hexdigest()
    if tracks_jsonl is not None:
        report['track_trace'] = str(tracks_jsonl)
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
                                 'software queue drops only; hardware/driver drops unknown; detector=' + detector)
    metrics_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description='EdgeVision CPU motion detection + native C++ tracking')
    parser.add_argument('--source', required=True, help='File path or camera index (e.g. 0)')
    parser.add_argument('--detector', choices=['motion','onnx'], default='motion')
    parser.add_argument('--model', help='Local raw YOLOv8/YOLO11 detection ONNX file (required for --detector onnx)')
    parser.add_argument('--confidence', type=float, default=0.25)
    parser.add_argument('--nms-iou', type=float, default=0.45)
    parser.add_argument('--output', default='artifacts/annotated.avi')
    parser.add_argument('--metrics', default='artifacts/metrics.json')
    parser.add_argument('--tracks-jsonl', default=None, help='Optional per-frame JSONL audit trail')
    parser.add_argument('--max-frames', type=int, default=0)
    parser.add_argument('--min-area', type=int, default=350)
    parser.add_argument('--capture-mode', choices=['sync', 'buffered'], default='sync')
    parser.add_argument('--queue-capacity', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.metrics, max_frames=args.max_frames,
                         min_area=args.min_area, capture_mode=args.capture_mode,
                         queue_capacity=args.queue_capacity, tracks_jsonl=args.tracks_jsonl,
                         detector=args.detector, model=args.model, confidence=args.confidence, nms_iou=args.nms_iou), indent=2))


if __name__ == '__main__':
    main()
