# EdgeVision ONNX stage — macOS Apple Silicon

**State: adapter and C++ integration tested on Linux with an injected session; a genuine ONNX model, ONNX Runtime on the user's Mac, and real-world neural inference are not yet tested.** The stable OpenCV motion mode remains the default.

## 0. Keep the working baseline

Use the existing Python 3.13 virtual environment on the Mac where 48 previous tests and camera capture succeeded. Do not delete `.venv`, do not rerun a setup script that can select Python 3.14, and do not overwrite the Mac's previous camera artifacts. The new project archive includes source changes; it does not include Python packages or a trained model.

On the affected Homebrew Python installation, use the same Terminal session where `pyexpat` works, or set (only for that shell):

```bash
export DYLD_LIBRARY_PATH="$(brew --prefix expat)/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
cd ~/Downloads/EdgeVision
source .venv/bin/activate
```

## 1. Install optional runtime (inside .venv)

```bash
python -m pip install -r requirements-onnx.txt
python -c 'import onnxruntime as ort; print(ort.__version__, ort.get_available_providers())'
bash scripts/build.sh
python -m pytest -q
```

ONNX Runtime provides CPU wheels for supported macOS versions; this package uses `CPUExecutionProvider`, not CoreML or Metal. If installing the optional package fails due to Python or OS compatibility, preserve the baseline and record the exact pip error.

## 2. Obtain and verify a compatible model

This project expects a **raw YOLO11 or YOLOv8 detection** ONNX model with static square NCHW float input and **no integrated NMS**. An example of exporting your own legally obtained model with Ultralytics (requires separate dependencies and may download licensed weights):

```bash
python -m pip install ultralytics onnx
python - <<'PY'
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
print(model.export(format='onnx', imgsz=640, dynamic=False, nms=False))
PY
```

Verify and follow the model's own license, distribution and commercial-use restrictions. Do not commit model weights into the repository unless redistribution is allowed. Ultralytics has separate licensing terms; the code in this repository does not grant rights to third-party weights. The example names and export parameters are not evidence that the model was exported in this environment.

## 3. Run a semantic camera trial

```bash
python -m edgevision --source 0 --detector onnx --model yolo11n.onnx \
  --capture-mode buffered --queue-capacity 3 --max-frames 300 \
  --output artifacts/mac_onnx_camera.avi \
  --metrics artifacts/mac_onnx_camera.json \
  --tracks-jsonl artifacts/mac_onnx_camera_tracks.jsonl
```

This is a new trial, not yet completed. Mac hardware/model throughput **must** be observed. The report includes detector type, model path and SHA256, total compute p50/p95, separated preprocess/inference/postprocess timing, measured RSS, source reads and queue drops. Host timings do not include true exposure-to-display latency.

## 4. Fair offline A/B comparison using the exact same video

Record an *unannotated* clip first (this is private and local):

```bash
python -m scripts.record_raw --source 0 --frames 300 \
  --output artifacts/mac_raw_for_comparison.avi \
  --metadata artifacts/mac_raw_for_comparison.json
```

Then run both detectors on exactly those stored frames:

```bash
python -m scripts.compare_detectors \
  --source artifacts/mac_raw_for_comparison.avi \
  --model yolo11n.onnx \
  --outdir artifacts/paired_mac
```

Review `artifacts/paired_mac/summary.json` and the two annotated videos. This is only a performance comparison without manually labelled ground truth, so it cannot establish precision, recall, IDF1, MOTA, or HOTA. Single-run results can vary with temperature, power, background load and model warm-up. For a stronger benchmark run multiple repetitions and record hardware details.

## 5. How to collect accuracy evidence

Create a labelled set of frames with known XYWH object boxes and class IDs, *independently of detector predictions*. Split clips by scene, use a separate unseen set, match each predicted box at IoU >= 0.5, and report precision, recall, F1 and ID switch counts. The existing evaluation helpers can score box/ID fixtures but do not yet implement COCO mAP or MOTChallenge IDF1.

## Compatibility boundaries

- Supported raw output: `[1,4+C,N]` or `[1,N,4+C]` for a YOLO detection head (`C` class scores and no objectness term). Embedded NMS, YOLOv5, segmentation, pose, classification, dynamic/rectangular input and arbitrary ONNX models are **not supported**.
- Inference runtime and trained model are intentionally optional and absent from the release ZIP.
- This code labels classes by numeric `class_id` unless you independently establish model-specific label names.
- CPU-only ONNX may be slower than motion baseline and may drop more frames in buffered capture; actual values are TBD.
