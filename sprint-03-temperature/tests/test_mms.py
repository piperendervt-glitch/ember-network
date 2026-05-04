"""
test_mms: KR-S4 (Method of Manufactured Solutions による解析解との一致)

複数の製造解 (多項式・三角関数・指数関数) を SymPy で導出し、対応する強制項を
逆算して数値積分を実行。期待値が実装と完全に独立する MMS の核心 (Rule 10.3)。

各製造解で RK4 (dt=0.01) の最大誤差 < 1e-6。
"""

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from mms import (  # noqa: E402
    manufactured_polynomial,
    manufactured_trigonometric,
    manufactured_exponential,
    compute_source_term,
    manufactured_to_callable,
    integrate_with_source,
)


def _measure_max_error(T_manufactured, t_sym, T_0, t_span, dt,
                       heating_rate=0.1, cooling_rate=0.05, T_env=0.0,
                       input_value=0, integrator='rk4'):
    """MMS による最大誤差を測定する共通ロジック。"""
    source_func = compute_source_term(
        T_manufactured, t_sym, heating_rate, cooling_rate, T_env, input_value
    )
    times, T_num = integrate_with_source(
        T_0=T_0, t_span=t_span, dt=dt,
        heating_rate=heating_rate, cooling_rate=cooling_rate, T_env=T_env,
        input_value=input_value, source_func=source_func,
        integrator=integrator,
    )
    T_man_func = manufactured_to_callable(T_manufactured, t_sym)
    T_exact = np.array([T_man_func(t) for t in times])
    return float(np.max(np.abs(T_num - T_exact)))


# ----- 多項式の製造解 -----

def test_kr_s4_polynomial_quadratic():
    """T_man(t) = 0.5·t² + 0.1·t (T_0=0)。RK4 で誤差 < 1e-6。"""
    T, t = manufactured_polynomial([0.0, 0.1, 0.5])
    err = _measure_max_error(T, t, T_0=0.0, t_span=(0.0, 10.0), dt=0.01)
    assert err < 1e-6, f"polynomial quadratic 誤差: {err:.3e}"


def test_kr_s4_polynomial_cubic():
    """T_man(t) = 0.01·t³ + 0.5·t² + 0.1·t (T_0=0)。"""
    T, t = manufactured_polynomial([0.0, 0.1, 0.5, 0.01])
    err = _measure_max_error(T, t, T_0=0.0, t_span=(0.0, 5.0), dt=0.01)
    assert err < 1e-6, f"polynomial cubic 誤差: {err:.3e}"


def test_kr_s4_polynomial_constant():
    """定数の製造解 T_man(t) = 0.5。dT/dt = 0、強制項で釣り合い。"""
    T, t = manufactured_polynomial([0.5])
    err = _measure_max_error(T, t, T_0=0.5, t_span=(0.0, 10.0), dt=0.01)
    assert err < 1e-6


# ----- 三角関数の製造解 -----

def test_kr_s4_trigonometric():
    """T_man(t) = 0.3·sin(0.2·t) + 0.5 (T_0=0.5)。"""
    T, t = manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                      offset=0.5)
    err = _measure_max_error(T, t, T_0=0.5, t_span=(0.0, 30.0), dt=0.01)
    assert err < 1e-6, f"trigonometric 誤差: {err:.3e}"


def test_kr_s4_trigonometric_higher_frequency():
    """高周波 sin (frequency=1.0) でも RK4 が追従できる。"""
    T, t = manufactured_trigonometric(amplitude=0.2, frequency=1.0,
                                      offset=0.0)
    err = _measure_max_error(T, t, T_0=0.0, t_span=(0.0, 5.0), dt=0.01)
    assert err < 1e-6, f"high-frequency trig 誤差: {err:.3e}"


# ----- 指数関数の製造解 -----

def test_kr_s4_exponential():
    """T_man(t) = 1·(1 - exp(-0.05·t)) (T_0=0)。物理モデルと同形だが
    強制項を 0 に縮退させない (input=0 の問題に再キャスト)。"""
    T, t = manufactured_exponential(amplitude=1.0, decay_rate=0.05,
                                    offset=0.0)
    # input=0 で計算するとき、source は cooling_rate=0.05 とのズレを補正
    err = _measure_max_error(T, t, T_0=0.0, t_span=(0.0, 60.0), dt=0.01)
    assert err < 1e-6, f"exponential 誤差: {err:.3e}"


def test_kr_s4_exponential_different_decay_rate():
    """decay_rate=0.2 (物理 cooling_rate=0.05 と異なる)。"""
    T, t = manufactured_exponential(amplitude=0.5, decay_rate=0.2,
                                    offset=0.1)
    err = _measure_max_error(T, t, T_0=0.1, t_span=(0.0, 30.0), dt=0.01)
    assert err < 1e-6


# ----- 入力固定値を input=1 に変えた場合 -----

def test_kr_s4_polynomial_with_input_one():
    """input=1 (heating 適用時) でも MMS が機能する。"""
    T, t = manufactured_polynomial([0.0, 0.1, 0.5])
    err = _measure_max_error(T, t, T_0=0.0, t_span=(0.0, 10.0), dt=0.01,
                             input_value=1)
    assert err < 1e-6


# ----- RK4 vs Euler の比較 (RK4 が高精度) -----

def test_kr_s4_rk4_more_accurate_than_euler():
    """同じ製造解で RK4 が Euler より高精度。"""
    T, t = manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                      offset=0.5)
    err_rk4 = _measure_max_error(T, t, T_0=0.5, t_span=(0.0, 30.0),
                                 dt=0.05, integrator='rk4')
    err_euler = _measure_max_error(T, t, T_0=0.5, t_span=(0.0, 30.0),
                                   dt=0.05, integrator='euler')
    assert err_rk4 < err_euler, (
        f"RK4 ({err_rk4:.3e}) 〉= Euler ({err_euler:.3e})"
    )


# ----- KR-S4 sentinel test -----

def test_kr_s4_summary_all_three_solution_types_pass():
    """3 種類の製造解 (poly, trig, exp) すべてで誤差 < 1e-6。"""
    cases = [
        ("polynomial", manufactured_polynomial([0.0, 0.1, 0.5])),
        ("trigonometric",
         manufactured_trigonometric(amplitude=0.3, frequency=0.2,
                                    offset=0.5)),
        ("exponential",
         manufactured_exponential(amplitude=1.0, decay_rate=0.05,
                                  offset=0.0)),
    ]
    initials = {"polynomial": 0.0, "trigonometric": 0.5, "exponential": 0.0}
    errors = {}
    for name, (T, t) in cases:
        err = _measure_max_error(T, t, T_0=initials[name],
                                 t_span=(0.0, 10.0), dt=0.01)
        errors[name] = err
        assert err < 1e-6, f"{name}: 誤差 {err:.3e}"
    # 全製造解で 1e-6 を厳密達成しているか確認
    print(f"\nKR-S4 max errors: {errors}")
