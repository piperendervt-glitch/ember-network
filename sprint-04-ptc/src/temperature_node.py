"""
temperature_node モジュール (Sprint 4: PTC 効果版)

ember-network Sprint 4 の温度依存抵抗 R(T) を導入した連続時間 AAS ノード。
微分方程式
    dT/dt = (R(T) / R_0) · heating_rate · input(t) - cooling_rate · (T - T_env)
    R(T) = R_0 · (1 + α_PTC · (T - T_ref))
を 1 ステップ dt 進めて温度 T を更新する。weight および R(T)/R_0 は派生量。
"""


class TemperatureNode:
    """
    PTC 効果を導入した連続時間 AAS ノード (無次元モデル、Sprint 4 版)。

    Parameters
    ----------
    heating_rate : float, optional
        基準 (T = T_ref) における Joule 加熱率。デフォルト 0.1。
    cooling_rate : float, optional
        Newton 冷却率。デフォルト 0.05。
    T_env : float, optional
        周囲温度 (無次元)。デフォルト 0.0。
    T_max : float, optional
        最大温度 (無次元)。デフォルト 1.0。T_max > T_env が必須。
    alpha_PTC : float, optional
        PTC の温度係数 (R(T) の T 依存を支配する、新規)。デフォルト 0.3。
    T_ref : float or None, optional
        PTC 参照温度 (R(T_ref) = R_0)。None のとき T_env を使用。
    T_initial : float or None, optional
        初期温度 (reset() 後の T 値)。None のとき T_env を使用。
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
    resistance_ratio : float
        派生量 R(T) / R_0 = 1 + α_PTC · (T - T_ref) (読み取り専用 property)。
    heating_rate, cooling_rate, T_env, T_max : float
    alpha_PTC, T_ref, T_initial : float
        パラメータの読み取り専用 property。

    Notes
    -----
    物理モデル:

        Joule 加熱率は抵抗 R に比例し、PTC 素材では R が温度上昇と共に増大する
        ため、加熱率も温度上昇と共に強まる正のフィードバックを内包する。

        dT/dt = (R(T) / R_0) · heating_rate · input(t)
                - cooling_rate · (T - T_env)
        R(T) = R_0 · (1 + α_PTC · (T - T_ref))

        第 1 項: 温度依存の Joule 加熱
        第 2 項: Newton 冷却 (Sprint 3 と同形)

    State variable:

        T (温度) が primary な状態変数。w (weight) と R(T)/R_0 は派生量として
        @property でアクセス。reset() は T を T_initial にリセットする
        (Sprint 3 の T_env から変更、PRL-011 への対処)。

    Clip の物理的解釈:

        T_max は素材損傷リスクによる物理的上限 (deterrence の物理的基盤)。
        T_env は熱力学第二法則による下限 (Newton 冷却則由来の漸近境界、ただし
        α_PTC > 0 では heating 側に正のフィードバックが入るため、熱暴走時は
        clip が deterrence の安全網として機能する)。

    熱暴走の閾値:

        b = α_PTC · heating_rate · input - cooling_rate (input 一定の場合)

        b < 0 (cooling 優勢): T → T_eq に漸近 (熱平衡)
        b = 0 (臨界): T が線形成長
        b > 0 (heating 優勢): T が指数発散 (熱暴走、α_PTC > cooling_rate /
                              heating_rate = 0.5 で input=1 の場合)

        この閾値はパラメータ空間の特異点であり、温度時系列の特異点では
        ない (温度自体は連続)。

    Sprint 3 との数値的等価性 (KR-S1):

        alpha_PTC=0 のとき、R(T)/R_0 = 1 + 0 · (T - T_ref) = 1.0 となり、
        IEEE 754 の `1.0 * x == x` 性質により Sprint 3 の dT/dt と
        bit-identical な計算経路となる。

    Sprint 4 では物理単位なしの無次元モデル。物理単位の導入は Sprint 7。

    Examples
    --------
    >>> # alpha_PTC=0 で Sprint 3 と同等の挙動
    >>> node = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
    ...                        alpha_PTC=0.0, integrator='euler')
    >>> node.update(input_value=1, dt=0.1)
    >>> round(node.temperature, 6)
    0.01
    >>> round(node.weight, 6)
    0.01
    >>> round(node.resistance_ratio, 6)
    1.0

    >>> # PTC 効果あり (alpha_PTC=0.3)
    >>> node = TemperatureNode(alpha_PTC=0.3, T_initial=0.5,
    ...                        integrator='euler')
    >>> round(node.resistance_ratio, 6)  # T=0.5, T_ref=T_env=0 → 1+0.3·0.5
    1.15

    >>> # fractional input (Sprint 4 新規)
    >>> node = TemperatureNode(alpha_PTC=0.0, integrator='euler')
    >>> node.update(input_value=0.5, dt=0.1)
    >>> round(node.temperature, 6)  # 0.1·0.5·0.1 = 0.005
    0.005

    >>> # dt=0 は no-op (Sprint 4 新規、PRL-010 対処)
    >>> node = TemperatureNode(integrator='euler')
    >>> node.update(input_value=1, dt=0.1)
    >>> T_before = node.temperature
    >>> node.update(input_value=1, dt=0.0)
    >>> node.temperature == T_before
    True
    """

    def __init__(self,
                 heating_rate: float = 0.1,
                 cooling_rate: float = 0.05,
                 T_env: float = 0.0,
                 T_max: float = 1.0,
                 alpha_PTC: float = 0.3,
                 T_ref: 'float | None' = None,
                 T_initial: 'float | None' = None,
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
        self._alpha_PTC = alpha_PTC
        self._T_ref = T_env if T_ref is None else T_ref
        self._T_initial = T_env if T_initial is None else T_initial
        self._clip_enabled = clip_enabled
        self._integrator = integrator
        self._T = self._T_initial

    def _R_factor(self, T: float) -> float:
        """R(T) / R_0 = 1 + α_PTC · (T - T_ref)。"""
        return 1.0 + self._alpha_PTC * (T - self._T_ref)

    def _dTdt(self, T: float, input_value: float) -> float:
        return (self._R_factor(T) * self._heating_rate * input_value
                - self._cooling_rate * (T - self._T_env))

    def update(self, input_value: float, dt: float) -> None:
        """
        1 ステップ dt 分の時間を進める。

        Parameters
        ----------
        input_value : float
            0 から 1 の連続値 (Sprint 3 では int 0/1 のみだったが、
            Sprint 4 では fractional input をサポート、PRL-010 対処)。
            bool 型は明示的に拒否する (Python の bool は int の subclass の
            ため、fractional チェックの前に弾く必要がある)。
        dt : float
            時間刻み (非負)。dt=0 は no-op (PRL-010 対処)。

        Raises
        ------
        ValueError
            input_value が bool 型の場合、または [0, 1] の数値でない場合。
            dt が負の場合。

        Notes
        -----
        dt=0 で no-op となるのは ChatGPT I Test 8 の独立提案 (PRL-010)。
        これにより「現在状態の参照」が dt=0 でも安全に行える。
        """
        if isinstance(input_value, bool):
            raise ValueError(
                f"input_value must be a number in [0, 1], not bool, "
                f"got {input_value!r}"
            )
        if not isinstance(input_value, (int, float)):
            raise ValueError(
                f"input_value must be a number in [0, 1], "
                f"got {input_value!r} of type {type(input_value).__name__}"
            )
        if not (0 <= input_value <= 1):
            raise ValueError(
                f"input_value must be in [0, 1], got {input_value!r}"
            )
        if dt < 0:
            raise ValueError(f"dt must be non-negative, got {dt}")
        if dt == 0:
            return  # no-op (Sprint 4 新規)

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
    def resistance_ratio(self) -> float:
        """派生量 R(T) / R_0 = 1 + α_PTC · (T - T_ref) を返す (Sprint 4 新規)。"""
        return self._R_factor(self._T)

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

    @property
    def alpha_PTC(self) -> float:
        return self._alpha_PTC

    @property
    def T_ref(self) -> float:
        return self._T_ref

    @property
    def T_initial(self) -> float:
        return self._T_initial

    def reset(self) -> None:
        """T を T_initial にリセット (Sprint 3 では T_env、Sprint 4 で変更)。"""
        self._T = self._T_initial
