from scripts.evaluate_synthetic import run


def test_labelled_synthetic_evaluation_writes_auditable_metrics(tmp_path):
    output = tmp_path / 'synthetic_scores.json'
    scores = run(output)
    assert output.exists()
    assert scores['scored_frames'] == 80
    assert scores['tp'] + scores['fn'] == 80
    assert scores['tp'] + scores['fp'] >= 0
    assert 0 <= scores['precision'] <= 1
    assert 0 <= scores['recall'] <= 1
    assert scores['dataset'].startswith('synthetic_')
