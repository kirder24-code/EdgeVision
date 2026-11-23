# Physical macOS test evidence — user-run baseline (2026-11-23)

The following values were transcribed from terminal screenshots supplied by the project owner. They were **not** obtained by executing on the current Linux runner. They describe the **pre-ONNX motion baseline** and must not be attributed to the optional ONNX mode.

- Apple Silicon MacBook Air (Homebrew `/opt/homebrew`, `arm64` wheel download observed); exact chip model and macOS version not supplied.
- Python 3.13.18 in `.venv` and C++ shared-library build `build/libedgevision_tracker.dylib` completed.
- `python -m pytest -q`: **48 passed in 0.74 s** after correcting platform-specific ABI test path.
- `python -m edgevision.camera_probe --index 0 --frames 30`: **30/30** frames; **1920×1080**; observed camera read-loop rate **31.12 FPS**. The initial attempt was blocked by camera permission; the second succeeded.
- Live buffered run (reported by user): processing-only FPS **260.51**; end-to-end including I/O FPS **29.52**; processing latency **p50 3.921 ms, p95 5.355 ms, max 7.931 ms**; peak RSS **309.22 MiB**; elapsed **10.161 s**; source frames read **302**, frames processed inferred from report **300**, queue overflow drops **0**, frames left unprocessed **2**, queue max depth **1** of **3**; queue wait **p50 0.09 ms, p95 0.146 ms, max 6.614 ms**. The user confirmed that output video displayed motion bounding rectangles.

## Interpretation and limits

The observed values validate that the camera acquisition and classical motion + native tracker + video output worked on that Mac under the reported test conditions. There is no independent camera ground truth, and it is unknown whether all rectangle IDs were correct. Neither the neural detector nor camera-to-display latency was measured. The 260.51 FPS number is a measured processing-only throughput, **not** camera throughput. The Homebrew Python `pyexpat` issue was resolved in the active shell by pointing the dynamic loader at Homebrew `expat`; it may recur in another shell until the local system is repaired.

No personal camera video is included in the archive.
