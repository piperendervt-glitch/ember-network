"""
test_sprint2_consistency: KR-S1 (Sprint 2 との数値的整合性)

TemperatureNode (T_env=0, T_max=1) と Sprint 2 の ContinuousNode を同条件で
実行し、全 t で |T_sprint3 - w_sprint2| < 1e-15 (bit-perfect) を検証。

これにより数学モデルの数値的等価性を実証する。実装の同型性ではなく、
IEEE 754 算術での bit 一致を確認することで、Sprint 3 の TemperatureNode が
Sprint 2 の ContinuousNode の純然たる物理的解釈であることを示す。
"""

import sys
from pathlib import Path

import numpy as np

_SPRINT3 = Path(__file__).resolve().parent.parent
_SPRINT2 = _SPRINT3.parent / "sprint-02-continuous-time"
sys.path.insert(0, str(_SPRINT3 / "src"))
sys.path.insert(0, str(_SPRINT3))
sys.path.insert(0, str(_SPRINT2 / "src"))
sys.path.insert(0, str(_SPRINT2))

from temperature_node import TemperatureNode  # noqa: E402
from continuous_node import ContinuousNode  # noqa: E402
from scenarios import (  # noqa: E402
    run_constant_input_scenario as run_const_T,
    run_input_cessation_scenario as run_cess_T,
)

# Sprint 2 の scenarios.py を別名で import
_sprint2_scenarios_path = _SPRINT2 / "scenarios.py"
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "sprint2_scenarios", _sprint2_scenarios_path
)
_sprint2_scenarios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sprint2_scenarios)
run_const_w = _sprint2_scenarios.run_constant_input_scenario
run_cess_w = _sprint2_scenarios.run_input_cessation_scenario


def test_kr_s1_bit_perfect_constant_input_rk4():
    """KR-S1: input=1 を 100 単位時間、RK4、全 t で bit-perfect 一致。"""
    dt = 0.01
    total_time = 100.0
    node3 = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
                            T_env=0.0, T_max=1.0,
                            clip_enabled=False, integrator='rk4')
    node2 = ContinuousNode(learning_rate=0.1, forgetting_rate=0.05,
                           clip_enabled=False, integrator='rk4')
    t3, T3 = run_const_T(node3, total_time=total_time, dt=dt, input_value=1)
    t2, w2 = run_const_w(node2, total_time=total_time, dt=dt, input_value=1)

    assert np.array_equal(t3, t2), "時刻配列が不一致"
    max_diff = float(np.max(np.abs(T3 - w2)))
    assert max_diff < 1e-15, (
        f"KR-S1 失敗: max |T_sprint3 - w_sprint2| = {max_diff:.3e} >= 1e-15"
    )


def test_kr_s1_bit_perfect_constant_input_euler():
    """KR-S1 補助: Euler でも bit-perfect 一致。"""
    dt = 0.1
    total_time = 50.0
    node3 = TemperatureNode(heating_rate=0.1, cooling_rate=0.05,
                            T_env=0.0, T_max=1.0,
                            clip_enabled=False, integrator='euler')
    node2 = ContinuousNode(learning_rate=0.1, forgetting_rate=0.05,
                           clip_enabled=False, integrator='euler')
    t3, T3 = run_const_T(node3, total_time=total_time, dt=dt, input_value=1)
    t2, w2 = run_const_w(node2, total_time=total_time, dt=dt, input_value=1)
    max_diff = float(np.max(np.abs(T3 - w2)))
    assert max_diff < 1e-15, (
        f"Euler bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_input_cessation():
    """KR-S1: 入力切替シナリオでも bit-perfect。"""
    dt = 0.01
    total_time = 100.0
    node3 = TemperatureNode(clip_enabled=False, integrator='rk4')
    node2 = ContinuousNode(clip_enabled=False, integrator='rk4')
    _, T3 = run_cess_T(node3, t_switch=50.0, total_time=total_time, dt=dt)
    _, w2 = run_cess_w(node2, t_switch=50.0, total_time=total_time, dt=dt)
    max_diff = float(np.max(np.abs(T3 - w2)))
    assert max_diff < 1e-15, (
        f"cessation bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_with_clip():
    """KR-S1 補助: clip 有効時も bit-perfect (T_max=1=Sprint 2 の上限)。"""
    dt = 0.01
    total_time = 30.0
    node3 = TemperatureNode(clip_enabled=True, integrator='rk4')
    node2 = ContinuousNode(clip_enabled=True, integrator='rk4')
    _, T3 = run_const_T(node3, total_time=total_time, dt=dt, input_value=1)
    _, w2 = run_const_w(node2, total_time=total_time, dt=dt, input_value=1)
    max_diff = float(np.max(np.abs(T3 - w2)))
    assert max_diff < 1e-15, (
        f"clip 有効時 bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_full_array_equal():
    """KR-S1 厳密版: 配列が numpy.array_equal で完全一致 (差が 0.0 でも検出)。"""
    dt = 0.01
    total_time = 30.0
    node3 = TemperatureNode(clip_enabled=False, integrator='rk4')
    node2 = ContinuousNode(clip_enabled=False, integrator='rk4')
    _, T3 = run_const_T(node3, total_time=total_time, dt=dt, input_value=1)
    _, w2 = run_const_w(node2, total_time=total_time, dt=dt, input_value=1)
    # IEEE 754 の T - 0.0 == T 性質により、bit-identical を期待
    assert np.array_equal(T3, w2), (
        f"配列が完全一致しない (max diff = "
        f"{float(np.max(np.abs(T3 - w2))):.3e})"
    )
