# EdgeVision — macOS installation and camera validation

Status: **the project owner has verified the earlier motion-only release on a physical Apple Silicon Mac** (48/48 tests, 30 camera frames, live annotated video). See `MACOS_TEST_EVIDENCE.md`. The optional ONNX v0.9 mode has **not** been run on that Mac.

## Prerequisites

- macOS with Apple Silicon or Intel, built-in or USB camera.
- Python 3.11–3.13 recommended; `python3 --version` must be 3.11+ (3.12 is a good default).
- Apple Xcode Command Line Tools (`xcode-select --install`, if not already installed).
- Internet access for first-time `pip` package installation.
- At least 2 GB free disk space is recommended.

## Installation

Download and extract the EdgeVision archive. Open **Terminal** on Mac, navigate into its `EdgeVision` directory (for example, type `cd ` then drag the extracted `EdgeVision` folder into Terminal and press Return).

```bash
xcode-select --install           # Only if Apple Command Line Tools are missing
python3 --version
bash scripts/macos/setup.sh     # Creates .venv, installs dependencies, compiles C++, runs pytest
source .venv/bin/activate
```

For a fresh Terminal window, activate again with `source .venv/bin/activate` from the project directory.

## Camera preflight, with no video file written

Quit FaceTime, Zoom and any other camera app first.

```bash
python -m edgevision.camera_probe --index 0 --frames 30
```

macOS should request camera access for the Terminal app or the Python executable. **Allow it**. If denied, check **System Settings > Privacy & Security > Camera** and enable access for the relevant application; then restart Terminal. If camera index 0 is unavailable, test index 1.

Expected JSON fields include `frames_read`, `resolution` and `read_fps_including_io`. `frames_read` must be positive; 30 is ideal. This is not detector FPS or true camera-to-display latency.

## Actual camera pipeline: short, bounded test

```bash
mkdir -p artifacts
python -m edgevision --source 0 --capture-mode buffered --queue-capacity 3 \
  --max-frames 180 --output artifacts/mac_camera_output.avi \
  --metrics artifacts/mac_camera_metrics.json \
  --tracks-jsonl artifacts/mac_camera_tracks.jsonl
```

This records a **processed** output AVI and metrics, not the original camera video. Use an actual moving person or object in a stable, well-lit scene. The built-in MOG2 detects motion only; a motionless person may not be detected. The camera should not be moved during this trial.

If camera capture works but `VideoWriter` fails on macOS, record your Terminal error and run the offline smoke test below. The AVI/MJPG codec still requires confirmation on your Mac.

## Independent offline test

```bash
bash scripts/verify_release.sh
```

This regenerates deterministic input, runs pytest, evaluates synthetic boxes and verifies that resulting video files are actually readable. It does **not** test camera permissions or live capture.

## Report diagnostic information

```bash
sw_vers
uname -m
python --version
python -c 'import cv2; print(cv2.__version__)'
python -m pytest -q
cat artifacts/mac_camera_metrics.json
```

The earlier motion-camera trial succeeded on the user's Mac; see `MACOS_TEST_EVIDENCE.md`. New ONNX trials still require separate evidence. For privacy, the `.avi` file may contain images of the user or their home: review it before sharing. If any command fails, send the error message and the OS/architecture information; avoid uploading private videos unless necessary.

## Known limitations

- No semantic classification, pose estimation, ROS 2 or sensor timestamp synchronization.
- Headless OpenCV does not display live video. Review output files in a compatible player (e.g. VLC).
- The AVFoundation backend may depend on macOS permission grants and camera compatibility.
- `processing_latency_ms` includes only detection/tracking, not exposure, sensor transfer, video output or glass-to-glass delay.
- The streaming mode drops frames when overloaded by design.


## ABI test fix (macOS)

On macOS, `scripts/build.sh` produces `build/libedgevision_tracker.dylib`.
Before this fix, two tests in `tests/test_tracker_abi_contract.py`
incorrectly hard-coded the Linux `.so` filename and failed in fixture setup.
The ABI tests now use `native_library_filename()` from the production tracker wrapper.

From an activated Python 3.13 environment, run:

```bash
bash scripts/build.sh
python -m pytest -q
python -m edgevision.camera_probe --index 0 --frames 30
```

On Macs affected by the Homebrew `pyexpat` / `libexpat` symbol issue,
run these commands in the same Terminal session in which the working
`DYLD_LIBRARY_PATH` and `.venv` have been configured. macOS test results
and actual camera availability must be verified on the target Mac.

## Optional neural detector after baseline validation

Keep the existing working `.venv`. Refer to `ONNX_MACOS.md` for the separate optional `onnxruntime` installation, the explicitly supported raw YOLO model format, model license checks and paired offline benchmark. Do **not** repeat the base installer on this Mac: an earlier Homebrew Python / `pyexpat` linkage problem required a shell-local Expat workaround.
