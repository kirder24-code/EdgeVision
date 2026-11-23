# EdgeVision — local release candidate evidence (2026-11-23)

## Intended use

Technical interview portfolio / reproducible CPU OpenCV + C++ tracking baseline. Not production software.

## Completed, objectively verified

1. Strict C++17 native library build with GCC; native ABI independently tested with Clang address/undefined-behavior sanitizers.
2. 44 Python automated tests including multiple test-first regression cycles (RED/GREEN logs).
3. 180-frame 640x480 prerecorded synthetic source decoded/processed/encoded in sync mode; frame count verified by decoding the output again.
4. Bounded buffered pipeline with source-sequence trace and explicit overflow accounting; processed frame count depends on runtime scheduling.
5. Per-frame track audit JSONL including source sequence and native track IDs.
6. Offline one-to-one IoU box evaluation and a separate descriptive identity-switch metric with hand-labelled unit fixtures.
7. Repeated local recorded-file CPU benchmark (3 iterations) with per-run JSON and platform metadata.
8. MP4 screenable demonstration from the actual algorithm output.

## Measured latest benchmark

See `artifacts/benchmark_v1/summary.json` for authoritative measurements; report includes CPU, OS, Python/OpenCV versions, and per-run throughput/latency. This is not sensor latency or an edge-device benchmark.

## Gaps and constraints

- Real-world accuracy not measured on independently annotated real footage; synthetic F1 must not be presented as a field-performance figure.
- No semantic person/object-class model. Motion detector cannot distinguish humans from moving shadows or background changes reliably.
- Dockerfile and GitHub Actions workflow exist but this environment lacks Docker and no remote CI run was performed.
- No camera accessible for optical latency, hardware timing or driver-drop measurements.
- No ROS2, hardware I/O, embedded deploy, calibration, complex multi-target association guarantee or production operational hardening.
- A repository exists locally with Git history; no external GitHub remote was published.

## Next real acceptance gates

1. Supply two or more reusable permitted, annotated real videos (static camera and harder crossing/occlusion) with provenance and partitioned holdout metrics.
2. Verify `docker build` and `docker run` on a Docker-enabled Linux machine.
3. Run a camera test and record resolution, target CPU, sample size, hardware/driver drop visibility and true end-to-end age measurement where possible.
4. Publish to user-selected GitHub repo and inspect real hosted CI results.
5. Only after error analysis choose and benchmark an optional ONNX detector and a stronger data association algorithm.
