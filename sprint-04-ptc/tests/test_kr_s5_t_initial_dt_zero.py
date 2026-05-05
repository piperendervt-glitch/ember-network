"""
test_kr_s5_t_initial_dt_zero: KR-S5 (T_initial と dt=0 の検証)

Sprint 4 で新規導入した 2 つのパラメータ機能を検証する:

(a) T_initial < T_env からの復帰 (PRL-011 対応)
    Sprint 3 では T_initial = T_env で固定 (T が下から T_env に近づくことが
    できなかった、PRL-011)。Sprint 4 では T_initial を独立に指定可能。
    Newton 冷却則の対称性により、T < T_env でも T → T_env (上昇方向で
    漸近、不変量 2-B、不変量 5-A)。

(b) dt=0 の no-op 処理 (PRL-010 対応)
    ChatGPT I Test 8 が提案。dt=0 で update を呼んでも状態が不変、累積
    効果なし。これにより「現在状態の参照」が dt=0 でも安全に行える。

(c) T_initial > T_max の境界ケース (Sprint 4 で新規許容される構成)
    clip 有効 (init 時には clip しないが、最初の update で T <= T_max に
    制限) と clip 無効 (T_initial > T_max で進化) の両方を検証。

(d) T_initial と T_ref の組み合わせ (Sprint 4 新規)
    T_initial != T_ref で R(T_initial) != R_0、PTC 効果が初期から非自明
    に効く。例: T_initial = T_max、T_ref = T_env で max PTC 効果から開始。

物理的観察 (タスク 12 で発見された α_PTC × input 臨界曲線が
T_initial < T_env でも成立するか確認):
    α_PTC=1.0、input=0.5 では b=0、dT/dt = a = 0.05 (一定)。
    T_initial=-1.0 から T が線形に増加し、T_env=0 を t=20 で通過、
    その後も同じ傾きで成長を継続。これは α × input 臨界曲線が初期
    条件に依らず b=0 を保つことの demonstration。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

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
# (a) T_initial < T_env からの復帰 (PRL-011 対応)
# ============================================================

def test_kr_s5_recovery_input_zero_pure_cooling():
    """T_initial=-1.0、input=0、α_PTC=0 で T → T_env=0 (純冷却の対称性)。

    解析解: T(t) = T_initial · exp(-c·t) (T_env=0 のとき、α_PTC=0、input=0)
    """
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.0,
        T_initial=-1.0, clip_enabled=False, integrator='rk4',
    )
    assert node.temperature == -1.0
    t_arr, T = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=0.0,
    )
    # 解析解 T(t) = -1·exp(-0.05·t)
    T_ana = -1.0 * np.exp(-0.05 * t_arr)
    max_err = float(np.max(np.abs(T - T_ana)))
    assert max_err < 1e-6, f"recovery 解析解一致違反: {max_err:.3e}"
    # 不変量 2-B: T → T_env (= 0) 漸近
    assert node.temperature > -1.0  # 上昇している
    assert node.temperature < 0.0   # しかし T_env を超えない
    assert abs(node.temperature - 0.0) < 1e-2  # 100 単位時間 = 5τ 後


def test_kr_s5_recovery_input_one_with_alpha_zero():
    """T_initial=-1.0、input=1.0、α_PTC=0 で T → T_eq=2.0 (Newton + 加熱)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.0,
        T_initial=-1.0, clip_enabled=False, integrator='rk4',
    )
    t_arr, T = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=1.0,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=-1.0, input_value=1.0,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=0.0,
    )
    max_err = float(np.max(np.abs(T - T_ana)))
    assert max_err < 1e-6, f"recovery + heating 違反: {max_err:.3e}"
    # T → T_eq=2.0 (Sprint 3 と同じ)
    # τ = 1/cooling = 20、t=100 = 5τ で T_eq の 99.33% に到達 (残り ~0.0135)
    T_eq = equilibrium_temperature(input_value=1.0, alpha_PTC=0.0)
    assert abs(T_eq - 2.0) < 1e-12
    # T(100) = T_eq + (T_0-T_eq)·exp(-5) = 2 - 3·exp(-5)
    expected_at_5tau = 2.0 - 3.0 * np.exp(-5.0)
    assert abs(T[-1] - expected_at_5tau) < 1e-6  # 解析解との厳密一致
    assert abs(T[-1] - T_eq) < 0.05              # 5τ 後の漸近誤差 (~0.0135)


def test_kr_s5_invariant_2b_asymptotic_recovery_strict():
    """不変量 2-B: T_initial < T_env、input=0 で全時刻 T <= T_env (strict)。"""
    # PRL-004: 漸近のみ、厳密一致しない、しかし T_env を超えない
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_initial=-2.0, clip_enabled=False, integrator='rk4',
    )
    _, T = run_constant_input_scenario(
        node, total_time=200.0, dt=0.01, input_value=0.0,
    )
    # 全時刻で T <= T_env (= 0、PRL-004 で「下から漸近」)
    assert np.all(T <= 0.0 + 1e-15), (
        f"asymptotic 違反: max(T)={float(np.max(T)):.3e}"
    )
    # 単調増加 (T が T_env に向かって上昇)
    assert np.all(np.diff(T) >= -1e-12)


def test_kr_s5_invariant_5a_heat_flow_below_t_env():
    """不変量 5-A: T < T_env、input=0 のとき dT/dt > 0 (Newton 冷却の対称性)。"""
    for T_init in [-0.5, -1.0, -2.0]:
        node = TemperatureNode(
            T_env=0.0, T_max=10.0, alpha_PTC=0.3,
            T_initial=T_init, clip_enabled=False, integrator='rk4',
        )
        T_before = node.temperature
        node.update(input_value=0.0, dt=0.01)
        T_after = node.temperature
        assert T_after > T_before, (
            f"T_initial={T_init}: T < T_env で dT/dt <= 0: "
            f"{T_before} → {T_after}"
        )


def test_kr_s5_recovery_with_ptc_alpha_one_critical():
    """
    物理的観察: α_PTC=1.0、input=0.5、T_initial=-1.0 で b=0 の臨界。
    dT/dt = a = 0.05 (一定)、T が線形成長 -1.0 → 0 → +1 を経由する。

    α_PTC × input = 0.5 (= cooling/heating) 臨界曲線 (タスク 12) が
    T_initial < T_env の場合にも適用されることを確認。
    """
    alpha = 1.0
    inp = 0.5
    # b = α·h·input - c = 1·0.1·0.5 - 0.05 = 0
    b = alpha * 0.1 * inp - 0.05
    assert b == 0.0  # 臨界 (literal 0、IEEE 754 で exact)
    # a = h·input·(1 - α·T_ref) + c·T_env = 0.1·0.5·1 + 0 = 0.05
    a = 0.1 * inp * (1.0 - alpha * 0.0) + 0.05 * 0.0
    assert abs(a - 0.05) < 1e-15

    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=100.0, alpha_PTC=alpha,
        T_ref=None, T_initial=-1.0,
        clip_enabled=False, integrator='rk4',
    )
    assert node.temperature == -1.0

    t_arr, T = run_constant_input_scenario(
        node, total_time=40.0, dt=0.01, input_value=inp,
    )
    # 線形成長 T(t) = T_initial + a·t = -1.0 + 0.05·t
    T_expected = -1.0 + 0.05 * t_arr
    max_err = float(np.max(np.abs(T - T_expected)))
    assert max_err < 1e-6, (
        f"linear growth 違反: max err = {max_err:.3e}"
    )
    # T(20) = 0.0 (T_env を通過する瞬間)
    idx_20 = int(round(20.0 / 0.01))
    assert abs(T[idx_20] - 0.0) < 1e-6, (
        f"T(20) != 0: T[{idx_20}]={T[idx_20]}"
    )
    # T(40) = +1.0 (T_env を通過後も同じ傾き)
    assert abs(T[-1] - 1.0) < 1e-6


# ============================================================
# (b) dt=0 の no-op 処理 (PRL-010 対応)
# ============================================================

def test_kr_s5_dt_zero_state_unchanged():
    """dt=0 で update を呼んでも状態が変わらない (ChatGPT I Test 8)。"""
    node = TemperatureNode(alpha_PTC=0.3, integrator='rk4')
    # まず通常の update で T を進化させる
    node.update(input_value=1.0, dt=0.1)
    T_before_zero = node.temperature
    assert T_before_zero != node.T_env  # T が変化した

    # dt=0 で複数回 update
    for _ in range(10):
        node.update(input_value=1.0, dt=0.0)
        assert node.temperature == T_before_zero, (
            f"dt=0 で T が変化: {T_before_zero!r} → {node.temperature!r}"
        )


def test_kr_s5_dt_zero_with_various_input_values():
    """dt=0 では input_value が何でも T が変化しない (input は無視される)。"""
    node = TemperatureNode(alpha_PTC=0.5, T_initial=0.5, integrator='rk4')
    T_before = node.temperature
    for inp in [0.0, 0.1, 0.5, 0.9, 1.0]:
        node.update(input_value=inp, dt=0.0)
        assert node.temperature == T_before, (
            f"dt=0, input={inp} で T が変化: "
            f"{T_before!r} → {node.temperature!r}"
        )


def test_kr_s5_dt_zero_mixed_with_nonzero():
    """dt=0 と dt>0 を混在させても、dt>0 の効果のみ累積。"""
    node_mixed = TemperatureNode(alpha_PTC=0.3, integrator='rk4')
    node_pure = TemperatureNode(alpha_PTC=0.3, integrator='rk4')
    # mixed: dt=0 を間に挟む
    for _ in range(10):
        node_mixed.update(input_value=1.0, dt=0.0)  # no-op
        node_mixed.update(input_value=1.0, dt=0.01)
        node_mixed.update(input_value=1.0, dt=0.0)  # no-op
    # pure: dt>0 のみ 10 回
    for _ in range(10):
        node_pure.update(input_value=1.0, dt=0.01)
    # bit-perfect 一致を期待 (dt=0 は文字通り no-op)
    assert node_mixed.temperature == node_pure.temperature, (
        f"mixed と pure で挙動差: "
        f"mixed={node_mixed.temperature!r}, pure={node_pure.temperature!r}"
    )


def test_kr_s5_dt_zero_negative_dt_still_raises():
    """dt=0 が許容されても、dt<0 は依然として ValueError。"""
    node = TemperatureNode()
    # dt<0 はエラー (Sprint 4 では dt=0 のみが no-op、dt<0 は不正)
    with pytest.raises(ValueError, match="non-negative"):
        node.update(input_value=1.0, dt=-0.01)
    # dt=0 は no-op (エラーにならない)
    node.update(input_value=1.0, dt=0.0)


def test_kr_s5_dt_zero_invalid_input_still_raises():
    """dt=0 でも input_value のバリデーションは先に実施される。"""
    node = TemperatureNode()
    # bool は dt=0 でも reject
    with pytest.raises(ValueError, match="not bool"):
        node.update(input_value=True, dt=0.0)
    # 範囲外は dt=0 でも reject
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        node.update(input_value=1.5, dt=0.0)


# ============================================================
# (c) T_initial > T_max の境界ケース
# ============================================================

def test_kr_s5_t_initial_above_t_max_with_clip():
    """T_initial > T_max、clip 有効: 初期は T_initial だが update 後に clip。"""
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.3,
        T_initial=2.0,  # T_max=1.0 を超える
        clip_enabled=True, integrator='rk4',
    )
    # 初期状態は T_initial=2.0 (constructor は clip しない)
    assert node.temperature == 2.0
    # 1 step 進めると clip が発動
    node.update(input_value=0.0, dt=0.01)
    # clip により T <= T_max
    assert node.temperature <= 1.0 + 1e-15
    # input=0、T_initial=2.0 > T_env=0 なので冷却して T が下がる
    # しかし clip により上限 T_max=1.0 に張り付かない (T が T_max 以下なので
    # 上限 clip は発動しない、Newton 冷却で T が下がるだけ)
    # 結果: T < 2.0 (冷却で下がった) かつ T <= T_max=1.0 (clip で制限)
    # 1 step (dt=0.01) なので T = 2.0 - 0.05·(2.0)·0.01 ≈ 1.999、clip で 1.0 に
    assert node.temperature == 1.0  # 上限 clip


def test_kr_s5_t_initial_above_t_max_no_clip():
    """T_initial > T_max、clip 無効: T が制限されず、Newton 冷却で漸近。"""
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.0,
        T_initial=2.0,
        clip_enabled=False, integrator='rk4',
    )
    assert node.temperature == 2.0
    # input=0、α_PTC=0 で T → T_env 漸近 (T_max は clip がなければ意味なし)
    _, T = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=0.0,
    )
    # T(t) = 2.0 · exp(-0.05·t)
    T_ana = 2.0 * np.exp(-0.05 * np.arange(len(T)) * 0.01)
    max_err = float(np.max(np.abs(T - T_ana)))
    assert max_err < 1e-6
    # T 値の一部は T_max を超える (clip 無効のため)
    assert np.any(T > 1.0)
    # しかし最終的に T_env=0 に漸近 (5τ 後の T = 2·exp(-5) ≈ 0.0135)
    assert abs(T[-1] - 2.0 * np.exp(-5.0)) < 1e-6  # 解析解と厳密一致
    assert abs(T[-1]) < 0.02                        # 漸近の進行確認


def test_kr_s5_t_initial_above_t_max_clip_with_heating():
    """T_initial > T_max、clip 有効、input=1 で T が T_max に張り付く。"""
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.3,
        T_initial=2.0,
        clip_enabled=True, integrator='rk4',
    )
    # input=1 で加熱、PTC でさらに加熱、しかし clip で T_max 上限
    for _ in range(100):
        node.update(input_value=1.0, dt=0.01)
        assert node.temperature <= 1.0 + 1e-15
    # 最終的に T_max に張り付く (clip により)
    assert abs(node.temperature - 1.0) < 1e-12


# ============================================================
# (d) T_initial と T_ref の組み合わせ
# ============================================================

def test_kr_s5_t_initial_eq_t_max_with_t_ref_t_env():
    """T_initial=T_max、T_ref=T_env で初期 R_factor が最大 (PTC max heating)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_ref=0.0,        # = T_env
        T_initial=10.0,   # = T_max
        clip_enabled=False,
    )
    # R_factor = 1 + 0.3·(10 - 0) = 4.0
    assert abs(node.resistance_ratio - 4.0) < 1e-15


def test_kr_s5_t_initial_eq_t_env_with_t_ref_t_max():
    """T_initial=T_env、T_ref=T_max で初期 R_factor が最小 (heating 抑制)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_ref=10.0,        # = T_max
        T_initial=0.0,     # = T_env
        clip_enabled=False,
    )
    # R_factor = 1 + 0.3·(0 - 10) = -2.0 (負の R、unphysical だが線形モデル)
    assert abs(node.resistance_ratio - (-2.0)) < 1e-15


def test_kr_s5_t_ref_independent_of_t_initial():
    """T_ref と T_initial が独立に設定可能、R(T_ref) = R_0 が常に成立。"""
    for T_init, T_ref in [(0.0, 5.0), (5.0, 0.0), (-2.0, 3.0), (10.0, 10.0)]:
        node = TemperatureNode(
            T_env=-10.0, T_max=20.0, alpha_PTC=0.5,
            T_ref=T_ref, T_initial=T_init,
            clip_enabled=False,
        )
        assert node.temperature == T_init
        assert node.T_ref == T_ref
        # R(T_initial) = 1 + α·(T_init - T_ref)
        expected_R = 1.0 + 0.5 * (T_init - T_ref)
        assert abs(node.resistance_ratio - expected_R) < 1e-15
        # T_init = T_ref のときのみ R = 1
        if T_init == T_ref:
            assert node.resistance_ratio == 1.0


def test_kr_s5_t_initial_t_ref_evolution_consistent_with_analytical():
    """T_initial != T_ref で動的進化が解析解と一致 (PTC 効果が初期から効く)。"""
    # T_initial=2.0, T_ref=0.0, α=0.3, input=1
    # 解析解の a, b:
    #   a = h·input·(1 - α·T_ref) + c·T_env = 0.1·1·1 + 0 = 0.1
    #   b = α·h·input - c = 0.3·0.1·1 - 0.05 = -0.02
    #   T_eq = -a/b = 0.1/0.02 = 5.0
    node = TemperatureNode(
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, T_max=100.0, alpha_PTC=0.3,
        T_ref=0.0, T_initial=2.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T = run_constant_input_scenario(
        node, total_time=50.0, dt=0.01, input_value=1.0,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=2.0, input_value=1.0,
        heating_rate=0.1, cooling_rate=0.05,
        T_env=0.0, alpha_PTC=0.3, T_ref=0.0,
    )
    max_err = float(np.max(np.abs(T - T_ana)))
    assert max_err < 1e-6, f"T_initial=2.0, T_ref=0 evolution: {max_err:.3e}"


def test_kr_s5_reset_returns_to_t_initial_not_t_env():
    """reset() は T を T_initial にリセット (Sprint 3 では T_env、Sprint 4 で変更)。"""
    T_init = 0.7
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.3,
        T_initial=T_init, clip_enabled=False,
    )
    assert node.temperature == T_init

    # 進化させる
    node.update(input_value=1.0, dt=0.5)
    assert node.temperature != T_init

    # reset
    node.reset()
    assert node.temperature == T_init


def test_kr_s5_reset_with_t_initial_below_t_env():
    """reset() で T_initial < T_env の状態に戻れる (PRL-011 対処)。"""
    node = TemperatureNode(
        T_env=0.0, T_max=10.0, alpha_PTC=0.3,
        T_initial=-1.0, clip_enabled=False,
    )
    assert node.temperature == -1.0
    # 進化
    node.update(input_value=1.0, dt=10.0)
    assert node.temperature > -1.0
    # reset で T_initial=-1.0 に戻る (Sprint 3 では T_env=0 に戻ってしまう)
    node.reset()
    assert node.temperature == -1.0


# ============================================================
# Sentinel: KR-S5 が KR-S1〜S4 と整合
# ============================================================

def test_kr_s5_consistency_t_initial_eq_t_env_default():
    """T_initial=None (デフォルト = T_env) で Sprint 3 互換挙動。"""
    # Sprint 3 の挙動を Sprint 4 で再現
    node = TemperatureNode(
        T_env=0.0, T_max=1.0, alpha_PTC=0.0,  # α_PTC=0 で Sprint 3 同形
        T_initial=None,  # = T_env
        clip_enabled=False, integrator='rk4',
    )
    assert node.temperature == 0.0
    # τ=20 のため、漸近確認には 5τ=100 単位時間が必要
    _, T = run_constant_input_scenario(
        node, total_time=100.0, dt=0.01, input_value=1.0,
    )
    # 不変量 2 (Sprint 3 と同じ): T >= T_env
    assert np.all(T >= 0.0 - 1e-15)
    # T → T_eq=2.0 漸近 (t=100=5τ で T = 2·(1-exp(-5)) ≈ 1.9865)
    expected_at_5tau = 2.0 * (1.0 - np.exp(-5.0))
    assert abs(T[-1] - expected_at_5tau) < 1e-6  # 解析解と厳密一致
    assert abs(T[-1] - 2.0) < 0.02                # 漸近の進行確認
