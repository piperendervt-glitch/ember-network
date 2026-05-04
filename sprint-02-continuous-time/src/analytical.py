"""
analytical モジュール

ember-network Sprint 2 の解析解。
微分方程式 dw/dt = α·input - β·w (clip なし) の閉形式解を提供する。

Notes
-----
解析解の導出は Sprint 2 の SPRINT_OKR.md を参照。
"""

import numpy as np


def analytical_solution(t, w_0, input_value,
                        alpha: float = 0.1,
                        beta: float = 0.05):
    """
    clip なしの方程式 dw/dt = α·input - β·w の解析解。

    Parameters
    ----------
    t : float or numpy.ndarray
        時刻。スカラーまたは配列。
    w_0 : float
        t=0 での初期値 weight。
    input_value : int
        0 または 1。bool 型は明示的に拒否する。
    alpha : float, optional
        学習率 α。デフォルト 0.1。
    beta : float, optional
        忘却率 β。デフォルト 0.05。

    Returns
    -------
    float or numpy.ndarray
        時刻 t での weight (clip 未適用)。

    Raises
    ------
    ValueError
        input_value が 0 または 1 (int) でない場合、または bool 型の場合。

    Notes
    -----
    解析解:

    - input=1 の場合: w(t) = w_eq + (w_0 - w_eq) · exp(-β·t)
      ここで w_eq = α/β
    - input=0 の場合: w(t) = w_0 · exp(-β·t)

    Examples
    --------
    >>> w = analytical_solution(t=0.0, w_0=0.0, input_value=1)
    >>> round(w, 10)
    0.0
    >>> w = analytical_solution(t=20.0, w_0=0.0, input_value=1)
    >>> round(w, 6)
    1.264241
    """
    if isinstance(input_value, bool) or input_value not in (0, 1):
        raise ValueError(
            f"input_value must be 0 or 1 (int, not bool), "
            f"got {input_value!r} of type {type(input_value).__name__}"
        )
    t_arr = np.asarray(t, dtype=float)
    if input_value == 1:
        w_eq = alpha / beta
        result = w_eq + (w_0 - w_eq) * np.exp(-beta * t_arr)
    else:
        result = w_0 * np.exp(-beta * t_arr)
    if np.ndim(t) == 0:
        return float(result)
    return result
