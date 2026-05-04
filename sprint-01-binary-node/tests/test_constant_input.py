"""
test_constant_input: KR-S1 の検証

一定入力 input=1 を 100 ステップ提示すると、weight が 1.0 に到達し、
その後 1.0 で安定することを確認する。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from binary_node import BinaryNode  # noqa: E402


def _run_constant_input(steps: int = 100) -> list[float]:
    """input=1 を steps 回提示して weight 時系列を返す (t=0 を含む)。"""
    node = BinaryNode()
    trajectory = [node.weight]
    for _ in range(steps):
        node.update(1)
        trajectory.append(node.weight)
    return trajectory


def test_final_weight_is_one():
    """100 ステップ input=1 後の最終 weight が 1.0 (誤差 < 1e-10)。"""
    trajectory = _run_constant_input(100)
    assert abs(trajectory[-1] - 1.0) < 1e-10


def test_weight_reaches_one_at_t20():
    """t=20 で weight が 1.0 に到達する (誤差 < 1e-10)。

    数学的には 0.05 * 20 = 1.0 だが、浮動小数点誤差により実測値は
    1.0 よりわずかに小さい。許容誤差 1e-10 で検証する。
    """
    trajectory = _run_constant_input(100)
    assert abs(trajectory[20] - 1.0) < 1e-10


def test_weight_is_stable_at_one_from_t20_to_t100():
    """t=20 から t=100 の間、weight は 1.0 で一定 (誤差 < 1e-10)。"""
    trajectory = _run_constant_input(100)
    for t in range(20, 101):
        assert abs(trajectory[t] - 1.0) < 1e-10, (
            f"t={t}: weight={trajectory[t]} differs from 1.0"
        )


def test_clipping_prevents_upper_overflow():
    """weight が 1.0 に到達後、追加 input でも 1.0 を超えないこと。

    検証ロジック:
    - 20 ステップ input=1 で weight ≒ 1.0 (誤差 < 1e-10) に到達
    - さらに 1 ステップ input=1 を与えると、clip がなければ
      weight + 0.05 → ~1.05 になるはず
    - 実測 weight が厳密に 1.0 であることで、clip 機能の発動を確認

    このテストは clip ロジックを直接検証するため、もし将来 clip を
    意図せず削除した場合、本テストは fail する (regression detection)。
    """
    node = BinaryNode()
    for _ in range(20):
        node.update(1)

    pre_clip_weight = node.weight
    assert abs(pre_clip_weight - 1.0) < 1e-10, (
        f"前提条件: 20 ステップ後の weight が 1.0 近傍であること。"
        f"実測 = {pre_clip_weight}"
    )

    naive_next = pre_clip_weight + 0.05
    assert naive_next > 1.0, (
        f"clip テストの前提: clip がない場合に 1.0 を超えるはず。"
        f"naive_next = {naive_next}"
    )

    node.update(1)
    assert node.weight == 1.0, (
        f"clip 発動後の weight は厳密に 1.0 になるべき。実測 = {node.weight}"
    )


def test_linear_growth_before_clipping():
    """t=1 から t=19 までは線形増加 (傾き 0.05)。"""
    trajectory = _run_constant_input(100)
    for t in range(1, 20):
        expected = 0.05 * t
        assert abs(trajectory[t] - expected) < 1e-10, (
            f"t={t}: weight={trajectory[t]}, expected={expected}"
        )
