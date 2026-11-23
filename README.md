# EdgeVision — CPU video motion detection + native C++ tracking

A reproducible **engineering prototype**, not a production robotics perception stack. Designed to demonstrate Python/OpenCV, a native C++17 tracking core, telemetry, testing, and Docker packaging.

## Architecture

`VideoCapture (Python/OpenCV) → MOG2 + contour motion detection (Python/OpenCV) → nearest-centroid multi-object tracker (C++17 via ctypes) → annotated MJPG video + JSON metrics`

Detection **does not** perform semantic classification. Tracking is deterministic global-greedy assignment, not Hungarian/Kalman/DeepSORT; crossing trajectories may swap IDs. No GPU required.

## Engineering specification and TDD evidence

Start with [`ARCHITECTURE.md`](ARCHITECTURE.md), [`REQUIREMENTS.md`](REQUIREMENTS.md), [`TEST_PLAN.md`](TEST_PLAN.md) and [`ACCEPTANCE.md`](ACCEPTANCE.md). The first post-baseline change is a red/green regression test for atomic C ABI updates when an output buffer is too small. See `tests/test_tracker_abi_contract.py` and `artifacts/tdd_red.log`, `artifacts/tdd_green.log`.

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

## v0.2 TDD verification

Requirements and tests were written before the C++ update. The legacy library failed both new ABI atomicity tests. The native library was rebuilt after implementing a transactional update, and the expanded local suite passed **12/12**. The C++ tracker currently copies its state for each update; this is a correctness-first approach, with overhead to benchmark separately. No camera, Docker or cloud CI verification is implied.

## v0.3 — bounded timestamped capture (TDD)

The default `--capture-mode sync` is unchanged and processes each decoded file frame in sequence. For latency-oriented acquisition, choose an explicit **drop-oldest** fixed-capacity queue and a dedicated capture thread:

```bash
python scripts/generate_video.py --output artifacts/input.avi
python -m edgevision --source artifacts/input.avi --capture-mode buffered \
  --queue-capacity 3 --output artifacts/buffered.avi --metrics artifacts/buffered.json
# Camera input where supported (not yet verified on hardware):
python -m edgevision --source 0 --capture-mode buffered --queue-capacity 3
```

The `FramePacket` timestamp is taken on the host **after** `VideoCapture.read()` succeeds. `queue_wait_ms` is residence time from that timestamp to consumption, *not* glass-to-glass latency or hardware sensor timing. The reported `frames_dropped_overflow` only accounts for overflows inside our Python queue; driver/internal codec drops remain unknown. When the decoder is faster than the CPU processing path, many file frames can deliberately be discarded. **Use sync mode for exhaustive offline processing and buffered mode for freshness under load.**

Spec and tests committed first (`e15c206`), producing a recorded RED import error because no `edgevision.capture` module existed; after implementation all **20 tests passed**. This RED checkpoint establishes module absence, not a behavioral test failure; the contract behavior is established by the subsequent GREEN run. Evidence logs `artifacts/tdd_v03_red.log`, `artifacts/tdd_v03_green.log`, and a sample buffered benchmark `artifacts/v03_metrics.json`. Tests cover FIFO, 100-frame overload, monotonic timestamps, close/drain semantics, worker EOF/exception/early stop, and end-to-end encoded output. OS thread scheduling affects dropped counts; do not assert fixed drops in integration runs.

**Known limitations:** Capture worker shutdown depends on `VideoCapture.read()` returning. A blocked native camera read may prevent timely shutdown; `stop()` then raises after the join timeout. No hardware-camera validation, ROS integration, hard real-time deadline guarantee, true sensor timestamps or image-quality metrics have been performed.

## v0.4 — independent offline box evaluation + crossing identity

The evaluator `edgevision/evaluation.py` computes one-to-one IoU association,
TP/FP/FN, micro precision/recall/F1. Its unit tests use hand-calculated expected
answers; the synthetic scoring script generates scene boxes from **known geometry**,
not from the detector's predicted output.

```bash
bash scripts/build.sh
python -m pytest -q
python scripts/evaluate_synthetic.py artifacts/v04_synthetic_evaluation.json
```

The C++ tracker now uses last-observed centroid velocity to predict association
locations and passes the two-object, five-frame crossing fixture. This is a
constant-velocity heuristic, **not** a Kalman filter, identity guarantee or
crowded-scene benchmark. Crossing can still fail with abrupt motion or long gaps.
The artificial single-rectangle detection score is **not representative of real camera
accuracy**. Real footage with independently labelled ground truth remains pending.

TDD history: tests and spec committed before implementation; missing evaluation
module failed collection; after adding evaluator the crossing identity test failed;
then C++ was changed and the complete suite passed. Logs: `artifacts/tdd_v04_*`.
