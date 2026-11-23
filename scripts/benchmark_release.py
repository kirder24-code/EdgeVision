"""Repeated offline benchmark with machine identity, never claimed as live-camera latency."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import cv2
import psutil
from edgevision.__main__ import run


def benchmark(source, directory, repetitions=3):
    if repetitions < 1:
        raise ValueError('repetitions must be >= 1')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    runs = []
    for i in range(repetitions):
        report = run(source, directory/f'iteration_{i+1}.avi', directory/f'iteration_{i+1}.json')
        runs.append(report)
    result = {
        'environment': {
            'platform': platform.platform(), 'machine': platform.machine(),
            'python': sys.version.split()[0], 'opencv': cv2.__version__,
            'logical_cpus': psutil.cpu_count(),
            'cpu_name': (Path('/proc/cpuinfo').read_text().split('model name',1)[-1].split(':',1)[-1].split('\n',1)[0].strip()
                         if Path('/proc/cpuinfo').is_file() else 'not recorded'),
        },
        'sample_size': repetitions,
        'source': str(source),
        'per_run': runs,
        'median_file_throughput_fps': statistics.median(r['end_to_end_fps_including_io'] for r in runs),
        'median_processing_p95_ms': statistics.median(r['processing_latency_ms']['p95'] for r in runs),
        'limitations': ('Local recorded-video CPU throughput, no camera input, no sensor exposure timestamps; '
                        'non-thermal-controlled machine with variable resource contention'),
    }
    (directory/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='artifacts/release_input.avi')
    parser.add_argument('--directory', default='artifacts/benchmark_v1')
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.source,args.directory,args.repetitions),indent=2))
