"""
mms モジュール (Method of Manufactured Solutions)

ember-network Sprint 3 における数値積分手法の独立検証。

SymPy で任意の製造解 T_man(t) を定義し、対応する強制項 s(t) を逆算する。
強制項付き ODE
    dT/dt = heating_rate · input - cooling_rate · (T - T_env) + s(t)
を数値積分し、数値解と T_man の誤差を測定することで RK4 の精度を
製造解と独立に検証する (Rule 10.3)。

Notes
-----
製造解 T_man(t) を任意に選べるため、検証時の期待値が実装と完全に独立する。
これにより doctest 自己参照 (PRL-005) を回避する。
"""

from typing import Callable, Tuple

import numpy as np
import sympy as sp


def manufactured_polynomial(coefficients):
    """多項式の製造解 T(t) = sum_i c_i · t^i を SymPy で生成。

    Parameters
    ----------
    coefficients : sequence of float
        最低次から並べた係数 [c_0, c_1, c_2, ...]。

    Returns
    -------
    T : sympy expression
        T(t) の SymPy 表現。
    t_sym : sympy.Symbol
        独立変数 t のシンボル。

    Examples
    --------
    >>> T, t = manufactured_polynomial([0.0, 0.1, 0.5])
    >>> T
    0.5*t**2 + 0.1*t
    """
    t = sp.Symbol('t', real=True)
    T = sum(c * t**i for i, c in enumerate(coefficients))
    return sp.sympify(T), t


def manufactured_trigonometric(amplitude: float,
                               frequency: float,
                               offset: float):
    """三角関数の製造解 T(t) = amplitude · sin(frequency · t) + offset。

    Examples
    --------
    >>> T, t = manufactured_trigonometric(0.3, 0.2, 0.5)
    >>> T
    0.3*sin(0.2*t) + 0.5
    """
    t = sp.Symbol('t', real=True)
    T = amplitude * sp.sin(frequency * t) + offset
    return T, t


def manufactured_exponential(amplitude: float,
                             decay_rate: float,
                             offset: float):
    """指数関数の製造解 T(t) = amplitude · (1 - exp(-decay_rate · t)) + offset。

    Examples
    --------
    >>> T, t = manufactured_exponential(1.0, 0.05, 0.0)
    >>> sp.simplify(T - (1 - sp.exp(-0.05 * t))) == 0
    True
    """
    t = sp.Symbol('t', real=True)
    T = amplitude * (1 - sp.exp(-decay_rate * t)) + offset
    return T, t


def compute_source_term(T_manufactured,
                        t_sym,
                        heating_rate: float,
                        cooling_rate: float,
                        T_env: float,
                        input_value: int = 0
                        ) -> Callable[[float], float]:
    """製造解から強制項 s(t) を逆算。

    s(t) = dT_man/dt - (heating_rate · input - cooling_rate · (T_man - T_env))

    Returns
    -------
    source_func : callable
        s(t) を numpy 互換で評価するスカラー関数。

    Notes
    -----
    SymPy で記号微分し、lambdify で関数化する。期待値が実装と完全に独立
    するのが MMS の核心 (Rule 10.3)。

    Examples
    --------
    >>> T, t = manufactured_polynomial([0.0, 1.0])  # T_man = t
    >>> source = compute_source_term(T, t, heating_rate=0.1,
    ...                               cooling_rate=0.05, T_env=0.0,
    ...                               input_value=0)
    >>> # T_man = t, dT/dt = 1, RHS = -0.05·t, source = 1 + 0.05·t
    >>> round(source(0.0), 6)
    1.0
    >>> round(source(2.0), 6)
    1.1
    """
    dT_dt = sp.diff(T_manufactured, t_sym)
    rhs_homogeneous = (heating_rate * input_value
                       - cooling_rate * (T_manufactured - T_env))
    source_expr = dT_dt - rhs_homogeneous
    source_func = sp.lambdify(t_sym, source_expr, modules='numpy')

    # SymPy が定数式に対して非配列対応の関数を返す場合のラッパ
    def safe_source(t_val: float) -> float:
        result = source_func(t_val)
        return float(result) if np.isscalar(result) else float(result)
    return safe_source


def manufactured_to_callable(T_manufactured, t_sym
                             ) -> Callable[[float], float]:
    """製造解 SymPy 表現を numpy 互換のスカラー関数に変換。"""
    func = sp.lambdify(t_sym, T_manufactured, modules='numpy')

    def safe_func(t_val):
        result = func(t_val)
        return result
    return safe_func


def integrate_with_source(T_0: float,
                          t_span: Tuple[float, float],
                          dt: float,
                          heating_rate: float,
                          cooling_rate: float,
                          T_env: float,
                          input_value: int,
                          source_func: Callable[[float], float],
                          integrator: str = 'rk4'
                          ) -> Tuple[np.ndarray, np.ndarray]:
    """強制項付きで dT/dt = heating_rate·input - cooling_rate·(T - T_env)
    + s(t) を数値積分。

    Parameters
    ----------
    T_0 : float
        初期温度。
    t_span : tuple of (float, float)
        (t_start, t_end)。
    dt : float
        時間刻み。
    heating_rate, cooling_rate, T_env : float
        モデルパラメータ。
    input_value : int
        固定 input (0 または 1)。シナリオを単純化するため、ステップ内で
        input が固定される運用 (PRL-003 への対処の継続)。
    source_func : callable
        強制項 s(t) を返すスカラー関数。
    integrator : {'euler', 'rk4'}, optional
        数値積分手法。デフォルト 'rk4'。

    Returns
    -------
    times : numpy.ndarray
        時刻配列、shape (n_steps + 1,)。
    T_array : numpy.ndarray
        各時刻での数値解 T。

    Examples
    --------
    >>> T_man, t_sym = manufactured_polynomial([0.0, 1.0])
    >>> source = compute_source_term(T_man, t_sym, 0.1, 0.05, 0.0, 0)
    >>> times, T = integrate_with_source(
    ...     T_0=0.0, t_span=(0.0, 1.0), dt=0.1,
    ...     heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
    ...     input_value=0, source_func=source)
    >>> len(times)
    11
    >>> bool(abs(T[-1] - 1.0) < 1e-10)  # T_man(1.0) = 1.0
    True
    """
    if integrator not in ('euler', 'rk4'):
        raise ValueError(
            f"integrator must be 'euler' or 'rk4', got {integrator!r}"
        )
    t_start, t_end = t_span
    n_steps = int(round((t_end - t_start) / dt))
    times = t_start + np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    T_array[0] = T_0

    def f(t: float, T_val: float) -> float:
        return (heating_rate * input_value
                - cooling_rate * (T_val - T_env)
                + source_func(t))

    T = T_0
    for i in range(n_steps):
        t = times[i]
        if integrator == 'rk4':
            k1 = f(t, T)
            k2 = f(t + dt / 2.0, T + dt / 2.0 * k1)
            k3 = f(t + dt / 2.0, T + dt / 2.0 * k2)
            k4 = f(t + dt, T + dt * k3)
            T = T + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        else:
            T = T + dt * f(t, T)
        T_array[i + 1] = T
    return times, T_array
