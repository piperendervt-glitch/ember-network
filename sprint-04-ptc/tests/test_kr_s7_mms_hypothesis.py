"""
test_kr_s7_mms_hypothesis: KR-S7 (MMS と Hypothesis 本格運用、Sprint 4)

Sprint 3 で導入された Method of Manufactured Solutions (MMS、Rule 10.3) を
Sprint 4 の非線形 ODE (PTC 効果あり) に拡張する。製造解 T_man(t) を SymPy で
記号的に定義し、対応する強制項 s(t) を逆算 (期待値が実装と完全に独立)。

加えて、タスク 11 で確立された Hypothesis 本格運用 (max_examples=200) を、
ε-near-critical sampling (Devil's Advocate #2 タスク 14 への対応) で補強する。

----- self-check (Devil's Advocate #1 タスク 13 への構造的対応の継続) -----

各 MMS ケースで、T_man の time scale と RK4 ステップ数を事前計算する。

| 製造解 | T_man(t) | t_span | n_steps | T_max in span | 期待精度 |
|--------|----------|--------|---------|---------------|----------|
| poly2  | 0.5t² + 0.1t  | (0,10) | 1000 | 51.0     | 1e-6 RK4 |
| poly3  | 0.01t³+0.5t²+0.1t | (0,5) | 500 | 14.05  | 1e-6 RK4 |
| trig   | 0.3·sin(0.2t)+0.5 | (0,30) | 3000 | 0.8 | 1e-6 RK4 |
| exp    | 1-exp(-0.05t) | (0,60) | 6000 | 0.95   | 1e-6 RK4 |

各製造解で α_PTC ∈ {0.0, 0.3, 0.5, 1.0} を sweep。α_PTC=0 では Sprint 3 の
MMS と数学的同形のため、誤差は機械精度 (~1e-13) を期待。α_PTC>0 では非線形
ODE への適用、誤差 < 1e-6 が KR target。

ε-near-critical sampling (Hypothesis):
    α_PTC · input ∈ [0.5 - 1e-3, 0.5 + 1e-3] の細粒度範囲で、subcritical
    と supercritical の連続的遷移を verify。PRL-014 の運用で subnormal を
    除外。

----- assertion threshold の物理的根拠 -----

KR-S7 公式 target は MMS で 1e-6。実測では:
- α_PTC=0 (Sprint 3 同形): 1e-13 〜 1e-15 を期待 (タスク 10 KR-S2 より)
- α_PTC=0.3: 1e-9 〜 1e-12 を期待 (RK4 4 次精度、smooth manufactured solution)
- α_PTC=0.5 (臨界): タスク 10 で 2.2e-13 だったが、MMS では多項式 source
  term の相互作用により異なる挙動の可能性
- α_PTC=1.0: 1e-6 〜 1e-9 を期待 (R_factor が T と共に大きく成長)

Tripwire #6 発動条件: 1e-6 を大幅に超過 (例: 1e-4 以上)。
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import sympy as sp
from hypothesis import assume, given, settings, strategies as st

_SPRINT4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode  # noqa: E402
from analytical import analytical_temperature  # noqa: E402
from mms import (  # noqa: E402
    manufactured_polynomial,
    manufactured_trigonometric,
    manufactured_exponential,
    compute_source_term,
    manufactured_to_callable,
    integrate_with_source,
)


# ============================================================
# 共通ユーティリティ
# ============================================================

def _measure_mms_error(T_man, t_sym, T_0, t_span, dt,
                       heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
                       input_value=1.0, alpha_PTC=0.0, T_ref=None,
                       integrator='rk4'):
    """MMS による最大誤差を測定 (Sprint 4 PTC 対応)。"""
    source_func = compute_source_term(
        T_man, t_sym, heating_rate, cooling_rate, T_env, input_value,
        alpha_PTC=alpha_PTC, T_ref=T_ref,
    )
    times, T_num = integrate_with_source(
        T_0=T_0, t_span=t_span, dt=dt,
        heating_rate=heating_rate, cooling_rate=cooling_rate, T_env=T_env,
        input_value=input_value, source_func=source_func,
        alpha_PTC=alpha_PTC, T_ref=T_ref, integrator=integrator,
    )
    T_man_func = manufactured_to_callable(T_man, t_sym)
    T_exact = np.array([T_man_func(t) for t in times])
    return float(np.max(np.abs(T_num - T_exact)))


# ============================================================
# Section A: 3 製造解 × 4 α_PTC sweep
# ============================================================

@pytest.mark.parametrize("alpha_PTC", [0.0, 0.3, 0.5, 1.0])
def test_kr_s7_polynomial_quadratic_with_alpha(alpha_PTC):
    """T_man = 0.5t² + 0.1t、α_PTC sweep で MMS 誤差 < 1e-6。"""
    T, t = manufactured_polynomial([0.0, 0.1, 0.5])
    err = _measure_mms_error(
        T, t, T_0=0.0, t_span=(0.0, 10.0), dt=0.01,
        input_value=1.0, alpha_PTC=alpha_PTC,
    )
    assert err < 1e-6, (
        f"polynomial², α={alpha_PTC}: MMS error = {err:.3e} >= 1e-6 "
        f"(Tripwire #6)"
    )


@pytest.mark.parametrize("alpha_PTC", [0.0, 0.3, 0.5, 1.0])
def test_kr_s7_trigonometric_with_alpha(alpha_PTC):
    """T_man = 0.3·sin(0.2t) + 0.5、α_PTC sweep で MMS 誤差 < 1e-6。"""
    T, t = manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                      offset=0.5)
    err = _measure_mms_error(
        T, t, T_0=0.5, t_span=(0.0, 30.0), dt=0.01,
        input_value=1.0, alpha_PTC=alpha_PTC,
    )
    assert err < 1e-6, (
        f"trigonometric, α={alpha_PTC}: MMS error = {err:.3e}"
    )


@pytest.mark.parametrize("alpha_PTC", [0.0, 0.3, 0.5, 1.0])
def test_kr_s7_exponential_with_alpha(alpha_PTC):
    """T_man = 1 - exp(-0.05t)、α_PTC sweep で MMS 誤差 < 1e-6。"""
    T, t = manufactured_exponential(amplitude=1.0, decay_rate=0.05,
                                    offset=0.0)
    err = _measure_mms_error(
        T, t, T_0=0.0, t_span=(0.0, 60.0), dt=0.01,
        input_value=1.0, alpha_PTC=alpha_PTC,
    )
    assert err < 1e-6, (
        f"exponential, α={alpha_PTC}: MMS error = {err:.3e}"
    )


# ============================================================
# Section B: Sprint 3 連続性 (α_PTC=0 で機械精度)
# ============================================================

def test_kr_s7_sprint3_continuity_polynomial_machine_precision():
    """α_PTC=0、polynomial で誤差が Sprint 3 と同等の機械精度レベル。"""
    T, t = manufactured_polynomial([0.0, 0.1, 0.5])
    err = _measure_mms_error(
        T, t, T_0=0.0, t_span=(0.0, 10.0), dt=0.01,
        input_value=1.0, alpha_PTC=0.0,
    )
    # Sprint 3 と同等の機械精度を期待 (実測 ~1e-13)
    assert err < 1e-10, f"Sprint 3 連続性 (poly): {err:.3e}"


def test_kr_s7_sprint3_continuity_trigonometric_machine_precision():
    """α_PTC=0、trig で誤差が Sprint 3 と同等の機械精度レベル。"""
    T, t = manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                      offset=0.5)
    err = _measure_mms_error(
        T, t, T_0=0.5, t_span=(0.0, 30.0), dt=0.01,
        input_value=1.0, alpha_PTC=0.0,
    )
    assert err < 1e-10, f"Sprint 3 連続性 (trig): {err:.3e}"


# ============================================================
# Section C: タスク 8 発見の確認 (α_PTC=0.5、T_man=t、s=0.9 定数)
# ============================================================

def test_kr_s7_task8_observation_alpha_05_linear_source_constant():
    """
    タスク 8 で発見された「α_PTC=0.5、T_man=t、input=1 で s(t)=0.9 定数」
    を改めて verify。これは熱暴走閾値 α=0.5 が MMS の文脈でも特異な
    意味を持つことの確認。
    """
    T, t = manufactured_polynomial([0.0, 1.0])  # T_man = t
    source = compute_source_term(
        T, t, heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
        input_value=1.0, alpha_PTC=0.5,
    )
    # s(t) = 0.9 (定数、t に依らない)
    for t_val in [0.0, 0.5, 1.0, 5.0, 10.0, 100.0]:
        s = source(t_val)
        assert abs(s - 0.9) < 1e-12, (
            f"s({t_val}) = {s} != 0.9 (タスク 8 観察の崩壊)"
        )


def test_kr_s7_alpha_05_t_man_linear_mms_machine_precision():
    """α_PTC=0.5、T_man=t、s=0.9 で MMS 誤差が機械精度レベル。"""
    T, t = manufactured_polynomial([0.0, 1.0])
    err = _measure_mms_error(
        T, t, T_0=0.0, t_span=(0.0, 30.0), dt=0.01,
        input_value=1.0, alpha_PTC=0.5,
    )
    # 線形成長 + 定数 source、最も simple な MMS ケース
    assert err < 1e-10, f"α=0.5 linear MMS 機械精度違反: {err:.3e}"


# ============================================================
# Section D: 4 つの独立検証経路で α_PTC=0.5 が特異点
# (タスク 8/10/11/14 の統合確認、KR-S7 の sentinel として)
# ============================================================

def test_kr_s7_alpha_05_critical_appears_in_mms_polynomial():
    """
    多項式 T_man=t² で α_PTC sweep。α=0.5 で source の構造が
    どう変わるかを記号的に確認。

    s(t) = dT/dt - [(1+α(T-T_ref))·h·input - c·(T-T_env)]
         = 2t - [(1+α·t²)·0.1·1 - 0.05·t²]
         = 2t - 0.1 - 0.1·α·t² + 0.05·t²
         = 2t - 0.1 + (0.05 - 0.1·α)·t²

    α=0.5 で (0.05 - 0.1·0.5) = 0、t² 項が消える!
    s(t) = 2t - 0.1 (α=0.5 のとき、t² 項なし、線形 t)
    """
    T, t = manufactured_polynomial([0.0, 0.0, 1.0])  # T_man = t²
    source = compute_source_term(
        T, t, heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
        input_value=1.0, alpha_PTC=0.5,
    )
    # s(t) = 2t - 0.1 (t² 項が消える)
    for t_val in [0.0, 1.0, 5.0, 10.0]:
        expected = 2.0 * t_val - 0.1
        s = source(t_val)
        assert abs(s - expected) < 1e-12, (
            f"α=0.5 で s({t_val}) = {s} != {expected} (t² 項残存)"
        )


# ============================================================
# Section E: Hypothesis - ε-near-critical sampling
# (Devil's Advocate #2 タスク 14 への対応)
# ============================================================

@given(
    eps=st.floats(min_value=1e-5, max_value=1e-2,
                  allow_nan=False, allow_infinity=False),
    sign=st.sampled_from([-1, +1]),
)
@settings(max_examples=200, deadline=5000)
def test_kr_s7_hypothesis_eps_near_critical_continuity(eps, sign):
    """
    α_PTC = 0.5 + sign·eps で b ≈ sign·eps·h·input、subcritical/critical/
    supercritical の境界で T 系列が連続的に変化することを confirm。

    PRL-014 関連: ε-near-critical でも IEEE 754 で b を非自明に表現できる
    範囲 (eps >= 1e-5) に制限。eps=1e-5 で b = ±1e-6 (machine epsilon の
    ~10^10 倍上、十分に表現可能)。
    """
    alpha = 0.5 + sign * eps
    inp = 1.0
    # b = α·h·input - c
    b = alpha * 0.1 * inp - 0.05
    expected_b = sign * eps * 0.1
    assert abs(b - expected_b) < 1e-15

    # 短時間 (t=10) で安全に検証 (b の符号で挙動分岐するが、|b·t| <= 1e-2
    # で T の変化は小さい)
    node = TemperatureNode(
        T_env=0.0, T_max=100.0, alpha_PTC=alpha,
        T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    n_steps = 1000  # t=10
    for _ in range(n_steps):
        node.update(input_value=inp, dt=0.01)
    assert np.isfinite(node.temperature)

    # 解析解との一致
    t_arr = np.array([10.0])
    T_ana = float(analytical_temperature(
        t=t_arr, T_0=0.0, input_value=inp,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )[0])
    err = abs(node.temperature - T_ana)
    assert err < 1e-6, (
        f"ε-near-critical: α={alpha}, eps={eps}, sign={sign}, "
        f"err = {err:.3e}"
    )


@given(
    inp=st.floats(min_value=0.001, max_value=1.0,
                  allow_nan=False, allow_infinity=False),
    alpha=st.floats(min_value=0.001, max_value=2.0,
                    allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=5000)
def test_kr_s7_hypothesis_mms_polynomial_property_based(inp, alpha):
    """
    Hypothesis: random (alpha, input) で polynomial MMS が成立。

    安定域に限定するため、|b·t_max| が大きくなりすぎる組み合わせを除外
    (assume)。これは Tripwire #7 (発散制御不能) の事前回避。
    """
    # b = α·h·input - c、t_max=5 で |b·t_max| < 5 に制限
    # → |α·input - 0.5| < 5/(0.1·5) = 10、これは常に成立 (極端に発散しない)
    b = alpha * 0.1 * inp - 0.05
    # exp(b·5) overflow 防止 (b·5 が大きすぎないこと)
    assume(abs(b) * 5.0 < 5.0)  # |T| < e^5 程度に制限

    T, t = manufactured_polynomial([0.0, 0.1, 0.5])  # 0.5t² + 0.1t
    err = _measure_mms_error(
        T, t, T_0=0.0, t_span=(0.0, 5.0), dt=0.01,
        input_value=inp, alpha_PTC=alpha,
    )
    assert err < 1e-6, (
        f"hypothesis poly MMS, α={alpha}, input={inp}: err = {err:.3e}"
    )


# ============================================================
# Section F: Hypothesis sentinel (タスク 11 不変量の Sprint 4 全体での再確認)
# ============================================================

@given(
    heating=st.floats(min_value=0.01, max_value=2.0,
                      allow_nan=False, allow_infinity=False),
    cooling=st.floats(min_value=0.01, max_value=1.0,
                      allow_nan=False, allow_infinity=False),
    alpha=st.floats(min_value=0.0, max_value=1.0,
                    allow_nan=False, allow_infinity=False),
    inp=st.floats(min_value=0.0, max_value=1.0,
                  allow_nan=False, allow_infinity=False),
    seed=st.integers(0, 10**6),
)
@settings(max_examples=200, deadline=5000)
def test_kr_s7_hypothesis_bounded_invariant_clip_on(heating, cooling,
                                                    alpha, inp, seed):
    """
    Hypothesis: clip 有効、ランダム (h, c, α, input) で常に T <= T_max。

    タスク 11 の test_invariant_3_bounded_property_based を Sprint 4
    全体パラメータ範囲で再検証 (sentinel 的位置づけ)。
    """
    T_env = 0.0
    T_max = 1.0
    node = TemperatureNode(
        heating_rate=heating, cooling_rate=cooling,
        T_env=T_env, T_max=T_max,
        alpha_PTC=alpha, T_ref=None, T_initial=None,
        clip_enabled=True, integrator='rk4',
    )
    rng = np.random.default_rng(seed=seed)
    for _ in range(100):
        node.update(input_value=float(rng.uniform(0, inp + 1e-9)), dt=0.05)
        assert node.temperature <= T_max + 1e-10
        assert node.temperature >= T_env - 1e-10


# ============================================================
# Section G: RK4 vs Euler の精度比較 (Sprint 4 非線形 ODE で)
# ============================================================

@pytest.mark.parametrize("alpha_PTC", [0.0, 0.3, 0.5])
def test_kr_s7_rk4_more_accurate_than_euler_with_alpha(alpha_PTC):
    """非線形 ODE (α_PTC>0) でも RK4 が Euler より精度高い。"""
    T, t = manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                      offset=0.5)
    err_rk4 = _measure_mms_error(
        T, t, T_0=0.5, t_span=(0.0, 30.0), dt=0.05,
        input_value=1.0, alpha_PTC=alpha_PTC, integrator='rk4',
    )
    err_euler = _measure_mms_error(
        T, t, T_0=0.5, t_span=(0.0, 30.0), dt=0.05,
        input_value=1.0, alpha_PTC=alpha_PTC, integrator='euler',
    )
    assert err_rk4 < err_euler, (
        f"α={alpha_PTC}: RK4 ({err_rk4:.3e}) >= Euler ({err_euler:.3e})"
    )


# ============================================================
# Section H: MMS 製造解と物理 ODE 解の crossover 確認
# ============================================================

def test_kr_s7_mms_with_zero_source_recovers_physical_ode():
    """製造解が物理 ODE の解そのものなら、source = 0 で MMS が成立。

    具体的に T_man(t) = analytical_temperature(t; α=0.3, input=1) を
    使うと、s(t) = 0 (定数) になるはず。これは MMS の特殊ケースで、
    強制項なしの物理 ODE 解との連続性を verify。
    """
    # T_man = -10/3 + (10/3)·exp(-0.02·t) (α=0.3、input=1 の解析解)
    # ※ a/b = 0.1/-0.02 = -5、いや、再計算: a=0.1, b=0.3·0.1-0.05=-0.02
    # T_eq = -a/b = 5、T(t) = 5 - 5·exp(-0.02·t)
    t_sym = sp.Symbol('t', real=True)
    T_man = 5 - 5 * sp.exp(-sp.Rational(2, 100) * t_sym)
    source = compute_source_term(
        T_man, t_sym, heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
        input_value=1.0, alpha_PTC=0.3,
    )
    # s(t) は理論上 0 (符号の収束を全 t で確認)
    for t_val in [0.0, 1.0, 5.0, 10.0, 30.0]:
        s = source(t_val)
        # SymPy 計算誤差で完全 0 ではないが、機械精度レベル
        assert abs(s) < 1e-12, (
            f"物理解で source != 0: s({t_val}) = {s}"
        )


# ============================================================
# Sentinel: KR-S7 の総合確認 (3 製造解 × 4 α_PTC = 12 組合せ)
# ============================================================

def test_kr_s7_summary_three_solutions_four_alphas():
    """KR-S7 の sentinel: 3 製造解 × 4 α_PTC で全て < 1e-6、tabulate して記録。"""
    cases = [
        ("polynomial", manufactured_polynomial([0.0, 0.1, 0.5]),
         0.0, (0.0, 10.0)),
        ("trigonometric",
         manufactured_trigonometric(amplitude=0.3, frequency=0.2, offset=0.5),
         0.5, (0.0, 30.0)),
        ("exponential",
         manufactured_exponential(amplitude=1.0, decay_rate=0.05, offset=0.0),
         0.0, (0.0, 60.0)),
    ]
    alphas = [0.0, 0.3, 0.5, 1.0]
    errors = {}
    for name, (T, t), T_0, span in cases:
        for alpha in alphas:
            err = _measure_mms_error(
                T, t, T_0=T_0, t_span=span, dt=0.01,
                input_value=1.0, alpha_PTC=alpha,
            )
            errors[(name, alpha)] = err
            assert err < 1e-6, (
                f"{name}, α={alpha}: MMS err = {err:.3e}"
            )
