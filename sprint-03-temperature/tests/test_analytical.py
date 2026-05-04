"""
test_analytical: analytical_temperature の検証

解析解 T(t) = T_eq + (T_0 - T_eq)·exp(-cooling_rate·t) の境界値・単調性等。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from analytical import analytical_temperature  # noqa: E402


def test_at_t_zero_returns_T_0():
    """t=0 で T_0 を返す。"""
    T = analytical_temperature(t=0.0, T_0=0.5, input_value=1)
    assert abs(T - 0.5) < 1e-15


def test_input_one_approaches_T_eq():
    """input=1 で長時間後、T_eq = T_env + heating/cooling に漸近。"""
    T = analytical_temperature(t=1000.0, T_0=0.0, input_value=1,
                               heating_rate=0.1, cooling_rate=0.05,
                               T_env=0.0)
    assert abs(T - 2.0) < 1e-15


def test_input_zero_approaches_T_env():
    """input=0 で長時間後、T_env に漸近。"""
    T = analytical_temperature(t=1000.0, T_0=1.0, input_value=0,
                               cooling_rate=0.05, T_env=0.0)
    assert abs(T - 0.0) < 1e-15


def test_input_zero_with_nonzero_T_env():
    """T_env != 0 の場合、input=0 で T → T_env に漸近。"""
    T = analytical_temperature(t=1000.0, T_0=20.0, input_value=0,
                               cooling_rate=0.05, T_env=10.0)
    assert abs(T - 10.0) < 1e-12


def test_t_clip_in_unit_T_max_setup():
    """t_clip = 20·ln(2) で T = 1 (T_env=0, T_max=1, heating/cooling=2)。"""
    t_clip = 20.0 * np.log(2.0)
    T = analytical_temperature(t=t_clip, T_0=0.0, input_value=1)
    assert abs(T - 1.0) < 1e-12


def test_array_input():
    """numpy 配列入力で各時刻の解析解を返す。"""
    t = np.array([0.0, 10.0, 100.0])
    T = analytical_temperature(t=t, T_0=0.0, input_value=1)
    assert T.shape == (3,)
    assert abs(T[0] - 0.0) < 1e-15
    # t=100 でほぼ T_eq=2 に到達 (誤差 2·exp(-5) ≈ 0.0135)


def test_input_bool_rejected():
    """bool 型 input は ValueError。"""
    with pytest.raises(ValueError):
        analytical_temperature(t=0.0, T_0=0.0, input_value=True)
    with pytest.raises(ValueError):
        analytical_temperature(t=0.0, T_0=0.0, input_value=False)


def test_input_invalid_int_rejected():
    """0/1 以外の int は ValueError。"""
    with pytest.raises(ValueError):
        analytical_temperature(t=0.0, T_0=0.0, input_value=2)


def test_monotonicity_with_heating():
    """input=1 で T(t) は単調増加 (T_0 < T_eq)。"""
    times = np.linspace(0, 50, 100)
    T = analytical_temperature(t=times, T_0=0.0, input_value=1)
    assert np.all(np.diff(T) > 0)


def test_monotonicity_with_cooling():
    """input=0 で T(t) は単調減少 (T_0 > T_env)。"""
    times = np.linspace(0, 50, 100)
    T = analytical_temperature(t=times, T_0=1.0, input_value=0)
    assert np.all(np.diff(T) < 0)
