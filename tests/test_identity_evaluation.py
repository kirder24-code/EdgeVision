"""Independent labelled-trajectory evaluation contracts (written before implementation)."""
import pytest
from edgevision.identity_evaluation import evaluate_identities


def obj(identity, x, y=10):
    return {'id': identity, 'box': (x, y, 12, 12)}


def test_perfect_two_object_sequence_has_no_switches():
    frames = [([obj('A', i*10), obj('B', 120-i*10)],
               [obj(1, i*10), obj(2, 120-i*10)]) for i in range(4)]
    result = evaluate_identities(frames)
    assert result['matches'] == 8
    assert result['id_switches'] == 0
    assert result['unmatched_gt'] == 0
    assert result['unmatched_predictions'] == 0
    assert result['id_switch_rate'] == 0


def test_identity_swap_is_counted_twice():
    frames = [([obj('A', 0), obj('B', 100)], [obj(7, 0), obj(8, 100)]),
              ([obj('A', 10), obj('B', 90)], [obj(8, 10), obj(7, 90)])]
    result = evaluate_identities(frames)
    assert result['id_switches'] == 2
    assert result['matches'] == 4


def test_unmatched_frames_not_assigned_identity():
    frames = [([obj('A', 0)], [obj(1, 0)]),
              ([obj('A', 10)], []),
              ([obj('A', 20)], [obj(2, 20)])]
    result = evaluate_identities(frames)
    assert result['unmatched_gt'] == 1
    assert result['id_switches'] == 1


def test_matching_is_one_to_one_even_with_duplicate_predictions():
    result = evaluate_identities([([obj('A', 0)], [obj(1, 0), obj(2, 0)])])
    assert result['matches'] == 1
    assert result['unmatched_predictions'] == 1


def test_invalid_duplicate_ids_per_frame_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        evaluate_identities([([obj('A', 0), obj('A', 30)], [])])


def test_empty_input_is_well_defined():
    assert evaluate_identities([])['id_switch_rate'] == 0
