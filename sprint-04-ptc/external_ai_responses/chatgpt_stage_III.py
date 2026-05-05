import pytest
import math

from your_module import TemperatureNode


def test_negative_alpha_ptc_reduces_heating():
    """PTC係数が負の場合（NTC的挙動）、温度が高いほど加熱が弱くなるべき"""
    node_low = TemperatureNode(T_env=0.0, T_initial=0.1, heating_rate=0.5, alpha_PTC=-0.5)
    node_high = TemperatureNode(T_env=0.0, T_initial=0.5, heating_rate=0.5, alpha_PTC=-0.5)

    node_low.update(input_value=1.0, dt=1.0)
    node_high.update(input_value=1.0, dt=1.0)

    delta_low = node_low.temperature - 0.1
    delta_high = node_high.temperature - 0.5

    assert delta_high < delta_low  # 符号反転チェック


def test_equilibrium_point_with_constant_input():
    """定常入力で平衡点に収束する（発散しない）"""
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.0,
        heating_rate=0.2,
        cooling_rate=0.2,
        alpha_PTC=0.0  # 線形化
    )

    for _ in range(200):
        node.update(input_value=1.0, dt=0.1)

    t1 = node.temperature

    for _ in range(200):
        node.update(input_value=1.0, dt=0.1)

    t2 = node.temperature

    assert t2 == pytest.approx(t1, rel=1e-3)  # ほぼ収束


def test_large_dt_stability_no_nan_or_inf():
    """dtが大きくてもNaN/infにならない"""
    node = TemperatureNode(T_env=0.0, T_initial=0.5)

    node.update(input_value=1.0, dt=100.0)

    assert not math.isnan(node.temperature)
    assert not math.isinf(node.temperature)


def test_cooling_does_not_cross_environment():
    """冷却のみの場合、環境温度を跨がない（オーバーシュート防止）"""
    node = TemperatureNode(T_env=0.0, T_initial=1.0, cooling_rate=1.0)

    for _ in range(10):
        node.update(input_value=0.0, dt=0.5)

    assert node.temperature >= 0.0


def test_reference_temperature_affects_ptc():
    """T_refを変えるとPTC応答が変わる"""
    node_ref_low = TemperatureNode(T_env=0.0, T_initial=0.5, T_ref=0.0, alpha_PTC=1.0)
    node_ref_high = TemperatureNode(T_env=0.0, T_initial=0.5, T_ref=1.0, alpha_PTC=1.0)

    node_ref_low.update(input_value=1.0, dt=1.0)
    node