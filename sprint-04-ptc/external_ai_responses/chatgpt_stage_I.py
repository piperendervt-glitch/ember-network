import pytest
import math

from your_module import TemperatureNode


def test_rhs_matches_model_single_step_linear_case():
    """
    alpha=0 のとき、RHSは線形になる：
    dT/dt = heating_rate * input - cooling_rate * (T - T_env)
    → 1ステップでの増分がこれと一致するか
    """
    node = TemperatureNode(
        heating_rate=0.4,
        cooling_rate=0.1,
        T_env=0.2,
        T_initial=0.5,
        alpha_PTC=0.0
    )

    T0 = node.temperature
    dt = 1e-4
    input_value = 0.7

    node.update(input_value=input_value, dt=dt)
    T1 = node.temperature

    rhs = 0.4 * input_value - 0.1 * (T0 - 0.2)
    expected = T0 + rhs * dt

    assert T1 == pytest.approx(expected, rel=1e-3)


def test_rhs_sign_error_detection_cooling_term():
    """
    冷却項の符号ミス（+ instead of -）を検出するテスト
    → input=0なら必ず温度は環境に近づく
    """
    node = TemperatureNode(T_env=0.0, T_initial=1.0, cooling_rate=0.2)

    node.update(input_value=0.0, dt=0.5)

    assert node.temperature < 1.0  # 上がったら符号バグ


def test_rhs_requires_temperature_dependent_heating():
    """
    R(T)依存を忘れるバグ検出
    → alpha>0なら高温の方が加熱が強い
    """
    node1 = TemperatureNode(T_env=0.0, T_initial=0.2, alpha_PTC=1.0, heating_rate=0.5)
    node2 = TemperatureNode(T_env=0.0, T_initial=0.8, alpha_PTC=1.0, heating_rate=0.5)

    node1.update(1.0, 0.1)
    node2.update(1.0, 0.1)

    d1 = node1.temperature - 0.2
    d2 = node2.temperature - 0.8

    assert d2 > d1  # R(T)が効いているか


def test_dt_splitting_consistency():
    """
    dt分割しても結果がほぼ同じ（一次精度チェック）
    """
    node_big = TemperatureNode(T_env=0.0, T_initial=0.3)
    node_small = TemperatureNode(T_env=0.0, T_initial=0.3)

    # 1回
    node_big.update(1.0, 1.0)

    # 分割
    for _ in range(100):
        node_small.update(1.0, 0.01)

    assert node_small.temperature == pytest.approx(node_big.temperature, rel=1e-2)


def test_alpha_near_runaway_threshold_growth():
    """
    αが大きい場合、加熱優勢で増加が加速する
    （thermal runaway傾向の検出）
    """
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.1,
        heating_rate=1.0,
        cooling_rate=0.05,
        alpha_PTC=5.0,  # 強いPTC
        clip_enabled=False
    )

    node.update(1.0, 0.1)
    d1 = node.temperature - 0.1

    node.update(1.0, 0.1)
    d2 = node.temperature - (0.1 + d1)

    assert d2 > d1  # 加速している


def test_alpha_negative_strong_damps_heating():
    """
    強い負αで加熱がほぼ抑制される（極端ケース）
    """
    node = TemperatureNode(
        T_env=0.0,
        T_initial=1.0,
        heating_rate=1.0,
        cooling_rate=0.0,
        alpha_PTC=-1.0
    )

    node.update(1.0, 0.1)

    # 加熱がほぼ止まる or 減少方向
    assert node.temperature <= 1.0 + 1e-6


def test_dt_zero_with_nonzero_input_and_alpha():
    """
    dt=0でも非線形項が誤って評価されて状態が変わるバグ検出
    """
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.5,
        alpha_PTC=2.0,
        heating_rate=1.0
    )

    before = node.temperature
    node.update(1.0, 0.0)

    assert node.temperature == pytest.approx(before)


def test_clip_interacts_with_runaway():
    """
    runaway状態でもクリップが効くか
    """
    node = TemperatureNode(
        T_env=0.0,
        T_initial=0.5,
        heating_rate=5.0,
        cooling_rate=0.0,
        alpha_PTC=5.0,
        T_max=1.0,
        clip_enabled=True
    )

    for _ in range(10):
        node.update(1.0, 0.1)

    assert node.temperature <= 1.0


def test_reference_temperature_shift_symmetry():
    """
    T_refのシフトがR(T)に正しく効いているか
    """
    node_a = TemperatureNode(T_env=0.0, T_initial=0.5, T_ref=0.0, alpha_PTC=1.0)
    node_b = TemperatureNode(T_env=0.0, T_initial=0.5, T_ref=1.0, alpha_PTC=1.0)

    node_a.update(1.0, 0.1)
    node_b.update(1.0, 0.1)

    assert node_a.temperature != pytest.approx(node_b.temperature)