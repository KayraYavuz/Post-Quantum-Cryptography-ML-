"""CPU-only checks with general synthetic sine, cosine, and noise waveforms."""

import inspect
import io

import pytest
import torch
from torch import nn

from pqc_bench.models.waveform_transformer import WaveformTransformer1D


@pytest.fixture(autouse=True)
def cpu_settings():
    threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(17)
            yield
    finally:
        torch.set_num_threads(threads)


def waveforms(length=64):
    t = torch.linspace(0, 1, length)
    return torch.stack((torch.sin(2 * torch.pi * t), torch.cos(4 * torch.pi * t)))


def small_model(**kwargs):
    config = dict(input_length=64, d_model=8, num_heads=2, num_layers=1,
                  ff_dim=16, fc_dim=8, dropout_p=0.0, patch_size=8)
    config.update(kwargs)
    return WaveformTransformer1D(**config)


def nonprefix_mask(length=65):
    """Mix fully masked patches, partial patches, and a partial final patch."""
    mask = torch.zeros(2, length, dtype=torch.bool)
    mask[0, :8] = True
    mask[0, 16:24] = True
    mask[0, 33::3] = True
    mask[1, 8:16] = True
    mask[1, 24:32] = True
    mask[1, ::5] = True
    mask[0, -1] = True
    mask[1, -1] = False
    return mask


def test_shape_and_convenience_input():
    model = small_model().eval()
    x = waveforms()
    with torch.no_grad():
        logits = model(x)
        assert logits.shape == (2, 4)
        assert torch.isfinite(logits).all()
        torch.testing.assert_close(logits, model(x.unsqueeze(1)))


@pytest.mark.parametrize('length,patch_size', [
    (32, 1), (33, 8), (65, 8), (256, 1), (4096, 16), (32, 64),
])
def test_supported_lengths_and_partial_patches(length, patch_size):
    model = small_model(input_length=length, patch_size=patch_size).eval()
    with torch.no_grad():
        output = model(waveforms(length)[:1])
    assert output.shape == (1, 4)
    assert torch.isfinite(output).all()


@pytest.mark.parametrize('channels,classes', [(2, 2), (8, 64)])
def test_multiple_channels_and_classes(channels, classes):
    model = small_model(in_channels=channels, num_classes=classes).eval()
    x = torch.randn(2, channels, 64)
    with torch.no_grad():
        assert model(x).shape == (2, classes)
    with pytest.raises(ValueError):
        model(waveforms())


def test_maximum_batch_size():
    model = small_model(input_length=32).eval()
    with torch.no_grad():
        assert model(torch.randn(64, 32)).shape == (64, 4)


def test_no_mask_and_all_false_mask_match():
    model = small_model(input_length=65).eval()
    x = waveforms(65)
    mask = torch.zeros_like(x, dtype=torch.bool)
    with torch.no_grad():
        expected = model(x)
        torch.testing.assert_close(model(x, padding_mask=mask), expected)
        torch.testing.assert_close(model(x.unsqueeze(1), padding_mask=mask), expected)


@pytest.mark.parametrize('channels', [1, 2])
def test_nonprefix_masked_values_do_not_affect_output(channels):
    model = small_model(input_length=65, in_channels=channels).eval()
    x = waveforms(65).unsqueeze(1).repeat(1, channels, 1)
    mask = nonprefix_mask()
    expanded_mask = mask.unsqueeze(1).expand_as(x)
    changed = x.clone()
    changed[expanded_mask] = 100 * torch.randn_like(changed[expanded_mask])
    zeroed = x.masked_fill(expanded_mask, 0)
    with torch.no_grad():
        expected = model(x, padding_mask=mask)
        torch.testing.assert_close(model(changed, padding_mask=mask), expected,
                                   rtol=0, atol=0)
        torch.testing.assert_close(model(zeroed, padding_mask=mask), expected,
                                   rtol=0, atol=0)
        if channels == 1:
            torch.testing.assert_close(model(x[:, 0], padding_mask=mask), expected)
    assert torch.isfinite(expected).all()


@pytest.mark.parametrize('sample_index', [0, 3, 32, 64])
def test_one_unmasked_sample_in_any_patch_is_valid(sample_index):
    model = small_model(input_length=65).eval()
    x = waveforms(65)
    mask = torch.ones(2, 65, dtype=torch.bool)
    mask[:, sample_index] = False
    with torch.no_grad():
        result = model(x, padding_mask=mask)
    assert result.shape == (2, 4)
    assert torch.isfinite(result).all()


def test_patch_attention_mask_and_valid_token_mean():
    """Check token-level masking and pooling independently of the final logits."""
    model = small_model(input_length=65, num_layers=2).eval()
    mask = nonprefix_mask()
    # One row's final partial patch is wholly masked; the other's is valid.
    padded_mask = nn.functional.pad(mask, (0, 7), value=True)
    expected_token_mask = padded_mask.reshape(2, 9, 8).all(dim=-1)
    attention_masks = []
    normalized_tokens = []
    pooled_inputs = []

    def capture_attention(module, args, kwargs):
        attention_masks.append(kwargs['key_padding_mask'].detach().clone())

    def capture_norm(module, args, output):
        normalized_tokens.append(output.detach().clone())

    def capture_pool(module, args):
        pooled_inputs.append(args[0].detach().clone())

    handles = [module.register_forward_pre_hook(capture_attention, with_kwargs=True)
               for module in model.modules() if isinstance(module, nn.MultiheadAttention)]
    handles.append(model.norm.register_forward_hook(capture_norm))
    handles.append(model.classifier.register_forward_pre_hook(capture_pool))
    try:
        with torch.no_grad():
            # Nonzero norm bias makes accidental inclusion of ignored tokens visible.
            model.norm.bias.fill_(0.37)
            model(waveforms(65), padding_mask=mask)
    finally:
        for handle in handles:
            handle.remove()
    assert len(attention_masks) == 2
    for observed in attention_masks:
        torch.testing.assert_close(observed, expected_token_mask)
    assert len(normalized_tokens) == len(pooled_inputs) == 1
    expected_pool = torch.stack([
        row[~ignored].mean(dim=0)
        for row, ignored in zip(normalized_tokens[0], expected_token_mask)
    ])
    torch.testing.assert_close(pooled_inputs[0], expected_pool)


def test_masked_input_gradients_are_zero():
    model = small_model(input_length=65, in_channels=2)
    x = torch.randn(2, 2, 65, requires_grad=True)
    mask = nonprefix_mask()
    loss = nn.functional.cross_entropy(model(x, padding_mask=mask), torch.tensor([0, 1]))
    loss.backward()
    assert x.grad is not None
    assert torch.isfinite(x.grad).all()
    expanded_mask = mask.unsqueeze(1).expand_as(x)
    assert torch.count_nonzero(x.grad[expanded_mask]) == 0
    assert x.grad[~expanded_mask].abs().sum() > 0


def test_gradient_and_optimizer_step():
    model = small_model()
    x = waveforms().requires_grad_()
    parameters = dict(model.named_parameters())
    before = {name: p.detach().clone() for name, p in parameters.items()}
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    loss = nn.functional.cross_entropy(model(x), torch.tensor([0, 1]))
    loss.backward()
    assert torch.isfinite(loss)
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert x.grad.abs().sum() > 0
    for parameter in parameters.values():
        if parameter.requires_grad:
            assert parameter.grad is not None
            assert torch.isfinite(parameter.grad).all()
    optimizer.step()
    assert any(not torch.equal(before[name], p) for name, p in parameters.items())


def test_single_sample_training_with_one_valid_token():
    model = small_model(input_length=33)
    x = waveforms(33)[:1].requires_grad_()
    mask = torch.ones(1, 33, dtype=torch.bool)
    mask[0, -1] = False
    output = model(x, padding_mask=mask)
    assert output.shape == (1, 4)
    output.square().sum().backward()
    assert torch.isfinite(output).all()
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert torch.count_nonzero(x.grad[mask]) == 0


def test_state_dict_roundtrip():
    model = small_model(input_length=65).eval()
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    buffer.seek(0)
    restored = small_model(input_length=65).eval()
    restored.load_state_dict(torch.load(buffer, weights_only=True, map_location='cpu'))
    x = waveforms(65)
    with torch.no_grad():
        for mask in (None, nonprefix_mask()):
            torch.testing.assert_close(model(x, padding_mask=mask),
                                       restored(x, padding_mask=mask), rtol=0, atol=0)


@pytest.mark.parametrize('masked', [False, True])
def test_probability_helper_eval_and_no_grad_semantics(masked):
    model = small_model(input_length=65, dropout_p=0.25).train()
    x = waveforms(65).requires_grad_()
    mask = nonprefix_mask() if masked else None
    first = model.predict_probabilities(x, padding_mask=mask)
    second = model.predict_probabilities(x, padding_mask=mask)
    assert first.shape == (2, 4)
    assert not first.requires_grad and first.grad_fn is None
    assert x.grad is None
    assert all(parameter.grad is None for parameter in model.parameters())
    assert not model.training
    assert all(not module.training for module in model.modules())
    assert torch.isfinite(first).all()
    assert ((first >= 0) & (first <= 1)).all()
    torch.testing.assert_close(first.sum(dim=1), torch.ones(2))
    torch.testing.assert_close(first, second, rtol=0, atol=0)
    with torch.no_grad():
        torch.testing.assert_close(first, model(x, padding_mask=mask).softmax(dim=-1))
    model.train()
    assert model.training


INT_BOUNDS = {
    'input_length': (32, 4096), 'num_classes': (2, 64), 'in_channels': (1, 8),
    'd_model': (4, 128), 'num_heads': (1, 8), 'num_layers': (1, 4),
    'ff_dim': (4, 512), 'fc_dim': (1, 256), 'patch_size': (1, 64),
}


@pytest.mark.parametrize('name,bounds', list(INT_BOUNDS.items()))
@pytest.mark.parametrize('invalid_kind', ['below', 'above', 'bool', 'float', 'none', 'string'])
def test_rejects_invalid_integer_configuration(name, bounds, invalid_kind):
    low, high = bounds
    values = dict(below=low - 1, above=high + 1, bool=True,
                  float=float(low), none=None, string=str(low))
    with pytest.raises(ValueError):
        small_model(**{name: values[invalid_kind]})


@pytest.mark.parametrize('config', [
    {'d_model': 5, 'num_heads': 1}, {'d_model': 10, 'num_heads': 4},
    {'d_model': 4, 'num_heads': 8}, {'num_heads': 3},
    {'input_length': 257, 'patch_size': 1},
    {'input_length': 4096, 'patch_size': 15},
    {'input_length': 513, 'patch_size': 2},
])
def test_rejects_incompatible_dimensions_and_excess_tokens(config):
    with pytest.raises(ValueError):
        small_model(**config)


@pytest.mark.parametrize('value', [True, False, -0.1, 1.0, float('nan'),
                                   float('inf'), -float('inf'), '0.1', None])
def test_rejects_invalid_dropout(value):
    with pytest.raises(ValueError):
        small_model(dropout_p=value)


@pytest.mark.parametrize('config', [
    {'d_model': 4, 'num_heads': 1, 'ff_dim': 4, 'fc_dim': 1},
    {'d_model': 128, 'num_heads': 8, 'ff_dim': 512, 'fc_dim': 256, 'num_layers': 4},
    {'d_model': 6, 'num_heads': 3}, {'dropout_p': 0}, {'dropout_p': 0.999},
])
def test_valid_configuration_boundaries(config):
    model = small_model(input_length=32, **config).eval()
    with torch.no_grad():
        result = model(waveforms(32)[:1])
    assert result.shape == (1, 4)
    assert torch.isfinite(result).all()


@pytest.mark.parametrize('shape', [(), (64,), (2, 1, 1, 64), (0, 64), (65, 64),
                                  (2, 2, 64), (2, 0, 64), (2, 63), (2, 65)])
def test_rejects_invalid_shape(shape):
    with pytest.raises(ValueError):
        small_model()(torch.zeros(shape))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('masked', [False, True])
def test_rejects_nonfinite_even_when_masked(value, masked):
    x = waveforms()
    x[0, 0] = value
    mask = torch.zeros(2, 64, dtype=torch.bool)
    mask[0, 0] = masked
    with pytest.raises(ValueError):
        small_model()(x, padding_mask=mask)


@pytest.mark.parametrize('dtype', [torch.int64, torch.bool, torch.complex64,
                                   torch.float16, torch.bfloat16, torch.float64])
def test_rejects_incompatible_dtype(dtype):
    with pytest.raises(ValueError):
        small_model()(torch.zeros(2, 64, dtype=dtype))


def test_matching_double_precision_is_supported():
    model = small_model().double().eval()
    with torch.no_grad():
        result = model(waveforms().double(), padding_mask=torch.zeros(2, 64, dtype=torch.bool))
    assert result.dtype == torch.float64
    assert torch.isfinite(result).all()


def test_rejects_non_tensor_and_sparse_input():
    with pytest.raises(TypeError):
        small_model()([[0.] * 64])
    with pytest.raises(ValueError):
        small_model()(waveforms().to_sparse())


def test_rejects_input_device_mismatch_without_accelerator():
    with pytest.raises(ValueError):
        small_model()(torch.empty(2, 64, device='meta'))


@pytest.mark.parametrize('shape', [(64,), (1, 64), (2, 63), (2, 65), (2, 1, 64)])
def test_rejects_invalid_mask_shape(shape):
    with pytest.raises(ValueError):
        small_model()(waveforms(), padding_mask=torch.zeros(shape, dtype=torch.bool))


@pytest.mark.parametrize('dtype', [torch.uint8, torch.int64, torch.float32, torch.complex64])
def test_rejects_nonboolean_mask(dtype):
    with pytest.raises(ValueError):
        small_model()(waveforms(), padding_mask=torch.zeros(2, 64, dtype=dtype))


def test_rejects_nontensor_sparse_and_wrong_device_mask():
    model = small_model()
    with pytest.raises(TypeError):
        model(waveforms(), padding_mask=[[False] * 64] * 2)
    with pytest.raises(ValueError):
        model(waveforms(), padding_mask=torch.zeros(2, 64, dtype=torch.bool).to_sparse())
    with pytest.raises(ValueError):
        model(waveforms(), padding_mask=torch.empty(2, 64, dtype=torch.bool, device='meta'))


@pytest.mark.parametrize('all_rows', [False, True])
def test_rejects_any_fully_masked_row(all_rows):
    mask = torch.zeros(2, 64, dtype=torch.bool)
    mask[1] = True
    if all_rows:
        mask[0] = True
    model = small_model()
    with pytest.raises(ValueError):
        model(waveforms(), padding_mask=mask)
    with pytest.raises(ValueError):
        model.predict_probabilities(waveforms(), padding_mask=mask)


def test_noncontiguous_dense_input_and_mask():
    model = small_model().eval()
    x = torch.randn(2, 128)[:, ::2]
    mask = torch.zeros(2, 128, dtype=torch.bool)[:, ::2]
    mask[:, 4::7] = True
    assert not x.is_contiguous() and not mask.is_contiguous()
    with torch.no_grad():
        torch.testing.assert_close(model(x, padding_mask=mask),
                                   model(x.contiguous(), padding_mask=mask.contiguous()))


def test_public_export_and_defaults():
    from pqc_bench.models import WaveformTransformer1D as Exported
    assert Exported is WaveformTransformer1D
    expected = dict(input_length=256, num_classes=4, in_channels=1, d_model=32,
                    num_heads=4, num_layers=2, ff_dim=64, fc_dim=64,
                    dropout_p=0.25, patch_size=8)
    signature = inspect.signature(Exported)
    for name, value in expected.items():
        assert signature.parameters[name].default == value
    model = Exported().eval()
    with torch.no_grad():
        result = model(waveforms(256))
    assert result.shape == (2, 4)
    assert torch.isfinite(result).all()
