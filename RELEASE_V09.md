# EdgeVision v0.9 — ONNX adapter release candidate

**Status: verified local Linux engineering prototype, not production robotics or validated neural inference.**

## Verified in this session

- 67/67 pytest tests passed on local Linux; generated native C++ library and tested its Python C ABI.
- RED stage: the ONNX weights/output collision contract failed on the existing implementation, because the model was initialized before output safety validation. GREEN stage: output protection is now performed before initializing a model session. Logs: `artifacts/tdd_semantic_safety_red.log` and `artifacts/tdd_semantic_safety_green.log`.
- `bash scripts/verify_release.sh` completed; both output modes created and decoded, source tracking and deterministic geometry evaluation exercised. Full command log: `artifacts/v09_verify.log`.
- Three measured Linux offline-file runs: median file throughput **217.11 FPS**, median p95 per-frame processing latency **3.348 ms**; see `artifacts/v09_benchmark.log`. These are specific to this environment and the synthetic source, and are not genuine ONNX or live-camera measurements.
- Optional ONNX adapter has fake-session integration tests for input preprocessing, raw prediction decoding, class-aware NMS, native C++ tracker, file metadata, stage timings and paired offline evaluation.
- User-reported previous real Mac baseline validations are preserved separately in `MACOS_TEST_EVIDENCE.md`.

## Not verified

- ONNX Runtime model execution with real pretrained weights: `onnxruntime` and `onnx` could not be installed in this runner due to package-server DNS failure; no ONNX model bundled.
- v0.9 ONNX on Apple Silicon Mac; real footage class precision/recall, class-specific tracking, ROS 2, synchronization, Docker runtime, real GitHub-hosted CI, power/thermal stress.
- A single end-to-end camera test does not establish robustness to lighting, occlusion, repeated deployments, or robotics safety requirements.

## Minimal next external actions when available

Use the existing working macOS `.venv`; install `requirements-onnx.txt`, provide a legitimately obtained compatible raw YOLO ONNX model, verify the model's license, then run the comparison protocol in `ONNX_MACOS.md`. Do not overwrite or delete previous baseline artifacts. The user need not perform any work to inspect the current engineering release.
