"""
test_integrators: 数値積分 src/integrators.py の検証 (KR-S1, S2 補助)

- Euler 法と RK4 法が同じインターフェース
- 両手法で initial value を正しく扱える
- 入力関数の切り替えを正しく扱える
- KR-S1: RK4 (dt=0.01, input=1) で解析解との最大誤差 < 1e-6
- KR-S2: RK4 (dt=0.01, cessation) で解析解との最大誤差 < 1e-6
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analytical import analytical_solution  # noqa: E402
from integrators import integrate_euler, integrate_rk4  # noqa: E402


ALPHA = 0.1
BETA = 0.05


def _dwdt(t: float, w: float, input_value: int) -> float:
    """微分方程式の右辺。"""
    return ALPHA * input_value - BETA * w


def _const_input(value: int):
    """定数入力関数を返す。"""
    return lambda t: value


def _cessation_input(t_switch: float):
    """t < t_switch で 1、それ以降 0 を返す入力関数。"""
    return lambda t: 1 if t < t_switch else 0


def test_initial_value_handling():
    """両手法で initial value w_0 が正しく t_array[0] に設定される。"""
    for integrator in (integrate_euler, integrate_rk4):
        t, w = integrator(_dwdt, 0.5, (0.0, 1.0), 0.1, _const_input(1))
        assert w[0] == 0.5


def test_t_span_endpoints():
    """t_array の先頭と末尾が t_span と一致する。"""
    for integrator in (integrate_euler, integrate_rk4):
        t, w = integrator(_dwdt, 0.0, (0.0, 10.0), 0.1, _const_input(1))
        assert abs(t[0] - 0.0) < 1e-10
        assert abs(t[-1] - 10.0) < 1e-10


def test_same_interface():
    """Euler と RK4 が同じシグネチャで呼べる。"""
    args = (_dwdt, 0.0, (0.0, 1.0), 0.1, _const_input(1))
    te, we = integrate_euler(*args)
    tr, wr = integrate_rk4(*args)
    assert te.shape == tr.shape
    assert we.shape == wr.shape


def test_input_switching():
    """入力関数の切り替えが正しく扱える (cessation シナリオ)。"""
    t, w = integrate_rk4(_dwdt, 0.0, (0.0, 100.0), 0.01,
                         _cessation_input(50.0))
    # t=50 直前は input=1 で増加、その後減衰
    idx_before = np.argmin(np.abs(t - 49.99))
    idx_after = np.argmin(np.abs(t - 80.0))
    assert w[idx_before] > 1.0
    assert w[idx_after] < w[idx_before]


def test_kr_s1_constant_input_max_error():
    """KR-S1 検証: RK4 (dt=0.01) で input=1 を 100 単位時間、
    解析解との最大誤差 < 1e-6。"""
    t, w = integrate_rk4(_dwdt, 0.0, (0.0, 100.0), 0.01, _const_input(1))
    analytical = analytical_solution(t, 0.0, 1, ALPHA, BETA)
    max_err = float(np.max(np.abs(w - analytical)))
    assert max_err < 1e-6, (
        f"KR-S1 失敗: max error = {max_err:.3e}, 閾値 1e-6"
    )


def test_rk4_loses_accuracy_at_input_discontinuity():
    """RK4 が input_func の不連続点で 4 次精度を失うことの直接検証。

    Notes
    -----
    KR-S2 検証は test_continuous_node.py に移動した。
    本テストは、RK4 + input_func で構成される integrator API では、
    不連続点で精度が低下する数値解析的事実を documenting するために残す。

    Sprint 2 で発見された方法論的観察:
    - dw/dt = α·input - β·w で input が step function の場合、RK4 の
      ステップ内中間評価 (k2, k3, k4) が input の異なる値を見るため、
      4 次精度が崩れる
    - Sprint 3 以降では「ステップ内で input が固定される」パターン
      (ContinuousNode + scenarios.py) を標準とする
    """
    t, w = integrate_rk4(_dwdt, 0.0, (0.0, 100.0), 0.01,
                         _cessation_input(50.0))

    n = len(t)
    ana = np.zeros(n)
    mask1 = t < 50.0
    ana[mask1] = analytical_solution(t[mask1], 0.0, 1, ALPHA, BETA)
    w_at_50 = analytical_solution(50.0, 0.0, 1, ALPHA, BETA)
    mask0 = ~mask1
    ana[mask0] = analytical_solution(t[mask0] - 50.0, w_at_50, 0, ALPHA, BETA)

    max_err = float(np.max(np.abs(w - ana)))
    # 不連続点での誤差は 1e-4 オーダーまで悪化することを documenting
    assert max_err > 1e-6, (
        f"想定外: 不連続点での RK4 精度が 1e-6 未満になった "
        f"(max_err = {max_err:.3e})。spec 解釈の見直しが必要。"
    )
    assert max_err < 1e-3, (
        f"RK4 不連続点誤差が想定より大きい (max_err = {max_err:.3e})。"
    )


def test_constant_zero_input_no_change_from_zero():
    """初期値 0 で input=0 を続けると weight=0 が維持される。"""
    t, w = integrate_rk4(_dwdt, 0.0, (0.0, 100.0), 0.1, _const_input(0))
    assert np.max(np.abs(w)) < 1e-15
