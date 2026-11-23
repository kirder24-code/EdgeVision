"""Paired offline comparison, never use two separate live camera sessions."""
import json
import cv2
import pytest
import numpy as np
from types import SimpleNamespace
from scripts.compare_detectors import compare_detectors
from scripts.generate_video import generate
from edgevision.onnx_detector import YoloRawDetector


class Fake:
    def get_inputs(self): return [SimpleNamespace(name='images',shape=[1,3,640,640],type='tensor(float)')]
    def get_outputs(self): return [SimpleNamespace(name='output0')]
    def run(self, outputs, feeds):
        out = np.zeros((1,6,1), dtype=np.float32)
        out[0,:,0] = [200,200,50,50,.9,.1]
        return [out]


def test_compare_replays_same_local_file_twice(tmp_path):
    source = tmp_path/'clip.avi'
    generate(source, frames=8, width=320, height=240)
    summary = compare_detectors(str(source), str(tmp_path/'paired'),
                                semantic_detector=YoloRawDetector(session=Fake()), max_frames=8)
    assert summary['comparison_kind'] == 'unlabelled_performance_only'
    assert len(summary['source_sha256']) == 64
    assert summary['motion']['frames_processed'] == 8
    assert summary['onnx']['frames_processed'] == 8
    assert summary['onnx']['inference'] == 'mock_session_not_real_model'
    assert (tmp_path/'paired'/'summary.json').exists()
    assert (tmp_path/'paired'/'motion.avi').exists()
    assert (tmp_path/'paired'/'onnx.avi').exists()


def test_compare_rejects_live_camera_and_requires_model(tmp_path):
    with pytest.raises(ValueError, match='record'):
        compare_detectors('0', str(tmp_path/'paired'), model='fake.onnx')
    with pytest.raises(ValueError, match='model'):
        compare_detectors(str(tmp_path/'clip.avi'), str(tmp_path/'paired'))
