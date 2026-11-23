#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts build
bash scripts/build.sh
python -m pytest -q
python scripts/generate_video.py --output artifacts/release_input.avi --frames 180
python -m edgevision --source artifacts/release_input.avi --output artifacts/release_sync.avi --metrics artifacts/release_sync.json --tracks-jsonl artifacts/release_tracks.jsonl
python -m edgevision --source artifacts/release_input.avi --capture-mode buffered --queue-capacity 3 --output artifacts/release_buffered.avi --metrics artifacts/release_buffered.json
python scripts/evaluate_synthetic.py artifacts/release_detection_eval.json
python - <<'PY'
import cv2, json
for mode in ('sync','buffered'):
    r=json.load(open(f'artifacts/release_{mode}.json'))
    cap=cv2.VideoCapture(f'artifacts/release_{mode}.avi')
    if not cap.isOpened(): raise RuntimeError(f'{mode} video could not be opened')
    frames=0
    while True:
        ok,_=cap.read()
        if not ok: break
        frames+=1
    cap.release()
    assert frames == r['frames_processed'], (mode,frames,r['frames_processed'])
    if mode=='sync':
        assert frames==180
        import json as _json
        rows=[_json.loads(line) for line in open('artifacts/release_tracks.jsonl')]
        assert len(rows)==180
        assert [r['source_sequence'] for r in rows] == list(range(180))
    print(f'verified {mode} video frames: {frames}')
PY
