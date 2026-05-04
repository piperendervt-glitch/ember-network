"""
test_external_ai: KR-S5 (外部 AI 3 段階による独立検証)

Robosheep が Grok と ChatGPT に独立で 3 段階で相談したテストケース
(計 6 ファイル、46 テスト) のうち、Type 5 (新規かつ binary input 互換、
interface adapt 可能) として採用した 18 件を統合 (Rule 10.5)。

採用方針 (Step D Halt-and-Confirm で確定した Option E):
- Type 1 (fractional input、10 件): Sprint 3 OKR Out of Scope 項目 17
  違反のため skip。PRL-010 として Sprint 4 Planning で再評価。
- Type 2 (Interface 矛盾): adapt して統合 (各テストにコメント明示)
- Type 3 (負の初期 T、2 件): skip。PRL-011 として Sprint 4 Planning。
- Type 4 (重複、約 11 件): 除外
- Type 5 (採用、18 件): adapt して統合

各テストの出典は `# Source: <AI> stage <N>, Test <#>` 形式。
adapter 適用箇所は `# Adapted: ...` で明示。
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from temperature_node import TemperatureNode  # noqa: E402


T_ENV = 0.0
T_MAX = 1.0
HEATING_RATE = 0.1
COOLING_RATE = 0.05


def _heat_until(node, target_T, dt=0.01, max_steps=100000):
    """Helper: input=1 で T が target_T 以上まで加熱。

    Type 2 adapter: 外部 AI tests が `node._temperature = X` で内部状態を
    直接設定する代わり。my impl の TemperatureNode は _T を private に
    保持し直接代入を許さないため、自然な加熱で目標 T に到達させる。
    """
    for _ in range(max_steps):
        if node.temperature >= target_T - 1e-6:
            return
        node.update(input_value=1, dt=dt)
    raise RuntimeError(
        f"加熱で {target_T} に到達せず: T={node.temperature}"
    )


# =========================================================================
# Source: Grok stage II, Test 1
# Original: cooling_decay_analytical (T_0=0.8, t=100, input=0)
# Adapted: node._temperature=0.8 → _heat_until で T≈0.8 に到達 (clip 無効)
# =========================================================================
def test_external_grok_stage_II_cooling_decay_long_time():
    """Newton 冷却則の長時間 (100 sec) 指数減衰が解析解と一致。"""
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    _heat_until(node, target_T=0.8)
    T_initial = node.temperature

    t_total = 100.0
    dt = 0.1
    for _ in range(int(t_total / dt)):
        node.update(input_value=0, dt=dt)

    expected = T_ENV + (T_initial - T_ENV) * math.exp(
        -COOLING_RATE * t_total
    )
    assert abs(node.temperature - expected) < 1e-6, (
        f"long-time cooling 不一致: actual={node.temperature}, "
        f"expected={expected}"
    )


# =========================================================================
# Source: Grok stage II, Test 6
# Original: boundary_stability (T=T_env+input=0; T=T_max+input=1)
# Adapted: node._temperature 直接代入なし (T_env は初期状態、T_max は加熱で到達)
# =========================================================================
def test_external_grok_stage_II_boundary_stability():
    """境界平衡の安定性: T_env+input=0 不変、T_max+input=1 clip 不変。"""
    # Case 1: T = T_env, input = 0 → 不変
    node1 = TemperatureNode(clip_enabled=True)
    assert node1.temperature == T_ENV
    for _ in range(50):
        node1.update(input_value=0, dt=0.1)
    assert abs(node1.temperature - T_ENV) < 1e-7

    # Case 2: T = T_max (clip により到達後)、input=1 で不変
    node2 = TemperatureNode(clip_enabled=True)
    _heat_until(node2, target_T=T_MAX)
    assert abs(node2.temperature - T_MAX) < 1e-12
    for _ in range(50):
        node2.update(input_value=1, dt=0.1)
    assert abs(node2.temperature - T_MAX) < 1e-12


# =========================================================================
# Source: Grok stage II, Test 7
# Original: long_term_numerical_stability (5000 random binary, no NaN)
# Adapted: なし (binary input そのまま)
# =========================================================================
def test_external_grok_stage_II_random_binary_long_term():
    """5000 ステップの random binary input で T ∈ [T_env, T_max]、有限。"""
    rng = np.random.default_rng(seed=20260504)
    node = TemperatureNode(clip_enabled=True)
    for _ in range(5000):
        node.update(input_value=int(rng.integers(0, 2)), dt=0.1)
    assert T_ENV - 1e-12 <= node.temperature <= T_MAX + 1e-12
    assert math.isfinite(node.temperature)


# =========================================================================
# Source: Grok stage III, Test 1
# Original: reset_idempotency_primary_state (T を 0.777 に直接設定後 5 回 reset)
# Adapted: _temperature=0.777 → _heat_until(0.777) (clip 無効で容易に到達)
# =========================================================================
def test_external_grok_stage_III_reset_idempotency_multi():
    """reset() を 5 回連発しても T が常に T_env、w が即座に 0 同期。"""
    node = TemperatureNode(clip_enabled=False)
    _heat_until(node, target_T=0.777)
    assert node.temperature >= 0.777 - 1e-6
    for _ in range(5):
        node.reset()
        assert abs(node.temperature - T_ENV) < 1e-14
        assert abs(node.weight - 0.0) < 1e-14


# =========================================================================
# Source: Grok stage III, Test 6
# Original: pulsed_input_transient_accumulation (5 on / 15 off × 8 cycles)
# Adapted: なし (binary input そのまま)
# =========================================================================
def test_external_grok_stage_III_pulsed_accumulation():
    """パルス input (5 on / 15 off × 8 cycles) で過渡応答が物理整合。"""
    node = TemperatureNode(clip_enabled=True)
    for _ in range(8):
        for _ in range(5):
            node.update(input_value=1, dt=0.05)
        for _ in range(15):
            node.update(input_value=0, dt=0.05)
    assert math.isfinite(node.temperature)
    assert 0.0 <= node.temperature < T_MAX  # T_max には到達しない


# =========================================================================
# Source: Grok stage I, Test 1
# Original: primary_secondary_strict_consistency
#           (node.weight = 0.999 で AttributeError 期待)
# Adapted: _temperature=0.333 → _heat_until(0.333)
# =========================================================================
def test_external_grok_stage_I_weight_read_only():
    """weight プロパティは read-only (assignment で AttributeError)。"""
    node = TemperatureNode(clip_enabled=False)
    _heat_until(node, target_T=0.333)
    expected_w = (node.temperature - T_ENV) / (T_MAX - T_ENV)
    assert abs(node.weight - expected_w) < 1e-14

    # weight に直接代入 → AttributeError
    with pytest.raises(AttributeError):
        node.weight = 0.999  # type: ignore[misc]


# =========================================================================
# Source: Grok stage I, Test 3
# Original: thermal_time_constant_e_folding (T0=0.8 から半減期で T 半分)
# Adapted: _temperature=0.8 → _heat_until(0.8)
# =========================================================================
def test_external_grok_stage_I_thermal_half_life():
    """冷却の半減期 t_half = ln(2)/cooling_rate ≈ 13.86 sec で T が半分に。

    Note: dt の量子化により厳密な t_half でサンプルできないため、actual
    total_time に対する解析解で期待値を計算する (RK4 精度のみ評価)。
    """
    node = TemperatureNode(clip_enabled=False)
    _heat_until(node, target_T=0.8)
    T_initial = node.temperature

    t_half = math.log(2.0) / COOLING_RATE
    dt = 0.02
    n_steps = int(t_half / dt)
    actual_time = n_steps * dt
    for _ in range(n_steps):
        node.update(input_value=0, dt=dt)

    # 期待値を actual_time で計算 (量子化分を補正)
    expected = T_ENV + (T_initial - T_ENV) * math.exp(
        -COOLING_RATE * actual_time
    )
    assert abs(node.temperature - expected) < 1e-6
    # 半減期判定 (粗い、量子化誤差込み)
    assert abs(node.temperature - T_initial / 2.0) < 1e-3


# =========================================================================
# Source: Grok stage I, Test 4
# Original: clip_interaction_with_underlying_ode
#           (T_max 到達後 input=0 で即冷却)
# Adapted: なし (binary input)
# =========================================================================
def test_external_grok_stage_I_clip_does_not_kill_cooling():
    """clip 適用後も ODE が動作: T_max 到達後 input=0 で即座に冷却。"""
    node = TemperatureNode(clip_enabled=True)
    _heat_until(node, target_T=T_MAX)
    assert abs(node.temperature - T_MAX) < 1e-12

    prev_T = node.temperature
    node.update(input_value=0, dt=0.05)
    assert node.temperature < prev_T - 1e-6, (
        "clip 後も冷却が動かない (clip が ODE を上書き?)"
    )


# =========================================================================
# Source: ChatGPT stage II, Test 6
# Original: response_to_impulse (10 步 input=1 → peak → 1000 步 input=0)
# Adapted: pure function step_temperature() → node.update()
# =========================================================================
def test_external_chatgpt_stage_II_impulse_response():
    """インパルス応答: 短いパルス後に上昇 → 減衰の形状。"""
    node = TemperatureNode(clip_enabled=True)
    for _ in range(10):
        node.update(input_value=1, dt=0.01)
    peak = node.temperature

    for _ in range(1000):
        node.update(input_value=0, dt=0.01)

    assert peak > T_ENV
    assert node.temperature < peak


# =========================================================================
# Source: ChatGPT stage II, Test 7
# Original: numerical_stability_large_dt (dt=1.0 × 100 steps input=1)
# Adapted: pure function → node.update(); 初期 T=0.5 を _heat_until で実現
# =========================================================================
def test_external_chatgpt_stage_II_large_dt_stability():
    """大きい dt (=1.0) でも NaN/Inf なし、有限値に留まる。"""
    node = TemperatureNode(clip_enabled=True)
    _heat_until(node, target_T=0.5, dt=0.1)
    for _ in range(100):
        node.update(input_value=1, dt=1.0)
        assert math.isfinite(node.temperature)


# =========================================================================
# Source: ChatGPT stage III, Test 3
# Original: dt_invariance_small_steps (dt=0.01 vs dt=0.001、同じ物理時間)
# Adapted: pure function → node.update()
# =========================================================================
def test_external_chatgpt_stage_III_dt_invariance():
    """dt=0.01 と dt=0.001 で同じ物理時間 1.0 sec を進めた結果が一致。"""
    node1 = TemperatureNode(clip_enabled=False, integrator='rk4')
    node2 = TemperatureNode(clip_enabled=False, integrator='rk4')

    total_time = 1.0
    for _ in range(int(total_time / 0.01)):
        node1.update(input_value=1, dt=0.01)
    for _ in range(int(total_time / 0.001)):
        node2.update(input_value=1, dt=0.001)

    assert abs(node1.temperature - node2.temperature) < 1e-6


# =========================================================================
# Source: ChatGPT stage III, Test 6
# Original: primary_secondary_no_feedback (w 計算が T 進化に影響しない)
# Adapted: pure function → node.update(); w 計算側は node.weight 読み
# =========================================================================
def test_external_chatgpt_stage_III_primary_secondary_no_feedback():
    """w を読んでも T の進化は変わらない (T が primary、w は副作用なし)。"""
    node1 = TemperatureNode(clip_enabled=True)
    node2 = TemperatureNode(clip_enabled=True)
    for _ in range(1000):
        node1.update(input_value=1, dt=0.01)
        _ = node2.weight  # 読み取りのみ、副作用想定なし
        node2.update(input_value=1, dt=0.01)

    # 完全 bit-identical (w 読みが T に影響しないことを保証)
    assert node1.temperature == node2.temperature


# =========================================================================
# Source: ChatGPT stage III, Test 7
# Original: floating_point_drift_near_bounds
#           (T=0.999999 + input=1 × 10000 steps、T <= T_max)
# Adapted: _temperature=0.999999 → _heat_until(0.999999); 以降 clip 適用
# =========================================================================
def test_external_chatgpt_stage_III_drift_near_T_max():
    """T が T_max ぎりぎりから input=1 を 10000 steps 続けても境界を守る。"""
    node = TemperatureNode(clip_enabled=True)
    _heat_until(node, target_T=0.999999)
    for _ in range(10000):
        node.update(input_value=1, dt=0.01)
        assert node.temperature <= T_MAX + 1e-9
        assert node.temperature >= T_ENV - 1e-9


# =========================================================================
# Source: ChatGPT stage III, Test 8
# Original: response_scaling_with_heating_rate (heating_rate × 2 で T 増加)
# Adapted: pure function → node.update(); 2 nodes 同時に進める
# =========================================================================
def test_external_chatgpt_stage_III_heating_rate_scaling():
    """heating_rate を 2 倍にすると、同じ時間で到達する T が高くなる。"""
    n1 = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
                         clip_enabled=False)
    n2 = TemperatureNode(heating_rate=0.2, cooling_rate=0.05,
                         clip_enabled=False)
    for _ in range(2000):
        n1.update(input_value=1, dt=0.01)
        n2.update(input_value=1, dt=0.01)
    assert n2.temperature > n1.temperature + 1e-3


# =========================================================================
# Source: ChatGPT stage I, Test 1
# Original: heating_and_cooling_terms_separable
#           (input=1 と 0 の差分から heating_rate を抽出)
# Adapted: pure function → 2 nodes が同じ T=0.3 から異なる input で 1 step
# =========================================================================
def test_external_chatgpt_stage_I_heating_cooling_separability():
    """input=1 と input=0 の差分から heating_rate が抽出できる。

    Mutation: dT/dt = a·input - b·T を (a-b)·input に書き換えるバグを検出。
    """
    node1 = TemperatureNode(clip_enabled=False)
    node2 = TemperatureNode(clip_enabled=False)
    _heat_until(node1, target_T=0.3)
    _heat_until(node2, target_T=0.3)
    assert abs(node2.temperature - node1.temperature) < 1e-12

    dt = 0.01
    node1.update(input_value=1, dt=dt)
    node2.update(input_value=0, dt=dt)

    estimated_heating = (node1.temperature - node2.temperature) / dt
    assert abs(estimated_heating - HEATING_RATE) < 1e-3


# =========================================================================
# Source: ChatGPT stage I, Test 2
# Original: cooling_depends_on_temperature_difference
#           (T_env shift で挙動変化)
# Adapted: pure function → 2 nodes with T_env=0 vs T_env=0.2
# =========================================================================
def test_external_chatgpt_stage_I_T_env_shift_sensitivity():
    """T_env を変えると input=0 の冷却挙動が変わる。

    Mutation: 冷却項 (T - T_env) → T (T_env 無視) のバグを検出。
    """
    n1 = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    n2 = TemperatureNode(T_env=0.2, T_max=1.0, clip_enabled=False)

    _heat_until(n1, target_T=0.5)
    _heat_until(n2, target_T=0.5)

    n1.update(input_value=0, dt=0.01)
    n2.update(input_value=0, dt=0.01)

    # T_env 違いで 1 step 後の T が明確に異なる
    assert abs(n1.temperature - n2.temperature) > 1e-5


# =========================================================================
# Source: ChatGPT stage I, Test 5
# Original: asymmetric_response_to_input_toggle (ON→OFF と OFF→ON 結果差)
# Adapted: pure function → node.update()
# Note: 線形 ODE では map がほぼ可換なので、差は微小 (~5e-7) であるが
#       bit-identical ではないことを確認 (atol > 1e-9)
# =========================================================================
def test_external_chatgpt_stage_I_on_off_asymmetry():
    """T=0.5 から ON→OFF と OFF→ON で 2 ステップ後の T が異なる (微小)。"""
    n1 = TemperatureNode(clip_enabled=False)
    n2 = TemperatureNode(clip_enabled=False)
    _heat_until(n1, target_T=0.5)
    _heat_until(n2, target_T=0.5)

    # n1: ON → OFF
    n1.update(input_value=1, dt=0.01)
    n1.update(input_value=0, dt=0.01)

    # n2: OFF → ON
    n2.update(input_value=0, dt=0.01)
    n2.update(input_value=1, dt=0.01)

    # 線形 ODE で完全可換ではない (RK4 の有限 dt 効果)
    diff = abs(n1.temperature - n2.temperature)
    assert diff > 1e-9


# =========================================================================
# Source: ChatGPT stage I, Test 7
# Original: parameter_swap_detectability (heating ↔ cooling swap で結果差)
# Adapted: pure function → node.update()
# =========================================================================
def test_external_chatgpt_stage_I_parameter_swap_detection():
    """heating_rate と cooling_rate を入れ替えると到達 T が大きく異なる。

    Mutation: パラメータ取り違えを検出。
    """
    n1 = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
                         clip_enabled=False)
    n2 = TemperatureNode(heating_rate=0.05, cooling_rate=0.1,
                         clip_enabled=False)

    for _ in range(1000):
        n1.update(input_value=1, dt=0.01)
        n2.update(input_value=1, dt=0.01)

    # n1: T_eq = 2.0 / n2: T_eq = 0.5
    # 1000 * 0.01 = 10 sec で大きく異なる
    assert abs(n1.temperature - n2.temperature) > 0.1
