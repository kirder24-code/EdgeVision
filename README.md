# EdgeVision | portfolio release v0.10

A camera-based perception engineering prototype developed with AI-assisted coding and iterative hands-on validation on Apple Silicon. Independent portfolio work; not affiliated with CSI or a production robotics deployment.

## Evidence at a glance
- Python/OpenCV + C++17 native tracker (C ABI/ctypes), bounded video queue, CPU YOLO11n ONNX inference and JSON/JSONL diagnostics.
- Linux: 81 automated tests passed on the v0.10 source recheck. macOS: 67 tests passed on v0.9; v0.10 camera and paired benchmark runs succeeded. The v0.10 macOS test count is not independently documented.
- Paired offline benchmark: same raw 300-frame video, identical model hash and settings, three runs per version. Median full throughput 26.19 -> 45.61 FPS (+74.15%); median postprocessing 18.687 -> 0.888 ms (21.04x); processing p95 39.762 -> 21.504 ms (-45.92%).
- Separate live camera runs: 18.07 -> 29.38 FPS; different scenes, so not a controlled comparison. v0.10 had 6 software queue drops in 308 reads; no hardware-drop measurement.

See `evidence/paired_summary.json` and the two live metrics files for sanitized operator-supplied summaries. Raw footage and model weights are excluded. The paired script is in `benchmarks/edgevision_paired_benchmark.py`; it requires two installed versions and local model weights as described in its help. Individual run logs and the exact raw video are not included, so the historical benchmark cannot be independently replayed from this archive alone. The source and procedure can be used with new footage. Historical documents below describe earlier milestones and may contain superseded statuses; this section is the latest evidence summary.

## Scope boundary and next validation (not release blockers for portfolio)
1. Docker/hosted CI clean build and a public, privacy-reviewed repository.
2. Annotated real video: precision/recall, ID switches and occlusion cases.
3. Long-duration memory/thermal test and camera disconnect/recovery.
4. Target Linux/ARM or Jetson benchmark, acceleration and deployment toolchain only if required.
5. Sensor timestamps, telemetry and control interfaces remain outside this single-camera prototype; no ROS, MAVLink or flight-control integration claimed.

Review third-party terms before distributing model weights or deploying commercially. No weights are included. This prototype is provided for technical evaluation; no production or hard real-time guarantees.

---

## Historical implementation guide
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

**Not verified in the current Linux runner:** Docker runtime, GitHub-hosted CI, real-world annotated detection/tracking accuracy, genuine ONNX inference, ROS 2 integration, sensor synchronization, embedded hardware, and hard real-time deadlines. **The project owner has separately verified live camera acquisition and motion processing on an Apple Silicon MacBook Air**; see `MACOS_TEST_EVIDENCE.md`. Do not represent this project as production-ready or claim real-world recognition accuracy from synthetic trials.

## TDD history

Git commits preserve test-first specification and failed tests before implementation for native ABI atomicity, buffered capture, crossing-identity stability, independent identity metrics, I/O safety and per-frame track trace. A collection error due to a missing module proves non-existence, **not** a functional behavioral failure; the I/O regression tests explicitly failed against real legacy behavior.

## macOS native build and camera test

The native C++ tracker now builds as `libedgevision_tracker.dylib` using Apple Clang on Darwin, while preserving `libedgevision_tracker.so` on Linux. macOS compatibility is covered by platform contract tests and a GitHub Actions macOS job, but **physical Mac camera testing is still required**.

Start with `MACOS_SETUP.md`. In short, extract the project, enter the `EdgeVision` folder and run `bash scripts/macos/setup.sh`, followed by `python -m edgevision.camera_probe --index 0 --frames 30`. Then run the bounded camera pipeline in the guide. The camera-only test requires permission in macOS Privacy & Security settings.

## Experimental semantic ONNX mode (test-first extension)

The stable default remains `--detector motion` (OpenCV MOG2 + native C++ tracker).
An **optional** `--detector onnx --model /path/to/raw-yolo11.onnx` CPU mode is implemented, with NCHW RGB letterboxing, output validation, class-aware NMS, reverse-coordinate mapping, numeric class labels and the same native tracker. No ONNX file or model weights are bundled. The optional dependency is listed in `requirements-onnx.txt`.

Read [ONNX_CONTRACT.md](ONNX_CONTRACT.md) and [ONNX_MACOS.md](ONNX_MACOS.md) for supported export format, setup, privacy, licensing, and a consistent camera/offline evaluation procedure. The test suite exercises a fake ONNX session plus native C++ tracking; **it does not prove genuine model inference or real-video recognition quality**. Model loading and CPU speed must be verified separately on the target Mac.

### For paired comparisons (requires model and optional dependencies)

```bash
python -m scripts.record_raw --source 0 --frames 300 --output artifacts/raw_camera.avi --metadata artifacts/raw_camera.json
python -m scripts.compare_detectors --source artifacts/raw_camera.avi --model yolo11n.onnx --outdir artifacts/paired
```

`compare_detectors` replays the exact same source in sync mode for both approaches, preserving output videos, track logs, performance reports and input SHA256. Without independent labels, it measures **performance only**, not detector accuracy. The raw camera file stays on the local computer.

## v0.9 verification

See `RELEASE_V09.md` for the 67-test green run, a test-first ONNX file-safety regression, and offline reproducibility results. This release is **not** a claim of successful genuine neural inference.
