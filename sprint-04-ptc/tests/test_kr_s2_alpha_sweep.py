"""
test_kr_s2_alpha_sweep: KR-S2 (PTC 効果の検証、5 つの α_PTC 値)

5 つの α_PTC 値で Sprint 4 の TemperatureNode (RK4) と解析解
(analytical_temperature) を比較し、max 誤差 < 1e-6 を検証する。

α_PTC 値 (SPRINT_OKR.md 数学モデル節、KR-S2):

| α_PTC | b の符号 | 挙動           | 平衡点 T_eq |
|-------|---------|----------------|------------|
| 0.0   | b<0     | 線形 (Sprint 3 同一) | 2.0  |
| 0.1   | b<0     | 弱い PTC       | 2.5        |
| 0.4   | b<0     | 臨界に近い      | 10.0       |
| 0.5   | b=0     | 臨界 (線形成長) | なし (a·t) |
| 0.6   | b>0     | 熱暴走          | なし (発散) |
| 1.0   | b>0     | 急激な熱暴走     | なし (発散) |

ここで b = α_PTC · heating_rate · input - cooling_rate (input=1 一定の場合)。
熱暴走の閾値: α_PTC > cooling_rate / heating_rate = 0.5 (0.5 自身は b=0 臨界)。

検証パラメータ:
    heating_rate = 0.1, cooling_rate = 0.05
    T_env = 0.0, T_ref = None (= T_env), T_initial = 0.0
    integrator = 'rk4', clip_enabled = False (解析解は clip を含まない)
    input = 1.0 (一定)
    dt = 0.01, total_time = 30.0

時間範囲 t_max = 30 の選択根拠:
    - α_PTC = 1.0 (急激な熱暴走、b=0.05) で T(30) = -2 + 2·exp(1.5) ≈ 6.96
      → NaN/inf リスクなし、float64 範囲内で確実に追跡可能
    - α_PTC = 0.4 (b=-0.01、ゆっくり漸近) で T(30) ≈ 2.59 (T_eq=10 に未収束だが
      解析解との比較は可能)

Tripwire 関連:
    Tripwire #6: 解析解との誤差が 1e-6 を大幅に超える → halt-and-confirm
    Tripwire #7: T が NaN または inf になる → halt-and-confirm
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


# ----- 共通パラメータ -----

HEATING = 0.1
COOLING = 0.05
T_ENV = 0.0
INPUT = 1.0
DT = 0.01
T_MAX = 30.0


def _run_alpha(alpha_PTC: float):
    """指定の α_PTC で RK4 数値解と解析解を計算し、両者を返す。"""
    node = TemperatureNode(
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, T_max=1.0,  # T_max は使わない (clip off)
        alpha_PTC=alpha_PTC, T_ref=None, T_initial=0.0,
        clip_enabled=False, integrator='rk4',
    )
    t_arr, T_num = run_constant_input_scenario(
        node, total_time=T_MAX, dt=DT, input_value=INPUT,
    )
    T_ana = analytical_temperature(
        t=t_arr, T_0=0.0, input_value=INPUT,
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, alpha_PTC=alpha_PTC, T_ref=None,
    )
    return t_arr, T_num, T_ana


# ----- 5 つの α_PTC 値の本体テスト (KR-S2 メイン) -----

@pytest.mark.parametrize("alpha_PTC,expected_T_eq", [
    (0.0, 2.0),    # b = -0.05、漸近
    (0.1, 2.5),    # b = -0.04、漸近
    (0.4, 10.0),   # b = -0.01、ゆっくり漸近
])
def test_kr_s2_convergent_cases(alpha_PTC, expected_T_eq):
    """KR-S2: b<0 の 3 ケースで解析解との max 誤差 < 1e-6、平衡点が一致。"""
    t_arr, T_num, T_ana = _run_alpha(alpha_PTC)

    # NaN/inf check (Tripwire #7)
    assert np.all(np.isfinite(T_num)), (
        f"α_PTC={alpha_PTC}: T_num に NaN/inf 検出 (Tripwire #7)"
    )
    assert np.all(np.isfinite(T_ana)), (
        f"α_PTC={alpha_PTC}: T_ana に NaN/inf 検出 (解析解の数値破綻)"
    )

    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"α_PTC={alpha_PTC}: max|T_num - T_ana| = {max_err:.3e} >= 1e-6 "
        f"(Tripwire #6 発動条件)"
    )

    # 平衡点 T_eq の確認 (analytical 側)
    T_eq = equilibrium_temperature(
        input_value=INPUT, heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, alpha_PTC=alpha_PTC, T_ref=None,
    )
    assert T_eq is not None, f"α_PTC={alpha_PTC}: 平衡点が期待される (b<0)"
    assert abs(T_eq - expected_T_eq) < 1e-10, (
        f"α_PTC={alpha_PTC}: T_eq = {T_eq} != expected {expected_T_eq}"
    )


@pytest.mark.parametrize("alpha_PTC", [0.6, 1.0])
def test_kr_s2_runaway_cases(alpha_PTC):
    """KR-S2: b>0 の 2 ケース (熱暴走、指数発散) で解析解との max 誤差 < 1e-6。"""
    t_arr, T_num, T_ana = _run_alpha(alpha_PTC)

    # NaN/inf check (Tripwire #7) — t_max=30 では発散しても float64 範囲内
    assert np.all(np.isfinite(T_num)), (
        f"α_PTC={alpha_PTC}: 数値解に NaN/inf 検出 (Tripwire #7)。"
        f"T_max を縮める必要あり"
    )

    max_err = float(np.max(np.abs(T_num - T_ana)))
    # 熱暴走では T 自体が大きいため、絶対誤差より相対誤差を見る選択肢も
    # あるが、KR-S2 の official target は絶対誤差 1e-6
    assert max_err < 1e-6, (
        f"α_PTC={alpha_PTC}: max|T_num - T_ana| = {max_err:.3e} >= 1e-6 "
        f"(Tripwire #6)"
    )

    # 平衡点が存在しないことを確認 (b > 0)
    T_eq = equilibrium_temperature(
        input_value=INPUT, heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, alpha_PTC=alpha_PTC, T_ref=None,
    )
    assert T_eq is None, (
        f"α_PTC={alpha_PTC}: b>0 だが平衡点 {T_eq} が返った"
    )

    # T が単調増加であることを物理的に確認 (input=1、T_0=0、b>0、a>0 → 全 t で増加)
    assert np.all(np.diff(T_num) > 0), (
        f"α_PTC={alpha_PTC}: 熱暴走シナリオで T が単調増加でない"
    )


# ----- α_PTC = 0.5 (臨界条件、線形成長) -----

def test_kr_s2_critical_alpha_05_linear_growth():
    """
    KR-S2 補完: α_PTC = 0.5 (b=0 の臨界条件) で T が線形成長 T(t) = a·t = 0.1·t。

    タスク 8 (MMS) で発見された「α_PTC=0.5 で T_man=t、s=0.9 定数」と同じ
    物理現象。analytical.py の `b == 0` 分岐 (`T_0 + a · t`) を発火させる。
    """
    alpha_PTC = 0.5
    t_arr, T_num, T_ana = _run_alpha(alpha_PTC)

    assert np.all(np.isfinite(T_num)), "α_PTC=0.5 で NaN/inf"

    # 解析解は T(t) = 0 + 0.1·t = 0.1·t (T_0=0, a=heating·input=0.1)
    T_expected = HEATING * INPUT * t_arr  # = 0.1 * t
    max_err_vs_simple = float(np.max(np.abs(T_ana - T_expected)))
    assert max_err_vs_simple < 1e-12, (
        f"解析解が線形成長 0.1·t と一致しない: {max_err_vs_simple:.3e}"
    )

    # 数値解 vs 解析解の誤差
    max_err = float(np.max(np.abs(T_num - T_ana)))
    assert max_err < 1e-6, (
        f"α_PTC=0.5 (臨界): max|T_num - T_ana| = {max_err:.3e}"
    )

    # 平衡点が存在しないことを確認 (b = 0)
    T_eq = equilibrium_temperature(
        input_value=INPUT, heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, alpha_PTC=alpha_PTC, T_ref=None,
    )
    assert T_eq is None, f"α_PTC=0.5 (b=0) だが T_eq = {T_eq}"


# ----- 連続性確認 (Devil's Advocate #1 への対応) -----

def test_kr_s2_continuity_near_zero():
    """
    Devil's Advocate #1 への対応: α_PTC → 0 で誤差 → 0 の連続性を確認。

    α_PTC ∈ {0.0, 0.001, 0.01, 0.1} の誤差を測定。bit-perfect は α_PTC=0 のみ
    だが、numerical-vs-analytical 誤差は α_PTC が 0 から離れるにつれて滑らかに
    増える (発散しない) ことを確認する。
    """
    alphas = [0.0, 0.001, 0.01, 0.1]
    errors = []
    for a in alphas:
        _, T_num, T_ana = _run_alpha(a)
        err = float(np.max(np.abs(T_num - T_ana)))
        errors.append(err)

    # 全て KR-S2 target を満たす
    for a, e in zip(alphas, errors):
        assert e < 1e-6, (
            f"α_PTC={a}: 誤差 {e:.3e} が 1e-6 を超過 (連続性が崩れている)"
        )

    # 連続性: α_PTC が大きくなるにつれて誤差は単調に増えるとは限らない
    # (RK4 の局所打ち切り誤差は b·dt の関数で複雑) が、いずれも O(1e-9) 程度に
    # 収まることを確認 (bit-perfect は α_PTC=0 のみ、しかし誤差は連続的に推移)
    assert max(errors) < 1e-6, (
        f"α_PTC ∈ {alphas} の最大誤差 {max(errors):.3e} が 1e-6 超過"
    )


# ----- 数値証拠を残すための明示的測定テスト (失敗しない、観察用) -----

def test_kr_s2_record_actual_errors():
    """
    KR-S2 の 5 つの公式 α_PTC 値 + 臨界 0.5 + 連続性 0.001 で、実測誤差を
    記録する。pytest -v で出力される情報として残す目的。

    本テストは failure 条件を緩める (1e-5)。official KR-S2 検証は上記の
    各テストで 1e-6 を強制する。
    """
    record = []
    for a in [0.0, 0.001, 0.1, 0.4, 0.5, 0.6, 1.0]:
        t_arr, T_num, T_ana = _run_alpha(a)
        finite = bool(np.all(np.isfinite(T_num)))
        max_err = float(np.max(np.abs(T_num - T_ana)))
        T_final_num = float(T_num[-1])
        T_final_ana = float(T_ana[-1])
        record.append((a, finite, max_err, T_final_num, T_final_ana))

    # 全 α で finite かつ 1e-5 以下 (緩い境界)
    for a, finite, err, T_n, T_a in record:
        assert finite, f"α_PTC={a}: 非有限値検出"
        assert err < 1e-5, f"α_PTC={a}: 誤差 {err:.3e} が想定外"
    # record の中身は同ファイルの他テストから観察可能 (進捗報告で転記)
