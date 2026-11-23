"""Fail-safe file path and metrics contracts defined before modifying runtime."""
import pytest
from edgevision.__main__ import run
from scripts.generate_video import generate


def test_output_must_not_overwrite_input(tmp_path):
    original = tmp_path / 'source.avi'
    generate(original, frames=12, width=320, height=240)
    before = original.read_bytes()
    with pytest.raises(ValueError, match='input'):
        run(original, original, tmp_path/'metrics.json')
    assert original.read_bytes() == before


def test_metrics_must_not_overwrite_input(tmp_path):
    original = tmp_path / 'source.avi'
    generate(original, frames=12, width=320, height=240)
    before = original.read_bytes()
    with pytest.raises(ValueError, match='input'):
        run(original, tmp_path/'out.avi', original)
    assert original.read_bytes() == before


def test_output_and_metrics_collisions_fail_before_decoding(tmp_path):
    source = tmp_path/'src.avi'
    generate(source, frames=5, width=320, height=240)
    with pytest.raises(ValueError, match='different'):
        run(source, tmp_path/'same.avi', tmp_path/'same.avi')


def test_invalid_max_frames_rejected(tmp_path):
    with pytest.raises(ValueError, match='max_frames'):
        run(tmp_path/'none.avi', tmp_path/'x.avi', tmp_path/'y.json', max_frames=-3)
