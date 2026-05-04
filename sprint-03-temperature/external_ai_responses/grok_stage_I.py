import pytest
import numpy as np
from ember_network.sprint_03_temperature.src.temperature_node import TemperatureNode  # 実際のパスに合わせて調整

# =============================================================================
# 共通設定（Sprint 3 温度モデルパラメータ）
# =============================================================================
T_ENV = 0.0
T_MAX = 1.0
HEATING_RATE = 0.1
COOLING_RATE = 0.05
TOLERANCE = 1e-9
DT_BASE = 0.02


@pytest.fixture
def node():
    """各テストで新鮮な TemperatureNode を提供（T が primary であることを保証）"""
    n = TemperatureNode(
        heating_rate=HEATING_RATE,
        cooling_rate=COOLING_RATE,
        T_env=T_ENV,
        T_max=T_MAX,
        clip_enabled=True,
        integrator="rk4"
    )
    n.reset()
    return n


# =============================================================================
# テスト 1
# =============================================================================
def test_primary_secondary_strict_consistency(node):
    """目的: T が primary 状態変数、w が純粋派生量である構造を厳密に検証。
    既存の Sprint 2 test_continuous_node.py や test_clip_behavior.py では w が直接更新される前提のため、
    「w を直接操作した場合の破綻」や「T 更新後に w が即時同期しない」バグを捕捉できない。
    """
    node.reset()
    # 内部 T を直接操作（テスト用）
    test_T = 0.333
    node._temperature = test_T  # 内部状態直接書き換え
    
    # w は必ず (T - T_env) / (T_max - T_env) に一致しなければならない
    expected_w = (test_T - T_ENV) / (T_MAX - T_ENV)
    assert abs(node.weight - expected_w) < 1e-14, \
        f"T primary / w derived 構造が破綻。T={test_T}, 期待 w={expected_w}, 実測 w={node.weight}"
    
    # w を外部から書き換えても T は変わらない（derived である証拠）
    node.weight = 0.999  # もし実装が w を primary と誤認していれば T も変わってしまう
    assert abs(node.temperature - test_T) < 1e-14, \
        "w を変更しても T が影響を受ける → derived 構造が崩れている"
    # 根拠: Sprint 3 の設計原則「T が物理状態、w は観測量」。mutation testing 的に w を primary 扱いする
    # 小さなコード変更（w を直接更新するバグ）で即座に失敗する。


# =============================================================================
# テスト 2
# =============================================================================
def test_equilibrium_power_balance(node):
    """目的: clip なしの平衡状態で Joule 加熱と Newton 冷却が完全につり合うことを検証。
    既存の test_convergence.py は「最終的に T_max に近づく」程度の粗いチェックのため、
    平衡時の物理的 power balance（heating_rate·input == cooling_rate·(T - T_env)）を定量的に検証しない。
    """
    node.reset()
    test_input = 0.6
    # clip を一時的に無効化して真の平衡を確認
    node._clip_enabled = False
    for _ in range(800):  # 十分長い時間
        node.update(input_value=test_input, dt=DT_BASE)
    
    T_eq = node.temperature
    heating_power = HEATING_RATE * test_input
    cooling_power = COOLING_RATE * (T_eq - T_ENV)
    assert abs(heating_power - cooling_power) < TOLERANCE, \
        f"平衡時の power balance が成立しない。加熱={heating_power:.10f}, 冷却={cooling_power:.10f}"
    # 根拠: 微分方程式 dT/dt = 0 の直接帰結。Sprint 2 の数学モデルから物理モデルへの移行で
    # 「冷却項の (T - T_env) 係数が欠落」する mutation を検出可能。


# =============================================================================
# テスト 3
# =============================================================================
def test_thermal_time_constant_e_folding(node):
    """目的: input=0 時の冷却時定数 1/cooling_rate が正確に現れることを検証（e-folding time）。
    既存の test_input_cessation.py は「冷却する」程度の定性的テストのため、
    時定数の定量的一致を検証しない（物理モデル移行特有のレート正確性）。
    """
    node.reset()
    node._temperature = 0.8
    initial_T = node.temperature
    target_time = 1.0 / COOLING_RATE * np.log(2)  # 半減期（≈13.8629）
    steps = int(target_time / DT_BASE)
    
    for _ in range(steps):
        node.update(input_value=0.0, dt=DT_BASE)
    
    # T が (initial_T - T_env) / 2 に近づいているはず
    expected_T = T_ENV + (initial_T - T_ENV) / 2
    assert abs(node.temperature - expected_T) < TOLERANCE, \
        f"時定数 1/cooling_rate が正しく現れない。期待 ≈{expected_T:.8f}, 実測 {node.temperature:.8f}"
    # 根拠: Newton 冷却則の解析的特性。mutation で cooling_rate の係数が 2 倍になっていた場合に即検出。


# =============================================================================
# テスト 4
# =============================================================================
def test_clip_interaction_with_underlying_ode(node):
    """目的: T_max クリップ適用後も内部 ODE が正しく動作し続け、clip 解除後に即座に冷却が再開することを検証。
    既存の test_clip_behavior.py は「T_max を超えない」だけのテストのため、
    「clip が ODE の右辺計算に干渉して冷却項を殺す」ような実装ミスを捕捉できない。
    """
    node.reset()
    # まず T_max まで加熱
    for _ in range(400):
        node.update(input_value=1.0, dt=DT_BASE)
    assert abs(node.temperature - T_MAX) < TOLERANCE
    
    # input=0 に切り替え → 即座に冷却開始
    prev_T = node.temperature
    node.update(input_value=0.0, dt=DT_BASE)
    assert node.temperature < prev_T - 1e-8, \
        "クリップ後も冷却が開始されない（clip が ODE を上書きしている可能性）"
    # 根拠: 物理的クリップは「T <= T_max」制約のみで、dT/dt の計算自体は変わらないはず。
    # mutation testing で clip 後に cooling_rate 項を無効化するコード変更を検出。


# =============================================================================
# テスト 5
# =============================================================================
def test_analog_input_scaling_exact(node):
    """目的: input ∈ (0,1) のアナログ値に対して加熱率が厳密に比例することを検証。
    Sprint 1 の test_constant_input.py は binary input のみ、Sprint 2 でもアナログ入力の
    定量スケーリングを「power balance」レベルで検証していない。
    """
    node.reset()
    inputs = np.array([0.25, 0.5, 0.75])
    final_Ts = []
    
    for inp in inputs:
        node.reset()
        for _ in range(300):
            node.update(input_value=inp, dt=DT_BASE)
        final_Ts.append(node.temperature)
    
    # 比例関係：input が 2 倍なら最終 T（平衡寄与）が 2 倍に近づく
    ratios = np.diff(final_Ts) / np.diff(inputs)
    assert np.all(np.abs(ratios - (HEATING_RATE / COOLING_RATE)) < 0.01), \
        f"アナログ入力のスケーリングが破綻。比率={ratios}"
    # 根拠: 線形 ODE の superposition 原理。実装で input を int 型にキャストする mutation を検出可能。


# =============================================================================
# テスト 6
# =============================================================================
def test_mutation_resistant_boundary_drift(node):
    """目的: 極端に長いランダム入力系列でも T が [T_env, T_max] の境界を厳密に守り、浮動小数点ドリフトしない。
    既存の test_reproducibility.py は同一入力での再現性のみで、長時間境界安定性（累積誤差）を検証しない。
    """
    node.reset()
    np.random.seed(42)  # 再現性確保
    for _ in range(5000):
        inp = np.random.uniform(0.0, 1.0)
        node.update(input_value=inp, dt=DT_BASE * 1.5)  # 大きめ dt で厳しい条件
    
    assert T_ENV - 1e-12 <= node.temperature <= T_MAX + 1e-12, \
        f"長時間境界ドリフト発生: {node.temperature}"
    assert not np.isnan(node.temperature) and not np.isinf(node.temperature), \
        "NaN/Inf 発生（数値的不安定）"
    # 根拠: 物理散逸系の本質的性質。clip ロジックや積分器の順序が 1 行変わった mutation で即座に境界逸脱する。