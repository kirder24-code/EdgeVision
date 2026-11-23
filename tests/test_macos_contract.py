"""macOS contract tests, deliberately written before implementation."""
from unittest.mock import Mock

import pytest


def test_native_library_name_matches_platform():
    from edgevision.tracking import native_library_filename
    assert native_library_filename('Darwin') == 'libedgevision_tracker.dylib'
    assert native_library_filename('Linux') == 'libedgevision_tracker.so'
    with pytest.raises(RuntimeError, match='Unsupported'):
        native_library_filename('Windows')


def test_camera_probe_closes_capture_and_counts_real_reads():
    from edgevision.camera_probe import probe_camera
    import numpy as np
    fake = Mock()
    fake.isOpened.return_value = True
    fake.read.side_effect = [(True, np.zeros((240,320,3), dtype=np.uint8))] * 4
    result = probe_camera(index=0, frames=4, capture_factory=lambda *_: fake)
    assert result['frames_read'] == 4
    assert result['resolution'] == [320,240]
    assert result['camera_index'] == 0
    fake.release.assert_called_once()


def test_camera_probe_reports_permission_or_unavailable_and_releases():
    from edgevision.camera_probe import probe_camera, CameraProbeError
    fake = Mock()
    fake.isOpened.return_value = False
    with pytest.raises(CameraProbeError, match='camera'):
        probe_camera(index=0, frames=3, capture_factory=lambda *_: fake)
    fake.release.assert_called_once()


def test_camera_probe_reports_no_frames_and_releases():
    from edgevision.camera_probe import probe_camera, CameraProbeError
    fake = Mock()
    fake.isOpened.return_value = True
    fake.read.return_value = (False, None)
    with pytest.raises(CameraProbeError, match='frames'):
        probe_camera(index=0, frames=2, capture_factory=lambda *_: fake)
    fake.release.assert_called_once()
