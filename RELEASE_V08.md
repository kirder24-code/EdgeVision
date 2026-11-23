# EdgeVision v0.8 — Test-first optional ONNX integration (2026-11-23)

This is an **engineering release candidate**, not production robotics software.

### Verified here (Linux)

- 64 pytest tests passed (including ONNX fake-session contracts, C++ tracker integration, recording and A/B compare).
- Linux shared library compiled with standard build script.
- End-to-end release verification passed, including decoding recorded video; full console log in `artifacts/onnx_release_verify.log`.
- Existing default motion detection preserved; ONNX mode is opt-in and its dependency/model are not bundled.
- Model SHA256 / stage timings / explicit detector mode recorded when available.

### TDD evidence

The test commits preceding implementation show RED states for the missing ONNX adapter, rejected CLI integration, absent provenance metadata, absent stage timings, missing raw recording module and missing paired comparison module. RED from an import failure proves an interface was missing, not a behavioural bug. Subsequent GREEN passes prove only the concrete assertions. Historical RED/GREEN logs are in `artifacts/tdd_*onnx*`, `artifacts/tdd_raw_record_red.log`, and `artifacts/tdd_compare_red.log`.

### Not verified (must remain pending)

- Genuine model/ONNX Runtime inference, ONNX throughput, COCO class accuracy, model weights provenance.
- macOS execution of these **new** v0.8 changes; only the earlier v0.7 motion baseline was validated by the user on Mac.
- Real-world annotated detection/identity metrics, ROS 2 / robotics edge integration, Docker build/runtime, externally-hosted CI and physical embedded target.

No user camera video is included. Recorded clips can contain private surroundings. The release does not automatically upload them.
