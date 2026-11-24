#!/usr/bin/env python3
"""Paired offline EdgeVision v0.9 vs v0.10 benchmark on macOS.

Requires both previously installed local projects and local YOLO ONNX weights.
Never uploads camera footage. Uses original unannotated frames and sync input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


def project_paths(base: Path):
    return {"v09": base / "EdgeVision_v09" / "EdgeVision", "v010": base / "EdgeVision_v010" / "EdgeVision"}


def check_project(root: Path):
    exe = root / ".venv" / "bin" / "python"
    if not exe.is_file():
        raise RuntimeError(f"Missing virtualenv Python: {exe}. Set up this project first.")
    if not (root / "build" / "libedgevision_tracker.dylib").is_file():
        raise RuntimeError(f"Missing C++ library in {root}/build; run bash scripts/build.sh")
    return exe


def execute(cmd, cwd: Path, *, quiet=False):
    print("\n$", " ".join(str(x) for x in cmd), "(cwd:", cwd, ")", flush=True)
    completed = subprocess.run([str(x) for x in cmd], cwd=cwd, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if not quiet or completed.returncode:
        print(completed.stdout[-5000:], flush=True)
    if completed.returncode:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}")
    return completed


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def summarize(reports):
    fields = {
        "end_to_end_fps_including_io": lambda x: x['end_to_end_fps_including_io'],
        "processing_fps_excluding_io": lambda x: x['processing_fps_excluding_io'],
        "processing_p95_ms": lambda x: x['processing_latency_ms']['p95'],
        "postprocess_p50_ms": lambda x: x['onnx_stage_latency_ms']['postprocess']['p50'],
        "postprocess_p95_ms": lambda x: x['onnx_stage_latency_ms']['postprocess']['p95'],
        "inference_p50_ms": lambda x: x['onnx_stage_latency_ms']['inference']['p50'],
        "peak_rss_mb": lambda x: x['peak_process_rss_mb'],
    }
    return {key: {f: round(statistics.median(fn(r) for r in values), 3) for f, fn in fields.items()}
            for key, values in reports.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, default=Path.home() / 'Downloads')
    parser.add_argument('--frames', type=int, default=300)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--source', type=str, default='0', help='Camera index for one-time raw capture')
    parser.add_argument('--existing-video', type=Path, help='Use an existing RAW unannotated video, skip camera capture')
    args = parser.parse_args(argv)
    if args.runs < 1 or args.frames < 1:
        parser.error('--runs and --frames must be positive')
    roots = project_paths(args.downloads.expanduser().resolve())
    py = {k: check_project(p) for k,p in roots.items()}
    model = roots['v09'] / 'models' / 'yolo11n.onnx'
    if not model.is_file():
        raise RuntimeError(f"Missing model: {model}")
    target = roots['v010'] / 'artifacts' / 'paired_benchmark'
    target.mkdir(parents=True, exist_ok=True)
    if args.existing_video:
        raw = args.existing_video.expanduser().resolve()
        if not raw.is_file():
            raise FileNotFoundError(raw)
        capture_metadata = None
    else:
        raw = target / 'raw_unannotated.avi'
        capture_metadata = target / 'raw_capture.json'
        execute([py['v010'], '-m', 'scripts.record_raw', '--source', args.source,
                 '--frames', args.frames, '--output', raw, '--metadata', capture_metadata], roots['v010'])
    probe = execute([py['v010'], '-c', 'import cv2,sys; c=cv2.VideoCapture(sys.argv[1]); print(int(c.get(cv2.CAP_PROP_FRAME_COUNT))); c.release()', raw], roots['v010'], quiet=True)
    expected_frames = int(probe.stdout.strip().splitlines()[-1])
    if expected_frames <= 0:
        raise RuntimeError('Video contains no readable frames')
    # Source file checksum logged to prove exact same input.
    raw_digest = sha256(raw)
    model_digest = sha256(model)
    reports = {'v09': [], 'v010': []}
    # Alternate versions to reduce bias from temperature or background load.
    for index in range(args.runs):
        for version in (('v09', 'v010') if index % 2 == 0 else ('v010', 'v09')):
            root = roots[version]
            result_dir = target / f'{version}_run_{index+1}'
            result_dir.mkdir(exist_ok=True)
            m = result_dir / 'metrics.json'
            execute([py[version], '-m', 'edgevision', '--source', raw, '--detector', 'onnx',
                     '--model', model, '--confidence', '0.35', '--nms-iou', '0.45',
                     '--capture-mode', 'sync', '--max-frames', args.frames,
                     '--output', result_dir / 'annotated.avi', '--metrics', m,
                     '--tracks-jsonl', result_dir / 'tracks.jsonl'], root, quiet=True)
            data = json.loads(m.read_text())
            if data['frames_processed'] != min(args.frames, expected_frames):
                raise RuntimeError(f"Unexpected processed frames: {version}: {data['frames_processed']}")
            if data.get('model_sha256') != model_digest:
                raise RuntimeError(f"Model hash mismatch: {version}")
            reports[version].append(data)
            print(f"{version} run {index+1}: processing={data['processing_fps_excluding_io']} FPS, "
                  f"postprocess p50={data['onnx_stage_latency_ms']['postprocess']['p50']} ms", flush=True)
    medians = summarize(reports)
    document = {
        'test': 'paired_offline_same_raw_video', 'capture_video': str(raw),
        'input_sha256': raw_digest, 'model_sha256': model_digest, 'runs_per_version': args.runs,
        'frames_per_run': min(args.frames, expected_frames), 'capture_metadata': str(capture_metadata) if capture_metadata else None,
        'versions': medians,
        'notes': [
            'Both versions process identical pre-recorded raw frames; offline, no live camera queue/drop comparison.',
            'No annotated output reused as input. Same ONNX weights and confidence/NMS settings.',
            'FPS includes file decoder and video writer; hardware camera-to-display latency not measured.',
            'Not a labeled detection accuracy or identity-switch benchmark.',
        ],
    }
    dest = target / 'paired_summary.json'
    dest.write_text(json.dumps(document, indent=2)+'\n')
    print('\n=== MEDIAN OF MATCHED OFFLINE RUNS ===')
    for key in sorted(medians['v09']):
        before, after = medians['v09'][key], medians['v010'][key]
        print(f'{key:38} v0.9={before:9}  v0.10={after:9}')
    print(f'\nResults: {dest}\nRaw camera video is local; do not upload if it reveals private surroundings.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('Benchmark failed:', exc, file=sys.stderr)
        sys.exit(1)
