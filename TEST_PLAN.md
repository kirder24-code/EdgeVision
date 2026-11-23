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
