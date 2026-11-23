"""Buffered file integration contract; scheduling-dependent frame count is NOT fixed."""
import cv2
from edgevision.__main__ import run
from scripts.generate_video import generate


def test_buffered_mode_produces_output_with_reconciled_counters(tmp_path):
    inp = tmp_path / 'input.avi'
    out = tmp_path / 'output.avi'
    generate(inp, frames=40, width=320, height=240)
    stats = run(inp, out, tmp_path / 'stats.json', capture_mode='buffered', queue_capacity=3, min_area=100)
    assert stats['capture_mode'] == 'buffered'
    assert 1 <= stats['frames_processed'] <= 40
    assert stats['capture_frames_read'] == 40
    assert stats['frames_dropped_overflow'] >= 0
    assert stats['queue_max_depth'] <= 3
    assert stats['capture_frames_read'] == (stats['frames_processed'] + stats['frames_dropped_overflow'] + stats['frames_unprocessed'])
    assert stats['queue_wait_ms']['p95'] >= 0
    video = cv2.VideoCapture(str(out))
    assert video.isOpened()
    assert int(video.get(cv2.CAP_PROP_FRAME_COUNT)) == stats['frames_processed']
    video.release()
