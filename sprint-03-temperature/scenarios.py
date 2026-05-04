"""
scenarios モジュール

ember-network Sprint 3 のシナリオ実行ロジック。Sprint 2 のパターンを継承
(1 ステップ内で input が固定される) し、TemperatureNode に対応する形で
温度 T を観測値として返す。

Notes
-----
Sprint 2 で確立された「ステップ内 input 固定」パターンは Sprint 3 でも継続。
これにより RK4 が不連続点を跨ぐことを避け、4 次精度を維持する (PRL-003)。
"""

import sys
from pathlib import Path
from typing import Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from temperature_node import TemperatureNode  # noqa: E402


def run_constant_input_scenario(node: TemperatureNode,
                                total_time: float,
                                dt: float,
                                input_value: int = 1
                                ) -> Tuple[np.ndarray, np.ndarray]:
    """
    一定入力でのシナリオ実行。

    Parameters
    ----------
    node : TemperatureNode
        対象の TemperatureNode インスタンス (in-place で更新される)。
    total_time : float
        シミュレーション総時間。
    dt : float
        時間刻み。
    input_value : int, optional
        定数入力。デフォルト 1。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列 (t=0 を含む)。
    T_array : numpy.ndarray
        各時刻での温度 T (primary な状態変数)。

    Notes
    -----
    node は in-place で更新される。weight の系列が必要な場合は
    w = (T_array - node.T_env) / (node.T_max - node.T_env) で派生計算する。

    Examples
    --------
    >>> node = TemperatureNode(integrator='euler')
    >>> t, T = run_constant_input_scenario(node, total_time=0.2, dt=0.1)
    >>> len(t)
    3
    >>> round(float(T[-1]), 6)
    0.01995
    """
    n_steps = int(round(total_time / dt))
    t_array = np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    T_array[0] = node.temperature
    for i in range(n_steps):
        node.update(input_value, dt)
        T_array[i + 1] = node.temperature
    return t_array, T_array


def run_input_cessation_scenario(node: TemperatureNode,
                                 t_switch: float,
                                 total_time: float,
                                 dt: float
                                 ) -> Tuple[np.ndarray, np.ndarray]:
    """
    入力停止シナリオ。t < t_switch で input=1、t >= t_switch で input=0。

    Parameters
    ----------
    node : TemperatureNode
        対象の TemperatureNode インスタンス (in-place で更新される)。
    t_switch : float
        入力切替時刻 (この時刻以降 input=0)。
    total_time : float
        シミュレーション総時間。
    dt : float
        時間刻み。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列 (t=0 を含む)。
    T_array : numpy.ndarray
        各時刻での温度 T。

    Notes
    -----
    切替判定は「ステップ開始時刻 t_i が t_switch 以上かどうか」で行う。
    つまり、ステップ i (時刻 t_i から t_i + dt への進行) で使う入力は、
    t_i < t_switch なら 1、そうでなければ 0。

    Examples
    --------
    >>> node = TemperatureNode(integrator='euler', clip_enabled=False)
    >>> t, T = run_input_cessation_scenario(
    ...     node, t_switch=0.1, total_time=0.2, dt=0.1)
    >>> len(t)
    3
    """
    n_steps = int(round(total_time / dt))
    t_array = np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    T_array[0] = node.temperature
    for i in range(n_steps):
        t_i = t_array[i]
        input_value = 1 if t_i < t_switch else 0
        node.update(input_value, dt)
        T_array[i + 1] = node.temperature
    return t_array, T_array
