"""
scenarios モジュール

ember-network Sprint 2 のシナリオ実行ロジックを共通モジュールとして提供する。
visualize.py および test ファイルから共通利用される。

Notes
-----
Sprint 1 では各テスト/visualize で同じシナリオを重複実装していた問題を、
Sprint 2 では本モジュールで一元化する (deferred_issues.md より)。
"""

import sys
from pathlib import Path
from typing import Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from continuous_node import ContinuousNode  # noqa: E402


def run_constant_input_scenario(node: ContinuousNode,
                                total_time: float,
                                dt: float,
                                input_value: int = 1
                                ) -> Tuple[np.ndarray, np.ndarray]:
    """
    一定入力でのシナリオ実行。

    Parameters
    ----------
    node : ContinuousNode
        対象の ContinuousNode インスタンス (in-place で更新される)。
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
    w_array : numpy.ndarray
        各時刻での weight。

    Notes
    -----
    node は in-place で更新される (シミュレーション後の最終 weight が
    node.weight に残る)。

    Examples
    --------
    >>> node = ContinuousNode(integrator='euler')
    >>> t, w = run_constant_input_scenario(node, total_time=0.2, dt=0.1)
    >>> len(t)
    3
    >>> round(float(w[-1]), 6)
    0.01995
    """
    n_steps = int(round(total_time / dt))
    t_array = np.arange(n_steps + 1) * dt
    w_array = np.zeros(n_steps + 1)
    w_array[0] = node.weight
    for i in range(n_steps):
        node.update(input_value, dt)
        w_array[i + 1] = node.weight
    return t_array, w_array


def run_input_cessation_scenario(node: ContinuousNode,
                                 t_switch: float,
                                 total_time: float,
                                 dt: float
                                 ) -> Tuple[np.ndarray, np.ndarray]:
    """
    入力停止シナリオ。t < t_switch で input=1、t >= t_switch で input=0。

    Parameters
    ----------
    node : ContinuousNode
        対象の ContinuousNode インスタンス (in-place で更新される)。
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
    w_array : numpy.ndarray
        各時刻での weight。

    Notes
    -----
    切替判定は「次ステップ開始時刻 t_i が t_switch 以上かどうか」で行う。
    つまり、ステップ i (時刻 t_i から t_i + dt への進行) で使う入力は、
    t_i < t_switch なら 1、そうでなければ 0。

    Examples
    --------
    >>> node = ContinuousNode(integrator='euler', clip_enabled=False)
    >>> t, w = run_input_cessation_scenario(
    ...     node, t_switch=0.1, total_time=0.2, dt=0.1)
    >>> len(t)
    3
    """
    n_steps = int(round(total_time / dt))
    t_array = np.arange(n_steps + 1) * dt
    w_array = np.zeros(n_steps + 1)
    w_array[0] = node.weight
    for i in range(n_steps):
        t_i = t_array[i]
        input_value = 1 if t_i < t_switch else 0
        node.update(input_value, dt)
        w_array[i + 1] = node.weight
    return t_array, w_array
