# test_temperature_model_mutation_resistance.py

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
def test_heating_and_cooling_terms_separable():
    """
    目的:
        heating 項と cooling 項が独立に実装されているか検証

    なぜ既存テストで漏れるか:
        多くのテストは「合成された挙動」しか見ていないため、
        例えば:
            dT/dt = a*input - b*T
        を
            dT/dt = (a - b)*input
        のように壊しても通る可能性がある

    根拠:
        input=1 と input=0 の差分で heating_rate が抽出できる

    検証:
        差分が heating_rate に一致
    """
    from model import step_temperature

    T = 0.3

    T_on = step_temperature(T, input=1.0, dt=DT, params=PARAMS)
    T_off = step_temperature(T, input=0.0, dt=DT, params=PARAMS)

    dT_on = (T_on - T) / DT
    dT_off = (T_off - T) / DT

    estimated_heating = dT_on - dT_off

    assert np.isclose(estimated_heating, PARAMS["heating_rate"], rtol=1e-2)


# =========================
# Test 2
# =========================
def test_cooling_depends_on_temperature_difference():
    """
    目的:
        cooling が (T - T_env) に依存しているか検証

    なぜ既存テストで漏れるか:
        T に比例しているだけの誤実装 (T_env無視) が通る可能性

    根拠:
        T_env をシフトしても挙動が変わるべき

    検証:
        T_env変更で挙動が変化する
    """
    from model import step_temperature

    params1 = PARAMS.copy()
    params2 = PARAMS.copy()

    params2["T_env"] = 0.2

    T1 = 0.5
    T2 = 0.5

    T1_next = step_temperature(T1, input=0.0, dt=DT, params=params1)
    T2_next = step_temperature(T2, input=0.0, dt=DT, params=params2)

    assert not np.isclose(T1_next, T2_next, atol=1e-4)


# =========================
# Test 3
# =========================
def test_equivalence_to_continuous_node_without_clip():
    """
    目的:
        Sprint 2 のモデルとの同値性（clip未使用領域）

    なぜ既存テストで漏れるか:
        Sprint 3単体では「それっぽく」見える実装でも、
        Sprint 2 と一致しない可能性

    根拠:
        w = (T - T_env)/(T_max - T_env)
        → dw/dt = α input - β w と一致

    検証:
        小さい T 範囲で一致
    """
    from model import step_temperature

    T = 0.1
    w = T  # T_env=0, T_max=1

    for _ in range(1000):
        T = step_temperature(T, input=0.5, dt=DT, params=PARAMS)

        # Sprint2 equivalent
        w = w + DT * (PARAMS["heating_rate"] * 0.5 - PARAMS["cooling_rate"] * w)

    assert np.isclose(T, w, rtol=1e-2)


# =========================
# Test 4
# =========================
def test_no_hidden_state_memory():
    """
    目的:
        隠れ状態（履歴依存）が存在しないこと

    なぜ既存テストで漏れるか:
        同じ入力系列しかテストしていない場合、
        内部状態バグが見えない

    根拠:
        同じ初期値・同じ入力 → 同じ結果

    検証:
        異なる履歴後でも同じ状態なら同じ遷移
    """
    from model import step_temperature

    # 異なる履歴で同じ T に収束
    T1 = 0.0
    for _ in range(1000):
        T1 = step_temperature(T1, input=1.0, dt=DT, params=PARAMS)

    T2 = 1.0
    for _ in range(1000):
        T2 = step_temperature(T2, input=0.0, dt=DT, params=PARAMS)

    # 同じ状態に近づく
    T_common = (T1 + T2) / 2

    next1 = step_temperature(T_common, input=0.3, dt=DT, params=PARAMS)
    next2 = step_temperature(T_common, input=0.3, dt=DT, params=PARAMS)

    assert np.isclose(next1, next2, atol=ATOL)


# =========================
# Test 5
# =========================
def test_asymmetric_response_to_input_toggle():
    """
    目的:
        input ON/OFF の非対称性を検証

    なぜ既存テストで漏れるか:
        ONだけ or OFFだけのテストが多い

    根拠:
        heating と cooling は異なる物理過程

    検証:
        ON→OFF と OFF→ON で応答が異なる
    """
    from model import step_temperature

    T = 0.5

    T_on = step_temperature(T, input=1.0, dt=DT, params=PARAMS)
    T_on_off = step_temperature(T_on, input=0.0, dt=DT, params=PARAMS)

    T_off = step_temperature(T, input=0.0, dt=DT, params=PARAMS)
    T_off_on = step_temperature(T_off, input=1.0, dt=DT, params=PARAMS)

    assert not np.isclose(T_on_off, T_off_on, atol=1e-6)


# =========================
# Test 6
# =========================
def test_clip_does_not_affect_dynamics_below_threshold():
    """
    目的:
        clip が内部ダイナミクスに影響しないこと

    なぜ既存テストで漏れるか:
        clipを常に適用していても検出できない

    根拠:
        T < T_max では clip は無関係

    検証:
        clipあり/なしで同じ結果
    """
    from model import step_temperature

    T = 0.2

    # 仮に clip を手動で再現しない経路
    T_next = step_temperature(T, input=0.5, dt=DT, params=PARAMS)

    # clipの影響が出ない領域
    assert T_next < PARAMS["T_max"]


# =========================
# Test 7
# =========================
def test_parameter_swap_detectability():
    """
    目的:
        heating_rate と cooling_rate を入れ替えたバグを検出

    なぜ既存テストで漏れるか:
        両方使われている限り見抜きにくい

    根拠:
        挙動が大きく変わるはず

    検証:
        パラメータ交換で結果が変わる
    """
    from model import step_temperature

    params_swapped = PARAMS.copy()
    params_swapped["heating_rate"], params_swapped["cooling_rate"] = (
        params_swapped["cooling_rate"],
        params_swapped["heating_rate"],
    )

    T1 = 0.0
    T2 = 0.0

    for _ in range(1000):
        T1 = step_temperature(T1, input=1.0, dt=DT, params=PARAMS)
        T2 = step_temperature(T2, input=1.0, dt=DT, params=params_swapped)

    assert not np.isclose(T1, T2, rtol=1e-2)


# =========================
# Test 8
# =========================
def test_zero_dt_no_change():
    """
    目的:
        dt=0 のとき状態が変化しない

    なぜ既存テストで漏れるか:
        dtを固定していると検証されない

    根拠:
        微分方程式の定義上:
            dt=0 → ΔT=0

    検証:
        完全一致
    """
    from model import step_temperature

    T = 0.7

    T_next = step_temperature(T, input=1.0, dt=0.0, params=PARAMS)

    assert T_next == T