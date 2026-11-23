"""Telemetry/recording contract: every written frame is counted and outputs are safe."""
import pytest
from edgevision.recorder import percentile_nearest_rank, validate_output_paths


def test_percentile_nearest_rank_explicit_boundary():
    assert percentile_nearest_rank([1, 2, 3, 4, 100], .95) == 100
    assert percentile_nearest_rank([1, 2, 3, 4, 100], .50) == 3
    assert percentile_nearest_rank([7], .95) == 7


def test_percentile_rejects_bad_inputs():
    with pytest.raises(ValueError):
        percentile_nearest_rank([], .95)
    with pytest.raises(ValueError):
        percentile_nearest_rank([1, 2], 1.1)


def test_output_and_metrics_paths_must_be_different(tmp_path):
    p = tmp_path/'out.avi'
    with pytest.raises(ValueError, match='different'):
        validate_output_paths(p, p)
    validate_output_paths(tmp_path/'out.avi', tmp_path/'result.json')
