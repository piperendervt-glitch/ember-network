import pytest
import numpy as np
from ember_network.sprint_03_temperature.src.temperature_node import TemperatureNode  # ← 実際の実装パスに合わせて調整してください
# 注意: 上記 import は Sprint 2 の ContinuousNode パターンを踏襲した想定です。
# 実装が異なる場合は適宜修正してください（例: PTCAdaptiveSynapse など）。

# =============================================================================
# 共通設定（Sprint 3 温度モデルパラメータ）
# =============================================================================
T_ENV = 0.0
T_MAX = 1.0
HEATING_RATE = 0.1
COOLING_RATE = 0.05
DEFAULT_DT = 0.1
TOLERANCE = 1e-7   # 数値的許容誤差（RK4 程度の積分器で期待される精度）
LONG_TIME_STEPS = 5000  # 十分長い時間（t≈500）で定常状態を確認するためのステップ数


@pytest.fixture
def node():
    """各テストで新鮮な TemperatureNode を提供"""
    n = TemperatureNode(
        heating_rate=HEATING_RATE,
        cooling_rate=COOLING_RATE,
        T_env=T_ENV,
        T_max=T_MAX,
        clip_enabled=True,
        integrator="rk4"  # Sprint 2 と同様に RK4 をデフォルト想定
    )
    n.reset()
    return n


# =============================================================================
# テスト 1
# =============================================================================
def test_temperature_cooling_analytical_decay(node):
    """目的: input=0 のとき、Newton 冷却則による指数減衰が解析解と一致することを検証
    （熱力学第二法則：自発的に T_env 以下へは冷えない）
    """
    # 初期条件: T0 = 0.8（任意の高温状態）
    node.reset()
    node._temperature = 0.8  # 内部状態を直接設定（テスト用；実装に temperature プロパティがあればそれを使う）
    
    # 解析解（input=0 の場合）
    # T(t) = T_env + (T0 - T_env) * exp(-cooling_rate * t)
    t_total = 100.0
    steps = int(t_total / DEFAULT_DT)
    analytical_T_final = T_ENV + (0.8 - T_ENV) * np.exp(-COOLING_RATE * t_total)
    
    for _ in range(steps):
        node.update(input_value=0.0, dt=DEFAULT_DT)
    
    assert abs(node.temperature - analytical_T_final) < TOLERANCE, \
        f"冷却減衰が解析解と一致しない。期待値 ≈ {analytical_T_final:.8f}"
    # 根拠: 線形1階ODEの厳密解。物理的に T >= T_env が保証され、浮動小数点誤差で T_env を下回らないことを確認。


# =============================================================================
# テスト 2
# =============================================================================
def test_heating_constant_input1_analytical_short_time(node):
    """目的: input=1 の短時間（クリップ前）で、Joule 加熱＋冷却の解析解と一致することを検証
    """
    # 解析解（定常 input=1 の場合）
    # T_eq = T_env + heating_rate / cooling_rate = 2.0
    # T(t) = T_eq + (T0 - T_eq) * exp(-cooling_rate * t)
    T0 = 0.0
    node.reset()
    node._temperature = T0
    
    t_total = 5.0  # クリップ前（t_clip ≈13.86 より短い）
    steps = int(t_total / DEFAULT_DT)
    T_eq = T_ENV + HEATING_RATE / COOLING_RATE
    analytical_T_final = T_eq + (T0 - T_eq) * np.exp(-COOLING_RATE * t_total)
    
    for _ in range(steps):
        node.update(input_value=1.0, dt=DEFAULT_DT)
    
    assert abs(node.temperature - analytical_T_final) < TOLERANCE, \
        f"加熱挙動が解析解と一致しない。期待値 ≈ {analytical_T_final:.8f}"
    # 根拠: 同一の1階線形ODEの厳密解（Sprint 2 の analytical_solution と等価）。数値積分器の正確性を検出。


# =============================================================================
# テスト 3
# =============================================================================
def test_clipping_at_Tmax_with_sustained_input(node):
    """目的: 十分長い input=1 で T == T_max に到達し、以後超過しない（物理的クリップ保証）
    """
    node.reset()
    t_clip_approx = np.log(2) / COOLING_RATE  # 解析的 t_clip ≈13.8629（T0=0 から T=1 に到達）
    steps_to_clip = int(t_clip_approx / DEFAULT_DT) + 100  # 余裕を持たせる
    
    for _ in range(steps_to_clip):
        node.update(input_value=1.0, dt=DEFAULT_DT)
    
    assert abs(node.temperature - T_MAX) < TOLERANCE, \
        f"T_max に収束しない。実測: {node.temperature:.8f}"
    assert node.temperature <= T_MAX + 1e-12, "クリップが破られ T > T_max"
    # 根拠: 無限時間で T_eq=2.0 へ向かうが、物理的境界 T <= T_max でクリップ。deterrence-oriented 設計の核心。


# =============================================================================
# テスト 4
# =============================================================================
def test_thermodynamic_consistency_no_spontaneous_heating(node):
    """目的: input=0 のとき常に dT/dt <= 0（T >= T_env の範囲で自発加熱なし）
       熱力学第二法則との整合を検出
    """
    node.reset()
    node._temperature = 0.3  # 任意の初期温度
    prev_T = node.temperature
    
    for _ in range(100):
        node.update(input_value=0.0, dt=DEFAULT_DT)
        assert node.temperature <= prev_T + 1e-12, "input=0 で自発加熱が発生（熱力学第二法則違反）"
        prev_T = node.temperature
    
    assert node.temperature >= T_ENV - 1e-12, "T_env 以下へ冷却（Newton冷却則違反）"
    # 根拠: dT/dt = heating_rate·input - cooling_rate·(T - T_env) の第1項が0のとき符号は明確。実装の符号ミスを検出。


# =============================================================================
# テスト 5
# =============================================================================
def test_weight_derivation_exact_and_normalized(node):
    """目的: 任意の T に対して w(t) = (T - T_env) / (T_max - T_env) が厳密に成立
       （T_env=0, T_max=1 のとき w ≡ T）
    """
    node.reset()
    test_T_values = np.linspace(0.0, 1.0, 11)
    
    for target_T in test_T_values:
        node._temperature = target_T
        expected_w = (target_T - T_ENV) / (T_MAX - T_ENV)
        assert abs(node.weight - expected_w) < 1e-14, \
            f"w の導出が破綻。T={target_T}, 期待 w={expected_w}, 実測 {node.weight}"
    # 根拠: 定義そのもの。浮動小数点丸めで w が [0,1] 外に出るケースや、T 更新後に w が同期しないバグを検出。


# =============================================================================
# テスト 6
# =============================================================================
def test_boundary_stability_at_Tenv_and_Tmax(node):
    """目的: 境界条件での安定性
       (T=T_env, input=0) → 不変
       (T=T_max, input=1) → 不変（クリップにより物理的に保証）
    """
    # Case 1: T_env + input=0
    node.reset()
    node._temperature = T_ENV
    for _ in range(50):
        node.update(input_value=0.0, dt=DEFAULT_DT)
    assert abs(node.temperature - T_ENV) < TOLERANCE, "T_env で input=0 の安定性が破綻"
    
    # Case 2: T_max + input=1
    node.reset()
    node._temperature = T_MAX
    for _ in range(50):
        node.update(input_value=1.0, dt=DEFAULT_DT)
    assert abs(node.temperature - T_MAX) < TOLERANCE, "T_max で input=1 のクリップ安定性が破綻"
    # 根拠: 微分方程式の平衡点＋クリップ。長時間シミュレーションで浮動小数点誤差によるドリフトを検出。


# =============================================================================
# テスト 7
# =============================================================================
def test_long_term_numerical_stability_no_drift(node):
    """目的: 極端に長い時間ステップ後でも T ∈ [T_env, T_max] を厳密に維持
       （浮動小数点累積誤差や NaN 発生を検出）
    """
    node.reset()
    for _ in range(LONG_TIME_STEPS):
        node.update(input_value=np.random.choice([0.0, 1.0]), dt=DEFAULT_DT)
    
    assert T_ENV - 1e-12 <= node.temperature <= T_MAX + 1e-12, \
        f"長時間シミュレーションで境界外逸脱: {node.temperature}"
    assert not np.isnan(node.temperature), "NaN 発生（数値的不安定）"
    # 根拠: 物理散逸系の本質的制限。実装の積分器やクリップが壊れた場合に即座に検出可能。


# =============================================================================
# テスト 8
# =============================================================================
def test_edge_case_input_zero_after_saturation(node):
    """目的: T=T_max 到達後に input=0 に切り替えたとき、即座に冷却開始（遅延なし）
    """
    node.reset()
    # まず T_max まで加熱
    for _ in range(200):
        node.update(input_value=1.0, dt=DEFAULT_DT)
    assert abs(node.temperature - T_MAX) < TOLERANCE
    
    # input=0 に切り替え
    prev_T = node.temperature
    node.update(input_value=0.0, dt=DEFAULT_DT)
    assert node.temperature < prev_T - 1e-8, "飽和後 input=0 で冷却が開始されない（物理的遅延バグ）"
    # 根拠: 物理的境界条件の即時反映。クリップ後に内部状態が正しく更新されないケースを検出。