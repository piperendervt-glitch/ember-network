"""
test_invariants: KR-S3 (preregister された 6 つの物理的不変量)

Sprint 3 Planning で preregister された 6 つの不変量 (Rule 10.2):

1. monotonicity   : input=1 継続中、T は単調増加 (clip 適用前まで)
2. positivity     : 全時刻で T(t) >= T_env  (Newton 冷却則による漸近境界)
3. bounded        : clip 適用時、全時刻で T(t) <= T_max
4. equilibrium    : input=1 継続後、T は T_eq (clip なし) または T_max (clip 付き) に漸近
5. heat-flow direction : input=0 かつ T > T_env のとき dT/dt < 0
6. weight-temperature linearity : 全時刻で w = (T - T_env) / (T_max - T_env)

PRL-004 の教訓: 連続時間モデルでは「T_env への厳密到達」を期待してはならない
(漸近境界)。positivity は >= で検証し、== は要求しない。

Hypothesis を試行的に導入し、不変量 2 (positivity) と 5 (heat-flow direction)
をパラメータ空間上で検証する。
"""

import sys
from pathlib import Path

import numpy as np
from hypothesis import given, settings, strategies as st

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from temperature_node import TemperatureNode  # noqa: E402
from scenarios import (  # noqa: E402
    run_constant_input_scenario,
    run_input_cessation_scenario,
)


# ----- 不変量 1: monotonicity -----

def test_invariant_1_monotonicity_during_constant_heating():
    """input=1 継続中、T は (clip 適用前まで) 単調増加。"""
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    times, T_array = run_constant_input_scenario(
        node, total_time=10.0, dt=0.01, input_value=1
    )
    diffs = np.diff(T_array)
    # 数値的丸めで僅かな逆転は許容 (1e-10)
    assert np.all(diffs >= -1e-10), (
        f"monotonicity 違反: 最大の負増分 = {float(np.min(diffs)):.3e}"
    )
    # 実質的には正の増分が支配的
    assert np.sum(diffs > 0) > len(diffs) * 0.99


def test_invariant_1_monotonicity_holds_for_clip_enabled_until_clip():
    """clip 有効でも、t < t_clip では単調増加 (t_clip ≈ 13.8629)。"""
    node = TemperatureNode(clip_enabled=True, integrator='rk4')
    dt = 0.01
    times, T_array = run_constant_input_scenario(
        node, total_time=13.0, dt=dt, input_value=1  # t_clip 手前まで
    )
    diffs = np.diff(T_array)
    assert np.all(diffs >= -1e-10)


# ----- 不変量 2: positivity -----

def test_invariant_2_positivity_constant_input():
    """input=1 継続中、T(t) >= T_env が全時刻で成立。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    times, T_array = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=1
    )
    assert np.all(T_array >= 0.0 - 1e-15)


def test_invariant_2_positivity_with_cessation():
    """入力切替後も T(t) >= T_env が成立 (PRL-004: 厳密到達は期待しない)。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    times, T_array = run_input_cessation_scenario(
        node, t_switch=10.0, total_time=200.0, dt=0.01
    )
    assert np.all(T_array >= 0.0 - 1e-15)
    # 漸近境界として、終端 T はほぼ T_env だが厳密一致しない
    # (PRL-004 の教訓を反映: == は要求しない)


def test_invariant_2_positivity_random_input_pattern():
    """ランダムな input パターンでも T >= T_env が成立。"""
    rng = np.random.default_rng(seed=2026)
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    for _ in range(1000):
        node.update(input_value=int(rng.integers(0, 2)), dt=0.01)
        assert node.temperature >= node.T_env - 1e-15


def test_invariant_2_positivity_with_nonzero_T_env():
    """T_env != 0 でも T >= T_env が成立。"""
    node = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
                           T_env=5.0, T_max=10.0, clip_enabled=False)
    rng = np.random.default_rng(seed=2027)
    for _ in range(500):
        node.update(input_value=int(rng.integers(0, 2)), dt=0.01)
        assert node.temperature >= 5.0 - 1e-12


@given(
    heating_rate=st.floats(min_value=0.01, max_value=1.0,
                           allow_nan=False, allow_infinity=False),
    cooling_rate=st.floats(min_value=0.01, max_value=1.0,
                           allow_nan=False, allow_infinity=False),
    T_env=st.floats(min_value=-10.0, max_value=10.0,
                    allow_nan=False, allow_infinity=False),
    T_offset=st.floats(min_value=0.1, max_value=10.0,
                       allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30, deadline=2000)
def test_invariant_2_positivity_property_based(heating_rate, cooling_rate,
                                                T_env, T_offset):  # noqa: E127
    """Hypothesis: 様々なパラメータで positivity が成立。"""
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating_rate,
        cooling_rate=cooling_rate,
        T_env=T_env,
        T_max=T_max,
        clip_enabled=False,
    )
    # input=0 のみで純粋な減衰: T_env への漸近、決して下回らない
    for _ in range(100):
        node.update(input_value=0, dt=0.01)
        assert node.temperature >= T_env - 1e-10, (
            f"positivity 違反: T={node.temperature}, T_env={T_env}"
        )


# ----- 不変量 3: bounded -----

def test_invariant_3_boundedness_below_T_max():
    """clip 適用時、全時刻で T(t) <= T_max。"""
    node = TemperatureNode(clip_enabled=True, integrator='rk4')
    rng = np.random.default_rng(seed=2028)
    for _ in range(2000):
        node.update(input_value=int(rng.integers(0, 2)), dt=0.01)
        assert node.temperature <= node.T_max + 1e-15


def test_invariant_3_boundedness_with_constant_heating():
    """input=1 連続でも T が T_max を超えない。"""
    node = TemperatureNode(clip_enabled=True, integrator='rk4')
    times, T_array = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=1
    )
    assert np.all(T_array <= node.T_max + 1e-15)


def test_invariant_3_no_clip_can_exceed_T_max():
    """対比: clip 無効では T_max を超えうる (T_eq=2 への漸近)。"""
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    times, T_array = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=1
    )
    assert T_array[-1] > 1.0  # T_max=1 を超えている


# ----- 不変量 4: equilibrium -----

def test_invariant_4_equilibrium_no_clip():
    """input=1 を十分長く継続後、T → T_eq = heating/cooling。"""
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    for _ in range(20000):
        node.update(input_value=1, dt=0.01)
    T_eq_expected = node.heating_rate / node.cooling_rate  # 2.0
    assert abs(node.temperature - T_eq_expected) < 1e-3, (
        f"clip なし平衡点違反: T={node.temperature}, "
        f"expected≈{T_eq_expected}"
    )


def test_invariant_4_equilibrium_with_clip():
    """clip 有効、input=1 を十分長く継続後、T → T_max。"""
    node = TemperatureNode(clip_enabled=True, integrator='rk4')
    for _ in range(20000):
        node.update(input_value=1, dt=0.01)
    assert abs(node.temperature - node.T_max) < 1e-12


def test_invariant_4_equilibrium_zero_input_asymptote():
    """input=0 を十分長く継続後、T → T_env (漸近のみ、厳密一致しない)。"""
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    # 一度温める
    for _ in range(1000):
        node.update(input_value=1, dt=0.01)
    T_before_cool = node.temperature
    assert T_before_cool > node.T_env

    # 冷却
    for _ in range(50000):
        node.update(input_value=0, dt=0.01)
    # PRL-004: 漸近のみ、厳密に T_env には到達しない
    # 50000 ステップ × 0.01 = 500 単位時間、cooling_rate=0.05
    # T_env からの差 = (T_before - T_env) · exp(-0.05·500) ≈ 1.4e-11
    assert node.temperature > node.T_env  # 厳密に超える (漸近)
    assert abs(node.temperature - node.T_env) < 1e-9


# ----- 不変量 5: heat-flow direction -----

def test_invariant_5_heat_flow_input_zero_decreases_T():
    """input=0 かつ T > T_env で T が減少する。"""
    node = TemperatureNode(clip_enabled=False)
    # 温める
    for _ in range(50):
        node.update(input_value=1, dt=0.01)
    T_before = node.temperature
    assert T_before > node.T_env

    node.update(input_value=0, dt=0.01)
    T_after = node.temperature
    assert T_after < T_before, (
        f"heat-flow 違反: T_before={T_before}, T_after={T_after}"
    )


def test_invariant_5_heat_flow_at_T_env_no_change():
    """T = T_env かつ input=0 で T は変化しない (T_env が漸近平衡)。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    assert node.temperature == 0.0
    node.update(input_value=0, dt=0.01)
    assert node.temperature == 0.0  # dT/dt = 0


@given(
    heating_rate=st.floats(min_value=0.01, max_value=2.0,
                           allow_nan=False, allow_infinity=False),
    cooling_rate=st.floats(min_value=0.01, max_value=1.0,
                           allow_nan=False, allow_infinity=False),
    T_env=st.floats(min_value=-5.0, max_value=5.0,
                    allow_nan=False, allow_infinity=False),
    T_offset=st.floats(min_value=0.5, max_value=10.0,
                       allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=10**6),
)
@settings(max_examples=40, deadline=3000)
def test_invariant_3_bounded_property_based(heating_rate, cooling_rate,
                                            T_env, T_offset,
                                            seed):  # noqa: E127
    """Hypothesis: 様々なパラメータで bounded 不変量が成立 (clip ロジック検証)。

    Note: Devil's Advocate #4 (Sprint 3 Step C 完了報告) で「Hypothesis 2
    件は違反しにくい性質を選んだ可能性」を自己批判したことへの対応。clip
    ロジックは入力切替時の境界条件で複雑な分岐を持ち、バグが入りやすい
    箇所として bounded (T <= T_max) を選択。
    """
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating_rate,
        cooling_rate=cooling_rate,
        T_env=T_env,
        T_max=T_max,
        clip_enabled=True,
    )
    rng = np.random.default_rng(seed=seed)
    # heating_rate >= cooling_rate * T_offset の場合、clip なしなら T_max
    # を超えうる (T_eq = T_env + heating/cooling > T_max)。clip がそれを
    # 防ぐかを検証する真のストレステスト。
    for _ in range(500):
        inp = int(rng.integers(0, 2))
        node.update(input_value=inp, dt=0.05)
        assert node.temperature <= T_max + 1e-10, (
            f"bounded 違反: T={node.temperature}, T_max={T_max}, "
            f"params=(h={heating_rate}, c={cooling_rate}, "
            f"T_env={T_env}, T_offset={T_offset})"
        )
        assert node.temperature >= T_env - 1e-10


@given(
    heating_rate=st.floats(min_value=0.01, max_value=1.0,
                           allow_nan=False, allow_infinity=False),
    cooling_rate=st.floats(min_value=0.01, max_value=1.0,
                           allow_nan=False, allow_infinity=False),
)
@settings(max_examples=20, deadline=2000)
def test_invariant_5_heat_flow_property_based(heating_rate, cooling_rate):
    """Hypothesis: 様々な (heating, cooling) で heat-flow direction が成立。"""
    node = TemperatureNode(
        heating_rate=heating_rate,
        cooling_rate=cooling_rate,
        T_env=0.0, T_max=10.0, clip_enabled=False,
    )
    # 温める
    for _ in range(100):
        node.update(input_value=1, dt=0.01)
    if node.temperature > node.T_env + 1e-6:
        T_before = node.temperature
        node.update(input_value=0, dt=0.01)
        assert node.temperature < T_before


# ----- 不変量 6: weight-temperature linearity -----

def test_invariant_6_linearity_during_evolution():
    """全時刻で w = (T - T_env) / (T_max - T_env) が成立。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=False)
    rng = np.random.default_rng(seed=2029)
    for _ in range(200):
        node.update(input_value=int(rng.integers(0, 2)), dt=0.01)
        T = node.temperature
        expected_w = (T - node.T_env) / (node.T_max - node.T_env)
        assert abs(node.weight - expected_w) < 1e-15


def test_invariant_6_linearity_with_shifted_range():
    """T_env != 0 のときも線形変換が常に成立。"""
    node = TemperatureNode(T_env=10.0, T_max=20.0, clip_enabled=False)
    for _ in range(100):
        node.update(input_value=1, dt=0.05)
        expected = (node.temperature - 10.0) / 10.0
        assert abs(node.weight - expected) < 1e-15


# ----- 6 不変量の同時検証 (KR-S3 sentinel test) -----

def test_kr_s3_all_six_invariants_simultaneously():
    """1 シミュレーション中に 6 不変量すべてを同時検証する sentinel test。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, clip_enabled=True,
                           integrator='rk4')
    times, T_array = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1
    )

    # 不変量 2: positivity
    assert np.all(T_array >= node.T_env - 1e-15)
    # 不変量 3: bounded (clip 有効のため)
    assert np.all(T_array <= node.T_max + 1e-15)

    # 不変量 1: monotonicity (input=1 連続のため、丸めを除いて単調増加)
    assert np.all(np.diff(T_array) >= -1e-10)

    # 不変量 4: equilibrium (30 単位時間後、clip により T_max)
    # t_clip = 20·ln(2) ≈ 13.86, t=30 で T=T_max
    assert abs(T_array[-1] - node.T_max) < 1e-12

    # 不変量 5: heat-flow direction を別シミュレーションで確認
    node2 = TemperatureNode(clip_enabled=False)
    for _ in range(50):
        node2.update(input_value=1, dt=0.01)
    T_b = node2.temperature
    node2.update(input_value=0, dt=0.01)
    assert node2.temperature < T_b

    # 不変量 6: 全時刻で linearity (T_env=0, T_max=1 なので w=T)
    # node の最終状態の weight を検証
    assert abs(node.weight - 1.0) < 1e-12  # clip により w=1
