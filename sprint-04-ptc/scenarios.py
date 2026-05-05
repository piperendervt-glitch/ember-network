"""
scenarios モジュール (Sprint 4)

ember-network Sprint 4 のシナリオ実行ロジック。Sprint 2/3 のパターン (1 ステップ
内で input が固定される) を継承し、TemperatureNode (Sprint 4 PTC 版) に対応する
形で温度 T を観測値として返す。

Sprint 3 から拡張:
- input_value は float (fractional input サポート、Sprint 4 KR-S4)
- run_fractional_input_scenario: 連続値入力シナリオ (新規)
- run_input_cessation_scenario の input_value も float 化

Notes
-----
Sprint 2 で確立された「ステップ内 input 固定」パターンは Sprint 4 でも継続。
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
                                input_value: float = 1.0
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
    input_value : float, optional
        定数入力 (Sprint 4 では float、[0, 1])。デフォルト 1.0。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列 (t=0 を含む)。
    T_array : numpy.ndarray
        各時刻での温度 T (primary な状態変数)。

    Notes
    -----
    node は in-place で更新される。weight や R(T)/R_0 の系列が必要な場合は
    各時刻について node を再構築するか、派生量として後付けで計算する。

    Examples
    --------
    >>> node = TemperatureNode(alpha_PTC=0.0, integrator='euler')
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
                                 dt: float,
                                 input_high: float = 1.0,
                                 input_low: float = 0.0
                                 ) -> Tuple[np.ndarray, np.ndarray]:
    """
    入力切替シナリオ。t < t_switch で input=input_high、それ以降 input=input_low。

    Parameters
    ----------
    node : TemperatureNode
        対象の TemperatureNode (in-place 更新)。
    t_switch : float
        入力切替時刻。
    total_time : float
        シミュレーション総時間。
    dt : float
        時間刻み。
    input_high : float, optional
        切替前の入力値。デフォルト 1.0。
    input_low : float, optional
        切替後の入力値。デフォルト 0.0。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列。
    T_array : numpy.ndarray
        各時刻での温度 T。

    Notes
    -----
    切替判定は「ステップ開始時刻 t_i が t_switch 以上かどうか」で行う。
    つまり、ステップ i (時刻 t_i から t_i + dt への進行) で使う入力は、
    t_i < t_switch なら input_high、そうでなければ input_low。

    Examples
    --------
    >>> node = TemperatureNode(alpha_PTC=0.0, integrator='euler',
    ...                        clip_enabled=False)
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
        input_value = input_high if t_i < t_switch else input_low
        node.update(input_value, dt)
        T_array[i + 1] = node.temperature
    return t_array, T_array


def run_fractional_input_scenario(node: TemperatureNode,
                                  total_time: float,
                                  dt: float,
                                  input_func
                                  ) -> Tuple[np.ndarray, np.ndarray]:
    """
    連続値入力シナリオ (Sprint 4 新規、KR-S4)。

    各ステップ開始時刻 t_i で input_func(t_i) を評価し、ステップ内では
    その値を一定として update する (PRL-003 対処の継続)。

    Parameters
    ----------
    node : TemperatureNode
        対象の TemperatureNode (in-place 更新)。
    total_time : float
        シミュレーション総時間。
    dt : float
        時間刻み。
    input_func : callable
        t (float) を受け取り [0, 1] の float を返す関数。

    Returns
    -------
    t_array : numpy.ndarray
        時刻配列。
    T_array : numpy.ndarray
        各時刻での温度 T。

    Examples
    --------
    >>> node = TemperatureNode(alpha_PTC=0.0, integrator='euler')
    >>> t, T = run_fractional_input_scenario(
    ...     node, total_time=0.2, dt=0.1, input_func=lambda t: 0.5)
    >>> len(t)
    3
    >>> round(float(T[-1]), 6)  # 一定 input=0.5 で Sprint 3 半分の加熱
    0.009975
    """
    n_steps = int(round(total_time / dt))
    t_array = np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    T_array[0] = node.temperature
    for i in range(n_steps):
        t_i = t_array[i]
        input_value = float(input_func(t_i))
        node.update(input_value, dt)
        T_array[i + 1] = node.temperature
    return t_array, T_array
