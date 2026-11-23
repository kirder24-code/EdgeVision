# EdgeVision — CPU video motion detection + native C++ tracking

A reproducible **engineering prototype**, not a production robotics perception stack. Designed to demonstrate Python/OpenCV, a native C++17 tracking core, telemetry, testing, and Docker packaging.

## Architecture

`VideoCapture (Python/OpenCV) → MOG2 + contour motion detection (Python/OpenCV) → nearest-centroid multi-object tracker (C++17 via ctypes) → annotated MJPG video + JSON metrics`

Detection **does not** perform semantic classification. Tracking is deterministic global-greedy assignment, not Hungarian/Kalman/DeepSORT; crossing trajectories may swap IDs. No GPU required.

## Quick start (Linux)

Requires Python 3.11+, g++, and venv. From repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/build.sh
python -m pytest -q
python scripts/generate_video.py --output artifacts/synthetic.avi
python -m edgevision --source artifacts/synthetic.avi --output artifacts/annotated.avi --metrics artifacts/metrics.json
```

For a USB camera: `python -m edgevision --source 0` (requires a camera and video capture permissions).

## Docker

```bash
docker build -t edgevision:dev .
docker run --rm -v "$PWD/artifacts:/app/artifacts" edgevision:dev \
  sh -c 'python scripts/generate_video.py && python -m edgevision --source artifacts/synthetic.avi'
```

The container builds the C++ library and runs unit/integration tests as part of `docker build`. Docker must be installed separately. No GPU or internet access is needed after image build.

## Metrics and interpretation

- `processing_fps_excluding_io` = frames / summed detector+tracker CPU time (not live capture FPS).
- `end_to_end_fps_including_io` = decoded and encoded frames / measured wall-clock time.
- `processing_latency_ms` = time for each frame's detector + tracker (p50, nearest-rank-like p95, max); excludes capture and encoding.
- `peak_process_rss_mb` = max sampled process RSS; not a continuous peak monitor.
- No real-camera latency, timestamps, hardware sensor sync, dropped frame accounting, or energy figures are claimed.

To benchmark properly, log CPU model, OS, Python/OpenCV versions, resolution, source, frame count and processing metrics. The synthetic video is a **pipeline correctness fixture**, not an accuracy benchmark. Do not extrapolate its results to real-world object detection.

## Test coverage

- Stable track ID on a smooth centroid trajectory
- Brief missing detections and track expiration
- Two-object ID assignment
- Rejection of invalid bounding boxes and invalid tracker configuration
- Full synthetic video decode → Python/OpenCV → C++ tracker → encoded video + JSON metrics

## Roadmap

1. Add timestamped camera capture with bounded queue and explicit drop policy; measure glass-to-glass latency when hardware is available.
2. Replace MOG2 with an optional ONNX detector, benchmark accuracy/throughput on labeled footage.
3. Improve assignment under crossing/occlusion (Hungarian+Kalman); introduce tracking metrics (IDF1, ID switches).
4. Add GPIO/sensor or ROS 2 integration when real hardware is available; evaluate edge hardware constraints.
5. Set CI for Linux build, tests and static analysis; make publishable demo video and record full benchmark conditions.

## Honest scope

This prototype demonstrates C++/Python interoperability, basic motion detection, ID association, CPU profiling and a documented Linux build. It is **not** a production real-time robotics system, **not** semantic object detection, and does **not** establish accuracy or latency on embedded devices.

## Local verification record (2026-11-23)

A single run in the available Linux container completed **7/7 pytest tests**, compiled the C++17 library with `-Wall -Wextra -Werror`, decoded and encoded **180/180** synthetic video frames, and produced `artifacts/metrics.json` and `artifacts/edgevision_demo.mp4`. Measured processing p50 **2.416 ms**, p95 **3.401 ms** and total file-processing throughput **200.51 FPS** (includes decode+encode, not live camera I/O). Peak sampled RSS **141.74 MiB**. Full conditions in `artifacts/benchmark_environment.json`. This is one local measurement, not a promise about other machines. **Docker image has not been built or executed in this environment** (Docker executable unavailable).
