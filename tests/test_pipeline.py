import json
import cv2
from edgevision.__main__ import run
from scripts.generate_video import generate


def test_synthetic_video_round_trip(tmp_path):
    source = tmp_path / 'input.avi'
    output = tmp_path / 'output.avi'
    metrics = tmp_path / 'metrics.json'
    generate(source, frames=40, width=320, height=240)
    report = run(source, output, metrics, max_frames=40, min_area=100)
    assert report['frames_processed'] == 40
    assert report['detections_total'] > 0
    assert report['processing_latency_ms']['p95'] >= 0
    assert json.loads(metrics.read_text())['frames_processed'] == 40
    cap = cv2.VideoCapture(str(output))
    assert cap.isOpened()
    assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 40
    cap.release()
