"""Regression contracts for semantic detector robustness and file safety."""
import json
from pathlib import Path

import numpy as np
import pytest

from edgevision.onnx_detector import decode_yolo_raw
from edgevision.__main__ import run


def test_onnx_model_is_protected_from_output_collision_before_loading(monkeypatch, tmp_path):
    """No user-supplied ONNX weights should ever be initialized as an output video."""
    import edgevision.onnx_detector as module
    model = tmp_path / 'weights.onnx'
    model.write_bytes(b'unmodified')
    called = []

    def bad_load(**kwargs):
        called.append(kwargs)
        raise AssertionError('A colliding model must not reach model initialization')

    monkeypatch.setattr(module, 'YoloRawDetector', bad_load)
    with pytest.raises(ValueError, match='ONNX model'):
        run('nonexistent.mp4', str(model), str(tmp_path/'metrics.json'),
            detector='onnx', model=str(model))
    assert not called
    assert model.read_bytes() == b'unmodified'


def test_real_onnx_decoder_keeps_all_classes_in_84_feature_raw_yolo():
    """An 80-class real-model-shaped head must not be mistaken for boxes by axis."""
    raw = np.zeros((1, 84, 100), dtype=np.float32)
    raw[0, 0:4, 2] = (50, 50, 20, 20)
    raw[0, 4 + 79, 2] = .9
    matches = decode_yolo_raw(raw, (100, 100), (1, (0,0)), confidence=.5)
    assert len(matches) == 1
    assert matches[0].class_id == 79
    assert matches[0].xywh == pytest.approx((40, 40, 20, 20))


def test_model_missing_does_not_create_output_directories(tmp_path):
    path = tmp_path/'missing.onnx'
    out = tmp_path/'new_output'/'result.avi'
    with pytest.raises(FileNotFoundError, match='ONNX model'):
        run('missing.mp4', str(out), str(tmp_path/'new_output'/'metrics.json'),
            detector='onnx', model=str(path))
    assert not out.parent.exists()
