"""
test_kr_s4_fractional_input: KR-S4 (fractional input サポートの検証、Sprint 4)

Sprint 3 では input ∈ {0, 1} (int) のみだったが、Sprint 4 では
input ∈ [0.0, 1.0] (float) を許容するよう拡張された (PRL-010 対処)。
本テストファイルは Claude Code の独立な観点で、fractional input が
正しく動作することを検証する。

外部 AI のテストケースとの統合は Sprint Backlog タスク 18 (Step D) で
実施する。本ファイルは Claude Code 独立実装 (Sprint 3 と同じ運用)。

検証する観点:
    (a) 解析解との比較 (input ∈ {0.1, 0.3, 0.5, 0.7, 0.9})
    (b) 物理的不変量 (monotonicity、heat-flow direction) が fractional
        input でも成立 (KR-S3 の再確認)
    (c) 線形性の検証: α_PTC=0 (linear ODE) で superposition 成立、
        α_PTC>0 (non-linear ODE) で superposition 崩壊
    (d) 境界ケース: input=0 (純冷却)、input=1 (純加熱)、input=0.5 等
    (e) α_PTC × input の臨界条件 (α_PTC · input = cooling/heating の
        曲線上で b=0、線形成長)

PRL-014 関連:
    Hypothesis テストでは input < 1e-10 の subnormal 領域を除外する。
    `1.0 + α_PTC · T) · heating · input` で input が極めて小さい場合、
    heating · input が underflow し、T の更新が IEEE 754 精度限界で
    無視される。Sprint 7 物理単位 (input は無次元の duty cycle) でも
    1e-10 未満の値は意味を持たない。
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from hypothesis import assume, given, settings, strategies as st

_SPRINT4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode  # noqa: E402
from analytical import (  # noqa: E402
    analytical_temperature,
    equilibrium_temperature,
)
from scenarios import (  # noqa: E402
    run_constant_input_scenario,
    run_fractional_input_scenario,
)


# ============================================================
# (a) 解析解との比較 (input ∈ {0.1, 0.3, 0.5, 0.7, 0.9})
# ============================================================

@pytest.mark.parametrize("inp", [0.1, 0.3, 0.5, 0.7, 0.9])
def test_kr_s4_analytical_match_alpha_zero(inp):
    """α_PTC=0、各 fractional input で解析解と数値解が一致 (誤差 < 1e-6)。"""
    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=10.0,
        alpha_PTC=0.0, T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=inp,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=inp,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=0.0,
    )
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"input={inp}, α_PTC=0: max error = {max_err:.3e} >= 1e-6"
    )


@pytest.mark.parametrize("inp", [0.1, 0.3, 0.5, 0.7, 0.9])
def test_kr_s4_analytical_match_alpha_03(inp):
    """α_PTC=0.3、各 fractional input で解析解と数値解が一致 (誤差 < 1e-6)。"""
    alpha = 0.3
    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=10.0,
        alpha_PTC=alpha, T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=inp,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=inp,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"input={inp}, α_PTC={alpha}: max error = {max_err:.3e} >= 1e-6"
    )


def test_kr_s4_equilibrium_for_fractional_input_alpha_zero():
    """α_PTC=0、fractional input で T_eq = (heating·input) / cooling。"""
    for inp in [0.2, 0.5, 0.8]:
        T_eq = equilibrium_temperature(
            input_value=inp, heating_rate=0.1, cooling_rate=0.05,
            T_env=0.0, alpha_PTC=0.0,
        )
        # T_eq = a/(-b) = (h·input) / c
        expected = (0.1 * inp) / 0.05
        assert T_eq is not None
        assert abs(T_eq - expected) < 1e-12


# ============================================================
# (b) 物理的不変量が fractional input でも成立
# ============================================================

@pytest.mark.parametrize("inp", [0.05, 0.2, 0.5, 0.8, 0.95])
def test_kr_s4_invariant_1_monotonicity_fractional(inp):
    """不変量 1: fractional input>0 で T<T_eq の間 T 単調増加 (clip なし)。"""
    node = TemperatureNode(
        alpha_PTC=0.3, T_initial=None,
        clip_enabled=False, integrator='rk4',
    )
    _, T = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=inp,
    )
    diffs = np.diff(T)
    assert np.all(diffs >= -1e-10), (
        f"input={inp}: monotonicity 違反 = {float(np.min(diffs)):.3e}"
    )


def test_kr_s4_invariant_5_heat_flow_small_input():
    """不変量 5: fractional input が小さい (0.01) で T > T_eq なら T 減少。"""
    inp = 0.01  # T_eq for input=0.01, α_PTC=0.3:
    # b = 0.3·0.1·0.01 - 0.05 = -0.0497
    # a = 0.1·0.01 = 0.001
    # T_eq = a/(-b) = 0.001/0.0497 ≈ 0.02013
    # T_initial=1.0 で T > T_eq、よって T は減少すべき
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_initial=1.0, clip_enabled=False, integrator='rk4',
    )
    T_before = node.temperature
    node.update(input_value=inp, dt=0.1)
    T_after = node.temperature
    assert T_after < T_before, (
        f"小 input で T>T_eq でも減少しない: {T_before} → {T_after}"
    )


def test_kr_s4_invariant_5_zero_input_pure_cooling():
    """不変量 5: input=0.0 (float、純冷却) で T > T_env なら T 減少。"""
    # Sprint 4 で input=0.0 (float) と input=0 (int) の両方が許容される
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_initial=2.0, clip_enabled=False,
    )
    T_before = node.temperature
    node.update(input_value=0.0, dt=0.1)
    assert node.temperature < T_before


# ============================================================
# (c) 線形性の検証 (α_PTC=0: superposition、α_PTC>0: 崩壊)
# ============================================================

def test_kr_s4_superposition_holds_for_alpha_zero():
    """α_PTC=0 (linear ODE) で T(input=0.3) + T(input=0.7) = T(input=1.0)。

    線形 ODE dT/dt = a·input + b·T (a, b は input に依らない) では
    superposition が成立。具体的に T_initial=0 から始めると
        T(t; input) = input · T(t; input=1)
    が成立し、T(0.3) + T(0.7) = (0.3 + 0.7)·T(1) = T(1)。
    """
    def make_node():
        return TemperatureNode(
            heating_rate=0.1, cooling_rate=0.05,
            T_env=0.0, T_max=100.0, alpha_PTC=0.0,
            T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )

    n_03 = make_node()
    _, T_03 = run_constant_input_scenario(n_03, total_time=20.0, dt=0.01,
                                          input_value=0.3)
    n_07 = make_node()
    _, T_07 = run_constant_input_scenario(n_07, total_time=20.0, dt=0.01,
                                          input_value=0.7)
    n_10 = make_node()
    _, T_10 = run_constant_input_scenario(n_10, total_time=20.0, dt=0.01,
                                          input_value=1.0)

    superposition_err = float(np.max(np.abs((T_03 + T_07) - T_10)))
    assert superposition_err < 1e-12, (
        f"α_PTC=0 で superposition 違反: max err = {superposition_err:.3e}"
    )


def test_kr_s4_superposition_fails_for_alpha_positive():
    """α_PTC>0 (non-linear ODE) で T(0.3) + T(0.7) ≠ T(1.0)。

    PTC 効果の非線形性の visualization。a は input に線形だが、b は
    input に依存する (b = α·h·input - c)。よって T(t; input) は input
    に対して非線形であり、superposition は崩壊する。
    """
    alpha = 0.3

    def make_node():
        return TemperatureNode(
            heating_rate=0.1, cooling_rate=0.05,
            T_env=0.0, T_max=100.0, alpha_PTC=alpha,
            T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )

    n_03 = make_node()
    _, T_03 = run_constant_input_scenario(n_03, total_time=20.0, dt=0.01,
                                          input_value=0.3)
    n_07 = make_node()
    _, T_07 = run_constant_input_scenario(n_07, total_time=20.0, dt=0.01,
                                          input_value=0.7)
    n_10 = make_node()
    _, T_10 = run_constant_input_scenario(n_10, total_time=20.0, dt=0.01,
                                          input_value=1.0)

    # 重ね合わせ崩壊の度合いを測定 (= 非線形性の強度の指標)
    superposition_err = float(np.max(np.abs((T_03 + T_07) - T_10)))
    assert superposition_err > 1e-3, (
        f"α_PTC={alpha} で superposition がほぼ成立してしまっている "
        f"(非線形性が見えない): err = {superposition_err:.3e}"
    )

    # T(0.3) + T(0.7) と T(1.0) の関係: PTC 効果により T(1.0) > T(0.3) + T(0.7)
    # (input=1 では b が大きくなり熱暴走に近づくため)
    assert T_10[-1] > T_03[-1] + T_07[-1], (
        "PTC 非線形性: T(input=1) が T(0.3)+T(0.7) を超えるはず"
    )


# ============================================================
# (d) 境界ケース
# ============================================================

def test_kr_s4_input_zero_pure_cooling_no_temperature_change():
    """input=0.0、T_initial=T_env で T は変化しない (dT/dt=0)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.3,
        T_initial=None, clip_enabled=False,
    )
    assert node.temperature == 0.0
    for _ in range(100):
        node.update(input_value=0.0, dt=0.01)
        assert node.temperature == 0.0


def test_kr_s4_input_zero_after_warming_decays_to_t_env():
    """input=1 で温めた後 input=0.0 で T → T_env に漸近 (PRL-004)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.0,
        clip_enabled=False, integrator='rk4',
    )
    # 温める
    for _ in range(1000):
        node.update(input_value=1.0, dt=0.01)
    T_warm = node.temperature
    assert T_warm > 0.0

    # input=0.0 で冷却 (Sprint 3 では int 0 だったが Sprint 4 は float 0.0)
    for _ in range(50000):
        node.update(input_value=0.0, dt=0.01)
    assert node.temperature > 0.0  # 漸近、厳密には届かない (PRL-004)
    assert abs(node.temperature - 0.0) < 1e-9


def test_kr_s4_input_one_matches_sprint3_pattern():
    """input=1.0 (float) と input=1 (int) で同一挙動 (Sprint 3 互換)。"""
    n_int = TemperatureNode(alpha_PTC=0.3, clip_enabled=False,
                            integrator='rk4')
    n_float = TemperatureNode(alpha_PTC=0.3, clip_enabled=False,
                              integrator='rk4')
    for _ in range(100):
        n_int.update(input_value=1, dt=0.01)
        n_float.update(input_value=1.0, dt=0.01)
        # int / float 差は IEEE 754 `1.0 * x == 1 * x` で bit-perfect
        assert n_int.temperature == n_float.temperature, (
            f"int 1 vs float 1.0 で挙動差: "
            f"int={n_int.temperature!r}, float={n_float.temperature!r}"
        )


def test_kr_s4_input_half_intermediate_behavior():
    """input=0.5 で T_eq が input=1 の半分 (α_PTC=0、線形性の確認)。"""
    n_half = TemperatureNode(alpha_PTC=0.0, clip_enabled=False,
                             integrator='rk4')
    n_full = TemperatureNode(alpha_PTC=0.0, clip_enabled=False,
                             integrator='rk4')
    for _ in range(20000):
        n_half.update(input_value=0.5, dt=0.01)
        n_full.update(input_value=1.0, dt=0.01)
    # T_eq(input=0.5) = 0.5 · T_eq(input=1.0) (α_PTC=0、線形)
    assert abs(n_half.temperature - 0.5 * n_full.temperature) < 1e-6


# ============================================================
# (e) α_PTC × input の臨界条件 (b=0 となる組み合わせ、線形成長)
# ============================================================

def test_kr_s4_critical_curve_alpha_one_input_half():
    """
    α_PTC × input の臨界条件: α_PTC · input = cooling/heating で b=0。

    具体例: α_PTC=1.0, input=0.5 → b = 1.0·0.1·0.5 - 0.05 = 0 (線形成長)
    タスク 11 で α_PTC=0.5 + input=1.0 が臨界として確認されたが、本テスト
    では α_PTC=1.0 + input=0.5 が同じ臨界条件 (a/heating·input=0.05) で
    異なる線形成長率を示すことを確認する。
    """
    # α_PTC=1.0, input=0.5: b=0, a=0.1·0.5=0.05
    # T(t) = a · t = 0.05 · t
    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        alpha_PTC=1.0, T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=20.0, dt=0.01, input_value=0.5,
    )
    # 解析解は T = 0.05 · t (b=0、a=0.05)
    T_expected = 0.05 * t_arr
    max_err = float(np.max(np.abs(T_num - T_expected)))
    assert max_err < 1e-6, (
        f"α_PTC=1.0, input=0.5 (b=0) 線形成長違反: err = {max_err:.3e}"
    )

    # T_eq が None (b=0) であることを確認
    T_eq = equilibrium_temperature(
        input_value=0.5, heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=1.0,
    )
    assert T_eq is None, f"b=0 だが T_eq={T_eq}"


def test_kr_s4_critical_curve_consistency_across_pairs():
    """
    α_PTC · input = 0.5 (= cooling/heating) を満たす複数の (α_PTC, input)
    ペアで全て b=0 の線形成長になり、傾きは a = heating · input に一致。

    タスク 8 / 10 / 11 / 12 で確認されている α_PTC=0.5 の特異性が、
    入力空間にも対応する曲線として広がることを示す。
    """
    pairs = [(0.5, 1.0), (1.0, 0.5), (2.0, 0.25), (5.0, 0.1)]
    for alpha, inp in pairs:
        # α · input = 0.5 を確認
        assert abs(alpha * inp - 0.5) < 1e-12

        node = TemperatureNode(
            heating_rate=0.1, cooling_rate=0.05,
            alpha_PTC=alpha, T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )
        n_steps = 500
        for _ in range(n_steps):
            node.update(input_value=inp, dt=0.01)
        # 線形成長: T(5) = a · 5 = (0.1 · inp) · 5 = 0.5 · inp
        expected = 0.1 * inp * (n_steps * 0.01)
        assert abs(node.temperature - expected) < 1e-6, (
            f"(α={alpha}, input={inp}): T={node.temperature}, "
            f"expected={expected}"
        )


def test_kr_s4_subcritical_vs_supercritical_input():
    """
    α_PTC=1.0 固定で input < 0.5 なら b<0 (収束)、input > 0.5 なら
    b>0 (熱暴走)、input = 0.5 で b=0 (線形成長) の 3 区分を確認。
    """
    alpha = 1.0
    # subcritical: input=0.4、b = 0.04 - 0.05 = -0.01、τ = 1/|b| = 100
    # T_eq = a/(-b) = 0.04/0.01 = 4.0
    # ※ τ=100 のため t=100 では 1τ 経過のみ (T ≈ T_eq · (1-1/e) ≈ 2.53)。
    # 厳密な T_eq 到達は 7-10τ = 700-1000 単位時間が必要だが、本テストは
    # 「subcritical (b<0): 平衡点存在 + T < T_eq で単調増加」のみ確認する。
    n_sub = TemperatureNode(
        alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    _, T_sub = run_constant_input_scenario(
        n_sub, total_time=100.0, dt=0.01, input_value=0.4,
    )
    T_eq_sub = equilibrium_temperature(input_value=0.4, alpha_PTC=alpha)
    assert T_eq_sub is not None  # b<0、平衡点存在
    assert abs(T_eq_sub - 4.0) < 1e-12
    # T < T_eq が常に成立 (bounded growth)
    assert np.all(T_sub < T_eq_sub), (
        f"subcritical で T が T_eq を超えた: max(T)={float(np.max(T_sub))}, "
        f"T_eq={T_eq_sub}"
    )
    # 単調増加
    assert np.all(np.diff(T_sub) > 0)
    # 1τ 経過時点で T ≈ T_eq · (1 - 1/e) ≈ 0.632 · T_eq の検証
    expected_at_tau = T_eq_sub * (1.0 - np.exp(-1.0))
    assert abs(n_sub.temperature - expected_at_tau) < 1e-6, (
        f"subcritical: T(t=100)={n_sub.temperature}, "
        f"expected (1τ)={expected_at_tau}"
    )

    # critical: input=0.5 (b=0、線形)
    n_crit = TemperatureNode(
        alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    for _ in range(1000):
        n_crit.update(input_value=0.5, dt=0.01)
    T_eq_crit = equilibrium_temperature(input_value=0.5, alpha_PTC=alpha)
    assert T_eq_crit is None  # b=0、平衡点なし
    # T(10) = 0.05 · 10 = 0.5 (線形成長)
    assert abs(n_crit.temperature - 0.5) < 1e-6

    # supercritical: input=0.6 (b=0.01、slow exponential growth)
    # T(t) = -a/b + (a/b)·exp(b·t) = -6 + 6·exp(0.01·t)
    # T(10) ≈ 0.631 (critical t=10 の 0.5 より大きい)
    n_super = TemperatureNode(
        alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    for _ in range(1000):
        n_super.update(input_value=0.6, dt=0.01)
    T_eq_super = equilibrium_temperature(input_value=0.6, alpha_PTC=alpha)
    assert T_eq_super is None  # b>0、平衡点なし

    # 3 ケース間の順序関係 (sub < crit < super) で物理的振る舞いを確認
    # 同じ t=10 (n_steps=1000) に揃えて比較
    n_sub_short = TemperatureNode(
        alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    for _ in range(1000):
        n_sub_short.update(input_value=0.4, dt=0.01)
    assert n_sub_short.temperature < n_crit.temperature, (
        f"sub T(10) >= crit T(10): {n_sub_short.temperature} vs "
        f"{n_crit.temperature}"
    )
    assert n_crit.temperature < n_super.temperature, (
        f"crit T(10) >= super T(10): {n_crit.temperature} vs "
        f"{n_super.temperature}"
    )

    # 指数発散の特徴: t=10 で super > crit、かつ super は exp(b·t) の形
    # 解析解 -6 + 6·exp(0.01·10) = -6 + 6·exp(0.1) = 0.6310...
    expected_super = -6.0 + 6.0 * np.exp(0.1)
    assert abs(n_super.temperature - expected_super) < 1e-6, (
        f"supercritical: T(10)={n_super.temperature}, "
        f"expected={expected_super}"
    )


# ============================================================
# Hypothesis: fractional input でも解析解と一致
# ============================================================

@given(
    inp=st.floats(min_value=0.001, max_value=1.0,
                  allow_nan=False, allow_infinity=False),
    alpha=st.floats(min_value=0.0, max_value=0.4,
                    allow_nan=False, allow_infinity=False),  # b<0 で安定
)
@settings(max_examples=100, deadline=5000)
def test_kr_s4_analytical_match_property_based(inp, alpha):
    """Hypothesis: random fractional input + α_PTC で b<0 域の解析解一致。

    α_PTC ∈ [0, 0.4] に制限する理由: α·0.1·1.0 - 0.05 < 0 ⇔ α < 0.5、
    かつ α·heating·input が cooling より小さいなら b<0 で安定。
    α=0.4, input=1 で b=-0.01 (slow approach)、安定動作の境界。
    熱暴走域は別テスト (KR-S2 で扱う) で検証済み、本 Hypothesis は安定域
    での numerical-vs-analytical 整合性に焦点を当てる。

    PRL-014 関連: input < 0.001 を除外する理由は、input が極端に小さい
    と heating·input が underflow し、T の更新が IEEE 754 精度限界で
    無視される領域に入るため。Sprint 7 物理単位 (duty cycle) でも 0.001
    未満は意味を持たない。
    """
    # 安定域 (b<0) のみ対象とする
    b = alpha * 0.1 * inp - 0.05
    assume(b < -1e-4)  # 臨界に近すぎない

    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=100.0,
        alpha_PTC=alpha, T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=10.0, dt=0.01, input_value=inp,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=inp,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"input={inp}, α_PTC={alpha}: max err = {max_err:.3e}"
    )


# ============================================================
# fractional input scenario (時変 input) との整合性
# ============================================================

def test_kr_s4_fractional_input_scenario_constant_callable():
    """run_fractional_input_scenario の input_func が定数の場合、
    run_constant_input_scenario と一致する。"""
    inp_const = 0.4
    n_const = TemperatureNode(alpha_PTC=0.3, clip_enabled=False)
    n_func = TemperatureNode(alpha_PTC=0.3, clip_enabled=False)
    _, T_const = run_constant_input_scenario(
        n_const, total_time=10.0, dt=0.01, input_value=inp_const,
    )
    _, T_func = run_fractional_input_scenario(
        n_func, total_time=10.0, dt=0.01,
        input_func=lambda t: inp_const,
    )
    np.testing.assert_array_equal(T_const, T_func)


def test_kr_s4_fractional_input_scenario_time_varying():
    """時変 input (sin 関数) で fractional input シナリオが動作する。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.2,
        clip_enabled=False, integrator='rk4',
    )
    # input(t) = 0.5 + 0.5*sin(t) ∈ [0, 1]
    _, T = run_fractional_input_scenario(
        node, total_time=20.0, dt=0.01,
        input_func=lambda t: 0.5 + 0.5 * np.sin(t),
    )
    # 不変量: T >= T_env (sin の最小値で input=0、純冷却フェーズ含む)
    assert np.all(T >= 0.0 - 1e-10)
    # 値の有限性
    assert np.all(np.isfinite(T))


# ============================================================
# Sentinel: KR-S4 が KR-S1/S2/S3 と矛盾しないことを確認
# ============================================================

def test_kr_s4_sentinel_consistency_with_other_KRs():
    """fractional input の中で input=1 のケースが KR-S2 (5 つの α_PTC) と整合。

    本テストは KR-S4 が KR-S2 を「拡張」しているのみで、KR-S2 の主張を
    崩していないことを sentinel として確認する。
    """
    for alpha in [0.0, 0.1, 0.4]:  # b<0 の 3 ケース
        node = TemperatureNode(
            alpha_PTC=alpha, T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )
        t_arr, T_num = run_constant_input_scenario(
            node, total_time=30.0, dt=0.01, input_value=1.0,
        )
        T_ana = analytical_temperature(
            t=t_arr, T_0=0.0, input_value=1.0,
            heating_rate=0.1, cooling_rate=0.05,
            T_env=0.0, alpha_PTC=alpha,
        )
        max_err = float(np.max(np.abs(T_num - T_ana)))
        # KR-S2 の閾値 1e-6 と整合
        assert max_err < 1e-6
