# EdgeVision acceptance scope for a demonstrable engineering release

**Target:** reproducible Linux CPU video analytics reference prototype, not production robotics or hard real time.

## Functional contracts

- All decoded frames in synchronous offline mode flow through OpenCV detection and native C++ ID association, with video + JSON telemetry saved.
- Timestamped buffered mode drops the oldest queued packet at fixed capacity; accounting distinguishes read, processed, dropped, and pending packets.
- Box scoring: one-to-one IoU matches, explicit TP/FP/FN, precision/recall/F1.
- Trajectory scoring: one-to-one IoU pairing against labelled IDs, and ID switches counted when a previously matched GT identity acquires a different prediction identity. Unmatched frames never create a spurious ID assignment; unmatched GT/prediction counts are explicit.
- Metrics: nearest-rank p95 on recorded per-frame samples; report the different scopes of wall throughput, compute throughput, and queue residence time.
- Invalid inputs and file destinations fail with explicit errors without destroying inputs.

## Test-first evidence

`tests/test_identity_evaluation.py` and `tests/test_recorder_contract.py` were committed before implementation; first run exits with ModuleNotFoundError (collection-level RED). Additional behavioral regressions must fail against older implementations before changes.

## Evidence requirements

- Compile C++ with strict warnings; full Linux pytest run, smoke video, JSON artifacts, repeat benchmark; preserve actual logs.
- Docker is not certified until build *and* runtime tests are executed in a Docker-enabled environment.
- ONNX inference is not certified without a valid exported model, licensing/provenance and labelled realistic footage.
- A hardware camera, hardware sensor timestamps, ROS 2 and edge target cannot be certified using prerecorded videos.
