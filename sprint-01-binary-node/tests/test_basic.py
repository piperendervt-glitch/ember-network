"""
test_basic: BinaryNode の基本動作テスト

- 初期化
- update() による weight 変更
- weight が範囲 [0, 1] を超えないこと
- 不正な input_value で ValueError が発生すること
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402

from binary_node import BinaryNode  # noqa: E402


def test_initial_weight_is_zero():
    """新規 BinaryNode の weight は 0 で初期化される。"""
    node = BinaryNode()
    assert node.weight == 0.0


def test_default_parameters():
    """デフォルト learning_rate=0.1, forgetting_rate=0.05 で 1 回 update した
    結果は 0.05。"""
    node = BinaryNode()
    node.update(1)
    assert abs(node.weight - 0.05) < 1e-10


def test_custom_parameters():
    """カスタム learning_rate / forgetting_rate が反映される。"""
    node = BinaryNode(learning_rate=0.2, forgetting_rate=0.1)
    node.update(1)
    assert abs(node.weight - 0.1) < 1e-10


def test_update_increments_weight_with_input_one():
    """input=1 で weight が増加する (clip 範囲内で)。"""
    node = BinaryNode()
    prev = node.weight
    node.update(1)
    assert node.weight > prev


def test_update_decrements_weight_with_input_zero():
    """input=0 で weight が減少する (clip 範囲内で)。"""
    node = BinaryNode()
    for _ in range(5):
        node.update(1)
    prev = node.weight
    node.update(0)
    assert node.weight < prev


def test_weight_does_not_go_below_zero():
    """input=0 を繰り返しても weight は 0 未満にならない。"""
    node = BinaryNode()
    for _ in range(10):
        node.update(0)
    assert node.weight == 0.0


def test_weight_does_not_exceed_one():
    """input=1 を多数繰り返しても weight は 1.0 を超えない。"""
    node = BinaryNode()
    for _ in range(100):
        node.update(1)
    assert node.weight == 1.0


def test_invalid_input_raises_value_error():
    """input_value が 0 または 1 (int) 以外の場合 ValueError が発生する。

    bool 型 (True, False) も明示的に拒否する。Python では bool が int の
    サブクラスのため `True in (0, 1)` は True を返す。これは仕様上の
    曖昧さを排除するため拒否する。
    """
    node = BinaryNode()
    for invalid in (-1, 2, 0.5, 100, True, False, None, "1"):
        with pytest.raises(ValueError):
            node.update(invalid)


def test_reset_returns_weight_to_zero():
    """reset() は weight を 0 に戻す。"""
    node = BinaryNode()
    for _ in range(10):
        node.update(1)
    assert node.weight > 0
    node.reset()
    assert node.weight == 0.0
