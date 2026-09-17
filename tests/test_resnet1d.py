"""CPU checks using general synthetic waveforms, never cryptographic labels."""

import io

import pytest
import torch
from torch import nn

from pqc_bench.models.resnet1d import ResidualBlock1D, SideChannelResNet1D


@pytest.fixture(autouse=True)
def cpu_settings():
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(17)
        yield
    torch.set_num_threads(threads)


def waveforms(length=64):
    t = torch.linspace(0, 1, length)
    return torch.stack((torch.sin(2 * torch.pi * t), torch.cos(4 * torch.pi * t)))


def small_model(**kwargs):
    config = dict(input_length=64, stem_channels=4, stage_channels=(8, 16),
                  blocks_per_stage=1, fc_dim=8, dropout_p=0.0)
    config.update(kwargs)
    return SideChannelResNet1D(**config)


def test_shape_and_convenience_input():
    model = small_model().eval()
    x = waveforms()
    with torch.no_grad():
        logits = model(x)
        assert logits.shape == (2, 4)
        assert torch.isfinite(logits).all()
        torch.testing.assert_close(logits, model(x.unsqueeze(1)))


@pytest.mark.parametrize('channels,stride,length', [(4, 1, 33), (8, 2, 33), (8, 2, 32)])
def test_residual_addition(channels, stride, length):
    block = ResidualBlock1D(4, channels, stride=stride).eval()
    with torch.no_grad():
        block.conv2.weight.zero_()
        x = torch.randn(2, 4, length)
        expected = torch.relu(block.downsample(x))
        torch.testing.assert_close(block(x), expected)
        assert block(x).shape == (2, channels, (length + stride - 1) // stride)


def test_gradient_and_optimizer_step():
    model = small_model()
    x = waveforms().requires_grad_()
    before = model.stem[0].weight.detach().clone()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    loss = nn.functional.cross_entropy(model(x), torch.tensor([0, 1]))
    loss.backward()
    assert torch.isfinite(loss)
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert x.grad.abs().sum() > 0
    for parameter in model.parameters():
        assert parameter.grad is not None
        assert torch.isfinite(parameter.grad).all()
    optimizer.step()
    assert not torch.equal(before, model.stem[0].weight)


def test_state_dict_roundtrip():
    model = small_model().eval()
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    buffer.seek(0)
    restored = small_model().eval()
    restored.load_state_dict(torch.load(buffer, weights_only=True, map_location='cpu'))
    with torch.no_grad():
        torch.testing.assert_close(model(waveforms()), restored(waveforms()), rtol=0, atol=0)


def test_probabilities():
    probabilities = small_model().predict_probabilities(waveforms())
    assert not probabilities.requires_grad
    assert (probabilities >= 0).all()
    torch.testing.assert_close(probabilities.sum(dim=1), torch.ones(2))


@pytest.mark.parametrize('config', [
    {'input_length': 31}, {'input_length': 4097}, {'input_length': True},
    {'input_length': 64.0}, {'num_classes': 1}, {'num_classes': 65},
    {'in_channels': 0}, {'in_channels': 9}, {'stem_channels': 0},
    {'stem_channels': 129}, {'blocks_per_stage': 0}, {'blocks_per_stage': 5},
    {'fc_dim': 0}, {'fc_dim': 257}, {'stage_channels': ()},
    {'stage_channels': (4, 4, 4, 4)}, {'stage_channels': [4, 8]},
    {'stage_channels': (True,)}, {'stage_channels': (129,)},
    {'dropout_p': True}, {'dropout_p': -0.1}, {'dropout_p': 1.0},
    {'dropout_p': float('nan')}, {'dropout_p': float('inf')},
    {'dropout_p': '0.1'},
])
def test_rejects_invalid_configuration(config):
    with pytest.raises(ValueError):
        small_model(**config)


@pytest.mark.parametrize('config', [
    {'kernel_size': 2}, {'kernel_size': 0}, {'kernel_size': 17},
    {'stride': 0}, {'stride': 3}, {'in_channels': True}, {'out_channels': 129},
])
def test_rejects_invalid_block(config):
    options = dict(in_channels=4, out_channels=4)
    options.update(config)
    with pytest.raises(ValueError):
        ResidualBlock1D(**options)


@pytest.mark.parametrize('shape', [(64,), (2, 1, 1, 64), (0, 64), (65, 64),
                                  (2, 2, 64), (2, 63)])
def test_rejects_invalid_shape(shape):
    with pytest.raises(ValueError):
        small_model()(torch.zeros(shape))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_rejects_nonfinite(value):
    x = waveforms()
    x[0, 0] = value
    with pytest.raises(ValueError, match='non-finite'):
        small_model()(x)


@pytest.mark.parametrize('dtype', [torch.int64, torch.bool, torch.complex64, torch.float64])
def test_rejects_incompatible_dtype(dtype):
    with pytest.raises(ValueError):
        small_model()(torch.zeros(2, 64, dtype=dtype))


def test_rejects_non_tensor_and_sparse():
    with pytest.raises(TypeError):
        small_model()([[0.] * 64])
    with pytest.raises(ValueError, match='dense'):
        small_model()(waveforms().to_sparse())


@pytest.mark.parametrize('length', [32, 33, 65, 256, 4096])
def test_supported_lengths_inference(length):
    model = small_model(input_length=length, stage_channels=(4, 8, 16)).eval()
    with torch.no_grad():
        assert model(waveforms(length)[:1]).shape == (1, 4)


@pytest.mark.parametrize('length', [33, 65, 256, 4096])
def test_single_sample_training(length):
    model = small_model(input_length=length, stage_channels=(4, 8, 16))
    x = waveforms(length)[:1]
    assert model(x).shape == (1, 4)


def test_batchnorm_single_temporal_position_training_error():
    """Batch-1 training is undefined when the deepest stage collapses to one
    temporal position; PyTorch BatchNorm raises a clear error."""
    model = small_model(input_length=32, stage_channels=(4, 8, 16))
    with pytest.raises(ValueError, match='more than 1 value per channel'):
        model(waveforms(32)[:1])


def test_multiple_channels():
    model = small_model(in_channels=2)
    assert model(waveforms().unsqueeze(0)).shape == (1, 4)
    with pytest.raises(ValueError, match='channels'):
        model(waveforms())


def test_identity_skip_preserves_gradient():
    block = ResidualBlock1D(4, 4).eval()
    with torch.no_grad():
        block.conv2.weight.zero_()
    x = torch.ones(2, 4, 32, requires_grad=True)
    block(x).sum().backward()
    torch.testing.assert_close(x.grad, torch.ones_like(x))


def test_public_export_and_default_model():
    from pqc_bench.models import SideChannelResNet1D as Exported
    assert Exported is SideChannelResNet1D
    model = Exported().eval()
    with torch.no_grad():
        assert model(waveforms(256)).shape == (2, 4)


def test_probability_helper_eval_semantics():
    model = small_model(dropout_p=0.25).train()
    mean_before = model.stem[1].running_mean.clone()
    x = waveforms()
    first = model.predict_probabilities(x)
    second = model.predict_probabilities(x)
    assert not model.training
    torch.testing.assert_close(first, second, rtol=0, atol=0)
    torch.testing.assert_close(mean_before, model.stem[1].running_mean)
    model.train()
    assert model.training
