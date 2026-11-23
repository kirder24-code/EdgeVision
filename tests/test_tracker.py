import math
import pytest
from edgevision.tracking import CppTracker


def test_id_is_stable_on_smooth_motion():
    with CppTracker(max_distance=30) as tracker:
        ids = [tracker.update([(10 + i * 4, 20, 20, 20)])[0]['id'] for i in range(15)]
    assert len(set(ids)) == 1


def test_track_survives_brief_occlusion():
    with CppTracker(max_missed=2) as tracker:
        first = tracker.update([(10, 10, 20, 20)])[0]['id']
        assert tracker.update([])[0]['missed'] == 1
        assert tracker.update([])[0]['missed'] == 2
        assert tracker.update([(14, 10, 20, 20)])[0]['id'] == first


def test_track_expires():
    with CppTracker(max_missed=1) as tracker:
        first = tracker.update([(10, 10, 20, 20)])[0]['id']
        tracker.update([])
        assert tracker.update([]) == []
        assert tracker.update([(10, 10, 20, 20)])[0]['id'] != first


def test_two_objects_have_distinct_ids():
    with CppTracker() as tracker:
        tracks = tracker.update([(10, 10, 20, 20), (200, 200, 20, 20)])
        assert len({t['id'] for t in tracks}) == 2


def test_bad_box_does_not_change_state():
    with CppTracker() as tracker:
        first = tracker.update([(10, 10, 20, 20)])[0]['id']
        with pytest.raises(ValueError):
            tracker.update([(math.nan, 10, 20, 20)])
        assert tracker.update([(12, 10, 20, 20)])[0]['id'] == first


def test_bad_configuration():
    with pytest.raises(ValueError):
        CppTracker(max_distance=-1)
