# EdgeVision architecture — baseline and target contracts

Status: **architecture baseline v0.2**, 2026-11-23. Scope: a measurable CPU video-perception prototype, not production robotics or hard real-time software.

## Mission and boundaries

Input: a local video file or a camera made available by OpenCV. Output: encoded annotated video, structured performance metrics, and a deterministic tracker state that can be tested independently of the detector. v0.1 detects **motion**, not semantic object classes. No GPU, ROS, sensor fusion or real-camera timing guarantee is claimed.

## Component diagram

```text
OpenCV VideoCapture (source adapter)
       | BGR uint8 frame
       v
MotionPipeline (Python, OpenCV MOG2 -> morphology -> contours)
       | ordered list[bounding box] (x,y,w,h)
       v
Python ctypes ABI adapter -> C++17 libedgevision_tracker.so
       | list[track {id, box, missed}]
       v
Renderer -> OpenCV VideoWriter (annotated video)
       |
       +--> telemetry (per-frame processing time; count; sampled RSS)
                -> JSON report
```

## Data contracts

- Frame: nonempty `H × W × 3`, BGR, unsigned byte array. The baseline processes frames sequentially in decoded order.
- Detection: floating-point `(x, y, width, height)`, all finite, width/height strictly positive; coordinates represent top-left pixel, center is `(x+w/2, y+h/2)`.
- C ABI: `ev_tracker_create(max_distance, max_missed)` returns a non-null opaque handle for finite positive distance and nonnegative missed threshold. `ev_tracker_update(handle, detections, count, output, capacity)` returns number of active tracks or a negative error. The caller owns buffers, the tracker owns its handle and persistent state.
- Track: monotonically allocated positive integer ID, last matched box, count of consecutive missed updates. An unmatched track is retained while `missed <= max_missed` and removed on the next miss.
- Error contract (v0.2): error results are **atomic**: invalid input or insufficient output capacity must leave the tracker's state and next ID unchanged. Errors must not write past the output buffer.
- Output order: existing tracks retain insertion order, new tracks are appended in input order; no promise of semantic identity through crossings.
- Assignment: deterministic globally greedy nearest-centroid matching with max-distance gate; crossing trajectories may switch IDs.
- Teardown: handle destroyed exactly once; Python wrapper rejects `update` after `close()`.

## Component responsibility and failure behavior

| Boundary | Responsibility | Failure handling |
|---|---|---|
| Acquisition | Decode frames / camera capture | Missing source fails explicitly; EOF ends file loop |
| Detection | Detect moving regions (MOG2) | Synthetic fixture validates pipeline only, not accuracy |
| C++ tracker | Maintain temporal IDs | Invalid input and inadequate buffer return error without mutation |
| FFI | Marshals double-precision boxes and handles | Raises Python error on negative native return code |
| Writer | Produce annotated output | Failure to open raises; successful `write()` cannot guarantee disk integrity |
| Metrics | Report processing latency and throughput | Clearly separate decode/encode from detector+tracker timings |

## Performance measurement definitions

- `processing_latency_ms`: `perf_counter_ns` around detection+tracking+rendering; excludes capture and encoding. p95 uses the existing discrete-index approximation, **not** a statistical confidence bound.
- `processing_fps_excluding_io`: processed frames divided by sum of processing times.
- `end_to_end_fps_including_io`: processed frames divided by full program loop wall time; throughput, **not** camera FPS.
- `peak_process_rss_mb`: maximum **sampled** RSS, reported in MiB (2^20 bytes).
- Source FPS is container metadata, not observed arrival FPS. No dropped-frame measurement exists in synchronous file mode.

## Concurrency and real-time constraints

v0.2 remains single-threaded and synchronous to preserve deterministic, auditable reference behavior. A future camera module may implement a bounded queue and explicit drop-oldest policy with capture timestamps; it will require separate tests, real hardware verification and latency reports. Never describe v0.2 as hard real-time.

## Build and reproducibility

Linux, g++ C++17 (`-Wall -Wextra -Werror`), Python 3.11+, OpenCV, numpy, psutil, pytest. Native `.so` compiled through `scripts/build.sh`; Python loads it with `ctypes`. Dockerfile exists but **Docker execution is not verified** in the local environment. CI and camera validation are separate acceptance gates.

## Evolution checkpoints

1. Baseline contracts and independent acceptance tests, including C ABI failure atomicity.
2. File-mode correctness and robust I/O failure coverage.
3. Optional timestamped camera adapter with bounded queue and drop telemetry.
4. Optional ONNX-based semantic detection, with labeled dataset and quality metrics.
5. Improved tracking for crossings, ID-switch tests, then hardware/ROS integration if available.

Changes to interfaces or success criteria require an updated specification and a new failing test before implementation.

## v0.3 proposed buffered acquisition (contract before implementation)

Optional **buffered** mode uses a dedicated capture thread: `VideoCapture.read()` -> timestamp immediately after successful decode -> bounded FIFO (`FramePacket(sequence, captured_ns, frame)`) -> main processing thread -> native tracking/writer. The default `sync` file mode remains unchanged, preserving exact-frame tests. `captured_ns` is a host monotonic timestamp **after decoding**, not a sensor exposure time; `queue_wait_ms` is dequeue time minus that timestamp, **not glass-to-glass latency**.

The queue has a fixed positive capacity and `drop-oldest` overflow policy: on full enqueue, remove precisely one oldest unconsumed packet and append the newest; increment `dropped_overflow`. Frame sequence numbers are monotonically increasing, allowing audit of skips. Closed queue drains existing packets and then returns `None`, rejects additional pushes, wakes waiting consumers. Invalid capacity fails before allocation. A capture worker closes the queue on EOF/failure, propagates worker exceptions to the consumer after draining, and is stopped/joined on exit. `max_frames` limits **processed** frames rather than decoded/produced frames; early termination stops the worker.

Buffered telemetry: `capture_frames_read`, `frames_processed`, `frames_dropped_overflow`, `queue_wait_ms` p50/p95/max, `queue_max_depth`, and `capture_mode=buffered`. `capture_frames_read = frames_processed + frames_dropped_overflow + frames_unprocessed` when capture thread has ended; `frames_unprocessed` includes remaining queued frames upon early termination. The main pipeline may read a changing number of frames from a finite file under overload; tests must not demand deterministic throughput/scheduling.

The queue unit tests and fake-capture worker tests are deterministic. Buffered end-to-end video tests only verify valid output and metric invariants; performance is assessed separately on actual camera hardware.

## v0.4 evaluation boundary (specified before code)

The evaluator is a pure Python offline module, independent of the detector and C++ tracker.
It accepts **external ground truth** and predictions as XYWH boxes, matches each
prediction to at most one ground-truth box at a stated IoU threshold and reports
micro-aggregated TP/FP/FN and precision/recall/F1. A deterministic crossing fixture
specifies required C++ track identity behavior; no claimed real-scene score follows
from this synthetic contract. The native ABI remains unchanged.
