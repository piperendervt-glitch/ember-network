import pytest
import numpy as np
from ember_network.sprint_03_temperature.src.temperature_node import TemperatureNode  # ← 実際のパスに合わせて調整（sprint-03-temperature ディレクトリ配下想定）

# =============================================================================
# 共通設定（Sprint 3 温度モデルパラメータ）
# =============================================================================
T_ENV = 0.0
T_MAX = 1.0
HEATING_RATE = 0.1
COOLING_RATE = 0.05
TOLERANCE = 1e-8      # RK4 相当の積分器で期待される数値精度
DT_BASE = 0.05
LONG_STEPS = 2000     # 過渡応答確認用の十分なステップ数


@pytest.fixture
def node():
    """各テストで新鮮な TemperatureNode を提供（primary state T がクリーン）"""
    n = TemperatureNode(
        heating_rate=HEATING_RATE,
        cooling_rate=COOLING_RATE,
        T_env=T_ENV,
        T_max=T_MAX,
        clip_enabled=True,
        integrator="rk4"  # Sprint 2 との整合性想定
    )
    n.reset()
    return n


# =============================================================================
# テスト 1
# =============================================================================
def test_reset_idempotency_primary_state(node):
    """目的: reset() を複数回呼び出しても primary 状態変数 T が常に正確に T_env に初期化され、
       derived 量 w が即座に同期する（T primary / w secondary 構造の完全性検証）
    """
    # 任意の状態にした後で reset を連発
    node._temperature = 0.777  # 内部直接操作（テスト用）
    for _ in range(5):
        node.reset()
        assert abs(node.temperature - T_ENV) < 1e-14, "reset が primary T を T_env に戻さない"
        assert abs(node.weight - 0.0) < 1e-14, "reset 後に derived w が同期しない"
    # 根拠: Sprint 3 特有の「T が primary、w は純粋派生量」という設計原則。Sprint 1/2 のリセットテストでは
    # 捕捉しきれなかった「state と derived quantity の同期漏れ」を検出。


# =============================================================================
# テスト 2
# =============================================================================
def test_rhs_numerical_fidelity_small_dt(node):
    """目的: 小さな dt で数値更新後の ΔT が、ODE の右辺（dT/dt = heating·input - cooling·(T-T_env)）と
       O(dt²) 精度で一致することを検証（積分器が正しい物理方程式を忠実に実装しているか）
    """
    node.reset()
    node._temperature = 0.4
    current_T = node.temperature
    test_input = 0.7
    dt_small = 1e-4

    # 理論的右辺
    rhs_theory = HEATING_RATE * test_input - COOLING_RATE * (current_T - T_ENV)

    # 1ステップ更新
    node.update(input_value=test_input, dt=dt_small)
    delta_T_actual = node.temperature - current_T

    # RK4 では O(dt²) 誤差が期待される
    assert abs(delta_T_actual - rhs_theory * dt_small) < 1e-10, \
        f"RHS 忠実度が破綻。理論 ΔT ≈ {rhs_theory * dt_small:.12f}, 実測 {delta_T_actual:.12f}"
    # 根拠: preregister された不変量は大局的性質のみ。局所的な数値積分器の物理方程式実装精度（浮動小数点丸めや
    # 微分計算順序ミス）を検出する Sprint 3 特有の微視的テスト。Sprint 2 の ContinuousNode では未検証。


# =============================================================================
# テスト 3
# =============================================================================
def test_fractional_input_proportional_response(node):
    """目的: input ∈ (0,1) の非バイナリ値に対して、加熱項が線形比例し、過渡応答が連続的に変化することを検証
    """
    node.reset()
    inputs = [0.0, 0.3, 0.7, 1.0]
    final_Ts = []

    for inp in inputs:
        node.reset()
        for _ in range(100):  # 同じ物理時間
            node.update(input_value=inp, dt=DT_BASE)
        final_Ts.append(node.temperature)

    # input が 2 倍なら加熱寄与が 2 倍（冷却項は同一 T では同等）→ T が比例的に大きくなるはず
    assert final_Ts[2] > final_Ts[1] + 1e-6, "input=0.7 が input=0.3 より十分に高温にならない"
    # 根拠: モデルが線形 ODE であることの物理的帰結。Sprint 1（BinaryNode）では input=0/1 のみだったため
    # 見落とされていたアナログ入力対応のロバストネスを検証。実装で input を int として扱うバグを検出可能。


# =============================================================================
# テスト 4
# =============================================================================
def test_dt_convergence_integrator_quality(node):
    """目的: dt を 1/10 に細かくしても最終状態が十分に収束することを確認（数値積分器の収束性）
    """
    t_total = 12.0
    # 基準：dt=0.1
    node.reset()
    steps_coarse = int(t_total / 0.1)
    for _ in range(steps_coarse):
        node.update(input_value=0.6, dt=0.1)
    T_coarse = node.temperature

    # 細かい dt=0.01
    node.reset()
    steps_fine = int(t_total / 0.01)
    for _ in range(steps_fine):
        node.update(input_value=0.6, dt=0.01)
    T_fine = node.temperature

    # dt 収束基準（RK4 なら極めて近い）
    assert abs(T_coarse - T_fine) < 1e-6, \
        f"dt 収束性が破綻。粗 dt={T_coarse:.8f}, 細 dt={T_fine:.8f}"
    # 根拠: 数値的方法の基本性質。preregister 不変量は dt 非依存だが、実装で dt が積分器内部で正しく扱われない
    # 場合（例: dt を無視するバグ）を検出。Sprint 2 でも十分検証されていなかった数値的品質テスト。


# =============================================================================
# テスト 5
# =============================================================================
def test_markov_property_same_T_different_history(node):
    """目的: 同じ T 状態に到達した2つの履歴（異なる過去 input 経路）から、未来の挙動が完全に一致する
       （1階 ODE の Markov 性検証）
    """
    # Path A: 最初から input=0.8 で加熱
    node.reset()
    for _ in range(80):
        node.update(0.8, DT_BASE)
    T_a = node.temperature

    # Path B: 最初 input=1.0 で速く加熱 → input=0 で冷却調整して同じ T に到達
    node2 = TemperatureNode(  # 別インスタンス
        heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE,
        T_env=T_ENV, T_max=T_MAX, clip_enabled=True
    )
    node2.reset()
    for _ in range(40):
        node2.update(1.0, DT_BASE)
    for _ in range(60):  # 調整冷却
        node2.update(0.0, DT_BASE * 0.8)  # 微調整で T を一致させる
    assert abs(node2.temperature - T_a) < 1e-7, "履歴調整で同一 T に到達できなかった（テスト準備）"

    # 同一 input 系列で未来を進める
    future_input = 0.4
    for _ in range(50):
        node.update(future_input, DT_BASE)
        node2.update(future_input, DT_BASE)
    assert abs(node.temperature - node2.temperature) < TOLERANCE, \
        "同一 T から出発しても未来が一致しない（Markov 性破綻）"
    # 根拠: 物理モデルが1階常微分方程式である本質。過去の履歴依存バグ（隠れ状態漏れ）を検出する Sprint 3 独自視点。


# =============================================================================
# テスト 6
# =============================================================================
def test_pulsed_input_transient_accumulation(node):
    """目的: 短いパルス input の繰り返しに対する過渡応答が、累積加熱と冷却のバランスとして物理的に整合する
    """
    node.reset()
    pulse_width = 5   # ステップ数
    cool_width = 15
    num_cycles = 8

    for _ in range(num_cycles):
        for _ in range(pulse_width):
            node.update(1.0, DT_BASE)
        for _ in range(cool_width):
            node.update(0.0, DT_BASE)

    # 最終 T は定常パルス応答の平衡値に近づくはず（解析的に計算可能な範囲）
    # ここでは「極端に低すぎ/高すぎない」ロバストネスをチェック（NaN や発散防止）
    assert not np.isnan(node.temperature), "パルス入力で NaN 発生"
    assert 0.1 < node.temperature < 0.95, \
        f"パルス過渡応答が異常。最終 T = {node.temperature:.6f}"
    # 根拠: 実運用で想定されるスパイク状入力に対する応答性。Sprint 1/2 の定常 input テストでは見落とされていた
    # 「高速スイッチング時の累積誤差・過渡不安定」を検出。


# =============================================================================
# テスト 7
# =============================================================================
def test_large_dt_numerical_safety(node):
    """目的: 物理的タイムスケール（1/cooling_rate ≈20）より極端に大きい dt でも発散・NaN せず安定
    """
    node.reset()
    large_dt = 5.0  # cooling time scale の 1/4 程度だが依然大きい
    for _ in range(30):
        node.update(np.random.uniform(0.0, 1.0), large_dt)  # ランダム fractional input

    assert not np.isnan(node.temperature) and not np.isinf(node.temperature), \
        "大 dt で数値的不安定（NaN/Inf）"
    # 根拠: 実数値計算機で起こりうる「dt が大きすぎる場合の積分器破綻」を検出。preregister 不変量は小 dt を前提としているため
    # 見落とされやすいエッジケース。