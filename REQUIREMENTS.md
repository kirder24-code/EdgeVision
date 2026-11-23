# EdgeVision requirements — v0.2

Status: engineering baseline, not a production product specification. Identifiers are stable references for tests and commits.

| ID | Priority | Requirement | Objective verification |
|---|---|---|---|
| FR-01 | MUST | Read every decodable frame of an input video until EOF or `max_frames` | Synthetic 40-frame input yields exactly 40 processed frames |
| FR-02 | MUST | Detect moving foreground regions; report boxes; suppress regions smaller than `min_area` | Deterministic synthetic moving-object fixture, counts > 0; no semantic claims |
| FR-03 | MUST | Call native C++ for all ID association; no Python fallback tracker | `ctypes` library required and C++ ABI tests exercise real `.so` |
| FR-04 | MUST | Preserve ID for single smoothly moving object within distance threshold | Tracking trajectory unit test |
| FR-05 | MUST | Retain unmatched track for exactly `max_missed` consecutive misses, then remove | Explicit 1/2/3-miss tests |
| FR-06 | MUST | Reject NaN/Inf/zero or negative box dimensions without state changes | Native negative status + unchanged next update |
| FR-07 | MUST | Reject insufficient output capacity without **any** state mutation or overrun | Direct C ABI test; retry returns original IDs and expected missed count |
| FR-08 | MUST | Clean up native resource after use and refuse updates on closed wrapper | Wrapper lifecycle tests |
| FR-09 | MUST | Emit annotated video and a parseable JSON metrics report | End-to-end file test |
| FR-10 | MUST | Fail explicitly for missing input and zero-decoded-frame source | Negative integration tests |
| NFR-01 | MUST | Compile native library with C++17 and strict warning flags | `scripts/build.sh` |
| NFR-02 | MUST | Report latency p50/p95/max, two clearly scoped throughput metrics, sampled peak RSS | JSON schema and range assertions |
| NFR-03 | MUST | Run deterministic automated test suite on Linux CPU without network after dependencies installed | `pytest` + native rebuild |
| NFR-04 | SHOULD | Package Docker image and reproduce tests in Linux container | Docker build/run on a Docker-enabled host (currently unverified) |
| NFR-05 | SHOULD | Benchmark >= 20 processing FPS and p95 <= 50 ms at 640×480 on a **specified** CPU and dataset | Repeated timed runs with environment log; target, not a result |
| NFR-06 | SHOULD | Validate actual camera behavior and record frame drops and arrival-to-output lag | Hardware-in-loop experiment; not present in v0.2 |
| NFR-07 | SHOULD | Run Linux CI: build, test, static analysis, artifact smoke test | CI execution log; not present in v0.2 |

## Explicit out-of-scope v0.2

Semantic object classification; resilience to crossings; embedded device compliance; real-time deadline guarantees; ROS messaging; hardware sensor timestamp synchronization; guaranteed video-write durability; cybersecurity hardening. These cannot be inferred from passing the tests.

## Definition of done for a milestone

Spec and acceptance test committed before behavior change; demonstrate red test on old build; implement minimal fix; confirm green suite and rebuilt C++; record actual tool commands; no unverified hardware, throughput or Docker claims; update changelog and honest limitations.

## v0.3 buffered capture addition (pre-implementation)

| ID | Priority | Requirement | Test |
|---|---|---|---|
| FR-11 | MUST | Fixed-capacity FIFO drops oldest upon overflow, never expands, counts drops and maximum depth | T-14 / T-15 |
| FR-12 | MUST | Monotonic sequence/timestamp packets and nonnegative measured queue residence time | T-16 |
| FR-13 | MUST | Closing a queue wakes consumers, drains queued packets before EOF and prevents new pushes | T-17 |
| FR-14 | MUST | Capture thread signals EOF, propagates read exceptions, and can be joined after early stop | T-18 / T-19 |
| FR-15 | MUST | Optional `buffered` pipeline writes annotated output and consistent capture/drop telemetry; sync mode unchanged | T-20 |
| NFR-08 | SHOULD | Real camera capture-to-consumer age benchmark with configured queue capacity and CPU load | Hardware pending |

Time stamps are host post-decode times, not exposure times. Queue overflow is a **software** drop counter and cannot detect frames lost inside camera drivers or codecs.

## v0.4 independently specified evaluation, tracker robustness (before implementation)

| ID | Priority | Contract | Verification |
|---|---|---|---|
| FR-16 | MUST | IoU from valid XYWH boxes; reject invalid boxes | identical=1, disjoint=0, half-width overlap=1/3 |
| FR-17 | MUST | One-to-one per-frame matching of GT and predictions at a declared IoU threshold | duplicate prediction cannot count twice |
| FR-18 | MUST | Dataset-level micro precision, recall and F1 from TP, FP, FN; zero denominators yield 0 | manually computed 3-frame fixture |
| FR-19 | MUST | Stable IDs for two labelled, constant-velocity objects crossing with modest vertical offset | five-frame C++ test, independent of foreground detector |
| FR-20 | SHOULD | Evaluate detection on independently annotated real camera footage | pending acquisition of recorded consent-safe footage; synthetic fixture is **not** a real-world accuracy estimate |

Target for crossing fixture: 0 ID switches. No general claim about occlusion, severe perspective shift or crowded scenes.
