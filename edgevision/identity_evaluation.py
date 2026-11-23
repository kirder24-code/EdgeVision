"""Deterministic IoU-based matching and identity continuity scoring.

A descriptive evaluation metric, not IDF1/MOTA or full MOTChallenge protocol.
"""
from .evaluation import iou

def evaluate_identities(frames, *, iou_threshold=0.5):
    if not 0 < iou_threshold <= 1:
        raise ValueError("IoU threshold must be in (0, 1]")
    last = {}
    matches = switches = missing_gt = missing_pred = 0
    total_gt = total_pred = 0
    for ground_truth, predictions in frames:
        for name, group in (("GT", ground_truth), ("prediction", predictions)):
            ids = [entry["id"] for entry in group]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate {name} IDs in a frame")
        total_gt += len(ground_truth)
        total_pred += len(predictions)
        candidates = []
        for gi, gt in enumerate(ground_truth):
            for pi, pred in enumerate(predictions):
                score = iou(gt["box"], pred["box"])
                if score >= iou_threshold:
                    candidates.append((-score, gi, pi))
        candidates.sort()
        used_gt, used_pred = set(), set()
        for _score, gi, pi in candidates:
            if gi in used_gt or pi in used_pred:
                continue
            used_gt.add(gi)
            used_pred.add(pi)
            gt_id, pred_id = ground_truth[gi]["id"], predictions[pi]["id"]
            if gt_id in last and last[gt_id] != pred_id:
                switches += 1
            last[gt_id] = pred_id
            matches += 1
        missing_gt += len(ground_truth) - len(used_gt)
        missing_pred += len(predictions) - len(used_pred)
    return {"matches": matches, "id_switches": switches,
            "unmatched_gt": missing_gt, "unmatched_predictions": missing_pred,
            "total_gt": total_gt, "total_predictions": total_pred,
            "id_switch_rate": switches / matches if matches else 0.0,
            "iou_threshold": iou_threshold}
