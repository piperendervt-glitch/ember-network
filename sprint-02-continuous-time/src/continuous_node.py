"""
continuous_node モジュール

ember-network Sprint 2 の連続時間版 AAS ノード。
微分方程式 dw/dt = α·input(t) - β·w(t) を 1 ステップ dt 進めて weight を
更新する。clip 有効/無効を選択可能。
"""


class ContinuousNode:
    """
    連続時間版の AAS ノード。

    Parameters
    ----------
    learning_rate : float, optional
        学習率 α。デフォルト 0.1。
    forgetting_rate : float, optional
        忘却率 β。デフォルト 0.05。
    clip_enabled : bool, optional
        weight を [0, 1] に制限するか。デフォルト True。
    integrator : {'euler', 'rk4'}, optional
        数値積分手法。デフォルト 'rk4'。

    Attributes
    ----------
    weight : float
        現在の weight (読み取り専用 property)。

    Notes
    -----
    数学モデル:

        dw/dt = α·input(t) - β·w(t)

    平衡点:

        w_eq = α/β = 2.0 (デフォルト値)
        clip 有効時は実質的に 1.0 で頭打ち

    時定数:

        τ = 1/β = 20 (デフォルト値)

    物理的解釈:

    - dw/dt = α·input(t) - β·w(t) は Newton の冷却則と同型
    - α·input: Joule 加熱による上昇率 (input=1 で電流が流れている時)
    - β·w(t): 周囲への熱放散による低下率 (温度差に比例)

    Sprint 2 では物理単位なしの抽象モデル。温度、抵抗、Joule 加熱の
    数式は Sprint 3 以降で導入。

    Examples
    --------
    >>> node = ContinuousNode(learning_rate=0.1, forgetting_rate=0.05,
    ...                       integrator='euler')
    >>> node.update(input_value=1, dt=0.1)
    >>> round(node.weight, 6)
    0.01
    """

    def __init__(self, learning_rate: float = 0.1,
                 forgetting_rate: float = 0.05,
                 clip_enabled: bool = True,
                 integrator: str = 'rk4') -> None:
        if integrator not in ('euler', 'rk4'):
            raise ValueError(
                f"integrator must be 'euler' or 'rk4', got {integrator!r}"
            )
        self._alpha = learning_rate
        self._beta = forgetting_rate
        self._clip_enabled = clip_enabled
        self._integrator = integrator
        self._weight = 0.0

    def _dwdt(self, w: float, input_value: int) -> float:
        return self._alpha * input_value - self._beta * w

    def update(self, input_value: int, dt: float) -> None:
        """
        1 ステップ dt 分の時間を進める。

        Parameters
        ----------
        input_value : int
            0 または 1。bool 型は明示的に拒否する。
        dt : float
            時間刻み (正の値)。

        Raises
        ------
        ValueError
            input_value が 0 または 1 (int) でない場合、または bool 型の場合。
            dt が正でない場合。
        """
        if isinstance(input_value, bool) or input_value not in (0, 1):
            raise ValueError(
                f"input_value must be 0 or 1 (int, not bool), "
                f"got {input_value!r} of type {type(input_value).__name__}"
            )
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")

        w = self._weight
        if self._integrator == 'euler':
            new_w = w + dt * self._dwdt(w, input_value)
        else:
            k1 = self._dwdt(w, input_value)
            k2 = self._dwdt(w + dt / 2.0 * k1, input_value)
            k3 = self._dwdt(w + dt / 2.0 * k2, input_value)
            k4 = self._dwdt(w + dt * k3, input_value)
            new_w = w + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        if self._clip_enabled:
            if new_w < 0.0:
                new_w = 0.0
            elif new_w > 1.0:
                new_w = 1.0
        self._weight = new_w

    @property
    def weight(self) -> float:
        """現在の weight を返す。"""
        return self._weight

    def reset(self) -> None:
        """weight を 0 にリセット。"""
        self._weight = 0.0
