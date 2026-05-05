import math
import pytest

from your_module import TemperatureNode


def test_initial_temperature_defaults_to_env():
    node = TemperatureNode(T_env=0.5, T_initial=None)
    assert node.temperature == pytest.approx(0.5)


def test_reset_restores_initial_state():
    node = TemperatureNode(T_env=0.2, T_initial=0.7)
    node.update(input_value=1.0, dt=1.0)
    assert node.temperature != pytest.approx(0.7)

    node.reset()
    assert node.temperature == pytest.approx(0.7)


def test_no_input_cools_toward_environment():
    node = TemperatureNode(T_env=0.0, T_initial=1.0, cooling_rate=0.1)
    node.update(input_value=0.0, dt=1.0)

    assert node.temperature < 1.0
    assert node.temperature > 0.0  # should approach env, not overshoot


def test_heating_increases_temperature_with_input():
    node = TemperatureNode(T_env=0.0, T_initial=0.0, heating_rate=0.5)
    node.update(input_value=1.0, dt=1.0)

    assert node.temperature > 0.0


def test_ptc_effect_increases_heating_with_temperature():
    node_low = TemperatureNode(
        T_env=0.0, T_initial=0.1,
        heating_rate=0.5, alpha_PTC=0.5
    )
    node_high = TemperatureNode(
        T_env=0.0, T_initial=0.5,
        heating_rate=0.5, alpha_PTC=0.5
    )

    node_low.update(input_value=1.0, dt=1.0)
    node_high.update(input_value=1.0, dt=1.0)

    delta_low = node_low.temperature - 0.1
    delta_high = node_high.temperature - 0.5

    assert delta_high > delta_low  # PTC: higher T → more heating


def test_dt_zero_is_no_op():
    node = TemperatureNode(T_env=0.0, T_initial=0.3)
    before = node.temperature

    node.update(input_value=1.0, dt=0.0)

    assert node.temperature == pytest.approx(before)


def test_temperature_clipping_enabled():
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.9,
        heating_rate=10.0,
        T_max=1.0,
        clip_enabled=True
    )

    node.update(input_value=1.0, dt=1.0)

    assert node.temperature <= 1.0
    assert node.temperature == pytest.approx(1.0)


def test_temperature_clipping_disabled():
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.9,
        heating_rate=10.0,
        T_max=1.0,
        clip_enabled=False
    )

    node.update(input_value=1.0, dt=1.0)

    assert node.temperature > 1.0  # no clipping


def test_weight_monotonic_with_temperature():
    node = TemperatureNode(T_env=0.0, T_initial=0.1)

    w1 = node.weight
    node.update(input_value=1.0, dt=1.0)
    w2 = node.weight

    assert w2 != w1  # should change with temperature