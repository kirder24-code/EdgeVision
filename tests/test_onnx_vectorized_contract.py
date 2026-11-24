"""Test-first contract for a fast raw-YOLO decoder. Independent scalar oracle.

These fixtures exercise 8400-anchor layouts and pathological inputs. Speed is
reported by a separate benchmark and never used as a flaky CI pass criterion.
"""
import numpy as np
import pytest

from edgevision.onnx_detector import decode_yolo_raw


def scalar_reference(raw, original_hw, letterbox, confidence=.25, iou=.45, max_detections=100):
    # Independent simple reference for raw shape [1, 4+C, N].
    import math
    height, width = original_hw
    ratio, (px,py) = letterbox
    detections = []
    for i, row in enumerate(raw[0].T):
        cx, cy, bw, bh = map(float, row[:4])
        if not all(math.isfinite(v) for v in (cx,cy,bw,bh)) or bw <= 0 or bh <= 0:
            continue
        scores = [float(v) if math.isfinite(float(v)) else float('-inf') for v in row[4:]]
        cls = max(range(len(scores)), key=lambda j: scores[j])
        score = scores[cls]
        if score < confidence or score > 1:
            continue
        x0 = max(0., min(float(width), ((cx-bw/2)-px)/ratio))
        y0 = max(0., min(float(height), ((cy-bh/2)-py)/ratio))
        x1 = max(0., min(float(width), ((cx+bw/2)-px)/ratio))
        y1 = max(0., min(float(height), ((cy+bh/2)-py)/ratio))
        if x1 <= x0 or y1 <= y0:
            continue
        detections.append((i, (x0,y0,x1-x0,y1-y0), score, cls))
    detections.sort(key=lambda d: (-d[2], d[0]))
    selected = []
    for candidate in detections:
        _, (x,y,w,h), score, cls = candidate
        suppress = False
        for _, (a,b,c,d), _, other_cls in selected:
            if cls != other_cls: continue
            xx0, yy0 = max(x,a), max(y,b)
            xx1, yy1 = min(x+w,a+c), min(y+h,b+d)
            intersection = max(0., xx1-xx0) * max(0., yy1-yy0)
            union = w*h+c*d-intersection
            if union > 0 and intersection/union > iou:
                suppress = True
                break
        if not suppress:
            selected.append(candidate)
            if len(selected) >= max_detections: break
    return [(box,score,cls) for _,box,score,cls in selected]


def make_large_fixture(seed=314, count=8400, classes=80):
    rng = np.random.default_rng(seed)
    raw = np.zeros((1, 4+classes, count), dtype=np.float32)
    raw[0,0] = rng.uniform(-100, 740, count)
    raw[0,1] = rng.uniform(-60, 700, count)
    raw[0,2:4] = rng.uniform(4, 140, (2,count))
    raw[0,4:] = rng.uniform(0, .15, (classes,count))
    # Keep a realistic small number of viable predictions, and deliberately
    # introduce exact-score ties, overlapping boxes and nonfinite entries.
    ids = rng.choice(count, 70, replace=False)
    raw[0,4,ids] = rng.uniform(.3, .99, 70)
    raw[0,4,ids[:3]] = .95
    raw[0,0:4,ids[0]] = [200,200,80,80]
    raw[0,0:4,ids[1]] = [201,201,80,80]
    raw[0,0:4,ids[2]] = [200,200,80,80]
    raw[0,0,ids[3]] = np.nan
    raw[0,5,ids[4]] = np.inf
    raw[0,2,ids[5]] = -1
    return raw


@pytest.mark.parametrize('seed', [10, 11, 12, 13])
@pytest.mark.parametrize('iou', [0., .45, 1.])
def test_large_yolo_decoder_matches_independent_reference(seed, iou):
    raw = make_large_fixture(seed=seed)
    expected = scalar_reference(raw, (480,640), (1.,(0,80)), confidence=.3, iou=iou)
    actual = decode_yolo_raw(raw, (480,640), (1.,(0,80)), confidence=.3, iou=iou)
    assert len(actual) == len(expected)
    for prediction, (box, score, cls) in zip(actual, expected):
        assert prediction.xywh == pytest.approx(box, abs=1e-5)
        assert prediction.score == pytest.approx(score, abs=1e-7)
        assert prediction.class_id == cls


def test_layouts_and_class_count_still_agree():
    raw = make_large_fixture(count=8400)
    left = decode_yolo_raw(raw, (480,640), (1.,(0,80)), confidence=.3)
    right = decode_yolo_raw(raw.transpose(0,2,1), (480,640), (1.,(0,80)), confidence=.3,
                            class_count=80)
    assert left == right


def test_vectorized_candidate_preselection_contract():
    """Fast decoder must expose batched candidate filtering, not a per-anchor Python scan."""
    from edgevision.onnx_detector import _vectorized_candidates
    raw = make_large_fixture(seed=91)
    rows = raw[0].T
    indexes, boxes, scores, classes = _vectorized_candidates(
        rows, (480,640), (1.,(0,80)), confidence=.3)
    expected = scalar_reference(raw, (480,640), (1.,(0,80)), confidence=.3, iou=1., max_detections=8400)
    assert len(indexes) == len(expected)
    assert len(boxes) == len(scores) == len(classes) == len(indexes)
    for box, score, cls in zip(boxes, scores, classes):
        assert any(np.allclose(box, candidate[0], atol=1e-5) and
                   score == pytest.approx(candidate[1], abs=1e-7) and cls == candidate[2]
                   for candidate in expected)
