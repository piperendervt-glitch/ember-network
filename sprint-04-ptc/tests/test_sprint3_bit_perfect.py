"""
test_sprint3_bit_perfect: KR-S1 (Sprint 3 との数値的整合性)

Sprint 4 の TemperatureNode を α_PTC=0 で動作させたとき、Sprint 3 の
TemperatureNode と全 t で bit-perfect に一致することを実測検証する。

数学的根拠:

    α_PTC = 0 のとき、Sprint 4 の R(T)/R_0 = 1 + 0·(T - T_ref) = 1.0 + 0.0
    = 1.0 (IEEE 754 で exact)。Sprint 4 の dT/dt は

        1.0 · heating_rate · input - cooling_rate · (T - T_env)

    となり、IEEE 754 の `1.0 * x == x` 性質により Sprint 3 の dT/dt と
    bit-identical な計算経路となる。

Devil's Advocate #2 への対応:

    タスク 8 報告で予告された「演算順序の差異 (Sprint 3 の
    heating_rate * input_value vs Sprint 4 の
    R_factor * heating_rate * input_value)」が bit-perfect を崩さないか
    を、複数のシナリオ (constant/cessation、euler/rk4、clip on/off) で
    実測する。

    bit-perfect が崩れた場合、Tripwire #3 として halt-and-confirm を
    発動する (本テストファイル単体の責務ではなく、Sprint 4 完了報告
    で Robosheep に判断を仰ぐ)。
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

_SPRINT4 = Path(__file__).resolve().parent.parent
_SPRINT3 = _SPRINT4.parent / "sprint-03-temperature"

# Sprint 4 の src と root (scenarios.py 配置先) を最優先で path に
sys.path.insert(0, str(_SPRINT4 / "src"))
sys.path.insert(0, str(_SPRINT4))

from temperature_node import TemperatureNode as TemperatureNodeS4  # noqa: E402
from scenarios import (  # noqa: E402
    run_constant_input_scenario as run_const_s4,
    run_input_cessation_scenario as run_cess_s4,
)

# Sprint 3 の TemperatureNode と scenarios を、別名でロードする
# (sys.path に追加すると Sprint 4 の同名モジュールと衝突するため、
#  importlib.util で名前空間を分離する)
_s3_node_path = _SPRINT3 / "src" / "temperature_node.py"
_spec_node = importlib.util.spec_from_file_location(
    "sprint3_temperature_node", _s3_node_path
)
_sprint3_node_mod = importlib.util.module_from_spec(_spec_node)
_spec_node.loader.exec_module(_sprint3_node_mod)
TemperatureNodeS3 = _sprint3_node_mod.TemperatureNode

_s3_scen_path = _SPRINT3 / "scenarios.py"
# Sprint 3 の scenarios.py は内部で `from temperature_node import ...`
# を行うため、Sprint 3 の src を一時的に sys.path 先頭に置いてからロード
_old_sys_path = sys.path[:]
sys.path.insert(0, str(_SPRINT3 / "src"))
sys.path.insert(0, str(_SPRINT3))
_spec_scen = importlib.util.spec_from_file_location(
    "sprint3_scenarios", _s3_scen_path
)
_sprint3_scen_mod = importlib.util.module_from_spec(_spec_scen)
# Sprint 3 の scenarios が import する `temperature_node` を Sprint 3 版に
# 固定するため、sys.modules に明示的に登録する
_prev_tn = sys.modules.get("temperature_node")
sys.modules["temperature_node"] = _sprint3_node_mod
try:
    _spec_scen.loader.exec_module(_sprint3_scen_mod)
finally:
    # Sprint 4 のテストが Sprint 4 の temperature_node を見るように戻す
    if _prev_tn is not None:
        sys.modules["temperature_node"] = _prev_tn
    else:
        sys.modules.pop("temperature_node", None)
    sys.path[:] = _old_sys_path

run_const_s3 = _sprint3_scen_mod.run_constant_input_scenario
run_cess_s3 = _sprint3_scen_mod.run_input_cessation_scenario


# ----- 共通パラメータ -----
# Sprint 3 と Sprint 4 で同一にできる物理パラメータ。Sprint 4 固有の
# alpha_PTC=0, T_ref=None (= T_env), T_initial=None (= T_env) を指定する
# ことで、reset 後の初期状態と _dTdt の計算経路が Sprint 3 と一致する。

HEATING = 0.1
COOLING = 0.05
T_ENV = 0.0
T_MAX = 1.0


def _make_pair(clip_enabled: bool, integrator: str):
    """Sprint 3 / Sprint 4 (α_PTC=0) の TemperatureNode ペアを生成する。"""
    s3 = TemperatureNodeS3(
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, T_max=T_MAX,
        clip_enabled=clip_enabled, integrator=integrator,
    )
    s4 = TemperatureNodeS4(
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, T_max=T_MAX,
        alpha_PTC=0.0, T_ref=None, T_initial=None,
        clip_enabled=clip_enabled, integrator=integrator,
    )
    return s3, s4


# ----- KR-S1 メインテスト (Tripwire #3 の発動条件) -----

def test_kr_s1_bit_perfect_constant_rk4_no_clip():
    """KR-S1 メイン: input=1 を 100 単位時間、RK4、clip off で bit-perfect。"""
    dt = 0.01
    total_time = 100.0
    s3, s4 = _make_pair(clip_enabled=False, integrator='rk4')
    t3, T3 = run_const_s3(s3, total_time=total_time, dt=dt, input_value=1)
    t4, T4 = run_const_s4(s4, total_time=total_time, dt=dt, input_value=1)

    assert np.array_equal(t3, t4), "時刻配列が不一致"
    max_diff = float(np.max(np.abs(T4 - T3)))
    # 厳密判定: literal 0.0 (bit-perfect、Tripwire #3 の発動条件)
    assert np.array_equal(T4, T3), (
        f"KR-S1 bit-perfect 失敗 (Tripwire #3): "
        f"max |T_sprint4 - T_sprint3| = {max_diff:.3e}, "
        f"len(T) = {len(T4)}, n_steps = {len(T4) - 1}"
    )
    assert max_diff == 0.0, (
        f"max diff が literal 0.0 でない: {max_diff!r}"
    )


def test_kr_s1_bit_perfect_constant_euler_no_clip():
    """KR-S1 補助: Euler、clip off でも bit-perfect。"""
    dt = 0.1
    total_time = 50.0
    s3, s4 = _make_pair(clip_enabled=False, integrator='euler')
    _, T3 = run_const_s3(s3, total_time=total_time, dt=dt, input_value=1)
    _, T4 = run_const_s4(s4, total_time=total_time, dt=dt, input_value=1)
    max_diff = float(np.max(np.abs(T4 - T3)))
    assert np.array_equal(T4, T3), (
        f"Euler bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_constant_rk4_with_clip():
    """KR-S1 補助: clip on でも bit-perfect (clip 経路が同一であることの確認)。"""
    dt = 0.01
    total_time = 100.0
    s3, s4 = _make_pair(clip_enabled=True, integrator='rk4')
    _, T3 = run_const_s3(s3, total_time=total_time, dt=dt, input_value=1)
    _, T4 = run_const_s4(s4, total_time=total_time, dt=dt, input_value=1)
    max_diff = float(np.max(np.abs(T4 - T3)))
    assert np.array_equal(T4, T3), (
        f"clip on bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_cessation_rk4():
    """KR-S1 補助: 入力切替 (input=1 → input=0) シナリオでも bit-perfect。"""
    dt = 0.01
    total_time = 100.0
    s3, s4 = _make_pair(clip_enabled=False, integrator='rk4')
    _, T3 = run_cess_s3(s3, t_switch=50.0, total_time=total_time, dt=dt)
    _, T4 = run_cess_s4(s4, t_switch=50.0, total_time=total_time, dt=dt)
    max_diff = float(np.max(np.abs(T4 - T3)))
    assert np.array_equal(T4, T3), (
        f"cessation bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


def test_kr_s1_bit_perfect_input_zero_rk4():
    """KR-S1 補助: input=0 (純冷却、初期 T=T_env=0 から動かない) でも bit-perfect。"""
    dt = 0.01
    total_time = 50.0
    s3, s4 = _make_pair(clip_enabled=False, integrator='rk4')
    _, T3 = run_const_s3(s3, total_time=total_time, dt=dt, input_value=0)
    _, T4 = run_const_s4(s4, total_time=total_time, dt=dt, input_value=0)
    max_diff = float(np.max(np.abs(T4 - T3)))
    assert np.array_equal(T4, T3), (
        f"input=0 bit-perfect 失敗: max diff = {max_diff:.3e}"
    )


# ----- 計算経路の単独 step 検証 (Devil's Advocate #2 への直接対応) -----

def test_kr_s1_bit_perfect_single_step_dTdt():
    """
    Devil's Advocate #2 への直接対応: 1 ステップだけ進めた場合の温度を
    bit-perfect 比較する。これは Sprint 3 (heating_rate * input_value) vs
    Sprint 4 (R_factor * heating_rate * input_value、R_factor=1.0) の
    演算順序差が IEEE 754 で吸収されることを最小単位で確認する。
    """
    s3, s4 = _make_pair(clip_enabled=False, integrator='rk4')
    s3.update(input_value=1, dt=0.01)
    s4.update(input_value=1, dt=0.01)
    assert s4.temperature == s3.temperature, (
        f"単独 step bit-perfect 失敗: "
        f"s4.T = {s4.temperature!r}, s3.T = {s3.temperature!r}"
    )

    # 中間温度 (T != T_env かつ T != T_ref) で R_factor の演算経路が
    # 確実に発火するケース。s4 の T を T_env=0 から離した状態で update。
    s3b = TemperatureNodeS3(
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, T_max=T_MAX,
        clip_enabled=False, integrator='rk4',
    )
    s4b = TemperatureNodeS4(
        heating_rate=HEATING, cooling_rate=COOLING,
        T_env=T_ENV, T_max=T_MAX,
        alpha_PTC=0.0, T_ref=None, T_initial=None,
        clip_enabled=False, integrator='rk4',
    )
    # 10 step 進めて T を warm-up させる (T が T_ref から離れる)
    for _ in range(10):
        s3b.update(input_value=1, dt=0.01)
        s4b.update(input_value=1, dt=0.01)
        assert s4b.temperature == s3b.temperature, (
            f"warm-up step bit-perfect 失敗: "
            f"s4 = {s4b.temperature!r}, s3 = {s3b.temperature!r}"
        )
