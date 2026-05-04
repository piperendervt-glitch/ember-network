# test_temperature_model.py

import numpy as np
import pytest

# =========================
# 想定インターフェース
# =========================
# 実装側で提供されることを想定
# def step_temperature(T, input, dt, params): ...
#
# params = {
#     "heating_rate": 0.1,
#     "cooling_rate": 0.05,
#     "T_env": 0.0,
#     "T_max": 1.0,
# }

# =========================
# 共通設定
# =========================

PARAMS = {
    "heating_rate": 0.1,
    "cooling_rate": 0.05,
    "T_env": 0.0,
    "T_max": 1.0,
}

DT = 0.01
ATOL = 1e-6
RTOL = 1e-5


# =========================
# Test 1
# =========================
def test_equilibrium_no_input():
    """
    目的:
        input=0 のとき T は T_env に収束する

    根拠:
        微分方程式:
            dT/dt = -cooling_rate * (T - T_env)
        → 指数減衰して T_env に収束

    検証:
        長時間後に T ≈ T_env
    """
    from model import step_temperature

    T = 1.0  # 初期温度
    for _ in range(10000):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    assert np.isclose(T, PARAMS["T_env"], atol=1e-3)


# =========================
# Test 2
# =========================
def test_heating_monotonic_increase():
    """
    目的:
        input=1 のとき、T < 定常値なら単調増加

    根拠:
        定常解:
            T* = T_env + heating_rate / cooling_rate

        今回:
            = 0 + 0.1 / 0.05 = 2.0 → clipで1.0

        よって T < 1.0 の範囲では dT/dt > 0

    検証:
        初期 T=0 から単調増加
    """
    from model import step_temperature

    T = 0.0
    prev_T = T

    for _ in range(1000):
        T = step_temperature(T, input=1.0, dt=DT, params=PARAMS)
        assert T >= prev_T - ATOL
        prev_T = T


# =========================
# Test 3
# =========================
def test_upper_bound_clipping():
    """
    目的:
        T は T_max を超えない

    根拠:
        物理境界条件: T <= T_max

    検証:
        長時間 input=1 でも T <= T_max
    """
    from model import step_temperature

    T = 0.0
    for _ in range(10000):
        T = step_temperature(T, input=1.0, dt=DT, params=PARAMS)

    assert T <= PARAMS["T_max"] + ATOL


# =========================
# Test 4
# =========================
def test_lower_bound_no_negative_temperature():
    """
    目的:
        T は T_env 未満に落ちない

    根拠:
        dT/dt = -k(T - T_env)
        → T < T_env のとき正方向に戻る

    検証:
        負初期値でも T_env に戻る
    """
    from model import step_temperature

    T = -1.0  # 非物理状態
    for _ in range(1000):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    assert T >= PARAMS["T_env"] - ATOL


# =========================
# Test 5
# =========================
def test_analytical_solution_no_input():
    """
    目的:
        input=0 の解析解と一致

    根拠:
        T(t) = T_env + (T0 - T_env) * exp(-k t)

    検証:
        数値解と解析解の一致
    """
    from model import step_temperature

    T0 = 1.0
    T = T0
    k = PARAMS["cooling_rate"]

    t_total = 1.0
    steps = int(t_total / DT)

    for _ in range(steps):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    T_expected = PARAMS["T_env"] + (T0 - PARAMS["T_env"]) * np.exp(-k * t_total)

    assert np.isclose(T, T_expected, rtol=RTOL, atol=ATOL)


# =========================
# Test 6
# =========================
def test_response_to_impulse():
    """
    目的:
        短い入力パルスで温度が一時的に上昇し、その後減衰

    根拠:
        線形系 + 入力 → インパルス応答

    検証:
        上昇→減衰の形状
    """
    from model import step_temperature

    T = 0.0

    # パルス入力
    for _ in range(10):
        T = step_temperature(T, input=1.0, dt=DT, params=PARAMS)

    peak = T

    # その後 cooling
    for _ in range(1000):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    assert peak > PARAMS["T_env"]
    assert T < peak


# =========================
# Test 7
# =========================
def test_numerical_stability_large_dt():
    """
    目的:
        大きな dt でも発散しない

    根拠:
        不安定な実装 (Euler暴走など) を検出

    検証:
        T が NaN / inf にならない
    """
    from model import step_temperature

    T = 0.5
    large_dt = 1.0

    for _ in range(100):
        T = step_temperature(T, input=1.0, dt=large_dt, params=PARAMS)
        assert np.isfinite(T)


# =========================
# Test 8
# =========================
def test_weight_mapping_consistency():
    """
    目的:
        w = (T - T_env) / (T_max - T_env) の整合性

    根拠:
        定義式そのもの（派生量の正しさ）

    検証:
        境界で w=0,1
    """
    T_env = PARAMS["T_env"]
    T_max = PARAMS["T_max"]

    def compute_w(T):
        return (T - T_env) / (T_max - T_env)

    assert np.isclose(compute_w(T_env), 0.0, atol=ATOL)
    assert np.isclose(compute_w(T_max), 1.0, atol=ATOL)


# =========================
# Test 9
# =========================
def test_second_law_directionality():
    """
    目的:
        熱力学的方向性の確認

    根拠:
        input=0 のとき
            T > T_env → 減少
            T < T_env → 増加

    検証:
        符号が正しい
    """
    from model import step_temperature

    # 高温 → 下降
    T_high = 1.0
    T_next = step_temperature(T_high, input=0.0, dt=DT, params=PARAMS)
    assert T_next < T_high

    # 低温 → 上昇
    T_low = -0.5
    T_next = step_temperature(T_low, input=0.0, dt=DT, params=PARAMS)
    assert T_next > T_low