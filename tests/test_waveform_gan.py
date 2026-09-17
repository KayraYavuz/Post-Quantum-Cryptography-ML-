"""CPU contract checks using only general synthetic waveforms and category IDs."""

import inspect
import io

import pytest
import torch

from pqc_bench.models.waveform_gan import (
    SyntheticWaveformDiscriminator,
    SyntheticWaveformGenerator,
)


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


def small_generator(**kwargs):
    config = dict(input_length=64, num_classes=4, in_channels=1,
                  latent_dim=8, hidden_dim=8, embedding_dim=4)
    config.update(kwargs)
    return SyntheticWaveformGenerator(**config)


def small_discriminator(**kwargs):
    config = dict(input_length=64, num_classes=4, in_channels=1,
                  hidden_dim=8, embedding_dim=4)
    config.update(kwargs)
    return SyntheticWaveformDiscriminator(**config)


def waveforms(length=64):
    t = torch.linspace(0, 1, length)
    return torch.stack((torch.sin(2 * torch.pi * t), torch.cos(4 * torch.pi * t)))


def model_and_input(kind):
    if kind == 'generator':
        return small_generator(), torch.randn(2, 8)
    return small_discriminator(), waveforms().unsqueeze(1)


KINDS = ['generator', 'discriminator']
COMMON_BOUNDS = {
    'input_length': (32, 4096), 'num_classes': (2, 64), 'in_channels': (1, 8),
    'hidden_dim': (4, 256), 'embedding_dim': (1, 64),
}


@pytest.mark.parametrize('length', [32, 33, 65, 256, 4096])
@pytest.mark.parametrize('batch', [1, 2])
def test_output_shapes_finiteness_and_generator_range(length, batch):
    generator = small_generator(input_length=length)
    discriminator = small_discriminator(input_length=length)
    labels = torch.arange(batch, dtype=torch.long)
    generated = generator(torch.randn(batch, 8), labels)
    assert generated.shape == (batch, 1, length)
    assert torch.isfinite(generated).all()
    assert ((generated >= -1) & (generated <= 1)).all()
    logits = discriminator(generated, labels)
    assert logits.shape == (batch, 1)
    assert torch.isfinite(logits).all()


@pytest.mark.parametrize('channels,classes', [(1, 2), (2, 4), (8, 64)])
def test_channels_and_boundary_category_ids(channels, classes):
    generator = small_generator(in_channels=channels, num_classes=classes).eval()
    discriminator = small_discriminator(in_channels=channels, num_classes=classes).eval()
    labels = torch.tensor([0, classes - 1])
    with torch.no_grad():
        generated = generator(torch.randn(2, 8), labels)
        assert generated.shape == (2, channels, 64)
        assert discriminator(generated, labels).shape == (2, 1)
    if channels != 1:
        with pytest.raises(ValueError):
            discriminator(waveforms(), labels)


def test_discriminator_returns_unbounded_raw_logits():
    model = small_discriminator().eval()
    final_linear = [module for module in model.modules()
                    if isinstance(module, torch.nn.Linear)][-1]
    with torch.no_grad():
        final_linear.weight.zero_()
        final_linear.bias.fill_(-2.0)
        negative = model(waveforms(), torch.tensor([0, 3]))
        torch.testing.assert_close(negative, torch.full((2, 1), -2.0), rtol=0, atol=0)
        final_linear.bias.fill_(2.0)
        positive = model(waveforms(), torch.tensor([0, 3]))
        torch.testing.assert_close(positive, torch.full((2, 1), 2.0), rtol=0, atol=0)


def test_discriminator_two_dimensional_convenience_input():
    model = small_discriminator().eval()
    labels = torch.tensor([0, 3])
    with torch.no_grad():
        torch.testing.assert_close(model(waveforms(), labels),
                                   model(waveforms().unsqueeze(1), labels), rtol=0, atol=0)


@pytest.mark.parametrize('kind', KINDS)
def test_maximum_batch_size(kind):
    labels = torch.arange(64) % 4
    if kind == 'generator':
        output = small_generator(input_length=32)(torch.randn(64, 8), labels)
        assert output.shape == (64, 1, 32)
    else:
        output = small_discriminator(input_length=32)(torch.randn(64, 1, 32), labels)
        assert output.shape == (64, 1)
    assert torch.isfinite(output).all()


def assert_connected_gradients(model):
    for name, parameter in model.named_parameters():
        assert parameter.grad is not None, name
        assert torch.isfinite(parameter.grad).all(), name
    embedding_grad = model.label_embedding.weight.grad
    assert embedding_grad is not None
    assert embedding_grad.abs().sum() > 0
    assert embedding_grad[0].abs().sum() > 0
    assert embedding_grad[3].abs().sum() > 0


@pytest.mark.parametrize('kind', KINDS)
def test_backward_connects_inputs_and_all_parameters(kind):
    model, inputs = model_and_input(kind)
    inputs.requires_grad_()
    output = model(inputs, torch.tensor([0, 3]))
    loss = output.square().mean()
    loss.backward()
    assert torch.isfinite(loss)
    assert inputs.grad is not None and torch.isfinite(inputs.grad).all()
    assert inputs.grad.abs().sum() > 0
    assert_connected_gradients(model)


def test_discriminator_gradients_flow_through_generator():
    generator = small_generator()
    discriminator = small_discriminator()
    noise = torch.randn(2, 8, requires_grad=True)
    labels = torch.tensor([0, 3])
    generated = generator(noise, labels)
    generated.retain_grad()
    discriminator(generated, labels).square().mean().backward()
    assert generated.grad is not None and torch.isfinite(generated.grad).all()
    assert generated.grad.abs().sum() > 0
    assert noise.grad is not None and torch.isfinite(noise.grad).all()
    assert noise.grad.abs().sum() > 0
    assert_connected_gradients(generator)
    assert_connected_gradients(discriminator)


@pytest.mark.parametrize('kind', KINDS)
def test_labels_have_causal_influence_with_identical_inputs(kind):
    torch.manual_seed(101)
    model, inputs = model_and_input(kind)
    model.eval()
    inputs = inputs[:1].expand_as(inputs).clone()
    with torch.no_grad():
        same_labels = model(inputs, torch.tensor([0, 0]))
        different_labels = model(inputs, torch.tensor([0, 3]))
    # Batched CPU kernels may round identical rows differently.
    torch.testing.assert_close(same_labels[0], same_labels[1])
    torch.testing.assert_close(same_labels[0], different_labels[0], rtol=0, atol=0)
    # Compare the same row between calls to distinguish conditioning from rounding.
    assert not torch.allclose(same_labels[1], different_labels[1])


@pytest.mark.parametrize('kind', KINDS)
def test_state_dict_weights_only_roundtrip_is_exact(kind):
    model, inputs = model_and_input(kind)
    model.eval()
    restored, _ = model_and_input(kind)
    restored.eval()
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    buffer.seek(0)
    restored.load_state_dict(torch.load(buffer, weights_only=True, map_location='cpu'))
    labels = torch.tensor([0, 3])
    with torch.no_grad():
        torch.testing.assert_close(model(inputs, labels), restored(inputs, labels), rtol=0, atol=0)


@pytest.mark.parametrize('kind', KINDS)
def test_matching_float64_supports_forward_and_backward(kind):
    model, inputs = model_and_input(kind)
    model.double()
    inputs = inputs.double().requires_grad_()
    output = model(inputs, torch.tensor([0, 3]))
    assert output.dtype == torch.float64
    assert torch.isfinite(output).all()
    output.square().mean().backward()
    assert inputs.grad is not None and torch.isfinite(inputs.grad).all()
    assert_connected_gradients(model)


@pytest.mark.parametrize('kind', KINDS)
def test_helpers_disable_gradients_and_leave_entire_model_in_eval(kind):
    model, inputs = model_and_input(kind)
    model.train()
    inputs.requires_grad_()
    labels = torch.tensor([0, 3])
    helper = model.generate if kind == 'generator' else model.predict_probabilities
    first = helper(inputs, labels)
    second = helper(inputs, labels)
    assert not first.requires_grad and first.grad_fn is None
    assert inputs.grad is None
    assert all(parameter.grad is None for parameter in model.parameters())
    assert all(not module.training for module in model.modules())
    torch.testing.assert_close(first, second, rtol=0, atol=0)
    with torch.no_grad():
        expected = model(inputs, labels)
        if kind == 'discriminator':
            expected = expected.sigmoid()
            assert ((first >= 0) & (first <= 1)).all()
        torch.testing.assert_close(first, expected, rtol=0, atol=0)
    model.train()
    assert model.training


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('name,bounds', list(COMMON_BOUNDS.items()))
@pytest.mark.parametrize('invalid_kind', ['below', 'above', 'bool', 'float', 'none', 'string'])
def test_rejects_invalid_common_configuration(kind, name, bounds, invalid_kind):
    low, high = bounds
    values = dict(below=low - 1, above=high + 1, bool=True,
                  float=float(low), none=None, string=str(low))
    factory = small_generator if kind == 'generator' else small_discriminator
    with pytest.raises(ValueError):
        factory(**{name: values[invalid_kind]})


@pytest.mark.parametrize('value', [0, 257, True, False, 8.0, None, '8'])
def test_rejects_invalid_latent_dimension(value):
    with pytest.raises(ValueError):
        small_generator(latent_dim=value)


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('name,bounds', list(COMMON_BOUNDS.items()))
@pytest.mark.parametrize('boundary', [0, 1])
def test_accepts_integer_configuration_boundaries(kind, name, bounds, boundary):
    config = {'input_length': 32, name: bounds[boundary]}
    length = config['input_length']
    channels = config.get('in_channels', 1)
    factory = small_generator if kind == 'generator' else small_discriminator
    model = factory(**config).eval()
    inputs = torch.randn(1, 8) if kind == 'generator' else torch.randn(1, channels, length)
    with torch.no_grad():
        output = model(inputs, torch.tensor([0]))
    expected_shape = (1, channels, length) if kind == 'generator' else (1, 1)
    assert output.shape == expected_shape
    assert torch.isfinite(output).all()


@pytest.mark.parametrize('latent_dim', [1, 256])
def test_accepts_latent_dimension_boundaries(latent_dim):
    with torch.no_grad():
        generator = small_generator(latent_dim=latent_dim)
        output = generator(torch.randn(1, latent_dim), torch.tensor([0]))
    assert output.shape == (1, 1, 64)


@pytest.mark.parametrize('shape', [(), (8,), (2, 1, 8), (0, 8), (65, 8), (2, 7), (2, 9)])
def test_rejects_invalid_noise_shapes(shape):
    batch = shape[0] if shape else 2
    with pytest.raises(ValueError):
        small_generator()(torch.zeros(shape), torch.zeros(batch, dtype=torch.long))


@pytest.mark.parametrize('shape', [(), (64,), (2, 1, 1, 64), (0, 1, 64), (65, 1, 64),
                                  (2, 0, 64), (2, 2, 64), (2, 1, 63), (2, 1, 65),
                                  (0, 64), (65, 64), (2, 63), (2, 65)])
def test_rejects_invalid_waveform_shapes(shape):
    batch = shape[0] if shape else 2
    with pytest.raises(ValueError):
        small_discriminator()(torch.zeros(shape), torch.zeros(batch, dtype=torch.long))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('dtype', [torch.int64, torch.bool, torch.complex64,
                                   torch.float16, torch.bfloat16, torch.float64])
def test_rejects_nonfloating_or_mismatched_input_dtype(kind, dtype):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs.to(dtype), torch.tensor([0, 3]))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_rejects_nonfinite_inputs(kind, value):
    model, inputs = model_and_input(kind)
    inputs.reshape(-1)[0] = value
    with pytest.raises(ValueError):
        model(inputs, torch.tensor([0, 3]))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('value', [None, 1, [0.0, 1.0]])
def test_rejects_nontensor_inputs(kind, value):
    model, _ = model_and_input(kind)
    with pytest.raises(TypeError):
        model(value, torch.tensor([0, 3]))


@pytest.mark.parametrize('kind', KINDS)
def test_rejects_sparse_input_layout(kind):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs.to_sparse(), torch.tensor([0, 3]))


@pytest.mark.parametrize('kind', KINDS)
def test_rejects_input_device_mismatch_without_accelerator(kind):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(torch.empty_like(inputs, device='meta'), torch.tensor([0, 3]))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('shape', [(), (0,), (1,), (3,), (2, 1), (1, 2)])
def test_rejects_malformed_label_shape(kind, shape):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs, torch.zeros(shape, dtype=torch.long))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('dtype', [torch.bool, torch.uint8, torch.int32, torch.float32,
                                   torch.float64, torch.complex64])
def test_rejects_label_dtype_other_than_long(kind, dtype):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs, torch.tensor([0, 1], dtype=dtype))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('labels', [[-1, 0], [0, 4], [4, 0]])
def test_rejects_out_of_range_labels(kind, labels):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs, torch.tensor(labels))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('labels', [None, 0, [0, 1]])
def test_rejects_nontensor_labels(kind, labels):
    model, inputs = model_and_input(kind)
    with pytest.raises(TypeError):
        model(inputs, labels)


@pytest.mark.parametrize('kind', KINDS)
def test_rejects_sparse_and_wrong_device_labels(kind):
    model, inputs = model_and_input(kind)
    with pytest.raises(ValueError):
        model(inputs, torch.tensor([0, 3]).to_sparse())
    with pytest.raises(ValueError):
        model(inputs, torch.empty(2, dtype=torch.long, device='meta'))


@pytest.mark.parametrize('kind', KINDS)
def test_noncontiguous_dense_inputs_and_labels_are_supported(kind):
    model, inputs = model_and_input(kind)
    model.eval()
    inputs = torch.stack((inputs, inputs), dim=-1)[..., 0]
    labels = torch.tensor([0, 1, 3, 2])[::2]
    assert not inputs.is_contiguous() and not labels.is_contiguous()
    with torch.no_grad():
        torch.testing.assert_close(model(inputs, labels),
                                   model(inputs.contiguous(), labels.contiguous()),
                                   rtol=0, atol=0)


@pytest.mark.parametrize('kind', KINDS)
def test_helpers_preserve_input_validation(kind):
    model, inputs = model_and_input(kind)
    helper = model.generate if kind == 'generator' else model.predict_probabilities
    with pytest.raises(TypeError):
        helper(None, torch.tensor([0, 3]))
    with pytest.raises(TypeError):
        helper(inputs, [0, 3])
    with pytest.raises(ValueError):
        helper(inputs, torch.tensor([0, 4]))
    with pytest.raises(ValueError):
        helper(torch.full_like(inputs, float('nan')), torch.tensor([0, 3]))


@pytest.mark.parametrize('model_class', [
    SyntheticWaveformGenerator, SyntheticWaveformDiscriminator,
])
def test_default_signature_and_forward(model_class):
    expected = dict(input_length=256, num_classes=4, in_channels=1,
                    hidden_dim=64, embedding_dim=16)
    if model_class is SyntheticWaveformGenerator:
        expected['latent_dim'] = 32
    signature = inspect.signature(model_class)
    for name, value in expected.items():
        assert signature.parameters[name].default == value
    model = model_class().eval()
    inputs = torch.randn(2, 32) if model_class is SyntheticWaveformGenerator else waveforms(256)
    with torch.no_grad():
        output = model(inputs, torch.tensor([0, 3]))
    expected_shape = (2, 1, 256) if model_class is SyntheticWaveformGenerator else (2, 1)
    assert output.shape == expected_shape
    assert torch.isfinite(output).all()
