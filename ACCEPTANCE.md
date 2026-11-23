# EdgeVision acceptance ledger

Recorded date: 2026-11-23. `PASS` means verified **in the local environment only**. `PENDING` is not a failure and must not be represented as pass.

| Gate | Evidence required | State |
|---|---|---|
| A01: architecture + test contracts | ARCHITECTURE.md, REQUIREMENTS.md, TEST_PLAN.md | DOCUMENTED |
| A02: native Linux build | `bash scripts/build.sh` output | PENDING recheck |
| A03: tests, including ABI atomicity | `python -m pytest -q` | PENDING recheck |
| A04: 40-frame synthetic integration | automated round-trip test | PENDING recheck |
| A05: metric integrity | JSON assertions and definitions | PENDING recheck |
| A06: realistic detector quality | labeled, unseen real-world clips + metrics | NOT STARTED |
| A07: Docker reproducibility | build and run logs from Docker-enabled machine | NOT VERIFIED |
| A08: camera latency and drops | instrumented USB/edge-device run | NOT STARTED |
| A09: edge benchmark | repeatable report on specified CPU and dataset | NOT STARTED |
| A10: public GitHub + CI | remote URL, successful workflow logs | NOT STARTED |

Candidate targets (not measurements): at least 20 processed FPS, p95 processing <= 50 ms at 640×480, measured on named target hardware. Define dataset and repeat count before evaluating this gate. There is no current target for recognition accuracy because the baseline is a motion detector.

## Change control

A milestone cannot be marked complete until independent tests, edge cases, and the relevant acceptance gate have evidence. Retain failing-test evidence for TDD milestones. Do not use the old green suite to claim new behavior without additional assertions.
