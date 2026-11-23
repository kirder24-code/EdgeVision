"""Independent public-interface checks from FR-08, FR-10 and NFR-02."""
import json

import pytest

from edgevision.__main__ import run
from edgevision.tracking import CppTracker
from scripts.generate_video import generate


def test_closed_tracker_rejects_update():
    tracker = CppTracker()
    tracker.close()
    with pytest.raises(RuntimeError, match='closed'):
        tracker.update([(10, 10, 5, 5)])


def test_missing_video_fails_explicitly(tmp_path):
    with pytest.raises(RuntimeError, match='Cannot open video source'):
        run(tmp_path / 'missing.avi', tmp_path / 'out.avi', tmp_path / 'metrics.json')


def test_report_exposes_measured_fields_without_claiming_capture_latency(tmp_path):
    source = tmp_path / 'source.avi'
    report_path = tmp_path / 'metrics.json'
    generate(source, frames=12, width=320, height=240)
    report = run(source, tmp_path / 'out.avi', report_path, max_frames=12, min_area=100)
    saved = json.loads(report_path.read_text())
    assert saved == report
    assert report['frames_processed'] == 12
    assert report['end_to_end_fps_including_io'] > 0
    assert report['processing_fps_excluding_io'] > 0
    assert report['peak_process_rss_mb'] > 0
    latency = report['processing_latency_ms']
    assert 0 <= latency['p50'] <= latency['max']
    assert 0 <= latency['p95'] <= latency['max']
    assert 'camera latency' in report['limitations']
