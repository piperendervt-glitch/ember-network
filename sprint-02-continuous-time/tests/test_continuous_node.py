"""
test_continuous_node: ContinuousNode クラスの検証

- 初期化
- update() による weight 変更
- clip_enabled=False で weight が 1.0 を超える
- clip_enabled=True で weight が [0, 1] に制限される
- input_value のバリデーション (bool 拒否)
- integrator のバリデーション
- reset() の動作
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from continuous_node import ContinuousNode  # noqa: E402
from scenarios import (  # noqa: E402
    run_constant_input_scenario,
    run_input_cessation_scenario,
)


def test_initial_weight_is_zero():
    """新規 ContinuousNode の weight は 0 で初期化される。"""
    node = ContinuousNode()
    assert node.weight == 0.0


def test_update_changes_weight():
    """update() が weight を変更する。"""
    node = ContinuousNode(integrator='euler')
    node.update(1, 0.1)
    assert node.weight > 0.0


def test_default_integrator_is_rk4():
    """デフォルト integrator は 'rk4'。"""
    node_default = ContinuousNode()
    node_rk4 = ContinuousNode(integrator='rk4')
    node_default.update(1, 0.1)
    node_rk4.update(1, 0.1)
    assert node_default.weight == node_rk4.weight


def test_euler_one_step():
    """Euler 法 1 ステップで w_new = dt·(α·input - β·w_0) = 0.01。"""
    node = ContinuousNode(integrator='euler')
    node.update(1, 0.1)
    assert abs(node.weight - 0.01) < 1e-10


def test_rk4_one_step():
    """RK4 法 1 ステップで w_new ≈ 0.009975 (事前計算)。"""
    node = ContinuousNode(integrator='rk4')
    node.update(1, 0.1)
    assert abs(node.weight - 0.0099750416) < 1e-9


def test_clip_disabled_allows_overshoot():
    """clip_enabled=False で weight が 1.0 を超えうる。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=False)
    dt = 0.01
    n_steps = int(round(20.0 / dt))
    for _ in range(n_steps):
        node.update(1, dt)
    # 解析的に t=20 で w ≈ 1.264
    assert node.weight > 1.0
    assert abs(node.weight - 1.2642411) < 1e-3


def test_clip_enabled_caps_at_one():
    """clip_enabled=True で weight が 1.0 を超えない。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=True)
    dt = 0.01
    n_steps = int(round(20.0 / dt))
    for _ in range(n_steps):
        node.update(1, dt)
    assert node.weight == 1.0


def test_clip_enabled_keeps_weight_non_negative():
    """clip_enabled=True で weight が全ステップで 0 以上を保つ。

    Notes
    -----
    連続時間モデル dw/dt = -β·w は w=0 を漸近境界とするため、input=0 の
    自然減衰では数学的に厳密に 0 に到達しない (Sprint 1 の離散時間モデル
    との根本的差異)。

    本テストは lower clip の「safety net としての存在意義」を直接検証する:
    - 全ステップを通じて weight >= 0 を保つこと
    - これは float 誤差で稀に負値が生成された場合も clip が機能することの
      間接証拠 (現実装では発動しないが、回帰検出器として有効)
    """
    node = ContinuousNode(integrator='rk4', clip_enabled=True)
    # 最初に少し増やしてから減衰させる
    for _ in range(10):
        node.update(1, 0.01)
        assert node.weight >= 0.0, f"weight became negative: {node.weight}"
    # input=0 で大きく減衰、毎ステップで非負を確認
    for i in range(10000):
        node.update(0, 0.01)
        assert node.weight >= 0.0, (
            f"weight became negative at step {i}: {node.weight}"
        )


def test_invalid_input_raises_value_error():
    """input_value が 0 または 1 以外で ValueError。bool 拒否。"""
    node = ContinuousNode()
    for invalid in (-1, 2, 0.5, 100, True, False, None, "1"):
        with pytest.raises(ValueError):
            node.update(invalid, 0.1)


def test_invalid_dt_raises_value_error():
    """dt が正でない場合 ValueError。"""
    node = ContinuousNode()
    for invalid_dt in (0.0, -0.1, -1.0):
        with pytest.raises(ValueError):
            node.update(1, invalid_dt)


def test_invalid_integrator_raises_value_error():
    """integrator が 'euler' / 'rk4' 以外で ValueError。"""
    for invalid in ('rk2', 'midpoint', 'EULER', 'RK4', '', None):
        with pytest.raises(ValueError):
            ContinuousNode(integrator=invalid)


def test_reset_returns_weight_to_zero():
    """reset() で weight が 0 に戻る。"""
    node = ContinuousNode()
    for _ in range(10):
        node.update(1, 0.1)
    assert node.weight > 0.0
    node.reset()
    assert node.weight == 0.0


def test_kr_s1_via_node_loop_max_error():
    """KR-S1 検証: ContinuousNode.update を 100 単位時間ループし、
    clip 無効・RK4・dt=0.01 で解析解との最大誤差 < 1e-6。"""
    from analytical import analytical_solution

    node = ContinuousNode(integrator='rk4', clip_enabled=False)
    dt = 0.01
    times, w_arr = run_constant_input_scenario(
        node, total_time=100.0, dt=dt, input_value=1
    )
    ana = analytical_solution(times, 0.0, 1)
    max_err = float(np.max(np.abs(w_arr - ana)))
    assert max_err < 1e-6, f"KR-S1 max error = {max_err:.3e}"


def test_kr_s2_via_node_loop_max_error():
    """KR-S2 検証: ContinuousNode で 0..50 input=1, 50..100 input=0,
    clip 無効・RK4・dt=0.01 で解析解との最大誤差 < 1e-6。

    Notes
    -----
    test_integrators.py で同じシナリオを integrate_rk4 + input_func で
    実装すると、不連続点 t=50 で RK4 が 4 次精度を失い max error が
    1e-4 オーダーまで悪化する。

    scenarios.py の run_input_cessation_scenario は「1 ステップ内で input
    を固定」する設計のため、不連続点でも RK4 の精度が保たれる。
    """
    from analytical import analytical_solution

    node = ContinuousNode(integrator='rk4', clip_enabled=False)
    dt = 0.01
    times, w_arr = run_input_cessation_scenario(
        node, t_switch=50.0, total_time=100.0, dt=dt
    )

    # 解析解: 区間ごとに計算
    ana = np.zeros_like(w_arr)
    mask1 = times < 50.0
    ana[mask1] = analytical_solution(times[mask1], 0.0, 1)
    w_at_50 = analytical_solution(50.0, 0.0, 1)
    mask0 = ~mask1
    ana[mask0] = analytical_solution(times[mask0] - 50.0, w_at_50, 0)

    max_err = float(np.max(np.abs(w_arr - ana)))
    assert max_err < 1e-6, f"KR-S2 max error = {max_err:.3e}"
