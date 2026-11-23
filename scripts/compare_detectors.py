"""Reproducible paired offline throughput comparison; not a model accuracy test."""
import argparse
import hashlib
import json
from pathlib import Path

from edgevision.__main__ import run


def file_hash(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def compare_detectors(source, outdir, *, model=None, semantic_detector=None, max_frames=0):
    if str(source).isdigit():
        raise ValueError('For fair comparisons, record camera source first with python -m scripts.record_raw')
    if model is None and semantic_detector is None:
        raise ValueError('ONNX comparison requires a local model (or a test-only injected session)')
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    outdir = Path(outdir).resolve()
    if source == outdir or outdir == source.parent and source.name in ('motion.avi','onnx.avi'):
        raise ValueError('Comparison output would overwrite input')
    outdir.mkdir(parents=True, exist_ok=True)
    motion = run(str(source), str(outdir/'motion.avi'), str(outdir/'motion_metrics.json'),
                 detector='motion', max_frames=max_frames, capture_mode='sync',
                 tracks_jsonl=str(outdir/'motion_tracks.jsonl'))
    onnx = run(str(source), str(outdir/'onnx.avi'), str(outdir/'onnx_metrics.json'),
               detector='onnx', model=model, semantic_detector=semantic_detector,
               max_frames=max_frames, capture_mode='sync',
               tracks_jsonl=str(outdir/'onnx_tracks.jsonl'))
    summary = {
        'comparison_kind': 'unlabelled_performance_only',
        'source': str(source), 'source_sha256': file_hash(source),
        'motion': motion, 'onnx': onnx,
        'interpretation': ('Same recorded input; different detector processing times. '
                           'No truth labels, so NO precision/recall or real-world ID accuracy. '
                           'Results are exploratory single runs without warmup/variance estimates.'),
    }
    (outdir/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description='Compare detectors on identical unannotated video file')
    parser.add_argument('--source', required=True)
    parser.add_argument('--model', required=True, help='Local raw YOLOv8/YOLO11 ONNX detection model')
    parser.add_argument('--outdir', default='artifacts/paired_comparison')
    parser.add_argument('--max-frames', type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(compare_detectors(args.source, args.outdir, model=args.model,
                                       max_frames=args.max_frames), indent=2))


if __name__ == '__main__':
    main()
