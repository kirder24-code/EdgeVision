# EdgeVision test plan (architecture-first / TDD)

Version: 2026-11-23. Tests are written from requirements, NOT invented from observed implementation behavior. A passing test establishes only the behavior it asserts.

| Test | Requirement | Fixture | Expected result | Tier |
|---|---|---|---|---|
| T-01 | FR-04 | 15 small movements (< distance gate) | One unchanged positive ID | unit/native |
| T-02 | FR-05 | Create, miss twice, reappear | Same ID, missed resets to zero | unit/native |
| T-03 | FR-05 | Create, miss over threshold | Original track removed; new ID when object returns | unit/native |
| T-04 | FR-06 | NaN box after valid track | Failure and preserved track ID | unit/native |
| T-05 | FR-07 | Native update with zero output capacity and one input | Error, **no new ID allocation**; retry returns ID=1 | C ABI/contract |
| T-06 | FR-07 | Native update with one output slot and two active objects | Error, no track boxes or missed count updated; retry behaves as if failed call never happened | C ABI/contract |
| T-07 | FR-08 | Update after `close` | Python RuntimeError | wrapper |
| T-08 | FR-01/09, NFR-02 | 40-frame generated AVI | 40 decoded/encoded frames, metrics JSON valid with nonnegative timings | end-to-end |
| T-09 | FR-10 | Nonexistent AVI | Explicit RuntimeError | negative integration |
| T-10 | NFR-01/03 | Clean C++ build + pytest | Build succeeds, all tests pass on target Linux | build |
| T-11 | NFR-04 | Container build + smoke run | Image builds and writes output artifacts | integration/manual, pending |
| T-12 | NFR-05 | repeated 640×480 input on named CPU | Report sample size, p50/p95, throughput, variance | benchmark/manual, pending |
| T-13 | NFR-06 | live USB camera | Frame-drop and capture-to-output timestamps validated | hardware/manual, pending |

## TDD evidence format

For each behavior change: record baseline SHA, new test name, command + failing assertion (RED), smallest code patch, passing command (GREEN), any refactor, and environment limitations. Do not claim CI/Docker or hardware pass without executed logs.

## Controlled limitations

A moving white rectangle tests a decode→detector→native tracker→encode path, not model accuracy or identity robustness in crowded scenes. MOG2 can classify the initial frame as background motion. Benchmark results depend on CPU, source encoding, library versions, warmup and the number of frames; one run does not establish an SLA.

## v0.3 test plan — specified before implementation

| Test | Contract | Controlled input | Expected observation |
|---|---|---|---|
| T-14 | FR-11 | queue capacity=2; push seq=0,1,2 | pop seq=1,2; exactly one overflow; max depth=2 |
| T-15 | FR-11 | queue capacity=1; push seq=0..99 | only seq=99 retained; 99 overflows; size never >1 |
| T-16 | FR-12 | injected monotonic timestamps and dequeue clock | ordered packet IDs and nonnegative queue residence; invalid capacity rejected |
| T-17 | FR-13 | queue waiting thread and close; separately close with queued data | waiter terminates with None; queued data drains; further put rejected |
| T-18 | FR-14 | fake finite capture | capture thread reaches EOF; all packets returned if no consumer delay/overflow; joins |
| T-19 | FR-14 | fake capture raising RuntimeError | worker error surfaces on consumer; worker terminates |
| T-20 | FR-15 | synthetic encoded AVI in buffered mode | positive processed frames; output opens; counters reconcile; sync existing tests remain green |

Execution evidence: retain RED pytest output before `capture.py` exists and GREEN output after implementation; never claim camera/sensor timestamp verification.

## v0.4 test-first contracts

- T-21: IoU identical/disjoint/partial with hand-computed results.
- T-22: One-to-one TP matching prevents duplicate detection credit.
- T-23: FP/FN accounting and safe empty-frame denominators.
- T-24: Three-frame handcrafted ground truth yields TP=1, FP=1, FN=2, precision=0.5, recall=1/3, F1=0.4.
- T-25: Invalid boxes and thresholds explicitly rejected.
- T-26: C++ tracking preserves two physically labelled identities across a five-frame crossing.
- T-27 (pending external dataset): record immutable frame annotations; measure detection metrics without using predictions to create labels.
