"""
test_invariants: KR-S3 (preregister された 8 つの物理的不変量、Sprint 4 版)

Sprint 4 で SPRINT_OKR.md に preregister された 8 つの不変量 (Rule 10.2):

1. monotonicity   : input>0 で T < T_eq なら T 単調増加 (clip 適用前まで、
                     fractional input 対応、修正案 1-A)
2. positivity     : (2-A) T_initial >= T_env なら全時刻で T >= T_env
                    (2-B) T_initial < T_env なら t→∞ で T → T_env (漸近)
                    (修正案 2-C: 両方を独立な不変量として検証)
3. bounded        : clip 適用時、全時刻で T <= T_max + 1e-15 (修正案 3-A)
4. equilibrium    : b<0 なら T → T_eq (clip なし); b=0 なら線形成長;
                     b>0 なら発散 (clip なし) または T_max 漸近 (clip 付き)
                     (修正案 4-B、Devil's Advocate #2 タスク 10 への対応)
5. heat-flow direction : input=0 で T と T_env の大小に応じた dT/dt 符号
                          (修正案 5-A、3 区分: T>T_env, T=T_env, T<T_env)
6. weight-temperature linearity : 全時刻で w = (T - T_env) / (T_max - T_env)
7. PTC monotonicity (新規) : α_PTC > 0 で R(T) は T に対し単調増加
                              (dR/dT = R_0 · α_PTC > 0)
8. PTC reference (新規) : T = T_ref のとき R(T) = R_0 (R_factor = 1.0)

Hypothesis 適用 (Sprint 4 ではタスク 11 指示により 6 不変量に max_examples=200):
    1. monotonicity     ✓
    2 (2-A). positivity ✓
    3. bounded          ✓
    4. equilibrium      ✓
    5. heat-flow        ✓
    7. PTC monotonicity ✓

物理的観察 (タスク 8 と 10 で発見された α_PTC=0.5 の特異性):
    α_PTC=0.5 (b=0、臨界条件) は不変量 4 (equilibrium) で「平衡点なし、
    線形成長」として独立した分岐となる。MMS と KR-S2 で誤差最大の特異点
    だったが、不変量検証の文脈でも「漸近平衡」と「指数発散」の境界に位置
    する。
"""

import sys
from pathlib import Path

import numpy as np
from hypothesis import assume, given, settings, strategies as st

_SPRINT4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode  # noqa: E402
from analytical import equilibrium_temperature  # noqa: E402
from scenarios import run_constant_input_scenario  # noqa: E402


# Hypothesis のパラメータ空間 (Sprint 4 拡張、α_PTC を含む)
# - heating_rate ∈ [0.01, 2.0]
# - cooling_rate ∈ [0.01, 1.0]
# - T_env ∈ [-5, 5]
# - T_offset ∈ [0.5, 10] (T_max = T_env + T_offset)
# - alpha_PTC ∈ [0.0, 1.0]
# 熱暴走 (b > 0) を含むため、t_max は短く (例: 0.5〜10) に制限する。

_HEATING = st.floats(min_value=0.01, max_value=2.0,
                     allow_nan=False, allow_infinity=False)
_COOLING = st.floats(min_value=0.01, max_value=1.0,
                     allow_nan=False, allow_infinity=False)
_T_ENV = st.floats(min_value=-5.0, max_value=5.0,
                   allow_nan=False, allow_infinity=False)
_T_OFFSET = st.floats(min_value=0.5, max_value=10.0,
                      allow_nan=False, allow_infinity=False)
_ALPHA = st.floats(min_value=0.0, max_value=1.0,
                   allow_nan=False, allow_infinity=False)
_INPUT_FRAC = st.floats(min_value=0.01, max_value=1.0,
                        allow_nan=False, allow_infinity=False)


# ============================================================
# 不変量 1: monotonicity (input>0 で T<T_eq なら単調増加)
# ============================================================

def test_invariant_1_monotonicity_constant_input_no_clip():
    """input=1、T_initial=T_env=0 で T<T_eq の間 T 単調増加 (α_PTC=0.3、b<0)。"""
    node = TemperatureNode(alpha_PTC=0.3, clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=1.0,
    )
    diffs = np.diff(T)
    assert np.all(diffs >= -1e-10), (
        f"monotonicity 違反: 最大の負増分 = {float(np.min(diffs)):.3e}"
    )


def test_invariant_1_monotonicity_fractional_input():
    """fractional input=0.5 でも T 単調増加 (Sprint 4 新規対応)。"""
    node = TemperatureNode(alpha_PTC=0.2, clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=10.0, dt=0.01, input_value=0.5,
    )
    diffs = np.diff(T)
    assert np.all(diffs >= -1e-10), (
        f"fractional monotonicity 違反: {float(np.min(diffs)):.3e}"
    )


def test_invariant_1_monotonicity_critical_alpha_05():
    """α_PTC=0.5 (b=0、線形成長) で単調増加 (KR-S2 で発見された臨界点)。"""
    node = TemperatureNode(alpha_PTC=0.5, clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=10.0, dt=0.01, input_value=1.0,
    )
    # 線形成長なので diff はほぼ一定 (= a · dt = 0.1 * 0.01 = 0.001)
    diffs = np.diff(T)
    assert np.all(diffs > 0), "α_PTC=0.5 で単調増加でない"
    assert abs(float(np.mean(diffs)) - 0.001) < 1e-10, (
        f"線形成長の傾き = {float(np.mean(diffs))!r}, expected 0.001"
    )


def test_invariant_1_monotonicity_runaway_alpha_10():
    """α_PTC=1.0 (b=0.05、熱暴走) でも単調増加 (clip なし)。"""
    node = TemperatureNode(alpha_PTC=1.0, clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=1.0,
    )
    diffs = np.diff(T)
    assert np.all(diffs > 0), "熱暴走で単調増加でない"


@given(heating=_HEATING, cooling=_COOLING, T_env=_T_ENV,
       T_offset=_T_OFFSET, alpha=_ALPHA, inp=_INPUT_FRAC)
@settings(max_examples=200, deadline=3000)
def test_invariant_1_monotonicity_property_based(
    heating, cooling, T_env, T_offset, alpha, inp,
):
    """Hypothesis: input>0、T_initial=T_env、clip なし、短時間で T 単調増加。

    ODE dT/dt = a + b*T において、初期条件 T=T_env=T_ref で
        a = heating·input·(1 - α·T_ref) + cooling·T_env
          = heating·input·(1 - α·T_env) + cooling·T_env
        b = α·heating·input - cooling
    dT/dt(T_env) = heating·input - cooling·0 + α·heating·input·... の
    具体的計算より、T_ref=T_env なら R(T_env)=1.0 で
        dT/dt(T_env) = heating·input > 0
    したがって t=0 で増加方向。線形 ODE で b<0/=0/>0 のいずれでも
    monotonic ODE の解は単調 (符号が反転しない)。
    """
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=None,
        clip_enabled=False, integrator='rk4',
    )
    # 短時間で熱暴走を制御 (b > 0 でも T が桁落ちしない範囲)
    n_steps = 100  # 1.0 単位時間
    for _ in range(n_steps):
        T_prev = node.temperature
        node.update(input_value=inp, dt=0.01)
        # 数値的丸めで僅かな逆転は許容
        assert node.temperature >= T_prev - 1e-10, (
            f"monotonicity 違反: T_prev={T_prev}, T_after={node.temperature}, "
            f"params=(h={heating}, c={cooling}, T_env={T_env}, "
            f"alpha={alpha}, inp={inp})"
        )


# ============================================================
# 不変量 2-A: positivity (T_initial >= T_env で T >= T_env)
# ============================================================

def test_invariant_2a_positivity_t_initial_eq_t_env():
    """T_initial = T_env で全時刻 T >= T_env (Sprint 3 の不変量 2 と同等)。"""
    node = TemperatureNode(T_env=0.0, T_max=10.0,
                           alpha_PTC=0.3, T_initial=None,
                           clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=1.0,
    )
    assert np.all(T >= 0.0 - 1e-15)


def test_invariant_2a_positivity_t_initial_above_t_env():
    """T_initial > T_env、input=0 でも T >= T_env (純冷却の漸近)。"""
    node = TemperatureNode(T_env=0.0, T_max=10.0,
                           alpha_PTC=0.3, T_initial=2.0,
                           clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=0.0,
    )
    assert np.all(T >= 0.0 - 1e-15), (
        f"positivity 違反: min(T)={float(np.min(T)):.3e}"
    )
    # 漸近的に T_env に近づくが、厳密には >= T_env (PRL-004)
    assert T[-1] >= 0.0


def test_invariant_2a_positivity_random_input_pattern():
    """ランダム fractional input でも T >= T_env (T_initial=T_env)。"""
    rng = np.random.default_rng(seed=2026)
    node = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=0.3,
                           clip_enabled=False)
    for _ in range(1000):
        node.update(input_value=float(rng.uniform(0, 1)), dt=0.01)
        assert node.temperature >= 0.0 - 1e-15


@given(heating=_HEATING, cooling=_COOLING, T_env=_T_ENV,
       T_offset=_T_OFFSET, alpha=_ALPHA)
@settings(max_examples=200, deadline=3000)
def test_invariant_2a_positivity_property_based(
    heating, cooling, T_env, T_offset, alpha,
):
    """Hypothesis: input=0、T_initial=T_env で全時刻 T >= T_env。"""
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=None,
        clip_enabled=False, integrator='rk4',
    )
    for _ in range(100):
        node.update(input_value=0.0, dt=0.01)
        assert node.temperature >= T_env - 1e-10, (
            f"positivity 違反: T={node.temperature}, T_env={T_env}, "
            f"params=(h={heating}, c={cooling}, alpha={alpha})"
        )


# ============================================================
# 不変量 2-B: asymptotic recovery (T_initial < T_env で漸近)
# ============================================================

def test_invariant_2b_asymptotic_recovery_t_initial_below_t_env():
    """T_initial < T_env、input=0 で T → T_env に漸近 (下から)。"""
    # PRL-011 対処: Sprint 4 では T_initial < T_env が許容される
    node = TemperatureNode(T_env=5.0, T_max=15.0,
                           alpha_PTC=0.3, T_initial=2.0,  # T_env=5 より下
                           clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=0.0,
    )
    # 開始時 T < T_env、徐々に T → T_env
    assert T[0] == 2.0
    assert T[-1] > 2.0  # 上昇している
    assert T[-1] < 5.0  # しかし T_env を厳密には超えない (漸近、PRL-004)
    assert (5.0 - T[-1]) < 1e-3, (
        f"漸近不十分: T_env - T(end) = {5.0 - T[-1]:.3e}"
    )


def test_invariant_2b_asymptotic_with_input_above_zero():
    """T_initial < T_env、input>0 で T → T_eq (T_env より上の平衡点)。"""
    node = TemperatureNode(T_env=5.0, T_max=20.0,
                           alpha_PTC=0.0, T_initial=2.0,
                           clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=1.0,
    )
    # T_eq for α_PTC=0, input=1: T_eq = T_env + heating/cooling = 5 + 2 = 7
    T_eq = equilibrium_temperature(
        input_value=1.0, heating_rate=0.1, cooling_rate=0.05,
        T_env=5.0, alpha_PTC=0.0,
    )
    assert T_eq is not None and abs(T_eq - 7.0) < 1e-10
    assert abs(T[-1] - T_eq) < 1e-3


# ============================================================
# 不変量 3: bounded (clip 適用時、T <= T_max + 1e-15)
# ============================================================

def test_invariant_3_bounded_below_T_max_constant_heating():
    """clip 有効、input=1 連続でも T <= T_max。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=0.3,
                           clip_enabled=True, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=1.0,
    )
    assert np.all(T <= 1.0 + 1e-15)


def test_invariant_3_bounded_with_runaway_alpha_10_clip():
    """clip 有効、α_PTC=1.0 (熱暴走) でも T <= T_max (deterrence の安全網)。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=1.0,
                           clip_enabled=True, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=1.0,
    )
    assert np.all(T <= 1.0 + 1e-15), (
        f"clip が熱暴走を防げていない: max(T)={float(np.max(T)):.3e}"
    )


def test_invariant_3_no_clip_can_exceed_T_max():
    """対比: clip 無効では T_max を超えうる (T_eq=2 への漸近)。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=0.0,
                           clip_enabled=False, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=1.0,
    )
    assert T[-1] > 1.0  # T_max=1 を超えている


@given(heating=_HEATING, cooling=_COOLING, T_env=_T_ENV,
       T_offset=_T_OFFSET, alpha=_ALPHA, seed=st.integers(0, 10**6))
@settings(max_examples=200, deadline=3000)
def test_invariant_3_bounded_property_based(
    heating, cooling, T_env, T_offset, alpha, seed,
):
    """Hypothesis: 様々なパラメータで bounded 不変量 (T <= T_max) が成立。

    熱暴走を含むパラメータ空間 (α_PTC ∈ [0, 1]、h ∈ [0.01, 2]、c ∈ [0.01, 1])
    でも clip ロジックが機能することを検証。
    """
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=None,
        clip_enabled=True, integrator='rk4',
    )
    rng = np.random.default_rng(seed=seed)
    for _ in range(100):
        node.update(input_value=float(rng.uniform(0, 1)), dt=0.05)
        assert node.temperature <= T_max + 1e-10, (
            f"bounded 違反: T={node.temperature}, T_max={T_max}, "
            f"params=(h={heating}, c={cooling}, alpha={alpha})"
        )
        assert node.temperature >= T_env - 1e-10


# ============================================================
# 不変量 4: equilibrium (b<0: T→T_eq, b=0: 線形, b>0: 発散/clip)
# ============================================================

def test_invariant_4_equilibrium_b_negative_no_clip():
    """b<0 (α_PTC=0.3、cooling 優勢) で T → T_eq に漸近 (clip なし)。"""
    alpha = 0.3
    node = TemperatureNode(alpha_PTC=alpha,
                           clip_enabled=False, integrator='rk4')
    for _ in range(50000):
        node.update(input_value=1.0, dt=0.01)
    T_eq = equilibrium_temperature(input_value=1.0, alpha_PTC=alpha)
    assert T_eq is not None
    assert abs(node.temperature - T_eq) < 1e-3, (
        f"b<0 平衡違反: T={node.temperature}, T_eq={T_eq}"
    )


def test_invariant_4_equilibrium_b_zero_linear_growth():
    """b=0 (α_PTC=0.5、臨界) で線形成長、平衡点なし。"""
    alpha = 0.5
    node = TemperatureNode(alpha_PTC=alpha,
                           clip_enabled=False, integrator='rk4')
    n_steps = 1000
    for _ in range(n_steps):
        node.update(input_value=1.0, dt=0.01)
    # 線形成長: T(t) = a · t = 0.1 * 10 = 1.0
    expected = 0.1 * (n_steps * 0.01)
    assert abs(node.temperature - expected) < 1e-6, (
        f"b=0 線形成長違反: T={node.temperature}, expected={expected}"
    )
    T_eq = equilibrium_temperature(input_value=1.0, alpha_PTC=alpha)
    assert T_eq is None, f"b=0 で T_eq が None でない: {T_eq}"


def test_invariant_4_equilibrium_b_positive_clip_to_T_max():
    """b>0 (α_PTC=1.0、熱暴走) かつ clip で T → T_max (発散を物理的に止める)。"""
    alpha = 1.0
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=alpha,
                           clip_enabled=True, integrator='rk4')
    for _ in range(20000):
        node.update(input_value=1.0, dt=0.01)
    assert abs(node.temperature - 1.0) < 1e-12, (
        f"熱暴走 clip 違反: T={node.temperature}, T_max=1.0"
    )


def test_invariant_4_equilibrium_zero_input_asymptote_to_T_env():
    """input=0 で T → T_env に漸近 (PRL-004: 厳密には到達しない)。"""
    node = TemperatureNode(alpha_PTC=0.3,
                           clip_enabled=False, integrator='rk4')
    # 一度温める
    for _ in range(2000):
        node.update(input_value=1.0, dt=0.01)
    T_warm = node.temperature
    assert T_warm > node.T_env

    # 冷却
    for _ in range(50000):
        node.update(input_value=0.0, dt=0.01)
    assert node.temperature > node.T_env  # 厳密に超える (漸近、PRL-004)
    assert abs(node.temperature - node.T_env) < 1e-8


@given(heating=_HEATING, cooling=_COOLING, T_env=_T_ENV,
       T_offset=_T_OFFSET, alpha=_ALPHA)
@settings(max_examples=200, deadline=5000)
def test_invariant_4_equilibrium_property_based(
    heating, cooling, T_env, T_offset, alpha,
):
    """Hypothesis: clip 有効、input=1 を長く回すと T は T_max 以下で安定。

    b<0 のとき T → T_eq (T_eq < T_max なら T_eq、>= なら T_max)
    b>=0 のとき T → T_max (clip により)。
    いずれにせよ、十分時間後の T は T_max + ε 以下、かつ T_env - ε 以上。
    """
    T_max = T_env + T_offset
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=None,
        clip_enabled=True, integrator='rk4',
    )
    # 十分長く input=1 を継続 (b>=0 なら T_max に飽和、b<0 なら T_eq に漸近)
    for _ in range(2000):
        node.update(input_value=1.0, dt=0.05)
    # T は [T_env, T_max] 範囲内
    assert T_env - 1e-10 <= node.temperature <= T_max + 1e-10, (
        f"equilibrium 範囲違反: T={node.temperature}, "
        f"[{T_env}, {T_max}], params=(h={heating}, c={cooling}, alpha={alpha})"
    )


# ============================================================
# 不変量 5: heat-flow direction (input=0 で 3 ケース、対称性)
# ============================================================

def test_invariant_5_heat_flow_T_above_T_env_decreases():
    """T > T_env, input=0 で T 減少。"""
    node = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=0.3,
                           T_initial=5.0,  # T_env より上で開始
                           clip_enabled=False)
    T_before = node.temperature
    node.update(input_value=0.0, dt=0.01)
    assert node.temperature < T_before


def test_invariant_5_heat_flow_T_eq_T_env_no_change():
    """T = T_env, input=0 で T 不変 (dT/dt = 0)。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=0.3,
                           clip_enabled=False)  # T_initial=None で T_env
    assert node.temperature == 0.0
    node.update(input_value=0.0, dt=0.01)
    assert node.temperature == 0.0


def test_invariant_5_heat_flow_T_below_T_env_increases():
    """T < T_env, input=0 で T 増加 (Newton 冷却の対称性、PRL-011 対処)。"""
    # T_initial < T_env が Sprint 4 で許容される
    node = TemperatureNode(T_env=5.0, T_max=15.0, alpha_PTC=0.3,
                           T_initial=2.0,  # T_env より下
                           clip_enabled=False)
    T_before = node.temperature
    assert T_before == 2.0
    node.update(input_value=0.0, dt=0.01)
    assert node.temperature > T_before, (
        f"対称性違反: T<T_env で増加しない: {T_before} → {node.temperature}"
    )


@given(heating=_HEATING, cooling=_COOLING, T_env=_T_ENV,
       T_offset=_T_OFFSET, alpha=_ALPHA)
@settings(max_examples=200, deadline=3000)
def test_invariant_5_heat_flow_property_based(
    heating, cooling, T_env, T_offset, alpha,
):
    """Hypothesis: input=0 で T と T_env の大小に応じた dT/dt 符号。

    1 step 進めて、T_before > T_env なら T_after < T_before、逆も成立。
    """
    T_max = T_env + T_offset
    # T_initial を T_env より上 (T_max 寄り) に設定
    T_initial = T_env + T_offset * 0.5
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=T_initial,
        clip_enabled=False, integrator='rk4',
    )
    T_before = node.temperature
    node.update(input_value=0.0, dt=0.01)
    T_after = node.temperature
    # T_before > T_env, input=0: 減少
    assert T_after < T_before, (
        f"heat-flow 違反: T_before={T_before}, T_after={T_after}, "
        f"T_env={T_env}, params=(h={heating}, c={cooling}, alpha={alpha})"
    )


# ============================================================
# 不変量 6: weight-temperature linearity
# ============================================================

def test_invariant_6_linearity_during_evolution():
    """全時刻で w = (T - T_env) / (T_max - T_env)、α_PTC=0.3。"""
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=0.3,
                           clip_enabled=False)
    rng = np.random.default_rng(seed=2029)
    for _ in range(200):
        node.update(input_value=float(rng.uniform(0, 1)), dt=0.01)
        T = node.temperature
        expected_w = (T - node.T_env) / (node.T_max - node.T_env)
        assert abs(node.weight - expected_w) < 1e-15


def test_invariant_6_linearity_with_shifted_range():
    """T_env != 0、T_max != 1 でも w = (T-T_env)/(T_max-T_env)。"""
    node = TemperatureNode(T_env=10.0, T_max=20.0, alpha_PTC=0.3,
                           clip_enabled=False)
    for _ in range(100):
        node.update(input_value=1.0, dt=0.05)
        expected = (node.temperature - 10.0) / 10.0
        assert abs(node.weight - expected) < 1e-15


def test_invariant_6_linearity_with_t_initial_below_t_env():
    """T_initial < T_env でも weight は (T-T_env)/(T_max-T_env) (負の値も許容)。"""
    node = TemperatureNode(T_env=5.0, T_max=15.0, alpha_PTC=0.3,
                           T_initial=2.0, clip_enabled=False)
    # 初期: w = (2 - 5) / (15 - 5) = -0.3 (負の値、Sprint 3 にはなかった)
    assert abs(node.weight - (-0.3)) < 1e-15


# ============================================================
# 不変量 7 (新規): PTC monotonicity (R(T) が T に対し単調増加)
# ============================================================

def test_invariant_7_ptc_monotonicity_alpha_positive():
    """α_PTC > 0 のとき、T が大きいほど R(T)/R_0 が大きい。"""
    alpha = 0.3
    nodes_T = []
    for T_init in [0.0, 0.5, 1.0, 2.0, 5.0]:
        n = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=alpha,
                            T_initial=T_init, clip_enabled=False)
        nodes_T.append((T_init, n.resistance_ratio))
    # 単調増加
    R_values = [r for _, r in nodes_T]
    diffs = np.diff(R_values)
    assert np.all(diffs > 0), (
        f"PTC monotonicity 違反: R values = {R_values}"
    )
    # 解析的に dR/dT = alpha なので diff(T) * alpha が diff(R)
    T_values = np.array([t for t, _ in nodes_T])
    expected_dR = np.diff(T_values) * alpha
    np.testing.assert_allclose(diffs, expected_dR, atol=1e-15)


def test_invariant_7_ptc_alpha_zero_constant_R():
    """α_PTC = 0 で R(T) = R_0 = 1.0、T 依存なし。"""
    for T_init in [0.0, 0.5, 2.0, 5.0]:
        n = TemperatureNode(alpha_PTC=0.0, T_initial=T_init,
                            clip_enabled=False)
        assert n.resistance_ratio == 1.0, (
            f"α_PTC=0 で R != 1: T_initial={T_init}, R={n.resistance_ratio}"
        )


def test_invariant_7_ptc_dynamic_during_simulation():
    """シミュレーション中、T が増加するにつれ R(T) も単調増加 (α_PTC>0)。"""
    node = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=0.5,
                           clip_enabled=False, integrator='rk4')
    R_seq = [node.resistance_ratio]
    for _ in range(100):
        node.update(input_value=1.0, dt=0.01)
        R_seq.append(node.resistance_ratio)
    # T が単調増加 (input=1、b=0 で線形成長) なので R も単調増加
    diffs = np.diff(R_seq)
    assert np.all(diffs >= -1e-15), (
        f"動的 R(T) monotonicity 違反: {float(np.min(diffs)):.3e}"
    )


@given(alpha=st.floats(min_value=0.001, max_value=2.0,
                       allow_nan=False, allow_infinity=False),
       T_a=st.floats(min_value=-10.0, max_value=10.0,
                     allow_nan=False, allow_infinity=False),
       T_b=st.floats(min_value=-10.0, max_value=10.0,
                     allow_nan=False, allow_infinity=False),
       T_ref=st.floats(min_value=-5.0, max_value=5.0,
                       allow_nan=False, allow_infinity=False))
@settings(max_examples=200, deadline=2000)
def test_invariant_7_ptc_monotonicity_property_based(alpha, T_a, T_b, T_ref):
    """Hypothesis: α_PTC > 0 で T_a < T_b なら R(T_a) < R(T_b)。

    R(T) = 1 + α_PTC · (T - T_ref) は T に対して厳密に単調増加 (α_PTC>0)。
    任意の T_a, T_b と T_ref で成立 (ただし IEEE 754 で表現可能な T 差で)。
    """
    # IEEE 754 精度限界による subnormal 領域を除外、PRL-014 参照。
    # threshold = 1e-10 の根拠:
    #   strict 単調検出条件: α · |T_a - T_b| > ε ≈ 2.22e-16
    #   binding は α_min = 0.001 のとき |T_a - T_b| > 2.22e-13
    #   安全係数 ~1000x、Sprint 7 物理単位 (典型 1e-3 K) も大幅下回るため
    #   1e-10 は研究上意味のある最小温度差として妥当
    assume(abs(T_a - T_b) > 1e-10 or T_a == T_b)
    # T_max は T 値より大きく取る (constructor の T_max > T_env 制約に注意)
    T_lo = min(T_a, T_b) - 1.0
    T_hi = max(T_a, T_b) + 1.0
    T_env = T_lo
    T_max = T_hi + 100.0  # 余裕を持って T_max
    node_a = TemperatureNode(
        T_env=T_env, T_max=T_max, alpha_PTC=alpha,
        T_ref=T_ref, T_initial=T_a, clip_enabled=False,
    )
    node_b = TemperatureNode(
        T_env=T_env, T_max=T_max, alpha_PTC=alpha,
        T_ref=T_ref, T_initial=T_b, clip_enabled=False,
    )
    R_a = node_a.resistance_ratio
    R_b = node_b.resistance_ratio
    if T_a < T_b:
        assert R_a < R_b, f"R_a={R_a}, R_b={R_b}, T_a={T_a}, T_b={T_b}"
    elif T_a > T_b:
        assert R_a > R_b
    else:
        assert R_a == R_b


# ============================================================
# 不変量 8 (新規): PTC reference (T = T_ref で R = R_0 = 1.0)
# ============================================================

def test_invariant_8_ptc_reference_R_equals_R_0():
    """T = T_ref のとき R(T)/R_0 = 1.0 (定義通り)。"""
    # T_ref を明示的に指定し、T_initial = T_ref で開始
    node = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=0.5,
                           T_ref=3.0, T_initial=3.0,
                           clip_enabled=False)
    assert node.resistance_ratio == 1.0


def test_invariant_8_ptc_reference_default_t_ref_is_t_env():
    """T_ref=None のときデフォルトで T_ref=T_env、よって T=T_env で R=R_0。"""
    node = TemperatureNode(T_env=2.0, T_max=10.0, alpha_PTC=0.7,
                           T_ref=None, T_initial=None,
                           clip_enabled=False)
    # T_initial=None → T_env=2.0、T_ref=None → T_env=2.0、よって T=T_ref
    assert node.temperature == 2.0
    assert node.T_ref == 2.0
    assert node.resistance_ratio == 1.0


def test_invariant_8_ptc_reference_independent_of_alpha():
    """T = T_ref では R = R_0、α_PTC の値に依らない (定義より)。"""
    for alpha in [0.0, 0.1, 0.5, 1.0, 2.0]:
        node = TemperatureNode(T_env=0.0, T_max=10.0, alpha_PTC=alpha,
                               T_ref=4.0, T_initial=4.0,
                               clip_enabled=False)
        assert node.resistance_ratio == 1.0, (
            f"α_PTC={alpha} で T=T_ref だが R={node.resistance_ratio}"
        )


# ============================================================
# Sprint 3 不変量との整合性 (回帰検証、Rule 11 の (1) commit 履歴整合)
# ============================================================

def test_consistency_with_sprint3_alpha_zero_invariants():
    """α_PTC=0 で Sprint 4 の不変量挙動が Sprint 3 と整合する。

    Sprint 3 の不変量 1, 2, 4, 5 は Sprint 4 で「修正」されているが、
    α_PTC=0 という Sprint 3 と数学的同形のパラメータでは、両者が同じ
    挙動を示すはず。
    """
    node = TemperatureNode(T_env=0.0, T_max=1.0, alpha_PTC=0.0,
                           clip_enabled=True, integrator='rk4')
    _, T = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1.0,
    )
    # 不変量 2 (Sprint 3): T >= T_env
    assert np.all(T >= 0.0 - 1e-15)
    # 不変量 3 (Sprint 3): T <= T_max
    assert np.all(T <= 1.0 + 1e-15)
    # 不変量 1 (Sprint 3): 単調増加
    assert np.all(np.diff(T) >= -1e-10)
    # 不変量 4 (Sprint 3、α_PTC=0): clip により T → T_max
    assert abs(T[-1] - 1.0) < 1e-12


# ============================================================
# Sentinel test: 1 シミュレーションで全 8 不変量を同時検証
# ============================================================

def test_kr_s3_all_eight_invariants_simultaneously():
    """1 シミュレーション (α_PTC=0.3、clip 有効) で 8 不変量すべてを同時検証。"""
    alpha = 0.3
    T_env = 0.0
    T_max = 1.0
    T_ref = 0.0  # = T_env
    node = TemperatureNode(
        T_env=T_env, T_max=T_max, alpha_PTC=alpha,
        T_ref=T_ref, T_initial=None,
        clip_enabled=True, integrator='rk4',
    )

    # 不変量 8 (PTC reference): 初期 T=T_env=T_ref、R=R_0
    assert node.temperature == T_ref
    assert node.resistance_ratio == 1.0

    times, T_array = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1.0,
    )

    # 不変量 2 (positivity): T >= T_env
    assert np.all(T_array >= T_env - 1e-15)
    # 不変量 3 (bounded): T <= T_max
    assert np.all(T_array <= T_max + 1e-15)
    # 不変量 1 (monotonicity, clip 適用前後通して): 単調非減少
    assert np.all(np.diff(T_array) >= -1e-10)
    # 不変量 4 (equilibrium): clip により最終的に T_max
    assert abs(T_array[-1] - T_max) < 1e-12
    # 不変量 6 (linearity): 最終 weight = (T_max - T_env) / (T_max - T_env) = 1
    assert abs(node.weight - 1.0) < 1e-12

    # 不変量 5 (heat-flow direction) を別シミュレーションで確認
    node2 = TemperatureNode(alpha_PTC=alpha, clip_enabled=False)
    for _ in range(50):
        node2.update(input_value=1.0, dt=0.01)
    T_b = node2.temperature
    assert T_b > 0.0
    node2.update(input_value=0.0, dt=0.01)
    assert node2.temperature < T_b  # 不変量 5 (T>T_env で減少)

    # 不変量 7 (PTC monotonicity): node の最終 R(T_max) > R(T_env)
    # T = T_max = 1.0、T_ref = 0.0、α_PTC = 0.3 → R = 1 + 0.3·1.0 = 1.3
    expected_R = 1.0 + alpha * (T_max - T_ref)
    assert abs(node.resistance_ratio - expected_R) < 1e-15
    assert node.resistance_ratio > 1.0  # 単調増加性 (T_max > T_ref)
