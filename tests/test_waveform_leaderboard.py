"""CPU contracts; fabricated prediction fixtures test arithmetic, not performance."""
from dataclasses import FrozenInstanceError, replace
import json
import math

import pytest

from pqc_bench.waveform_leaderboard import EvaluationResult, SyntheticSplit, build_leaderboard


def split():
    return SyntheticSplit("test-v1", "raw-v1", (
        tuple(math.sin(2 * math.pi * i / 32) for i in range(32)),
        tuple(math.cos(2 * math.pi * i / 32) for i in range(32)),
        tuple(0.1 if i % 2 else -0.1 for i in range(32)),
    ), (0, 1, 2))


def result(model_id="cnn-1", predictions=(0, 1, 2), **kwargs):
    return EvaluationResult(model_id, "CNN", "untrained", split(), predictions, **kwargs)


def test_exact_accuracy_ties_competition_rank_and_input_order():
    a, b, c = result("z"), result("a"), result("b", (0, 0, 0))
    report = build_leaderboard((c, a, b))
    assert [(r["model_id"], r["rank"]) for r in report["rows"]] == [("a", 1), ("z", 1), ("b", 3)]
    assert report == build_leaderboard((b, c, a))
    assert c.correct == 1 and c.accuracy == 1 / 3
    assert report["rows"][2]["accuracy"] == 1 / 3
    assert report["rows"][2]["correct"] == 1
    assert result(predictions=(1, 2, 0)).accuracy == 0


def test_empty_missing_metrics_and_json():
    assert build_leaderboard(())["rows"] == []
    assert build_leaderboard(())["split_fingerprint"] is None
    report = build_leaderboard((result(),))
    row = report["rows"][0]
    for name in row["unmeasured_metrics"]:
        assert row[name] is None
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    row["accuracy"] = -1
    assert build_leaderboard((result(),))["rows"][0]["accuracy"] == 1


@pytest.mark.parametrize("value", [None, [], True, "0", (0,), (0, 1, 3), (0, 1, -1),
                                  (0, 1, True), (0, 1, 2.0), (0, 1, float("nan")),
                                  (0, 1, float("inf")), (0, 1, -float("inf"))])
def test_invalid_predictions(value):
    with pytest.raises(ValueError):
        result(predictions=value)


@pytest.mark.parametrize("family", ["GAN", "Discriminator", "CPA", "MLP", None, [], True])
def test_invalid_family(family):
    with pytest.raises(ValueError):
        replace(result(), family=family)


@pytest.mark.parametrize("name", ["", "a" * 65, "a/b", "a\nb", None, True, 2])
@pytest.mark.parametrize("field", ["model_id", "split_id", "preprocessing_id"])
def test_invalid_identifiers(name, field):
    with pytest.raises(ValueError):
        replace(result() if field == "model_id" else split(), **{field: name})


@pytest.mark.parametrize("value", [None, [], "unknown", True])
def test_invalid_training_status(value):
    with pytest.raises(ValueError):
        replace(result(), training_status=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, None,
                                  "0", 1.01, -1.01, 1j, 10**400])
def test_invalid_waveform_samples(value):
    s = split()
    with pytest.raises(ValueError):
        replace(s, waveforms=((value,) + s.waveforms[0][1:],) + s.waveforms[1:])


@pytest.mark.parametrize("waveforms", [(), [], ((0.,) * 32,) * 2, ((0.,) * 32,) * 257,
                                      ((0.,) * 31,) * 3, ((0.,) * 4097,) * 3,
                                      ((0.,) * 32, (0.,) * 33, (0.,) * 32),
                                      ([0.] * 32,) * 3])
def test_invalid_waveform_shapes(waveforms):
    with pytest.raises(ValueError):
        replace(split(), waveforms=waveforms)


@pytest.mark.parametrize("targets", [(0, 0, 1), (0, 1), [0, 1, 2], (0, 1, True), (0, 1, 3)])
def test_invalid_targets(targets):
    with pytest.raises(ValueError):
        replace(split(), targets=targets)


@pytest.mark.parametrize("change", [
    {"split_id": "other"}, {"preprocessing_id": "normalized"}, {"targets": (2, 1, 0)},
    {"waveforms": ((0.,) * 32,) * 3},
])
def test_incomparable_splits(change):
    a = result("a")
    b = replace(a, model_id="b", split=replace(a.split, **change))
    with pytest.raises(ValueError, match="incomparable"):
        build_leaderboard((a, b))


def test_incomparable_training_and_duplicates():
    with pytest.raises(ValueError, match="training"):
        build_leaderboard((result("a"), replace(result("b"), training_status="trained")))
    with pytest.raises(ValueError, match="unique"):
        build_leaderboard((result(), result()))


@pytest.mark.parametrize("values", [[], None, (None,), ({},), (result(),) * 65])
def test_invalid_results(values):
    with pytest.raises(ValueError):
        build_leaderboard(values)


def test_immutable_and_strict_constructor_no_metrics():
    with pytest.raises(FrozenInstanceError):
        result().model_id = "edited"
    with pytest.raises(FrozenInstanceError):
        split().targets = (2, 1, 0)
    with pytest.raises(TypeError):
        result(accuracy=float("nan"))
    with pytest.raises(ValueError):
        replace(result(), split={})


def test_numeric_canonicalization_and_max_bounds():
    s = split()
    a = replace(s, waveforms=((0,) * 32,) * 3)
    b = replace(s, waveforms=((-0.0,) * 32,) * 3)
    assert a.fingerprint == b.fingerprint
    assert len(a.fingerprint) == 64
    big = SyntheticSplit("big", "raw", ((1.,) * 4096,) * 256, (0, 1) + (2,) * 254)
    assert len(big.waveforms) == 256
    report = build_leaderboard(tuple(result(f"model-{i}") for i in range(64)))
    assert len(report["rows"]) == 64
    assert all(r["rank"] == 1 for r in report["rows"])


def test_real_cpu_predictions_three_untrained_models():
    """Actual inference smoke test; no training, quality or speed assertion."""
    import torch
    from pqc_bench.models.resnet1d import SideChannelResNet1D
    from pqc_bench.models.side_channel_cnn import SideChannel1DCNN
    from pqc_bench.models.waveform_transformer import WaveformTransformer1D

    s = split()
    # A locally seeded random noise row, no secret-bearing labels/data.
    with torch.random.fork_rng():
        torch.manual_seed(64)
        noise = tuple((2 * torch.rand(32) - 1).tolist())
        s = replace(s, waveforms=s.waveforms[:2] + (noise,))
        models = (
            ("CNN", SideChannel1DCNN(input_length=32, num_classes=3,
                                    conv_channels=(4, 4, 4), fc_dim=4)),
            ("ResNet", SideChannelResNet1D(input_length=32, num_classes=3,
                                          stem_channels=4, stage_channels=(4,),
                                          blocks_per_stage=1, fc_dim=4)),
            ("Transformer", WaveformTransformer1D(input_length=32, num_classes=3,
                                                  d_model=4, num_heads=1, num_layers=1,
                                                  ff_dim=4, fc_dim=4)),
        )
        x = torch.tensor(s.waveforms, dtype=torch.float32)
        evaluations = []
        with torch.no_grad():
            for family, model in models:
                logits = model.eval()(x)
                assert logits.shape == (3, 3) and torch.isfinite(logits).all()
                predictions = tuple(logits.argmax(dim=1).tolist())
                evaluations.append(EvaluationResult(family.lower() + "-random-v1", family,
                                                    "untrained", s, predictions))
        report = build_leaderboard(tuple(evaluations))
        assert {r["family"] for r in report["rows"]} == {"CNN", "ResNet", "Transformer"}
        for r in report["rows"]:
            evaluation = next(e for e in evaluations if e.model_id == r["model_id"])
            assert r["accuracy"] == sum(p == t for p, t in zip(evaluation.predictions, s.targets)) / 3
            assert r["training_status"] == "untrained"
