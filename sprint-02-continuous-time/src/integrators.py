"""
integrators モジュール

ember-network Sprint 2 の数値積分手法。
微分方程式 dw/dt = f(t, w, input(t)) を Euler 法および RK4 法で積分する。

Notes
-----
- Euler 法: 1 次精度 O(dt)
- RK4 法: 4 次精度 O(dt^4)

scipy 等の外部ライブラリは使用せず numpy のみで実装する。これは
研究の transparency と Sprint 3 以降の拡張性のための判断。
"""

from typing import Callable, Tuple

import numpy as np


def integrate_euler(dwdt_func: Callable[[float, float, int], float],
                    w_0: float,
                    t_span: Tuple[float, float],
                    dt: float,
                    input_func: Callable[[float], int]
                    ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Euler 法による数値積分。

    Parameters
    ----------
    dwdt_func : callable
        微分方程式の右辺。シグネチャ ``f(t, w, input_value) -> float``。
    w_0 : float
        t=t_span[0] での初期値。
    t_span : tuple of (float, float)
        積分区間 (t_start, t_end)。
    dt : float
        時間刻み。
    input_func : callable
        ``g(t) -> int`` 形式の入力関数。各時刻 t で 0 または 1 を返す。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列。
    w_array : numpy.ndarray
        各時刻での weight。

    Notes
    -----
    精度: O(dt) - 1 次精度。

    更新則:

        w_{i+1} = w_i + dt * f(t_i, w_i, input(t_i))

    Examples
    --------
    >>> def dwdt(t, w, inp): return 0.1 * inp - 0.05 * w
    >>> def inp(t): return 1
    >>> t, w = integrate_euler(dwdt, 0.0, (0.0, 0.1), 0.1, inp)
    >>> round(float(w[-1]), 6)
    0.01
    """
    t_array = np.arange(t_span[0], t_span[1] + dt / 2.0, dt)
    w_array = np.zeros(len(t_array))
    w_array[0] = w_0
    for i in range(len(t_array) - 1):
        t = t_array[i]
        w = w_array[i]
        dwdt = dwdt_func(t, w, input_func(t))
        w_array[i + 1] = w + dt * dwdt
    return t_array, w_array


def integrate_rk4(dwdt_func: Callable[[float, float, int], float],
                  w_0: float,
                  t_span: Tuple[float, float],
                  dt: float,
                  input_func: Callable[[float], int]
                  ) -> Tuple[np.ndarray, np.ndarray]:
    """
    RK4 法 (Runge-Kutta 4 次) による数値積分。

    Parameters
    ----------
    dwdt_func : callable
        微分方程式の右辺。シグネチャ ``f(t, w, input_value) -> float``。
    w_0 : float
        t=t_span[0] での初期値。
    t_span : tuple of (float, float)
        積分区間 (t_start, t_end)。
    dt : float
        時間刻み。
    input_func : callable
        ``g(t) -> int`` 形式の入力関数。各時刻 t で 0 または 1 を返す。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列。
    w_array : numpy.ndarray
        各時刻での weight。

    Notes
    -----
    精度: O(dt^4) - 4 次精度。

    更新則:

        k1 = f(t_i, w_i, input(t_i))
        k2 = f(t_i + dt/2, w_i + dt/2 * k1, input(t_i + dt/2))
        k3 = f(t_i + dt/2, w_i + dt/2 * k2, input(t_i + dt/2))
        k4 = f(t_i + dt,   w_i + dt   * k3, input(t_i + dt))
        w_{i+1} = w_i + dt/6 * (k1 + 2*k2 + 2*k3 + k4)

    Examples
    --------
    >>> def dwdt(t, w, inp): return 0.1 * inp - 0.05 * w
    >>> def inp(t): return 1
    >>> t, w = integrate_rk4(dwdt, 0.0, (0.0, 0.1), 0.1, inp)
    >>> round(float(w[-1]), 6)
    0.009975
    """
    t_array = np.arange(t_span[0], t_span[1] + dt / 2.0, dt)
    w_array = np.zeros(len(t_array))
    w_array[0] = w_0
    for i in range(len(t_array) - 1):
        t = t_array[i]
        w = w_array[i]
        k1 = dwdt_func(t, w, input_func(t))
        k2 = dwdt_func(
            t + dt / 2.0,
            w + dt / 2.0 * k1,
            input_func(t + dt / 2.0),
        )
        k3 = dwdt_func(
            t + dt / 2.0,
            w + dt / 2.0 * k2,
            input_func(t + dt / 2.0),
        )
        k4 = dwdt_func(
            t + dt,
            w + dt * k3,
            input_func(t + dt),
        )
        w_array[i + 1] = w + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    return t_array, w_array
