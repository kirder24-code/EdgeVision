"""Offline, detector-independent bounding-box metrics for labelled frames."""
from dataclasses import dataclass
import math


def _validate_box(box):
    if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[2] <= 0 or box[3] <= 0:
        raise ValueError('Expected finite xywh box with positive width and height')


def iou(a, b):
    _validate_box(a)
    _validate_box(b)
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[0] + a[2], b[0] + b[2])
    bottom = min(a[1] + a[3], b[1] + b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = a[2] * a[3] + b[2] * b[3] - intersection
    return intersection / union


@dataclass(frozen=True)
class FrameScores:
    tp: int
    fp: int
    fn: int


def evaluate_frame(ground_truth, predictions, iou_threshold=0.5):
    if not math.isfinite(iou_threshold) or not (0 < iou_threshold <= 1):
        raise ValueError('IoU threshold must be in (0, 1]')
    for box in ground_truth:
        _validate_box(box)
    for box in predictions:
        _validate_box(box)
    candidates = [(iou(gt, pr), gi, pi)
                  for gi, gt in enumerate(ground_truth)
                  for pi, pr in enumerate(predictions)]
    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
    matched_g, matched_p = set(), set()
    for score, gi, pi in candidates:
        if score < iou_threshold:
            break
        if gi not in matched_g and pi not in matched_p:
            matched_g.add(gi)
            matched_p.add(pi)
    tp = len(matched_g)
    return FrameScores(tp, len(predictions) - tp, len(ground_truth) - tp)


def evaluate_sequence(frames, iou_threshold=0.5):
    tp = fp = fn = 0
    for gt, pred in frames:
        result = evaluate_frame(gt, pred, iou_threshold=iou_threshold)
        tp += result.tp
        fp += result.fp
        fn += result.fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision,
            'recall': recall, 'f1': 2 * precision * recall / (precision + recall)
            if precision + recall else 0.0, 'iou_threshold': iou_threshold}
