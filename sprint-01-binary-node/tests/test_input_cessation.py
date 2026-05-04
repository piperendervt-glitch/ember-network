"""
test_input_cessation: KR-S2 の検証

input=1 を 50 ステップ後、input=0 を 50 ステップ提示すると、
- t=50 で weight = 1.0
- t=51 から t=70 までは線形減衰 (傾き -0.05)
- t=70 で weight = 0 に到達
- t=70 から t=100 で weight は 0 で一定
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from binary_node import BinaryNode  # noqa: E402


def _run_cessation_scenario() -> list[float]:
    """50 ステップ input=1 + 50 ステップ input=0 の weight 時系列を返す。"""
    node = BinaryNode()
    trajectory = [node.weight]
    for t in range(1, 101):
        inp = 1 if t <= 50 else 0
        node.update(inp)
        trajectory.append(node.weight)
    return trajectory


def test_weight_is_one_just_before_input_change():
    """入力切替直前 t=50 で weight = 1.0。"""
    trajectory = _run_cessation_scenario()
    assert abs(trajectory[50] - 1.0) < 1e-10


def test_final_weight_is_zero():
    """100 ステップ後の最終 weight が 0。"""
    trajectory = _run_cessation_scenario()
    assert trajectory[-1] == 0.0


def test_linear_decay_slope():
    """t=51 から t=70 まで weight は傾き -0.05 で線形減衰する。

    t=50: weight = 1.0
    t=51: weight = 0.95
    t=52: weight = 0.90
    ...
    t=70: weight = 0.0
    """
    trajectory = _run_cessation_scenario()
    for t in range(51, 71):
        expected = 1.0 - 0.05 * (t - 50)
        if expected < 0:
            expected = 0.0
        assert abs(trajectory[t] - expected) < 1e-10, (
            f"t={t}: weight={trajectory[t]}, expected={expected}"
        )


def test_weight_reaches_zero_at_t70():
    """t=70 で weight が 0 に到達する。"""
    trajectory = _run_cessation_scenario()
    assert trajectory[70] == 0.0


def test_weight_stays_at_zero_after_t70():
    """t=70 から t=100 まで weight は 0 で一定 (clip 機能の確認)。"""
    trajectory = _run_cessation_scenario()
    for t in range(70, 101):
        assert trajectory[t] == 0.0, (
            f"t={t}: weight={trajectory[t]} is not zero"
        )


def test_decay_increment_per_step():
    """t=51 以降の weight 差分が常に -0.05 または 0 (clip 後)。"""
    trajectory = _run_cessation_scenario()
    for t in range(51, 101):
        diff = trajectory[t] - trajectory[t - 1]
        if trajectory[t - 1] > 0.05:
            assert abs(diff - (-0.05)) < 1e-10, (
                f"t={t}: diff={diff}, expected -0.05"
            )
        else:
            assert trajectory[t] == 0.0, (
                f"t={t}: weight should be clipped to 0"
            )
