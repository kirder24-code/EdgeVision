# EdgeVision semantic detector contract (v0.8)

The existing OpenCV MOG2 + native C++ tracker remains the default baseline.

## Supported ONNX contract

- A **local** ONNX file is required, with explicit `--detector onnx --model path.onnx`.
- CPU inference through `onnxruntime` (optional dependency; not required for baseline).
- Single NCHW RGB float32 input, static square spatial size (normally 640).
- Ultralytics YOLOv8/YOLO11 **raw detection** output `[1, 4+C, N]` or `[1,N,4+C]`, where the first four values are `cx,cy,w,h` in resized image pixels, followed by `C` class confidences. This excludes YOLOv5 objectness outputs and exported end-to-end NMS models.
- Aspect ratio preserved by letterboxing, padding value 114, input floats in `[0,1]`.
- Class-aware greedy IoU-NMS; deterministic confidence-descending ordering; max detections bound.
- Reverse-coordinate mapping to source image with clipping and dropping invalid boxes.
- Native tracker receives XYWH pixel boxes, **not** class labels; class labels are attached to visible tracks only by source detection alignment and are not persistent semantic identity.
- Motion and semantic pipeline metrics MUST declare detector mode; no accuracy assertions without external labelled data.

## Tests written before implementation

T-ONNX-01: letterbox preserves geometry, channel order and NCHW shape.
T-ONNX-02: decode of `[1,4+C,N]` maps boxes to source coordinates.
T-ONNX-03: transposed `[1,N,4+C]` decode yields same detections.
T-ONNX-04: same-class NMS; overlapping different classes retained.
T-ONNX-05: confidence threshold, clipping, invalid/NaN handling, max count.
T-ONNX-06: bad model path/output/input or missing runtime generates actionable error.
T-ONNX-07: synthetic ONNX session drives end-to-end C++ tracking without changing default motion mode.

Acceptance boundary: Passing a fake-session contract proves adapter integration, **not** a loaded real model, real-world detection accuracy, or neural inference speed. Real inference needs a third-party model with verified provenance and actual installed ONNX Runtime.
