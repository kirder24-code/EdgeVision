"""Black-box C ABI contract tests derived from FR-07, not implementation internals.

These intentionally call the exported C ABI rather than CppTracker, which normally
allocates a sufficiently large output buffer and cannot expose buffer failures.
"""
import ctypes as ct
from pathlib import Path

import pytest

from edgevision.tracking import Detection, Track

LIBRARY = Path(__file__).resolve().parents[1] / "build" / "libedgevision_tracker.so"


@pytest.fixture
def native_tracker():
    lib = ct.CDLL(str(LIBRARY))
    lib.ev_tracker_create.argtypes = (ct.c_double, ct.c_int)
    lib.ev_tracker_create.restype = ct.c_void_p
    lib.ev_tracker_update.argtypes = (ct.c_void_p, ct.POINTER(Detection), ct.c_int,
                                      ct.POINTER(Track), ct.c_int)
    lib.ev_tracker_update.restype = ct.c_int
    lib.ev_tracker_destroy.argtypes = (ct.c_void_p,)
    lib.ev_tracker_destroy.restype = None
    handle = lib.ev_tracker_create(50.0, 2)
    assert handle
    try:
        yield lib, handle
    finally:
        lib.ev_tracker_destroy(handle)


def call(lib, handle, boxes, capacity):
    dets = (Detection * len(boxes))(*(Detection(*b) for b in boxes))
    output = (Track * max(1, capacity))()
    rc = lib.ev_tracker_update(handle, dets, len(boxes), output, capacity)
    return rc, [output[i] for i in range(rc)] if rc >= 0 else []


def test_rejected_small_buffer_does_not_consume_first_track_id(native_tracker):
    """T-05: failed update acts like no update happened at all."""
    lib, handle = native_tracker
    rc, _ = call(lib, handle, [(10, 10, 20, 20)], capacity=0)
    assert rc == -3
    rc, tracks = call(lib, handle, [], capacity=1)
    assert rc == 0, "Rejected update must not create a track"
    rc, tracks = call(lib, handle, [(10, 10, 20, 20)], capacity=1)
    assert rc == 1
    assert tracks[0].id == 1, "A failed update must not allocate IDs"
    assert tracks[0].missed == 0


def test_failed_update_preserves_existing_tracks_and_boxes(native_tracker):
    """T-06: no partial state change on rejected update."""
    lib, handle = native_tracker
    rc, tracks = call(lib, handle, [(10, 10, 20, 20)], capacity=1)
    assert rc == 1 and tracks[0].id == 1
    rc, _ = call(lib, handle, [(20, 10, 20, 20), (200, 10, 20, 20)], capacity=1)
    assert rc == -3
    rc, tracks = call(lib, handle, [], capacity=1)
    assert rc == 1, "Rejected call must not have created a second track"
    assert tracks[0].id == 1
    assert tracks[0].missed == 1, "Only the successful empty frame should count as missed"
    assert tracks[0].x == 10.0, "Rejected call must not update tracked position"
