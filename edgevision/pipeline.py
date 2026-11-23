"""CPU-based motion detection and C++ tracking pipeline."""
import cv2

from .tracking import CppTracker


class MotionPipeline:
    def __init__(self, min_area=350, history=100, max_distance=65, max_missed=8):
        self.subtractor = cv2.createBackgroundSubtractorMOG2(history=history, varThreshold=20, detectShadows=False)
        self.min_area = min_area
        self.tracker = CppTracker(max_distance=max_distance, max_missed=max_missed)

    def process(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = self.subtractor.apply(gray)
        mask = cv2.medianBlur(mask, 5)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) >= self.min_area]
        boxes.sort(key=lambda b: (b[0], b[1]))
        tracks = self.tracker.update(boxes)
        rendered = frame.copy()
        for t in tracks:
            if t['missed']:
                continue
            x, y, w, h = map(int, t['box'])
            cv2.rectangle(rendered, (x, y), (x + w, y + h), (0, 220, 0), 2)
            cv2.putText(rendered, f"ID {t['id']}", (x, max(18, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)
        return rendered, tracks, len(boxes)

    def close(self):
        self.tracker.close()


class SemanticPipeline:
    """YOLO raw detections + existing native C++ ID tracking."""
    def __init__(self, detector, max_distance=65, max_missed=8):
        self.detector = detector
        self.tracker = CppTracker(max_distance=max_distance, max_missed=max_missed)

    def process(self, frame):
        predictions = self.detector.detect(frame)
        boxes = [p.xywh for p in predictions]
        tracks = self.tracker.update(boxes)
        rendered = frame.copy()
        # Attach current-frame semantics by box overlap, not persistent class identity.
        # This does not alter the native C++ tracking algorithm or its ID assignment.
        from .onnx_detector import _iou
        for track in tracks:
            if track['missed']:
                continue
            match = max(predictions, key=lambda p: _iou(track['box'], p.xywh), default=None)
            if match is not None and _iou(track['box'], match.xywh) >= 0.5:
                track['class_id'] = match.class_id
                track['confidence'] = round(match.score, 4)
            x,y,w,h = map(int, track['box'])
            cv2.rectangle(rendered, (x,y), (x+w,y+h), (0,220,0), 2)
            label = f"ID {track['id']}"
            if 'class_id' in track:
                label += f" class:{track['class_id']} {track['confidence']:.2f}"
            cv2.putText(rendered, label, (x, max(18, y-8)),
                        cv2.FONT_HERSHEY_SIMPLEX, .55, (0,220,0), 2)
        return rendered, tracks, len(predictions)

    def close(self):
        self.tracker.close()
