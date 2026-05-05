"""
test_kr_s6_thermal_runaway: KR-S6 (熱暴走の検証)

α_PTC > 0.5 (input=1 のとき) で b>0、T が指数発散することを実測検証する。
これは ember-network の deterrence の物理的限界の demonstration である。

主方程式 (input=1、T_env=0、T_ref=0、clip なし):
    dT/dt = a + b·T   where  a = h·input,  b = α·h·input - c
    解: T(t) = -a/b + (T_0 + a/b)·exp(b·t)  (b ≠ 0)

熱暴走の閾値: α_PTC > c/h = 0.5 (input=1 のとき)

----- self-check (Devil's Advocate #1 タスク 13 への構造的対応) -----

各検証ケースで τ = 1/|b| と t_max を事前計算し、Tripwire #7 (NaN/inf
発散制御不能) を回避する。テスト assertion threshold は時定数を考慮。

| Case          | α   | inp | b     | τ   | t_max | T(t_max)        |
|---------------|-----|-----|-------|-----|-------|-----------------|
| (a) clip off  | 0.6 | 1.0 | +0.01 | 100 | 100   | 10(e-1)≈17.18   |
| (a) extended  | 0.6 | 1.0 | +0.01 | 100 | 500   | 10(e^5-1)≈1473  |
| (b) clip on   | 0.6 | 1.0 | +0.01 | 100 | 30    | 1.0 (T_max)     |
|   t_clip ≈ 9.531 (= 100·ln(1.1))                                |
| (c) clip off  | 1.0 | 1.0 | +0.05 | 20  | 30    | -2+2e^1.5≈6.96  |
| (c) clip on   | 1.0 | 1.0 | +0.05 | 20  | 30    | 1.0             |
|   t_clip ≈ 8.109 (= 20·ln(1.5))                                 |
| (d)           | 1.0 | 0.6 | +0.01 | 100 | 100   | -6+6e≈10.31     |

全てのケースで T(t_max) < 1e6、float64 範囲 (~1.8e308) から十分余裕。

----- R<0 領域は本タスクで扱わない (Devil's Advocate #2 タスク 13) -----

タスク 13 で発見された「線形 PTC モデルで T < T_ref - 1/α で R<0」の
unphysical 領域は本タスクでは扱わない。本タスクは T_initial=T_env >= T_ref
の R>0 領域で熱暴走を検証。R<0 域は Sprint 7 物理パラメータ校正で再評価。
"""

import sys
from pathlib import Path

import numpy as np

_SPRINT4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode  # noqa: E402
from analytical import (  # noqa: E402
    analytical_temperature,
    equilibrium_temperature,
)
from scenarios import run_constant_input_scenario  # noqa: E402


# ============================================================
# (a) α_PTC = 0.6, clip OFF (b=0.01, τ=100, slow runaway)
# ============================================================

def test_kr_s6_alpha_06_clip_off_slow_runaway_short():
    """
    α_PTC=0.6, clip off で T が緩やかに発散 (τ=100)、t_max=100 で T≈17.18。
    解析解との誤差 < 1e-6、Tripwire #7 (NaN/inf) 不発動。
    """
    alpha = 0.6
    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=100.0, alpha_PTC=alpha,
        T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=1.0,
    )
    # Tripwire #7: NaN/inf 検出
    assert np.all(np.isfinite(T_num)), (
        f"Tripwire #7: T に NaN/inf、max(T)={float(np.max(T_num)):.3e}"
    )
    # 解析解との誤差
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=1.0,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"Tripwire #6: α={alpha}, t_max=100: err = {max_err:.3e}"
    )
    # 解析解 T(100) = 10·(e-1) ≈ 17.183
    expected_T_100 = 10.0 * (np.exp(1.0) - 1.0)
    assert abs(T_num[-1] - expected_T_100) < 1e-6
    # 平衡点なし (b>0)
    T_eq = equilibrium_temperature(input_value=1.0, alpha_PTC=alpha)
    assert T_eq is None
    # 単調増加 (発散の方向)
    assert np.all(np.diff(T_num) > 0)


def test_kr_s6_alpha_06_clip_off_extended_runaway():
    """
    α_PTC=0.6, clip off, t_max=500 で T が大きく発散 (T(500)≈1473)。
    Tripwire #7 不発動を確認、long-time integration での精度確認。
    """
    alpha = 0.6
    node = TemperatureNode(
        T_env=0.0, T_max=10000.0, alpha_PTC=alpha,
        T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=500.0, dt=0.01, input_value=1.0,
    )
    assert np.all(np.isfinite(T_num))
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=1.0,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )
    # 長時間積分で T が大きいため、相対誤差で判定
    rel_err = float(np.max(np.abs((T_num - T_ana) / np.maximum(T_ana, 1.0))))
    assert rel_err < 1e-6, (
        f"long-time relative error: {rel_err:.3e}"
    )
    # T(500) ≈ 10·(e^5 - 1) ≈ 1473.41
    expected_T_500 = 10.0 * (np.exp(5.0) - 1.0)
    assert abs(T_num[-1] - expected_T_500) < 1e-3  # 大きい T で絶対誤差は緩く


# ============================================================
# (b) α_PTC = 0.6, clip ON (T が T_max で停止)
# ============================================================

def test_kr_s6_alpha_06_clip_on_saturates_at_t_max():
    """
    α_PTC=0.6, clip on, T_max=1.0 で熱暴走が物理的に止まる (deterrence)。
    t_clip ≈ 100·ln(1.1) ≈ 9.531 で T = T_max、その後 T=1.0 (literal) 維持。
    """
    alpha = 0.6
    T_max = 1.0
    # t_clip の解析的計算: T(t_clip) = 10·(exp(0.01·t_clip) - 1) = 1
    # → exp(0.01·t_clip) = 1.1 → t_clip = 100·ln(1.1)
    t_clip_expected = 100.0 * np.log(1.1)
    assert abs(t_clip_expected - 9.531017980432486) < 1e-9

    node = TemperatureNode(
        T_env=0.0, T_max=T_max, alpha_PTC=alpha,
        T_ref=None, T_initial=0.0,
        clip_enabled=True, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1.0,
    )
    # Tripwire #4: bounded 不変量
    assert np.all(T_num <= T_max + 1e-15), (
        f"clip on で T_max 超過 (Tripwire #4): "
        f"max(T)={float(np.max(T_num)):.3e}"
    )
    # 終端 T = T_max (literal、clip 後の停止)
    assert T_num[-1] == T_max
    # t_clip 後は全て T=T_max
    idx_clip = int(round(t_clip_expected / 0.01)) + 1  # clip 直後の index
    # idx_clip 以降の T が全て T_max (literal、clip 経路の安定性)
    assert np.all(T_num[idx_clip:] == T_max), (
        f"clip 後 T が T_max から外れる: {T_num[idx_clip:idx_clip+5]}"
    )


def test_kr_s6_alpha_06_clip_on_pre_clip_matches_no_clip():
    """clip on / off で t < t_clip の T 系列は bit-perfect 一致。"""
    alpha = 0.6
    n_off = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    n_on = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=True, integrator='rk4',
    )
    # t_clip ≈ 9.531 まで (clip on の影響が出る前まで) を比較
    # 安全側に t < 9 までを比較
    n_steps = 900  # 9.0 単位時間
    for _ in range(n_steps):
        n_off.update(input_value=1.0, dt=0.01)
        n_on.update(input_value=1.0, dt=0.01)
        # まだ T < T_max=1 のため、両者 bit-perfect
        assert n_off.temperature == n_on.temperature, (
            f"t < t_clip で off/on 差: off={n_off.temperature!r}, "
            f"on={n_on.temperature!r}"
        )
        assert n_on.temperature < 1.0


# ============================================================
# (c) α_PTC = 1.0 (急激な熱暴走、b=0.05、τ=20)
# ============================================================

def test_kr_s6_alpha_10_clip_off_rapid_runaway():
    """α_PTC=1.0, clip off で急速に発散 (τ=20)、t_max=30 で T≈6.96。"""
    alpha = 1.0
    node = TemperatureNode(
        T_env=0.0, T_max=100.0, alpha_PTC=alpha,
        T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1.0,
    )
    assert np.all(np.isfinite(T_num))  # Tripwire #7
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=1.0,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=alpha,
    )
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, f"Tripwire #6: err = {max_err:.3e}"
    # T(30) = -2 + 2·exp(0.05·30) = -2 + 2·exp(1.5)
    expected_T_30 = -2.0 + 2.0 * np.exp(1.5)
    assert abs(T_num[-1] - expected_T_30) < 1e-6
    # 単調増加
    assert np.all(np.diff(T_num) > 0)


def test_kr_s6_alpha_10_clip_on_fast_saturation():
    """α_PTC=1.0, clip on で T が短時間で T_max に飽和 (material damage の demo)。"""
    alpha = 1.0
    T_max = 1.0
    # t_clip: -2 + 2·exp(0.05·t) = 1 → t = 20·ln(1.5) ≈ 8.109
    t_clip_expected = 20.0 * np.log(1.5)
    # α=0.6 の t_clip ≈ 9.531 より早い (急激な熱暴走 → clip 早期発動)
    assert t_clip_expected < 100.0 * np.log(1.1)
    # 値の sanity (20·ln(1.5) を別経路で計算)
    assert abs(t_clip_expected - 20.0 * 0.4054651081081644) < 1e-12

    node = TemperatureNode(
        T_env=0.0, T_max=T_max, alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=True, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1.0,
    )
    assert np.all(T_num <= T_max + 1e-15)  # Tripwire #4
    assert T_num[-1] == T_max
    # t_clip 後は T=T_max
    idx_clip = int(round(t_clip_expected / 0.01)) + 1
    assert np.all(T_num[idx_clip:] == T_max)


# ============================================================
# (d) (α_PTC, input) 空間での連続性 (タスク 12 観察 1 の拡張)
# ============================================================

def test_kr_s6_critical_curve_continuity():
    """
    熱暴走閾値 α_PTC × input = 0.5 の周辺で挙動が連続的に変化。

    各ペアで b、平衡点、T(t=100) を比較し、b<0/b=0/b>0 の 3 区分が
    smooth に推移することを確認。タスク 12 観察 1 の物理的洞察を熱暴走の
    文脈で再確認。
    """
    cases = [
        # (α, input, expected_b_sign)
        (0.5, 1.0, 'zero'),    # critical (Task 11 で検証済み)
        (0.6, 1.0, 'pos'),     # subcritical 超え少し
        (1.0, 0.5, 'zero'),    # critical (Task 13 で検証済み)
        (1.0, 0.6, 'pos'),     # subcritical 超え少し (slow runaway)
    ]
    results = []
    for alpha, inp, expected_b in cases:
        b = alpha * 0.1 * inp - 0.05
        node = TemperatureNode(
            T_env=0.0, T_max=1000.0, alpha_PTC=alpha,
            T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )
        n_steps = 10000  # t=100 単位時間
        for _ in range(n_steps):
            node.update(input_value=inp, dt=0.01)
        results.append((alpha, inp, b, node.temperature))
        # Tripwire #7 (各ケース)
        assert np.isfinite(node.temperature), (
            f"(α={alpha}, input={inp}): T が非有限"
        )

    # b=0 ケース (linear): T(100) = a · 100
    # (0.5, 1.0): a=0.1, T=10
    # (1.0, 0.5): a=0.05, T=5
    assert abs(results[0][3] - 10.0) < 1e-6  # (0.5, 1.0)
    assert abs(results[2][3] - 5.0) < 1e-6   # (1.0, 0.5)

    # b>0 ケース: 解析解と比較
    # (0.6, 1.0): T(100) = 10·(e-1) ≈ 17.18
    expected_06 = 10.0 * (np.exp(1.0) - 1.0)
    assert abs(results[1][3] - expected_06) < 1e-6
    # (1.0, 0.6): a=0.06, b=0.01, T(100) = -6 + 6·exp(1) ≈ 10.31
    expected_10_06 = -6.0 + 6.0 * np.exp(1.0)
    assert abs(results[3][3] - expected_10_06) < 1e-6

    # 連続性: b=0 (critical) → b>0 (slightly supercritical) で T が
    # 滑らかに増加 (熱暴走への遷移)。
    # (α=0.5, input=1) b=0 → (α=0.6, input=1) b=+0.01:
    #   T_critical(100)=10, T_slight_super(100)≈17.18 (1.7倍)
    # 同様に (α=1, input=0.5) b=0 → (α=1, input=0.6) b=+0.01:
    #   T_critical(100)=5,  T_slight_super(100)≈10.31 (2.06倍)
    assert results[1][3] > results[0][3]  # supercritical > critical
    assert results[3][3] > results[2][3]


def test_kr_s6_subcritical_to_supercritical_transition():
    """
    α_PTC=0.5 を中心に input ∈ {0.95, 1.0, 1.05} で subcritical → critical →
    supercritical の遷移を確認 (input>1 は不正のため、α 側を変える)。

    α ∈ {0.49, 0.50, 0.51}, input=1.0 で b ∈ {-0.001, 0, +0.001}。
    """
    n_steps = 1000  # t=10 単位時間 (短時間で安全)
    Ts = []
    for alpha in [0.49, 0.50, 0.51]:
        node = TemperatureNode(
            T_env=0.0, T_max=100.0, alpha_PTC=alpha,
            T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )
        for _ in range(n_steps):
            node.update(input_value=1.0, dt=0.01)
        assert np.isfinite(node.temperature)
        Ts.append(node.temperature)

    # 連続性: 順序 sub < crit < super
    assert Ts[0] < Ts[1] < Ts[2], (
        f"順序違反: {Ts}"
    )
    # critical (α=0.5, b=0): T(10) = 0.1·10 = 1.0
    assert abs(Ts[1] - 1.0) < 1e-6
    # b=+0.001, t=10: 微小な supercritical、T(10) ≈ T_critical で違いは微小
    # 解析: a=0.1, b=0.001, T(t) = -100 + 100·exp(0.001·t)
    # T(10) = 100·(exp(0.01)-1) ≈ 1.005
    expected_super = 100.0 * (np.exp(0.01) - 1.0)
    assert abs(Ts[2] - expected_super) < 1e-6


# ============================================================
# (e) Tripwire #7 (NaN/inf) 回避の robustness 検証
# ============================================================

def test_kr_s6_no_nan_inf_for_designed_t_max():
    """設計通りの t_max で各熱暴走ケースで NaN/inf が発生しない。"""
    cases = [
        # (alpha, input, t_max)
        (0.6, 1.0, 100.0),
        (0.6, 1.0, 500.0),
        (1.0, 1.0, 30.0),
        (1.0, 0.6, 100.0),
        (2.0, 1.0, 10.0),  # 極端な α、b=0.15、τ≈6.67、T(10) = -0.667+0.667·e^1.5
    ]
    for alpha, inp, t_max in cases:
        node = TemperatureNode(
            T_env=0.0, T_max=1e6, alpha_PTC=alpha,
            T_ref=None, T_initial=0.0,
            clip_enabled=False, integrator='rk4',
        )
        n_steps = int(round(t_max / 0.01))
        for _ in range(n_steps):
            node.update(input_value=inp, dt=0.01)
        assert np.isfinite(node.temperature), (
            f"Tripwire #7: (α={alpha}, input={inp}, t={t_max}) で非有限"
        )


# ============================================================
# (f) 物理的観察: clip の deterrence としての機能
# ============================================================

def test_kr_s6_clip_provides_deterrence():
    """
    clip 有効/無効で同じ熱暴走条件 (α=1.0、input=1.0) の挙動比較:
    - clip off: T が指数発散、deterrence 完全失敗
    - clip on: T が T_max=1.0 で停止、physical limit による deterrence
    """
    alpha = 1.0
    n_off = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    n_on = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=alpha, T_initial=0.0,
        clip_enabled=True, integrator='rk4',
    )
    n_steps = 3000  # t=30
    for _ in range(n_steps):
        n_off.update(input_value=1.0, dt=0.01)
        n_on.update(input_value=1.0, dt=0.01)

    # clip off: 指数発散 (T(30) ≈ 6.96)
    assert n_off.temperature > 5.0
    # clip on: T_max=1.0 で停止 (deterrence)
    assert n_on.temperature == 1.0
    # 比率: clip 無効では clip 有効の数倍まで発散
    assert n_off.temperature / n_on.temperature > 5.0
