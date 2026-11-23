"""Per-frame machine-readable trace is the reproducibility contract."""
import json
import pytest
from edgevision.__main__ import run
from scripts.generate_video import generate


def test_sync_trace_matches_video_and_contains_cpp_ids(tmp_path):
    src = tmp_path/'src.avi'
    generate(src, frames=35, width=320, height=240)
    trace = tmp_path/'tracks.jsonl'
    r = run(src, tmp_path/'out.avi', tmp_path/'metrics.json', tracks_jsonl=trace, min_area=100)
    records=[json.loads(x) for x in trace.read_text().splitlines()]
    assert len(records) == r['frames_processed'] == 35
    assert [row['source_sequence'] for row in records] == list(range(35))
    assert all(isinstance(t['id'],int) and t['id'] > 0 for row in records for t in row['tracks'])
    assert any(row['tracks'] for row in records)
    assert r['track_trace'] == str(trace)


def test_buffered_trace_preserves_capture_sequence_gaps(tmp_path):
    src=tmp_path/'src.avi'
    generate(src,frames=60,width=320,height=240)
    trace=tmp_path/'tracks.jsonl'
    r=run(src,tmp_path/'out.avi',tmp_path/'stats.json',tracks_jsonl=trace,capture_mode='buffered',queue_capacity=2,min_area=100)
    rows=[json.loads(x) for x in trace.read_text().splitlines()]
    seq=[x['source_sequence'] for x in rows]
    assert len(seq)==r['frames_processed']
    assert seq==sorted(set(seq))
    assert all(0<=i<r['capture_frames_read'] for i in seq)


def test_trace_must_not_overwrite_input_or_metrics(tmp_path):
    src=tmp_path/'src.avi'
    generate(src,frames=10,width=320,height=240)
    with pytest.raises(ValueError):
        run(src,tmp_path/'out.avi',tmp_path/'metrics.json',tracks_jsonl=src)
    with pytest.raises(ValueError):
        run(src,tmp_path/'out.avi',tmp_path/'metrics.json',tracks_jsonl=tmp_path/'metrics.json')
