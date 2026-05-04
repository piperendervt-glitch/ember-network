"""
binary_node モジュール

ember-network Sprint 1 の最小概念実装。
AAS (Adaptive Artificial Synapse) の核心ルール「使うと増える、使わないと減る」を
離散時間 binary input モデルで体現する。

Notes
-----
このモジュールは Sprint 1 の概念モデルであり、物理単位 (温度、抵抗、Joule 加熱) は
含まない。物理モデルへの拡張は Sprint 2 (連続時間)、Sprint 3 (温度変数) 以降で行う。
"""


class BinaryNode:
    """
    AAS 核心ルールの最小概念実装。

    Parameters
    ----------
    learning_rate : float, optional
        入力時の weight 増加量。デフォルト 0.1。
    forgetting_rate : float, optional
        各ステップでの weight 減少量。デフォルト 0.05。

    Attributes
    ----------
    weight : float
        現在の weight (読み取り専用 property)。値域 [0, 1]、初期値 0。

    Notes
    -----
    数学モデル:

        weight(t+1) = clip(weight(t) + learning_rate * input(t)
                           - forgetting_rate, 0, 1)

    物理的解釈:

    - input=1: 経路を使った状態 (Joule 加熱に相当、ember が燃える)
    - input=0: 経路を使わない状態 (自然冷却に相当、ember が冷める)
    - learning_rate: 加熱強度に相当
    - forgetting_rate: 冷却強度に相当
    - weight: 経路の重み (PTC の抵抗変化量に相当する量)

    Examples
    --------
    >>> node = BinaryNode()
    >>> node.weight
    0.0
    >>> node.update(1)
    >>> round(node.weight, 10)
    0.05
    """

    def __init__(self, learning_rate: float = 0.1,
                 forgetting_rate: float = 0.05) -> None:
        self._learning_rate = learning_rate
        self._forgetting_rate = forgetting_rate
        self._weight = 0.0

    def update(self, input_value: int) -> None:
        """
        1 ステップの更新。

        Parameters
        ----------
        input_value : int
            0 または 1。bool 型は明示的に拒否する。

        Raises
        ------
        ValueError
            input_value が 0 または 1 (int) でない場合、または bool 型の場合。
        """
        if isinstance(input_value, bool) or input_value not in (0, 1):
            raise ValueError(
                f"input_value must be 0 or 1 (int, not bool), "
                f"got {input_value!r} of type {type(input_value).__name__}"
            )
        new_weight = (
            self._weight
            + self._learning_rate * input_value
            - self._forgetting_rate
        )
        if new_weight < 0.0:
            new_weight = 0.0
        elif new_weight > 1.0:
            new_weight = 1.0
        self._weight = new_weight

    @property
    def weight(self) -> float:
        """現在の weight を返す。"""
        return self._weight

    def reset(self) -> None:
        """weight を 0 にリセット。"""
        self._weight = 0.0
