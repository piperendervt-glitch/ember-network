"""
temperature_node モジュール

ember-network Sprint 3 の温度変数を導入した連続時間 AAS ノード。
微分方程式 dT/dt = heating_rate·input - cooling_rate·(T - T_env) を
1 ステップ dt 進めて温度 T を更新する。weight は派生量。
"""


class TemperatureNode:
    """
    温度変数を導入した連続時間 AAS ノード (無次元モデル)。

    Parameters
    ----------
    heating_rate : float, optional
        加熱率 (Sprint 2 の learning_rate=α に対応)。デフォルト 0.1。
    cooling_rate : float, optional
        冷却率 (Sprint 2 の forgetting_rate=β に対応)。デフォルト 0.05。
    T_env : float, optional
        周囲温度 (無次元)。デフォルト 0.0。
    T_max : float, optional
        最大温度 (無次元)。デフォルト 1.0。T_max > T_env が必須。
    clip_enabled : bool, optional
        T を [T_env, T_max] に物理的に制限するか。デフォルト True。
    integrator : {'euler', 'rk4'}, optional
        数値積分手法。デフォルト 'rk4'。

    Attributes
    ----------
    temperature : float
        現在の温度 T (primary な状態変数、読み取り専用 property)。
    weight : float
        派生量 w = (T - T_env) / (T_max - T_env) (読み取り専用 property)。
    heating_rate, cooling_rate, T_env, T_max : float
        パラメータの読み取り専用 property。

    Notes
    -----
    物理モデル:

        PTC 経路の温度変化を以下の熱方程式で記述する。

        dT/dt = heating_rate · input(t) - cooling_rate · (T - T_env)

        第 1 項 heating_rate · input: Joule 加熱率
        - input=1 の時、抵抗 R_0 で電流 I_max が流れ、Joule 熱が発生
        - heating_rate = R_0 · I_max² / C_thermal (Sprint 7 で物理単位を導入)

        第 2 項 -cooling_rate · (T - T_env): Newton 冷却率
        - 温度差 (T - T_env) に比例した周囲への熱拡散
        - cooling_rate = 1 / τ_cool (時定数 τ_cool の逆数)

    State variable:

        T (温度) が primary な状態変数。
        w (weight) は派生量として @property でアクセス。
        reset() は T を T_env にリセットする。
        update() は T を進化させる。

    Clip の物理的解釈:

        T_max は素材損傷リスクによる物理的上限 (deterrence の物理的基盤)。
        T_env は熱力学第二法則による下限 (Newton 冷却則は T < T_env を
        生成しない、漸近境界)。clip は数値解の float 誤差や境界外への
        safety net として機能する。

    Sprint 2 との数値的等価性:

        T_env=0, T_max=1, heating_rate=α, cooling_rate=β のとき、
        IEEE 754 の `T - 0.0 == T` 性質により dT/dt の計算は Sprint 2 の
        dw/dt と bit-identical となる (KR-S1)。

    Sprint 3 では物理単位なしの無次元モデル。物理単位の導入は Sprint 7、
    PTC 効果 (温度依存の抵抗 R(T)) は Sprint 4 で導入する。

    Examples
    --------
    >>> node = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
    ...                        integrator='euler')
    >>> node.update(input_value=1, dt=0.1)
    >>> round(node.temperature, 6)
    0.01
    >>> round(node.weight, 6)
    0.01
    """

    def __init__(self,
                 heating_rate: float = 0.1,
                 cooling_rate: float = 0.05,
                 T_env: float = 0.0,
                 T_max: float = 1.0,
                 clip_enabled: bool = True,
                 integrator: str = 'rk4') -> None:
        if integrator not in ('euler', 'rk4'):
            raise ValueError(
                f"integrator must be 'euler' or 'rk4', got {integrator!r}"
            )
        if not (T_max > T_env):
            raise ValueError(
                f"T_max must be greater than T_env, "
                f"got T_max={T_max}, T_env={T_env}"
            )
        self._heating_rate = heating_rate
        self._cooling_rate = cooling_rate
        self._T_env = T_env
        self._T_max = T_max
        self._clip_enabled = clip_enabled
        self._integrator = integrator
        self._T = T_env  # 初期温度は周囲温度

    def _dTdt(self, T: float, input_value: int) -> float:
        return (self._heating_rate * input_value
                - self._cooling_rate * (T - self._T_env))

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

        T = self._T
        if self._integrator == 'euler':
            new_T = T + dt * self._dTdt(T, input_value)
        else:
            k1 = self._dTdt(T, input_value)
            k2 = self._dTdt(T + dt / 2.0 * k1, input_value)
            k3 = self._dTdt(T + dt / 2.0 * k2, input_value)
            k4 = self._dTdt(T + dt * k3, input_value)
            new_T = T + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

        if self._clip_enabled:
            if new_T < self._T_env:
                new_T = self._T_env
            elif new_T > self._T_max:
                new_T = self._T_max
        self._T = new_T

    @property
    def temperature(self) -> float:
        """現在の温度 T を返す (primary な状態変数)。"""
        return self._T

    @property
    def weight(self) -> float:
        """派生量 w = (T - T_env) / (T_max - T_env) を返す。"""
        return (self._T - self._T_env) / (self._T_max - self._T_env)

    @property
    def heating_rate(self) -> float:
        return self._heating_rate

    @property
    def cooling_rate(self) -> float:
        return self._cooling_rate

    @property
    def T_env(self) -> float:
        return self._T_env

    @property
    def T_max(self) -> float:
        return self._T_max

    def reset(self) -> None:
        """T を T_env にリセット。"""
        self._T = self._T_env
