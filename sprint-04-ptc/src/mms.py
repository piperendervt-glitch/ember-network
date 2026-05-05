"""
mms モジュール (Method of Manufactured Solutions、Sprint 4 非線形 ODE 対応)

ember-network Sprint 4 における数値積分手法の独立検証 (Rule 10.3)。

SymPy で任意の製造解 T_man(t) を定義し、対応する強制項 s(t) を逆算する。
強制項付き ODE
    dT/dt = (1 + α_PTC · (T - T_ref)) · heating_rate · input
            - cooling_rate · (T - T_env) + s(t)
を数値積分し、数値解と T_man の誤差を測定する。

Sprint 3 からの拡張:
- 強制項の右辺が非線形 (T に対する PTC 効果あり)
- s(t) = dT_man/dt - [(1 + α_PTC · (T_man - T_ref)) · heating_rate · input
                       - cooling_rate · (T_man - T_env)]
- 数値積分時は非線形項に「数値解 T」を代入 (製造解 T_man ではない)

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
                        input_value: float = 0.0,
                        alpha_PTC: float = 0.0,
                        T_ref: 'float | None' = None
                        ) -> Callable[[float], float]:
    """製造解から強制項 s(t) を逆算 (Sprint 4 非線形版)。

    s(t) = dT_man/dt
           - [(1 + α_PTC · (T_man - T_ref)) · heating_rate · input
              - cooling_rate · (T_man - T_env)]

    Parameters
    ----------
    T_manufactured : sympy expression
        製造解 T_man(t) の SymPy 表現。
    t_sym : sympy.Symbol
        独立変数 t。
    heating_rate, cooling_rate, T_env : float
        モデルパラメータ。
    input_value : float, optional
        固定 input ([0, 1])。デフォルト 0.0。
    alpha_PTC : float, optional
        PTC の温度係数。デフォルト 0.0 (= Sprint 3 と数学的に同形)。
    T_ref : float or None, optional
        PTC 参照温度。None のとき T_env を使用。

    Returns
    -------
    source_func : callable
        s(t) を numpy 互換で評価するスカラー関数。

    Notes
    -----
    SymPy で記号微分し、lambdify で関数化する。期待値が実装と完全に独立する
    のが MMS の核心 (Rule 10.3)。alpha_PTC=0 のとき、Sprint 3 の MMS と
    数学的に同形になる。

    Examples
    --------
    >>> T, t = manufactured_polynomial([0.0, 1.0])  # T_man = t
    >>> # alpha_PTC=0、input=0: dT/dt=1, 線形 RHS=-0.05·t, source=1+0.05·t
    >>> source = compute_source_term(T, t, heating_rate=0.1,
    ...                               cooling_rate=0.05, T_env=0.0,
    ...                               input_value=0.0, alpha_PTC=0.0)
    >>> round(source(0.0), 6)
    1.0
    >>> round(source(2.0), 6)
    1.1

    >>> # alpha_PTC=0.5, input=1, T_ref=0: 非線形項 (1 + 0.5·t)·0.1·1 が増加
    >>> # dT/dt=1, 非線形 RHS=(1+0.5·t)·0.1 - 0.05·t
    >>> # source = 1 - [(1+0.5·t)·0.1 - 0.05·t] = 1 - 0.1 - 0.05·t + 0.05·t
    >>> #        = 0.9 (定数!)
    >>> source = compute_source_term(T, t, heating_rate=0.1,
    ...                               cooling_rate=0.05, T_env=0.0,
    ...                               input_value=1.0, alpha_PTC=0.5)
    >>> round(source(0.0), 6)
    0.9
    >>> round(source(5.0), 6)
    0.9
    """
    if T_ref is None:
        T_ref = T_env

    dT_dt = sp.diff(T_manufactured, t_sym)
    rhs_full = ((1 + alpha_PTC * (T_manufactured - T_ref))
                * heating_rate * input_value
                - cooling_rate * (T_manufactured - T_env))
    source_expr = dT_dt - rhs_full
    source_func = sp.lambdify(t_sym, source_expr, modules='numpy')

    def safe_source(t_val: float) -> float:
        result = source_func(t_val)
        if np.isscalar(result):
            return float(result)
        return float(result)
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
                          input_value: float,
                          source_func: Callable[[float], float],
                          alpha_PTC: float = 0.0,
                          T_ref: 'float | None' = None,
                          integrator: str = 'rk4'
                          ) -> Tuple[np.ndarray, np.ndarray]:
    """強制項付きで非線形 ODE を数値積分 (Sprint 4 PTC 版)。

    dT/dt = (1 + α_PTC · (T - T_ref)) · heating_rate · input
            - cooling_rate · (T - T_env) + s(t)

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
    input_value : float
        固定 input ([0, 1])。シナリオを単純化するため、ステップ内で
        input が固定される運用 (PRL-003 への対処の継続)。
    source_func : callable
        強制項 s(t) を返すスカラー関数。
    alpha_PTC : float, optional
        PTC の温度係数。デフォルト 0.0。
    T_ref : float or None, optional
        PTC 参照温度。None のとき T_env を使用。
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
    >>> # alpha_PTC=0 で Sprint 3 と同等の MMS 検証
    >>> T_man, t_sym = manufactured_polynomial([0.0, 1.0])
    >>> source = compute_source_term(T_man, t_sym, 0.1, 0.05, 0.0, 0.0,
    ...                               alpha_PTC=0.0)
    >>> times, T = integrate_with_source(
    ...     T_0=0.0, t_span=(0.0, 1.0), dt=0.1,
    ...     heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
    ...     input_value=0.0, source_func=source, alpha_PTC=0.0)
    >>> len(times)
    11
    >>> bool(abs(T[-1] - 1.0) < 1e-10)  # T_man(1.0) = 1.0
    True

    >>> # alpha_PTC=0.5 (非線形) でも MMS が成立
    >>> source = compute_source_term(T_man, t_sym, 0.1, 0.05, 0.0, 1.0,
    ...                               alpha_PTC=0.5)
    >>> times, T = integrate_with_source(
    ...     T_0=0.0, t_span=(0.0, 1.0), dt=0.1,
    ...     heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
    ...     input_value=1.0, source_func=source, alpha_PTC=0.5)
    >>> bool(abs(T[-1] - 1.0) < 1e-10)  # T_man(1.0) = 1.0
    True
    """
    if integrator not in ('euler', 'rk4'):
        raise ValueError(
            f"integrator must be 'euler' or 'rk4', got {integrator!r}"
        )
    if T_ref is None:
        T_ref = T_env

    t_start, t_end = t_span
    n_steps = int(round((t_end - t_start) / dt))
    times = t_start + np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    T_array[0] = T_0

    def f(t: float, T_val: float) -> float:
        R_factor = 1.0 + alpha_PTC * (T_val - T_ref)
        return (R_factor * heating_rate * input_value
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
