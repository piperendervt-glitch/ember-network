"""
test_analytical: 解析解 src/analytical.py の検証

- t=0 で w_0 を返す
- 入力 input=1 で w_eq=α/β に収束
- 入力 input=0 で 0 に減衰
- t=t_clip で w=1.0 (clip なし解)
- input_value のバリデーション (bool 拒否含む)
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analytical import analytical_solution  # noqa: E402


ALPHA = 0.1
BETA = 0.05
W_EQ = ALPHA / BETA
T_CLIP = 20.0 * np.log(2.0)


def test_returns_initial_value_at_t_zero():
    """t=0 で w_0 を返す。"""
    assert analytical_solution(0.0, 0.5, 1, ALPHA, BETA) == pytest.approx(0.5)
    assert analytical_solution(0.0, 0.0, 1, ALPHA, BETA) == pytest.approx(0.0)
    assert analytical_solution(0.0, 1.5, 0, ALPHA, BETA) == pytest.approx(1.5)


def test_converges_to_equilibrium_with_input_one():
    """t→∞ で w_eq=α/β に収束する。"""
    w_inf = analytical_solution(1000.0, 0.0, 1, ALPHA, BETA)
    assert abs(w_inf - W_EQ) < 1e-15


def test_decays_to_zero_with_input_zero():
    """input=0 では t→∞ で 0 に減衰する。"""
    w_inf = analytical_solution(1000.0, 5.0, 0, ALPHA, BETA)
    assert abs(w_inf) < 1e-15


def test_reaches_one_at_analytical_t_clip():
    """t=20·ln(2) で weight が clip なし解で 1.0 に到達する。"""
    w_at_clip = analytical_solution(T_CLIP, 0.0, 1, ALPHA, BETA)
    assert abs(w_at_clip - 1.0) < 1e-10


def test_array_input():
    """numpy 配列入力で要素ごとの結果を返す。"""
    ts = np.array([0.0, 10.0, 20.0])
    ws = analytical_solution(ts, 0.0, 1, ALPHA, BETA)
    assert ws.shape == (3,)
    assert ws[0] == pytest.approx(0.0)
    assert ws[2] == pytest.approx(W_EQ + (0.0 - W_EQ) * np.exp(-BETA * 20.0))


def test_decay_formula():
    """input=0 の解析解: w(t) = w_0 · exp(-β·t)。"""
    t = 50.0
    w_0 = 2.0
    expected = w_0 * np.exp(-BETA * t)
    actual = analytical_solution(t, w_0, 0, ALPHA, BETA)
    assert abs(actual - expected) < 1e-15


def test_invalid_input_raises_value_error():
    """input_value が 0 または 1 (int) 以外で ValueError。bool も拒否。"""
    for invalid in (-1, 2, 0.5, 100, True, False, None, "1"):
        with pytest.raises(ValueError):
            analytical_solution(0.0, 0.0, invalid, ALPHA, BETA)


def test_default_parameters():
    """デフォルト alpha=0.1, beta=0.05 で計算が正しい。"""
    w = analytical_solution(20.0, 0.0, 1)
    expected = 2.0 + (0.0 - 2.0) * np.exp(-0.05 * 20.0)
    assert abs(w - expected) < 1e-15
