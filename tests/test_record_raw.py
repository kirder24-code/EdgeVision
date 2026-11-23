"""Acceptance for recording an independent unannotated source clip."""
import json
import cv2
import pytest

from scripts.generate_video import generate
from scripts.record_raw import record_raw


def test_record_raw_preserves_unannotated_frame_count_and_report(tmp_path):
    source = tmp_path/'source.avi'; output = tmp_path/'raw.avi'; metadata = tmp_path/'raw.json'
    generate(source, frames=14, width=320, height=240)
    report = record_raw(str(source), str(output), str(metadata), frames=11)
    assert report['frames_written'] == 11
    assert report['purpose'] == 'raw_unannotated_capture'
    assert json.loads(metadata.read_text()) == report
    cap = cv2.VideoCapture(str(output))
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 11
    ok, frame = cap.read()
    assert ok and frame.shape[:2] == (240,320)
    cap.release()


def test_record_raw_refuses_overwriting_source_or_metadata(tmp_path):
    source = tmp_path/'source.avi'
    generate(source, frames=3, width=320, height=240)
    original = source.read_bytes()
    with pytest.raises(ValueError):
        record_raw(str(source), str(source), str(tmp_path/'new.json'), frames=3)
    with pytest.raises(ValueError):
        record_raw(str(source), str(tmp_path/'new.avi'), str(source), frames=3)
    with pytest.raises(ValueError):
        record_raw(str(source), str(tmp_path/'same.avi'), str(tmp_path/'same.avi'), frames=3)
    assert source.read_bytes() == original


def test_record_raw_rejects_invalid_count_and_missing_camera(tmp_path):
    with pytest.raises(ValueError, match='positive'):
        record_raw('0', str(tmp_path/'out.avi'), str(tmp_path/'out.json'), frames=0)
    with pytest.raises(RuntimeError, match='Cannot open'):
        record_raw(str(tmp_path/'missing.avi'), str(tmp_path/'out.avi'), str(tmp_path/'out.json'), frames=1)
