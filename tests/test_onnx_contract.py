"""Independent contract tests for YOLO raw ONNX adapter (no model download)."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from edgevision.onnx_detector import YoloRawDetector, decode_yolo_raw, letterbox_rgb
from edgevision.pipeline import SemanticPipeline


def _frame(h=100, w=200):
    result = np.zeros((h,w,3), dtype=np.uint8)
    result[:,:] = (10, 20, 240)  # BGR red
    return result


def _output(*boxes):
    # rows cx,cy,w,h, score_class0, score_class1, 2 classes
    return np.asarray(boxes, dtype=np.float32).T[None,:,:]


class FakeSession:
    def __init__(self, predictions, shape=(1,3,200,200)):
        self.predictions = predictions
        self.inputs = [SimpleNamespace(name='images', shape=list(shape), type='tensor(float)')]
        self.outputs = [SimpleNamespace(name='output0')]
        self.calls = []

    def get_inputs(self):
        return self.inputs

    def get_outputs(self):
        return self.outputs

    def run(self, names, feed):
        self.calls.append((names, feed))
        return [self.predictions]


def test_letterbox_rgb_geometry_channel_order_and_padding():
    tensor, ratio, pad = letterbox_rgb(_frame(), 200)
    assert tensor.shape == (1,3,200,200)
    assert tensor.dtype == np.float32
    assert ratio == pytest.approx(1)
    assert pad == pytest.approx((0,50))
    assert tensor[0,0,100,10] == pytest.approx(240/255)
    assert tensor[0,2,100,10] == pytest.approx(10/255)
    assert tensor[0,0,0,10] == pytest.approx(114/255)


def test_raw_model_boxes_are_mapped_to_original_image():
    # 200x100 input -> 200x200 letterbox +50 vertical padding
    predictions = _output((40,80,40,40,.90,.10), (150,130,20,20,.20,.85))
    found = decode_yolo_raw(predictions, (100,200), (1.0,(0,50)), confidence=0.5)
    assert len(found) == 2
    assert found[0].class_id == 0
    assert found[0].xywh == pytest.approx((20,10,40,40))
    assert found[1].class_id == 1
    assert found[1].xywh == pytest.approx((140,70,20,20))


def test_transposed_raw_layout_is_equivalent():
    predictions = _output((40,80,40,40,.9,.1), (150,130,20,20,.2,.85))
    a = decode_yolo_raw(predictions, (100,200), (1,(0,50)), confidence=.5)
    b = decode_yolo_raw(predictions.transpose(0,2,1), (100,200), (1,(0,50)), confidence=.5)
    assert a == b


def test_class_aware_nms_removes_same_class_overlap_not_other_class():
    predictions = _output((50,100,40,40,.90,.05), (52,100,40,40,.80,.1), (50,100,40,40,.1,.85))
    found = decode_yolo_raw(predictions, (200,200), (1,(0,0)), confidence=.5, iou=.5)
    assert [(f.class_id, round(f.score,2)) for f in found] == [(0,.9),(1,.85)]


def test_clipping_invalid_scores_threshold_and_max_count():
    predictions = _output((-5,50,30,30,.9,.1), (100,100,20,20,float('nan'),0.8),
                          (110,110,-2,10,.95,.1), (150,150,20,20,.4,.2),
                          (170,170,15,15,.8,.1))
    found = decode_yolo_raw(predictions, (200,200), (1,(0,0)), confidence=.5, max_detections=2)
    assert len(found) == 2
    assert found[0].xywh == pytest.approx((0,35,10,30))
    assert found[1].class_id == 1
    assert all(f.xywh[2] > 0 and f.xywh[3] > 0 for f in found)


def test_session_validation_and_missing_model(tmp_path):
    with pytest.raises(FileNotFoundError, match='ONNX model'):
        YoloRawDetector(model_path=tmp_path/'not-present.onnx')
    with pytest.raises(ValueError, match='NCHW'):
        YoloRawDetector(session=FakeSession(_output((50,50,20,20,.9,.1)), shape=(1,200,200,3)))
    with pytest.raises(ValueError, match='raw YOLO'):
        decode_yolo_raw(np.zeros((1,6),dtype='float32'), (200,200), (1,(0,0)))


def test_fake_onnx_session_integrates_with_cpp_tracking():
    fake = FakeSession(_output((50,100,40,40,.95,.1)))
    detector = YoloRawDetector(session=fake, input_size=200, confidence=.5)
    pipeline = SemanticPipeline(detector=detector)
    try:
        rendered, tracks, count = pipeline.process(_frame(200,200))
        assert rendered.shape == (200,200,3)
        assert count == 1
        assert len(tracks) == 1 and tracks[0]['id'] == 1
        assert tracks[0]['box'] == pytest.approx((30,80,40,40))
        assert fake.calls[0][1]['images'].shape == (1,3,200,200)
    finally:
        pipeline.close()


def test_onnx_full_video_integration_is_explicit_and_auditable(tmp_path):
    """Uses fake inference (integration only); checks native tracker, recorder and report."""
    from edgevision.__main__ import run
    source = tmp_path / 'input.avi'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'MJPG'), 10, (200,200))
    assert writer.isOpened()
    for _ in range(4):
        writer.write(_frame(200,200))
    writer.release()
    session = FakeSession(_output((50,100,40,40,.95,.1)))
    detector = YoloRawDetector(session=session, input_size=200, confidence=.5)
    result = run(str(source), str(tmp_path/'output.avi'), str(tmp_path/'metrics.json'),
                 detector='onnx', semantic_detector=detector, tracks_jsonl=str(tmp_path/'tracks.jsonl'))
    assert result['detector'] == 'onnx'
    assert result['inference'] == 'mock_session_not_real_model'
    assert result['frames_processed'] == 4
    assert len(session.calls) == 4
    tracks = [__import__('json').loads(line) for line in (tmp_path/'tracks.jsonl').read_text().splitlines()]
    assert all(row['tracks'][0]['id'] == 1 for row in tracks)
    assert all(row['tracks'][0]['class_id'] == 0 for row in tracks)


def test_real_onnx_mode_requires_model_before_video_is_opened(tmp_path):
    from edgevision.__main__ import run
    with pytest.raises(ValueError, match='--model'):
        run('0', str(tmp_path/'out.avi'), str(tmp_path/'metrics.json'), detector='onnx')


def test_real_model_provenance_is_saved_in_metrics_with_mock_session(tmp_path):
    """Model metadata is recorded only for an explicit on-disk model."""
    from edgevision.__main__ import run
    import hashlib
    model = tmp_path/'model.onnx'
    model.write_bytes(b'example-model-data')
    source = tmp_path/'input.avi'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'MJPG'), 10, (200,200))
    assert writer.isOpened()
    writer.write(_frame(200,200)); writer.release()
    session = FakeSession(_output((50,100,40,40,.95,.1)))
    detector = YoloRawDetector(session=session, input_size=200, confidence=.5)
    result = run(str(source), str(tmp_path/'output.avi'), str(tmp_path/'metrics.json'),
                 detector='onnx', model=str(model), semantic_detector=detector)
    assert result['model_sha256'] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert result['model_path'] == str(model.resolve())
    assert result['inference'] == 'mock_session_not_real_model'
