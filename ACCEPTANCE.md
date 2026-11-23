# EdgeVision acceptance ledger

Recorded date: 2026-11-23. `PASS` means verified **in the local environment only**. `PENDING` is not a failure and must not be represented as pass.

| Gate | Evidence required | State |
|---|---|---|
| A01: architecture + test contracts | ARCHITECTURE.md, REQUIREMENTS.md, TEST_PLAN.md | DOCUMENTED |
| A02: native Linux build | `bash scripts/build.sh` output | PASS local (2026-11-23) |
| A03: tests, including ABI atomicity | `python -m pytest -q` | PASS local (2026-11-23) |
| A04: 40-frame synthetic integration | automated round-trip test | PASS local (2026-11-23) |
| A05: metric integrity | JSON assertions and definitions | PASS local (2026-11-23) |
| A06: realistic detector quality | labeled, unseen real-world clips + metrics | NOT STARTED |
| A07: Docker reproducibility | build and run logs from Docker-enabled machine | NOT VERIFIED |
| A08: camera latency and drops | instrumented USB/edge-device run | NOT STARTED |
| A09: edge benchmark | repeatable report on specified CPU and dataset | NOT STARTED |
| A10: public GitHub + CI | remote URL, successful workflow logs | NOT STARTED |

Candidate targets (not measurements): at least 20 processed FPS, p95 processing <= 50 ms at 640×480, measured on named target hardware. Define dataset and repeat count before evaluating this gate. There is no current target for recognition accuracy because the baseline is a motion detector.

## Change control

A milestone cannot be marked complete until independent tests, edge cases, and the relevant acceptance gate have evidence. Retain failing-test evidence for TDD milestones. Do not use the old green suite to claim new behavior without additional assertions.

## Verified local run — TDD milestone FR-07

- Previous commit: `e7380ac` (v0.1 baseline).
- New independent tests T-05/T-06 failed before the patch (`2 failed`). Both demonstrated state mutation on insufficient C ABI output capacity.
- Fix: apply each native update to a local tracker copy and commit it only when result is nonnegative. This favors correctness over peak-performance efficiency; capacity failure cannot leak mutated IDs or boxes.
- After C++ rebuild: `bash scripts/build.sh && python -m pytest -q` => **12 passed**.
- Red/green command output is captured in `artifacts/tdd_red.log` and `artifacts/tdd_green.log`.
- Native C++ and pytest run on this Linux host; Docker, camera, GitHub remote, and target-hardware benchmarking remain unverified.

## v0.3 bounded capture TDD milestone (2026-11-23)

| Gate | Status / evidence |
|---|---|
| A11: architecture/requirements/test cases before change | DOCUMENTED, commit `e15c206` |
| A12: RED evidence | PASS (missing `edgevision.capture` raises ModuleNotFoundError at test collection; no behavior tested yet), `artifacts/tdd_v03_red.log` |
| A13: bounded FIFO / drop-oldest / wake / worker tests | PASS locally, 7 new queue+worker tests |
| A14: buffered end-to-end video / metric reconciliation | PASS locally, 1 new integration test |
| A15: full regression after C++ rebuild | PASS locally, 20 tests |
| A16: actual USB camera / driver drops / exposure timing | NOT VERIFIED |
| A17: guaranteed interruptible device capture on shutdown | NOT IMPLEMENTED (blocking native read may delay stop) |

Sample **single local** buffered-file run (synthetic 640×480, 180 frames read, queue capacity=3, max 100 processed): `capture_frames_read=180`, `frames_processed=20`, `frames_dropped_overflow=160`, `queue_max_depth=3`, processing latency p95=8.444 ms, queue wait p95=10.542 ms. See `artifacts/v03_metrics.json`; machine load and thread scheduling vary between runs. This is NOT a camera benchmark, nor 180 frames processed, nor a guarantee of throughput.

## v0.4 evaluation / crossing (2026-11-23)

- FR-16/17/18: PASS. Hand-computed IoU and precision/recall/F1 fixtures, one-to-one matching.
- FR-19: PASS for **one deterministic five-frame two-object crossing** only. Legacy greedy matcher switched IDs; velocity-based C++ association passed after rebuild.
- FR-20: NOT VERIFIED. No independent real-world camera footage was supplied; synthetic video cannot substitute for it.
- Synthetic detector fixture: 80 scored frames, IoU threshold 0.5; TP=64, FP=16, FN=16, precision=0.800, recall=0.800, F1=0.800 (single local run). Score is fixture-dependent; not an accuracy estimate on robotics scenes.
- Native C++ compiled with strict warnings; full pytest suite to be rerun before release.
- Docker, actual camera, real-scene MOT benchmark and external GitHub CI still unverified.
