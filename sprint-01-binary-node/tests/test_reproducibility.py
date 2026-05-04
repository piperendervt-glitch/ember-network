"""
test_reproducibility: KR-S3 の検証

5 つの異なるランダムシードで完全に同じ結果が再現されることを確認する。
現在のモデルは決定論的なので、本来シードに依存しない。

このテストファイルは 2 つの目的を持つ:

1. KR-S3 文言の達成証拠 (test_*_bit_perfect_across_seeds, test_same_seed_*)
   - 5 シードで同一結果が出ることを bit-perfect に確認

2. 現モデルのシード非依存性の明示証明 (test_model_is_seed_independent)
   - シード設定なしの結果とシード設定ありの結果が一致することで、
     BinaryNode が random/numpy のグローバル状態を消費していないことを示す
   - Sprint 6-7 で確率要素 (個体差) を導入した場合、このテストは
     fail するはず → 意図した変化の検出器として機能する

シード設定は random.seed() と np.random.seed() の両方を呼ぶことで、
将来的に確率的要素を導入した際の一貫性インフラを Sprint 1 から確立する。
"""

import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from binary_node import BinaryNode  # noqa: E402


SEEDS = [0, 1, 2, 3, 42]


def _run_with_seed(seed: int) -> np.ndarray:
    """指定シードで constant input シナリオを実行し weight 時系列を返す。"""
    random.seed(seed)
    np.random.seed(seed)
    node = BinaryNode()
    trajectory = [node.weight]
    for _ in range(100):
        node.update(1)
        trajectory.append(node.weight)
    return np.array(trajectory)


def _run_cessation_with_seed(seed: int) -> np.ndarray:
    """指定シードで input cessation シナリオを実行し weight 時系列を返す。"""
    random.seed(seed)
    np.random.seed(seed)
    node = BinaryNode()
    trajectory = [node.weight]
    for t in range(1, 101):
        inp = 1 if t <= 50 else 0
        node.update(inp)
        trajectory.append(node.weight)
    return np.array(trajectory)


def test_constant_input_bit_perfect_across_seeds():
    """constant input シナリオで 5 シード全てが bit-perfect に一致。"""
    trajectories = [_run_with_seed(s) for s in SEEDS]
    reference = trajectories[0]
    for i, traj in enumerate(trajectories[1:], start=1):
        assert np.array_equal(traj, reference), (
            f"seed={SEEDS[i]} differs from seed={SEEDS[0]}"
        )


def test_cessation_bit_perfect_across_seeds():
    """input cessation シナリオで 5 シード全てが bit-perfect に一致。"""
    trajectories = [_run_cessation_with_seed(s) for s in SEEDS]
    reference = trajectories[0]
    for i, traj in enumerate(trajectories[1:], start=1):
        assert np.array_equal(traj, reference), (
            f"seed={SEEDS[i]} differs from seed={SEEDS[0]}"
        )


def test_same_seed_produces_same_result():
    """同一シードを 2 回使うと完全に同じ結果が得られる。"""
    traj1 = _run_with_seed(42)
    traj2 = _run_with_seed(42)
    assert np.array_equal(traj1, traj2)


def test_model_is_seed_independent():
    """現モデルは決定論的でシードに依存しないことを明示確認。

    BinaryNode が random/numpy のグローバル状態を消費していない場合、
    シード設定なしの実行と、シード設定ありの実行で結果が完全一致するはず。

    このテストの意図:
    - Sprint 1 では現モデル (シード非依存) の決定論性を明示証拠化
    - Sprint 2 以降で確率要素を導入した場合、このテストは fail するはず
      → 「意図した変化の検出器」として機能する
    """
    # シード設定なしで 100 ステップ
    node1 = BinaryNode()
    traj1 = [node1.weight]
    for _ in range(100):
        node1.update(1)
        traj1.append(node1.weight)

    # シード設定ありで 100 ステップ (異なるシード値で 2 回)
    random.seed(42)
    np.random.seed(42)
    node2 = BinaryNode()
    traj2 = [node2.weight]
    for _ in range(100):
        node2.update(1)
        traj2.append(node2.weight)

    random.seed(12345)
    np.random.seed(12345)
    node3 = BinaryNode()
    traj3 = [node3.weight]
    for _ in range(100):
        node3.update(1)
        traj3.append(node3.weight)

    # 全 3 軌跡が完全一致 = シードに依存しないことの証明
    assert np.array_equal(np.array(traj1), np.array(traj2))
    assert np.array_equal(np.array(traj1), np.array(traj3))
