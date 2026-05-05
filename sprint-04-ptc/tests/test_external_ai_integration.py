"""
test_external_ai_integration: 外部 AI (ChatGPT, Grok) の独立提案テスト

Rule 10.5 (別 AI による独立テストケース作成) に基づき、Sprint 4 用に
Robosheep が ChatGPT と Grok にそれぞれ 3 段階 (Stage I/II/III) で独立に
依頼したテスト群から、Claude Code の既存 147 テストと**重複しない観点**
かつ**Sprint 4 の仕様と整合する**もののみを採用した統合テスト。

採用基準:
- 既存テストにない物理的観点 (例: T_env > 0、T_ref ≠ T_env ≠ T_initial)
- Sprint 4 の仕様 (input ∈ [0,1]、dt ≥ 0、temperature 読取専用) と整合
- 数学的に正しい (元の外部 AI 提案には収束時間不足の数値設定が複数あり、
  本ファイルでは収束を保証する parameter に調整済み)

採用しなかったカテゴリ:
- 既存テストとの重複 (約 30 件)
- 仕様違反の test (input <0 や >1、dt<0、temperature setter 等、約 5 件)
- 収束時間不足等、外部 AI 提案の数値が成立しない test → adapt or skip
- chatgpt_stage_III の最終 test は file が途中で切れており skip (1 件)
- T_initial > T_max with clip_enabled=True 時に「constructor が clip する」
  という解釈の test (grok_stage_I::test_initial_above_tmax_with_clip_enabled)
  は **設計上 constructor は clip しない** という Sprint 4 の明示的選択
  (test_kr_s5_t_initial_above_t_max_with_clip 参照) と矛盾するため不採用。

タスク 16 の Devil's Advocate #1 (T_env=0 への暗黙の依存性) への対処:
  本 file の Test 4, 8 で T_env > 0 シナリオを導入し、Sprint 4 の test
  カバレッジに非ゼロ環境温度を追加する。これにより、Mutation Testing
  で survived だった analytical.py mutmut_18/19/21 (cooling_rate * T_env
  の符号変異 3 件) のうち少なくとも一部が将来的に kill される設計。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_SPRINT4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode  # noqa: E402


# =============================================================================
# Stage I: 前提を共有しない独立テスト (最も独立した視点)
# =============================================================================

def test_chatgpt_I_rhs_matches_model_single_step_linear_case():
    """ChatGPT Stage I 提案: alpha=0 で線形 RHS と単一ステップが一致。

    既存テストは alpha=0 で Sprint 3 と bit-perfect 一致を確認するが、
    閉形式の線形 RHS を直接検証する観点は本テストで初めて導入。

    観点: dT/dt = h·input - c·(T-T_env) を Euler 単一ステップで検証。
    """
    node = TemperatureNode(
        heating_rate=0.4,
        cooling_rate=0.1,
        T_env=0.2,
        T_initial=0.5,
        alpha_PTC=0.0,
        integrator='euler',  # 単一 Euler ステップで RHS を直接観察
        clip_enabled=False,
    )
    T0 = node.temperature
    dt = 1e-4
    input_value = 0.7

    node.update(input_value=input_value, dt=dt)
    T1 = node.temperature

    rhs = 0.4 * input_value - 0.1 * (T0 - 0.2)
    expected = T0 + rhs * dt
    assert T1 == pytest.approx(expected, rel=1e-3)


def test_chatgpt_I_dt_splitting_consistency():
    """ChatGPT Stage I 提案: dt 分割しても結果が概ね一致 (RK4 大ステップ安定性)。

    既存テストには分割粒度を変えた一致性検証がない。RK4 の大 dt での
    安定性を qualitative に確認する。
    """
    node_big = TemperatureNode(T_env=0.0, T_initial=0.3, integrator='rk4')
    node_small = TemperatureNode(T_env=0.0, T_initial=0.3, integrator='rk4')

    node_big.update(1.0, 1.0)
    for _ in range(100):
        node_small.update(1.0, 0.01)

    assert node_small.temperature == pytest.approx(node_big.temperature, rel=1e-2)


def test_chatgpt_I_alpha_negative_zero_rfactor_no_heating():
    """ChatGPT Stage I 提案 (改訂): 強い負 α で R_factor=0 となり加熱停止。

    元提案は alpha=-1.0, T_initial=1.0, cooling=0 で「加熱がほぼ止まる」
    を検証。R_factor = 1 + (-1)·(1-0) = 0 で heating 項がゼロ、cooling
    もゼロのため T 不変。NTC 的境界の最終形を確認。

    既存テストには負 α を扱うものがない。観点: R_factor の符号反転境界。
    """
    node = TemperatureNode(
        T_env=0.0,
        T_initial=1.0,
        T_max=2.0,  # T_initial=1.0 < T_max を確保
        heating_rate=1.0,
        cooling_rate=0.0,
        alpha_PTC=-1.0,
        T_ref=0.0,
        clip_enabled=False,
    )
    # R_factor(T=1) = 1 + (-1)·(1-0) = 0 → heating 項 = 0
    # cooling = 0 → cooling 項 = 0
    # dT/dt = 0 → T 不変
    T_before = node.temperature
    node.update(1.0, 0.1)
    assert node.temperature == pytest.approx(T_before, abs=1e-12)


def test_grok_I_nonzero_tenv_physical_ambient():
    """Grok Stage I 提案 (収束 parameter 調整済み): 非ゼロ T_env への冷却収束。

    タスク 16 Devil's Advocate #1 (T_env=0 暗黙依存) への直接対処。
    元提案 (cooling=0.05、total=30) は τ=20 で 1.5τ しか経過せず収束
    不足だったため、cooling を 0.5 に増強し total=20 (10τ) で十分収束
    させる。

    観点: T_env=25 (非ゼロ環境温度) で系が確実に T_env に収束する。
    既存 KR-S2/4/5 は全て T_env=0 のため、本テストで T_env > 0 を導入。
    """
    T_env = 25.0
    T_initial = 30.0
    node = TemperatureNode(
        heating_rate=0.1,
        cooling_rate=0.5,  # τ=2、収束を確保
        T_env=T_env,
        T_max=50.0,  # T_max > T_env 必須、余裕を持たせる
        T_initial=T_initial,
        alpha_PTC=0.0,
        clip_enabled=False,
    )
    dt = 0.05
    n_steps = 400  # total = 20 = 10τ → 収束保証
    for _ in range(n_steps):
        node.update(0.0, dt)  # pure cooling

    # T(t) = T_env + (T_init - T_env)·exp(-c·t) → exp(-10) ≈ 4.5e-5
    expected_residual = (T_initial - T_env) * np.exp(-0.5 * 20.0)
    assert node.temperature == pytest.approx(T_env + expected_residual, abs=1e-3)
    assert abs(node.temperature - T_env) < 0.01


def test_grok_I_tref_different_from_tenv_and_initial():
    """Grok Stage I 提案 (収束 parameter 調整済み): T_ref ≠ T_env ≠ T_initial の独立性。

    元提案 (heating=0.1, cooling=0.05, alpha=0.4) では b=-0.01、τ=100、
    20 time unit では 0.2τ しか経過しない。heating と cooling を増強し
    τ を短く再設計、解析的な定常解を確実に検証する。

    観点: T_ref ≠ T_env かつ T_ref ≠ T_initial の独立性 (R_factor の
    T_ref 中心化が正しく実装されているか)。既存テストには T_ref を独立
    に動かす観点が乏しい。
    """
    heating_rate = 0.5
    cooling_rate = 0.5
    alpha_PTC = 0.4
    T_ref = 0.5
    T_env = 0.0
    T_initial = 0.2
    input_val = 1.0

    node = TemperatureNode(
        heating_rate=heating_rate,
        cooling_rate=cooling_rate,
        T_env=T_env,
        T_max=10.0,
        alpha_PTC=alpha_PTC,
        T_ref=T_ref,
        T_initial=T_initial,
        clip_enabled=False,
    )
    dt = 0.01
    n_steps = 3000  # total = 30 = 10τ (τ ≈ 3.3)
    for _ in range(n_steps):
        node.update(input_val, dt)

    # 定常解 (dT/dt = 0):
    # k(1 - α·T_ref) + c·T_env = (c - kα)·T_ss
    # T_ss = [k(1-α·T_ref) + c·T_env] / (c - kα)
    k = heating_rate * input_val
    numerator = k * (1.0 - alpha_PTC * T_ref) + cooling_rate * T_env
    denom = cooling_rate - k * alpha_PTC
    T_ss = numerator / denom
    assert node.temperature == pytest.approx(T_ss, abs=1e-3)


def test_grok_I_dynamic_input_switching_ptc_clipping():
    """Grok Stage I 提案: 動的 input 切替 (1→0) と PTC + clip の組合せ。

    既存テストは input が定数 (KR-S6) または callable (KR-S4 fractional)
    だが、「heating 飽和 → power off → 冷却」の動的シナリオは未検証。
    Phase 1 で T_max クリップ後、Phase 2 で確実に冷却することを確認。

    観点: clip 飽和状態からの開放後の cooling pass-through。
    """
    node = TemperatureNode(
        heating_rate=0.5,
        cooling_rate=0.1,
        T_env=0.0,
        T_max=0.8,
        alpha_PTC=0.6,
        T_initial=0.0,
        clip_enabled=True,
    )
    # Phase 1: 強加熱 → T_max にクリップ
    for _ in range(200):
        node.update(1.0, 0.02)
    assert node.temperature == pytest.approx(0.8, abs=1e-9)
    assert node.weight == pytest.approx(1.0, abs=1e-9)

    # Phase 2: 突然 power off → 冷却
    for _ in range(300):
        node.update(0.0, 0.02)
    # 冷却で T が T_max 以下、weight も 1 未満に降下
    assert node.temperature < 0.8 - 0.1
    assert node.weight < 0.9


# =============================================================================
# Stage II: 前提を伝えるが具体的テストは共有しない (文脈共有)
# =============================================================================

def test_grok_II_steady_state_with_ptc_nonzero_tref():
    """Grok Stage II 提案 (収束 parameter 調整済み): PTC + 非ゼロ T_ref 定常状態。

    元提案 (heating=0.1, cooling=0.05, alpha=0.3, T_ref=0.2) では τ=50、
    60 time unit は 1.2τ で収束不足。heating/cooling を増強し τ を短縮。

    観点: T_ref ≠ 0 が PTC 定常解に与える影響。既存 MMS test は
    T_ref=T_env=0 のみなので、T_ref ≠ T_env の解析解検証は本テストで初。
    """
    heating_rate = 0.2
    cooling_rate = 0.5
    alpha = 0.3
    input_val = 1.0
    T_ref = 0.2
    T_env = 0.0

    node = TemperatureNode(
        heating_rate=heating_rate,
        cooling_rate=cooling_rate,
        T_env=T_env,
        T_max=10.0,
        alpha_PTC=alpha,
        T_ref=T_ref,
        T_initial=T_env,  # default
        clip_enabled=False,
    )
    dt = 0.01
    n_steps = 3000  # total = 30 ≈ 13τ
    for _ in range(n_steps):
        node.update(input_val, dt)

    k = heating_rate * input_val
    numerator = k * (1.0 - alpha * T_ref) + cooling_rate * T_env
    denominator = cooling_rate - k * alpha
    T_ss_expected = numerator / denominator
    assert node.temperature == pytest.approx(T_ss_expected, abs=5e-3)


def test_grok_II_weight_property_nonzero_tenv():
    """Grok Stage II 提案: T_env=10, T_max=30 での weight 計算正当性。

    元提案を踏襲。T_env > 0 + T_max > T_env で weight = (T-T_env)/(T_max-T_env)
    が正しく計算され、T > T_max でも (clip_enabled=False のとき) weight
    は線形に伸びることを検証。

    観点: T_env > 0 のスケールでの weight @property の正確性 (タスク 16
    Devil's Advocate #1 への直接対処)。
    """
    T_env = 10.0
    T_max = 30.0

    # ケース A: T_initial が中点 → weight=0.5
    node_inside = TemperatureNode(
        T_env=T_env, T_max=T_max, T_initial=20.0, clip_enabled=False,
    )
    assert node_inside.weight == pytest.approx(0.5, abs=1e-12)

    # ケース B: T_initial > T_max かつ clip_enabled=False → weight > 1.0
    node_above = TemperatureNode(
        T_env=T_env, T_max=T_max, T_initial=45.0, clip_enabled=False,
    )
    assert node_above.weight == pytest.approx((45.0 - 10.0) / 20.0, abs=1e-12)
    assert node_above.weight > 1.0


# =============================================================================
# Stage III: 既存テストを完全共有 (補完的視点)
# =============================================================================

def test_grok_III_thermal_runaway_boundary_alpha_ptc():
    """Grok Stage III 提案 (parameter 調整済み): α_PTC 臨界境界 3 ケース。

    既存 KR-S6 は alpha=0.6 / 1.0 の固定値 runaway を検証するが、
    α_crit = c / (h·input) を中心とした sub/exact/super-critical の
    系統的検証は未導入。元提案の time が短すぎたため、各 case が
    十分発散/収束する time に伸ばした。

    観点: 臨界曲線 b = α·h·input - c = 0 を直接挟む 3 ケースの定性挙動。
    """
    heating_rate = 0.2
    cooling_rate = 0.05
    input_val = 0.8
    alpha_crit = cooling_rate / (heating_rate * input_val)  # 0.3125

    dt = 0.1
    n_steps = 2000  # total = 200

    # Case 1: 0.5×α_crit (sub-critical) → 確実に有限 T_ss に収束
    node_stable = TemperatureNode(
        heating_rate=heating_rate, cooling_rate=cooling_rate,
        T_env=0.0, T_max=1000.0, T_ref=0.0,
        alpha_PTC=0.5 * alpha_crit, T_initial=0.1, clip_enabled=False,
    )
    for _ in range(n_steps):
        node_stable.update(input_val, dt)
    # b = 0.5*0.3125*0.16 - 0.05 = 0.025 - 0.05 = -0.025 < 0 → 収束
    # T_ss = 0.16 / 0.025 = 6.4
    assert node_stable.temperature < 10.0, "Sub-critical: bounded by T_ss"
    assert np.isfinite(node_stable.temperature)

    # Case 2: 2.0×α_crit (super-critical) → 指数発散
    node_runaway = TemperatureNode(
        heating_rate=heating_rate, cooling_rate=cooling_rate,
        T_env=0.0, T_max=1e10, T_ref=0.0,
        alpha_PTC=2.0 * alpha_crit, T_initial=0.1, clip_enabled=False,
    )
    for _ in range(n_steps):
        node_runaway.update(input_val, dt)
    # b = 2.0*0.3125*0.16 - 0.05 = 0.05 > 0 → 発散
    assert node_runaway.temperature > 100.0, "Super-critical: exponential runaway"
    assert np.isfinite(node_runaway.temperature)

    # Case 3: ちょうど α_crit → 線形成長
    node_crit = TemperatureNode(
        heating_rate=heating_rate, cooling_rate=cooling_rate,
        T_env=0.0, T_max=1e10, T_ref=0.0,
        alpha_PTC=alpha_crit, T_initial=0.1, clip_enabled=False,
    )
    T_before = node_crit.temperature
    for _ in range(n_steps):
        node_crit.update(input_val, dt)
    # b=0 → 線形: dT/dt = a = h·input·(1-α·T_ref) + c·T_env = 0.16
    # T(200) = 0.1 + 0.16*200 = 32.1
    delta_T = node_crit.temperature - T_before
    assert delta_T > 5.0, "Critical α: linear unbounded growth"
    # Sub-critical の T_ss=6.4 より大きく、Super-critical より小さい
    assert node_crit.temperature < node_runaway.temperature


def test_grok_III_negative_alpha_ptc_unconditional_stability():
    """Grok Stage III 提案: 負 α_PTC は無条件安定 (NTC 的挙動)。

    既存テストは α≥0 のみ。負 α では cooling 効果が温度上昇に伴い増大
    するため b は更に負方向、heating は減衰、収束は加速される。

    観点: 負 α でも T が単調増加 (T < T_eq の間) し有限値に収束。
    """
    node = TemperatureNode(
        heating_rate=0.1,
        cooling_rate=0.05,
        T_env=0.0,
        T_max=10.0,
        T_ref=0.0,
        alpha_PTC=-0.5,
        T_initial=0.3,
        clip_enabled=False,
    )
    dt = 0.1
    prev_T = node.temperature
    # T_eq = a / |b| where a = k·(1-α·T_ref) + c·T_env = 0.1, |b| = c - α·k = 0.1
    # T_eq = 1.0、τ = 1/|b| = 10 → 100 time units = 10τ で十分収束
    for _ in range(1000):
        node.update(1.0, dt)
        # 単調増加 (T < T_eq=1.0 の間、equilibrium 近傍では floating-point
        # による微小ふらつきがあり得るため strict ではなく > prev_T を期待)
        assert node.temperature >= prev_T - 1e-12
        prev_T = node.temperature

    assert node.temperature == pytest.approx(1.0, abs=1e-3)
    assert node.temperature < 3.0  # 確実に bounded
