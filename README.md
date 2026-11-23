# EdgeVision — C++/Python CPU perception engineering prototype

**Reproducible offline and buffered video processing on Linux; not production robotics.** A portfolio project demonstrating OpenCV motion detection, a native C++17 multi-object tracker, bounded capture, frame traceability, test-driven development, and measurable CPU performance.

## Architecture

```text
Recorded video / optional USB camera
       | OpenCV VideoCapture
       v
Sync all-frame mode  OR  capture worker -> bounded drop-oldest queue
       |  host monotonic timestamps (buffered mode)
       v
Python MOG2 foreground segmentation -> contours -> XYWH boxes
       | C ABI / ctypes
       v
C++17 centroid-velocity tracker -> track IDs / missed frames
       |                 |
       v                 v
Annotated MJPG video    JSONL per-frame track audit (optional)
       |
       v
JSON benchmark: compute latency p50/p95/max, file throughput, sampled RSS,
software queue drops and queue residence time when buffered
```

Native tracking is **not** semantic detection or deep-learning inference. The global greedy association can fail under complex occlusion, rapid direction changes, or crowded scenes. Host capture timestamps do not represent sensor exposure time.

## Reproduce locally (Linux)

```bash
sudo apt-get install -y g++ python3-venv libglib2.0-0 libgl1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
bash scripts/build.sh
python -m pytest -q
bash scripts/verify_release.sh
python -m scripts.benchmark_release --source artifacts/release_input.avi --repetitions 3
```

The release verification script compiles C++, runs automated tests, generates a 180-frame deterministic video, processes it through both sync and buffered modes, independently decodes the results, checks JSON metrics and video frame counts, and evaluates a synthetic bounding-box fixture.

### CLI and modes

```bash
# Process all video frames in order and write a per-frame track log:
python -m edgevision --source artifacts/release_input.avi \
  --output artifacts/my_output.avi --metrics artifacts/my_metrics.json \
  --tracks-jsonl artifacts/my_tracks.jsonl

# Process the freshest available frames under load. Some frames will be dropped:
python -m edgevision --source artifacts/release_input.avi \
  --capture-mode buffered --queue-capacity 3 \
  --output artifacts/live_like.avi --metrics artifacts/live_like.json

# Camera on a Linux system (device permission + hardware required):
python -m edgevision --source 0 --capture-mode buffered --queue-capacity 3
```

`--capture-mode sync` means exhaustive offline processing. Buffered mode is deliberately **lossy**: the generated output frame rate uses the source FPS but skipped frames are not time-stretched. Therefore buffered **file playback duration is not a reconstruction of original elapsed time**. Source sequence gaps are visible via `--tracks-jsonl`. If you need timeline-accurate archives, use sync mode and retain source timestamps separately.

### Docker (prepared, not executed here)

```bash
docker build -t edgevision:dev .
docker run --rm -v "$PWD/artifacts:/app/artifacts" edgevision:dev \
  sh -c 'python scripts/generate_video.py && python -m edgevision --source artifacts/synthetic.avi'
```

## Tests and evaluation

- Python pytest: independent behavioral tests of tracker IDs, occlusion, invalid C ABI inputs, transactional updates, bounded capture, output integrity, output-path protection, JSONL auditing, IoU/precision/recall/F1, descriptive ID switches and end-to-end file operation.
- Native smoke check: `clang++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -O1 cpp/tracker.cpp scripts/native_sanitizer_smoke.cpp -o build/native_sanitizer_smoke && ASAN_OPTIONS=detect_leaks=1 build/native_sanitizer_smoke` (requires Clang + sanitizers).
- `scripts/evaluate_synthetic.py`: synthetic single-rectangle quality check on deliberately simplistic data. This cannot establish detection accuracy on people, vehicles, or robotics scenes.
- `python -m scripts.benchmark_release`: repeated recorded-file CPU benchmark with environment metadata and distinct output per iteration.
- `edgevision.identity_evaluation.evaluate_identities`: one-to-one IoU pairing of independently labelled boxes and predicted track IDs, reporting descriptive ID switches. It is **not** MOTChallenge IDF1, MOTA, or HOTA.

Read `ARCHITECTURE.md`, `REQUIREMENTS.md`, `TEST_PLAN.md`, `ACCEPTANCE.md`, and `EDGEVISION_V1_SCOPE.md` for contracts, tests, original milestones, and unverified acceptance gates.

## Verified scope and outstanding work

Local Linux compilation, automated tests, native sanitizer smoke, sync and buffered file output, synthetic box evaluation, per-frame native track tracing and repeated benchmarks are supported by local evidence. See `artifacts/release_verification.log`, `artifacts/benchmark_v1/summary.json`, and TDD RED/GREEN logs supplied with the release archive.

**Not verified:** Docker runtime, GitHub-hosted CI, real camera acquisition, real-world annotated detection/tracking accuracy, ONNX inference, ROS 2 integration, sensor synchronization, embedded hardware, and hard real-time deadlines. Do not represent this project as production-ready or claim real-world recognition accuracy from synthetic trials.

## TDD history

Git commits preserve test-first specification and failed tests before implementation for native ABI atomicity, buffered capture, crossing-identity stability, independent identity metrics, I/O safety and per-frame track trace. A collection error due to a missing module proves non-existence, **not** a functional behavioral failure; the I/O regression tests explicitly failed against real legacy behavior.

## macOS native build and camera test

The native C++ tracker now builds as `libedgevision_tracker.dylib` using Apple Clang on Darwin, while preserving `libedgevision_tracker.so` on Linux. macOS compatibility is covered by platform contract tests and a GitHub Actions macOS job, but **physical Mac camera testing is still required**.

Start with `MACOS_SETUP.md`. In short, extract the project, enter the `EdgeVision` folder and run `bash scripts/macos/setup.sh`, followed by `python -m edgevision.camera_probe --index 0 --frames 30`. Then run the bounded camera pipeline in the guide. The camera-only test requires permission in macOS Privacy & Security settings.
