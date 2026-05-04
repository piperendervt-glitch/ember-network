# test_temperature_model_additional.py

import numpy as np
import pytest

# 想定:
# from model import step_temperature

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
def test_time_constant_consistency():
    """
    目的:
        冷却過程の時間定数が理論値と一致するか

    根拠:
        input=0 のとき:
            T(t) = T_env + (T0 - T_env) * exp(-k t)

        → 時間定数 τ = 1 / cooling_rate

        t = τ のとき:
            (T - T_env) / (T0 - T_env) = exp(-1)

    検証:
        数値解が exp(-1) に一致するか
    """
    from model import step_temperature

    T0 = 1.0
    T = T0
    k = PARAMS["cooling_rate"]

    tau = 1.0 / k
    steps = int(tau / DT)

    for _ in range(steps):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    ratio = (T - PARAMS["T_env"]) / (T0 - PARAMS["T_env"])
    assert np.isclose(ratio, np.exp(-1), rtol=RTOL)


# =========================
# Test 2
# =========================
def test_linearity_superposition():
    """
    目的:
        線形系としての重ね合わせ性

    根拠:
        このODEは線形なので:
            T(input=A+B) = T(A) + T(B) - T_env

    検証:
        2つの入力の和が成立するか
    """
    from model import step_temperature

    T_a = 0.0
    T_b = 0.0
    T_ab = 0.0

    for _ in range(1000):
        T_a = step_temperature(T_a, input=0.3, dt=DT, params=PARAMS)
        T_b = step_temperature(T_b, input=0.7, dt=DT, params=PARAMS)
        T_ab = step_temperature(T_ab, input=1.0, dt=DT, params=PARAMS)

    combined = T_a + T_b - PARAMS["T_env"]

    assert np.isclose(T_ab, combined, rtol=1e-3)


# =========================
# Test 3
# =========================
def test_dt_invariance_small_steps():
    """
    目的:
        dt を変えても解が収束する（時間離散化の健全性）

    根拠:
        同じ物理時間なら結果は一致するべき

    検証:
        dt=0.01 と dt=0.001 の結果比較
    """
    from model import step_temperature

    T1 = 0.0
    T2 = 0.0

    total_time = 1.0

    dt1 = 0.01
    dt2 = 0.001

    steps1 = int(total_time / dt1)
    steps2 = int(total_time / dt2)

    for _ in range(steps1):
        T1 = step_temperature(T1, input=1.0, dt=dt1, params=PARAMS)

    for _ in range(steps2):
        T2 = step_temperature(T2, input=1.0, dt=dt2, params=PARAMS)

    assert np.isclose(T1, T2, rtol=1e-2)


# =========================
# Test 4
# =========================
def test_no_heating_when_input_zero():
    """
    目的:
        input=0 のとき heating 項が完全に消えているか

    根拠:
        dT/dt = -cooling_rate * (T - T_env)
        → input が漏れているバグを検出

    検証:
        input=0 で T_env から上昇しない
    """
    from model import step_temperature

    T = PARAMS["T_env"]

    for _ in range(1000):
        T = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    assert np.isclose(T, PARAMS["T_env"], atol=ATOL)


# =========================
# Test 5
# =========================
def test_derivative_sign_near_equilibrium():
    """
    目的:
        平衡点近傍での微分符号の正しさ

    根拠:
        T > T_eq → dT/dt < 0
        T < T_eq → dT/dt > 0

    （clipなし理論値で検証）

    検証:
        微小ずれに対して復元方向に動くか
    """
    from model import step_temperature

    k = PARAMS["cooling_rate"]
    h = PARAMS["heating_rate"]

    T_eq = PARAMS["T_env"] + h / k

    eps = 1e-3

    T_high = T_eq + eps
    T_low = T_eq - eps

    T_high_next = step_temperature(T_high, input=1.0, dt=DT, params=PARAMS)
    T_low_next = step_temperature(T_low, input=1.0, dt=DT, params=PARAMS)

    assert T_high_next < T_high
    assert T_low_next > T_low


# =========================
# Test 6
# =========================
def test_primary_secondary_no_feedback():
    """
    目的:
        w が T にフィードバックしていないこと

    根拠:
        モデル定義:
            T が primary
            w は派生量

        → w の計算が T を変えてはいけない

    検証:
        同じ T 更新で w 計算の有無が結果に影響しない
    """
    from model import step_temperature

    def compute_w(T):
        return (T - PARAMS["T_env"]) / (PARAMS["T_max"] - PARAMS["T_env"])

    T1 = 0.0
    T2 = 0.0

    for _ in range(1000):
        T1 = step_temperature(T1, input=1.0, dt=DT, params=PARAMS)

        # wを計算する経路
        w = compute_w(T2)
        T2 = step_temperature(T2, input=1.0, dt=DT, params=PARAMS)

    assert np.isclose(T1, T2, rtol=RTOL)


# =========================
# Test 7
# =========================
def test_floating_point_drift_near_bounds():
    """
    目的:
        境界付近での浮動小数点ドリフト検出

    根拠:
        clip 周辺では誤差が蓄積しやすい

    検証:
        T_max 付近で振動・発散しない
    """
    from model import step_temperature

    T = 0.999999

    for _ in range(10000):
        T = step_temperature(T, input=1.0, dt=DT, params=PARAMS)
        assert T <= PARAMS["T_max"] + 1e-9
        assert T >= PARAMS["T_env"] - 1e-9


# =========================
# Test 8
# =========================
def test_response_scaling_with_heating_rate():
    """
    目的:
        heating_rate に比例して応答が変わるか

    根拠:
        定常解:
            T_eq ∝ heating_rate

    検証:
        heating_rate を倍にすると T も増加方向に変化
    """
    from model import step_temperature

    params1 = PARAMS.copy()
    params2 = PARAMS.copy()

    params2["heating_rate"] *= 2.0

    T1 = 0.0
    T2 = 0.0

    for _ in range(2000):
        T1 = step_temperature(T1, input=1.0, dt=DT, params=params1)
        T2 = step_temperature(T2, input=1.0, dt=DT, params=params2)

    assert T2 >= T1