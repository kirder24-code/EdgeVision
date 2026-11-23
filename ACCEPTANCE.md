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

## v0.5-v0.7 consolidated local verification (2026-11-23)

- Native C++ compiled with g++ -Wall -Wextra -Werror; Python **44 tests passed** after last track audit change.
- Separately compiled C++ native ABI smoke with Clang/ASan/UBSan; **passed**, no sanitizer errors in that run.
- Confirmed a concrete I/O safety defect before fixing: 4 legacy tests failed when source/output/metrics path collisions or invalid max-frame values were supplied. Protected inputs are now validated before opening VideoCapture.
- Tests-first JSONL audit records original source sequence, compute time and native C++ track records (3 new contracts). The trace can identify sequence gaps from buffered capture.
- New trajectory evaluator counts descriptive IoU-matched ID switches, unmatched GT and unmatched predictions; tests use hand-labelled sequences, not derived labels.
- Repeated **three sync runs**, 180 frames each, from the same synthetic file. See `artifacts/benchmark_v1/summary.json` for exact per-run results and environment.
- Full release smoke validates actual decoded output frames, not just metadata. The executable `scripts/verify_release.sh` is the reproducibility entry point.
- **PENDING**: real annotated videos, USB camera, target edge hardware, Docker image runtime, public GitHub remote and hosted CI. These are environment/external evidence gates, not automatically satisfied by a passing local test suite.

## macOS preflight acceptance (pending execution on an actual Mac)

- [x] Platform-specific `.so` / `.dylib` selection under unit tests (Linux host).
- [x] Camera probe validates open/read and releases device under mocked unit tests.
- [x] macOS setup script and macOS GitHub Actions job authored.
- [ ] macOS compiler executes and produces a loadable `.dylib` on real macOS hardware.
- [ ] macOS pytest and offline video end-to-end test pass in macOS CI.
- [ ] macOS camera permission grant, 30-frame acquisition and readable output video verified on user hardware.
- [ ] macOS camera metrics and real-world tracking evaluated and recorded.
