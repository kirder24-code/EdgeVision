"""Small, independently testable output and latency contracts."""
import math
from pathlib import Path

def percentile_nearest_rank(samples, fraction):
    if not samples or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Expected nonempty samples and percentile in [0, 1]")
    values = sorted(samples)
    return values[max(0, math.ceil(fraction * len(values)) - 1)]

def validate_output_paths(video, metrics):
    if Path(video).resolve() == Path(metrics).resolve():
        raise ValueError("Output video and metrics paths must be different")
