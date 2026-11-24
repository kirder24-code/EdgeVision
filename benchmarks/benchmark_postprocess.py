"""Opt-in reproducible decoder microbenchmark, not a real ONNX inference test.

Usage: python benchmarks/benchmark_postprocess.py
For a before/after comparison, supply a checkout of the previous version
using --baseline /path/to/old/onnx_detector.py.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgevision.onnx_detector import decode_yolo_raw


def fixture(seed=2026):
    rng = np.random.default_rng(seed)
    raw = np.empty((1,84,8400), dtype=np.float32)
    raw[0,0:2] = rng.uniform(0,640,(2,8400))
    raw[0,2:4] = rng.uniform(5,120,(2,8400))
    raw[0,4:] = rng.uniform(0,.14,(80,8400))
    ids = rng.choice(8400,100,replace=False)
    raw[0,4,ids] = rng.uniform(.35,.96,len(ids))
    return raw


def measure(callable_, tensor, rounds):
    for _ in range(8): callable_(tensor,(480,640),(1.,(0,80)),confidence=.3)
    samples=[]
    for _ in range(rounds):
        start=time.perf_counter_ns()
        callable_(tensor,(480,640),(1.,(0,80)),confidence=.3)
        samples.append((time.perf_counter_ns()-start)/1e6)
    return {'median_ms':round(statistics.median(samples),4),
            'p95_ms':round(sorted(samples)[int(.95*(len(samples)-1))],4),
            'iterations':rounds}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, help='Prior onnx_detector.py file; otherwise only current implementation')
    p.add_argument('--iterations', type=int, default=100)
    args=p.parse_args()
    if args.iterations < 10: p.error('iterations must be at least 10')
    raw=fixture()
    report={'description':'synthetic raw YOLO decode + class-aware NMS, no inference',
            'shape':list(raw.shape),'current':measure(decode_yolo_raw,raw,args.iterations)}
    if args.baseline:
        spec=importlib.util.spec_from_file_location('edgevision_old_decoder',args.baseline)
        mod=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=mod
        spec.loader.exec_module(mod)
        prior=mod.decode_yolo_raw(raw,(480,640),(1.,(0,80)),confidence=.3)
        updated=decode_yolo_raw(raw,(480,640),(1.,(0,80)),confidence=.3)
        assert len(prior) == len(updated), 'Different number of results'
        for a,b in zip(prior,updated):
            assert a.class_id == b.class_id and a.score == b.score and np.allclose(a.xywh,b.xywh,atol=1e-5), 'Decoder results differ'
        report['baseline']=measure(mod.decode_yolo_raw,raw,args.iterations)
        report['speedup_median']=round(report['baseline']['median_ms']/report['current']['median_ms'],2)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
