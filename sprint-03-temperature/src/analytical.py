"""
analytical モジュール

ember-network Sprint 3 の温度方程式 dT/dt = heating_rate·input -
cooling_rate·(T - T_env) (clip なし) の閉形式解。

Notes
-----
- input=1: T(t) = T_eq + (T_0 - T_eq) · exp(-cooling_rate · t)
  ここで T_eq = T_env + heating_rate / cooling_rate
- input=0: T(t) = T_env + (T_0 - T_env) · exp(-cooling_rate · t)

T_env=0 のときは Sprint 2 の解析解と完全に同形になる。
"""

import numpy as np


def analytical_temperature(t,
                           T_0: float,
                           input_value: int,
                           heating_rate: float = 0.1,
                           cooling_rate: float = 0.05,
                           T_env: float = 0.0):
    """
    clip なしの方程式 dT/dt = heating_rate·input - cooling_rate·(T - T_env)
    の解析解。

    Parameters
    ----------
    t : float or numpy.ndarray
        時刻。スカラーまたは配列。
    T_0 : float
        t=0 での初期温度。
    input_value : int
        0 または 1。bool 型は明示的に拒否する。
    heating_rate : float, optional
        加熱率。デフォルト 0.1。
    cooling_rate : float, optional
        冷却率。デフォルト 0.05。
    T_env : float, optional
        周囲温度。デフォルト 0.0。

    Returns
    -------
    float or numpy.ndarray
        時刻 t での温度 T (clip 未適用)。

    Raises
    ------
    ValueError
        input_value が 0 または 1 (int) でない場合、または bool 型の場合。

    Notes
    -----
    導出:
        dT/dt + cooling_rate · T = heating_rate · input + cooling_rate · T_env
        T_eq = T_env + heating_rate · input / cooling_rate (input が固定の場合)

        input=1: T_eq = T_env + heating_rate / cooling_rate
        input=0: T_eq = T_env (純粋な指数減衰、T → T_env に漸近)

    Examples
    --------
    >>> T = analytical_temperature(t=0.0, T_0=0.0, input_value=1)
    >>> round(T, 10)
    0.0
    >>> T = analytical_temperature(t=20.0, T_0=0.0, input_value=1)
    >>> round(T, 6)
    1.264241
    """
    if isinstance(input_value, bool) or input_value not in (0, 1):
        raise ValueError(
            f"input_value must be 0 or 1 (int, not bool), "
            f"got {input_value!r} of type {type(input_value).__name__}"
        )
    t_arr = np.asarray(t, dtype=float)
    if input_value == 1:
        T_eq = T_env + heating_rate / cooling_rate
    else:
        T_eq = T_env
    result = T_eq + (T_0 - T_eq) * np.exp(-cooling_rate * t_arr)
    if np.ndim(t) == 0:
        return float(result)
    return result
