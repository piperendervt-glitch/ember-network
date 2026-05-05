"""
analytical モジュール (Sprint 4)

ember-network Sprint 4 の温度方程式 (clip なし、input 一定) の閉形式解。

主方程式 (input = input_value で一定、clip なし):

    dT/dt = (1 + α_PTC · (T - T_ref)) · heating_rate · input
           - cooling_rate · (T - T_env)
          = a + b · T

where:
    a = heating_rate · input · (1 - α_PTC · T_ref) + cooling_rate · T_env
    b = α_PTC · heating_rate · input - cooling_rate

解 (場合分け):

    b ≠ 0: T(t) = -a/b + (T_0 + a/b) · exp(b · t)
    b = 0: T(t) = T_0 + a · t            (線形成長、臨界条件)

熱暴走の閾値:
    α_PTC > cooling_rate / heating_rate  (input=1 のとき)
    上記が成立すると b > 0 となり T が指数発散 (deterrence の物理的限界)。

Notes
-----
Sprint 3 の analytical_temperature と異なり、入力が fractional (input ∈ [0, 1])、
PTC 効果あり、3 ケース場合分けあり。α_PTC=0 で b = -cooling_rate となり
Sprint 3 の解析解と数学的に同形 (KR-S1 の前提)。
"""

import numpy as np


def analytical_temperature(t,
                           T_0: float,
                           input_value: float,
                           heating_rate: float = 0.1,
                           cooling_rate: float = 0.05,
                           T_env: float = 0.0,
                           alpha_PTC: float = 0.0,
                           T_ref: 'float | None' = None):
    """
    Sprint 4 の温度 ODE (clip なし、input 一定) の閉形式解。

    Parameters
    ----------
    t : float or numpy.ndarray
        時刻。スカラーまたは配列。
    T_0 : float
        t=0 での初期温度 (= T_initial に対応)。
    input_value : float
        固定 input ([0, 1] の連続値、Sprint 4 で fractional input サポート)。
        bool は明示的に拒否。
    heating_rate : float, optional
        基準 (T = T_ref) における Joule 加熱率。デフォルト 0.1。
    cooling_rate : float, optional
        Newton 冷却率。デフォルト 0.05。
    T_env : float, optional
        周囲温度。デフォルト 0.0。
    alpha_PTC : float, optional
        PTC の温度係数。デフォルト 0.0 (= Sprint 3 と数学的に同形)。
    T_ref : float or None, optional
        PTC 参照温度。None のとき T_env を使用。

    Returns
    -------
    float or numpy.ndarray
        時刻 t での温度 T (clip 未適用)。

    Raises
    ------
    ValueError
        input_value が bool 型または [0, 1] の数値でない場合。

    Notes
    -----
    a, b の数学定義:

        a = heating_rate · input · (1 - α_PTC · T_ref) + cooling_rate · T_env
        b = α_PTC · heating_rate · input - cooling_rate

    b の符号で場合分け:

        b < 0 (cooling 優勢): T → -a/b に漸近 (熱平衡)
        b = 0 (臨界): T(t) = T_0 + a · t (線形成長)
        b > 0 (heating 優勢): T(t) は指数発散 (熱暴走)

    Examples
    --------
    >>> # alpha_PTC=0, input=1: Sprint 3 解析解 (b<0、T → 2.0)
    >>> T = analytical_temperature(t=0.0, T_0=0.0, input_value=1.0,
    ...                             alpha_PTC=0.0)
    >>> round(T, 10)
    0.0
    >>> T = analytical_temperature(t=20.0, T_0=0.0, input_value=1.0,
    ...                             alpha_PTC=0.0)
    >>> round(T, 6)
    1.264241

    >>> # alpha_PTC=0.5, input=1: 臨界条件 b=0、線形成長
    >>> T = analytical_temperature(t=10.0, T_0=0.0, input_value=1.0,
    ...                             alpha_PTC=0.5)
    >>> round(T, 6)  # 0.1 · 10 = 1.0
    1.0

    >>> # alpha_PTC=1.0, input=1: 急激な熱暴走 b=0.05、解析解は指数発散
    >>> T = analytical_temperature(t=10.0, T_0=0.0, input_value=1.0,
    ...                             alpha_PTC=1.0)
    >>> round(T, 6)  # -2 + 2·exp(0.5) = -2 + 2·1.648721 = 1.297443
    1.297443

    >>> # 配列入力
    >>> import numpy as np
    >>> ts = np.array([0.0, 10.0])
    >>> T = analytical_temperature(t=ts, T_0=0.0, input_value=1.0,
    ...                             alpha_PTC=0.5)
    >>> [round(float(x), 6) for x in T]
    [0.0, 1.0]
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

    if T_ref is None:
        T_ref = T_env

    a = (heating_rate * input_value * (1.0 - alpha_PTC * T_ref)
         + cooling_rate * T_env)
    b = alpha_PTC * heating_rate * input_value - cooling_rate

    t_arr = np.asarray(t, dtype=float)

    if b == 0:
        # 線形成長
        result = T_0 + a * t_arr
    else:
        # 指数解 (b<0 で漸近、b>0 で発散)
        T_p = -a / b
        result = T_p + (T_0 - T_p) * np.exp(b * t_arr)

    if np.ndim(t) == 0:
        return float(result)
    return result


def equilibrium_temperature(input_value: float,
                            heating_rate: float = 0.1,
                            cooling_rate: float = 0.05,
                            T_env: float = 0.0,
                            alpha_PTC: float = 0.0,
                            T_ref: 'float | None' = None
                            ) -> 'float | None':
    """
    平衡点 T_eq (b < 0 の場合のみ存在) を返す。b >= 0 では None。

    T_eq = -a/b (b < 0 のとき、t → ∞ での漸近値)

    Parameters
    ----------
    input_value : float
        固定 input ([0, 1])。
    その他: analytical_temperature と同じ。

    Returns
    -------
    float or None
        平衡点 T_eq (b < 0 のとき)、または None (b >= 0 のとき、熱暴走)。

    Examples
    --------
    >>> # alpha_PTC=0, input=1: T_eq = 0.1/0.05 = 2.0
    >>> equilibrium_temperature(input_value=1.0, alpha_PTC=0.0)
    2.0

    >>> # alpha_PTC=0.5, input=1: b=0、平衡点なし
    >>> equilibrium_temperature(input_value=1.0, alpha_PTC=0.5) is None
    True

    >>> # alpha_PTC=0.6, input=1: 熱暴走 (b>0)、平衡点なし
    >>> equilibrium_temperature(input_value=1.0, alpha_PTC=0.6) is None
    True

    >>> # alpha_PTC=0.4, input=1: T_eq = 0.1/0.01 = 10.0
    >>> # (浮動小数点誤差を考慮して round で表示)
    >>> round(equilibrium_temperature(input_value=1.0, alpha_PTC=0.4), 10)
    10.0
    """
    if T_ref is None:
        T_ref = T_env
    a = (heating_rate * input_value * (1.0 - alpha_PTC * T_ref)
         + cooling_rate * T_env)
    b = alpha_PTC * heating_rate * input_value - cooling_rate
    if b >= 0:
        return None
    return -a / b
