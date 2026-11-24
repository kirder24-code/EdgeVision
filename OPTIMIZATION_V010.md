# EdgeVision v0.10: ONNX postprocessing optimization

## Input evidence

The original MacBook Air run was provided in `yolo_metrics.json`, `yolo_tracks.jsonl` and `yolo_camera.avi` by the operator. This release does **not** rerun the ONNX model; its contents are not included in the ZIP because footage may contain identifiable individuals. SHA-256 hashes and an aggregate audit summary are in `evidence/mac_v09_uploaded_evidence_summary.json`.

The real run processed 300 frames at 18.07 full-pipeline FPS; p50 postprocess = 25.364 ms, p50 inference = 23.997 ms, 73 software queue drops, 425.08 MiB peak RSS. Those are baseline observations from v0.9, not v0.10 results. Trace contains 300 records and 41 distinct tracking IDs; that **does not** establish 41 ID switches or tracking accuracy.

## Design and test-first change

The original `decode_yolo_raw` loop processed all 8400 anchor rows in Python, including low-confidence rows. The replacement `_vectorized_candidates` computes finite class scores, argmax classes, validity flags, original-frame boxes, and stable score sorting with NumPy vector operations. Class-aware NMS retains the same threshold, ordering, tie handling, and candidate limits. Public `decode_yolo_raw` signature is unchanged. Tests in `tests/test_onnx_vectorized_contract.py` were authored before the fast helper existed; test-first RED failed on importing the absent helper, then GREEN passed after the implementation.

## Measured comparison (local Linux, synthetic raw predictions)

Run: `python benchmarks/benchmark_postprocess.py --baseline /tmp/edgevision_onnx_old.py --iterations 100` where the baseline is the `edgevision/onnx_detector.py` from v0.9. The benchmark verifies equal decoder results before timing. It does **not** exercise ONNX inference.

- Input raw tensor: `[1,84,8400]`, 100 sparse above-threshold candidates
- Previous decoder median: **44.8913 ms**; p95: 47.6026 ms
- Updated decoder median: **3.0097 ms**; p95: 3.5306 ms
- Ratio: **14.92× faster** for decode+NMS on this particular machine and fixture
- `python -m pytest -q`: **81 passed** in the local Linux environment

These are benchmark numbers from the development machine, **not** performance measurements from the user's MacBook. Full-frame latency and drop rate on v0.10 are unknown until a paired Mac run.

## macOS change installation

The old installed EdgeVision v0.9 remains safe and unchanged. Use the `EdgeVision_v010_patch.zip` files in a **copy** of the v0.9 directory, not in the known-working v0.9 directly.

If the project's .venv is reused, preserve the macOS Expat workaround from the previous working shell before invoking Python: `export DYLD_LIBRARY_PATH="$(brew --prefix expat)/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"`.

Then compile native C++ with `bash scripts/build.sh`, run `python -m pytest -q`, and run the same YOLO command on camera with new output names. Keep `--model models/yolo11n.onnx` and `--detector onnx`. Check the p50/p95 of `onnx_stage_latency_ms.postprocess` and end-to-end FPS, and note scene, background, lighting, hardware, and provider for fair comparison. CPU timing may change due to camera content, temperature and thread scheduling.

## Remaining limits

No production-readiness claim, no model accuracy without annotations, no verified Core ML acceleration, and no guaranteed real-time performance on another device. A paired reproducible replay of **raw ONNX outputs** would be preferable to comparing two changing live scenes.
