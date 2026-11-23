"""Independent metric contracts; expected values defined without implementation calls."""
import pytest
from edgevision.evaluation import evaluate_frame, evaluate_sequence, iou


def box(x, y=0):
    return (x, y, 10, 10)


def test_iou_exact_and_partial():
    assert iou(box(0), box(0)) == pytest.approx(1)
    assert iou(box(0), box(20)) == 0
    assert iou(box(0), box(5)) == pytest.approx(1 / 3)


def test_one_to_one_match_prevents_double_credit():
    result = evaluate_frame([box(0)], [box(0), box(0)], iou_threshold=0.5)
    assert (result.tp, result.fp, result.fn) == (1, 1, 0)


def test_missing_and_false_detections():
    result = evaluate_frame([box(0), box(50)], [box(0), box(90)])
    assert (result.tp, result.fp, result.fn) == (1, 1, 1)


def test_empty_frames_have_no_division_errors():
    summary = evaluate_sequence([([], []), ([box(0)], [])])
    assert (summary['tp'], summary['fp'], summary['fn']) == (0, 0, 1)
    assert summary['precision'] == 0.0
    assert summary['recall'] == 0.0


def test_known_sequence_detection_metrics():
    summary = evaluate_sequence([([box(0)], [box(0)]), ([box(0)], [box(50)]), ([box(0)], [])])
    assert (summary['tp'], summary['fp'], summary['fn']) == (1, 1, 2)
    assert summary['precision'] == pytest.approx(0.5)
    assert summary['recall'] == pytest.approx(1 / 3)
    assert summary['f1'] == pytest.approx(0.4)


def test_reject_invalid_threshold_and_boxes():
    with pytest.raises(ValueError):
        evaluate_frame([], [], iou_threshold=1.5)
    with pytest.raises(ValueError):
        iou((0, 0, 0, 10), box(0))


def test_crossing_scenario_preserves_ids_without_using_detector():
    from edgevision.tracking import CppTracker
    trajectory_a = [10, 30, 50, 70, 90]
    trajectory_b = [110, 90, 70, 50, 30]
    observed_a, observed_b = [], []
    with CppTracker(max_distance=40, max_missed=2) as tracker:
        for ax, bx in zip(trajectory_a, trajectory_b):
            tracks = tracker.update([(ax, 10, 12, 12), (bx, 15, 12, 12)])
            tracks = [t for t in tracks if t['missed'] == 0]
            assert len(tracks) == 2
            a = min(tracks, key=lambda t: abs(t['box'][0] - ax) + abs(t['box'][1] - 10))
            b = min(tracks, key=lambda t: abs(t['box'][0] - bx) + abs(t['box'][1] - 15))
            assert a['id'] != b['id']
            observed_a.append(a['id'])
            observed_b.append(b['id'])
    assert len(set(observed_a)) == len(set(observed_b)) == 1
