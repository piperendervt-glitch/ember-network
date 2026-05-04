"""
test_temperature_node: TemperatureNode の基本動作テスト

bool 拒否、引数検証、reset、property の基本機能。
KR-S1〜S4 はそれぞれ専用ファイルで検証。
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from temperature_node import TemperatureNode  # noqa: E402


def test_default_construction():
    """デフォルト引数で構築可能、初期 T = T_env = 0。"""
    node = TemperatureNode()
    assert node.temperature == 0.0
    assert node.T_env == 0.0
    assert node.T_max == 1.0
    assert node.heating_rate == 0.1
    assert node.cooling_rate == 0.05


def test_custom_parameters():
    """カスタムパラメータで構築可能。"""
    node = TemperatureNode(heating_rate=0.5, cooling_rate=0.1,
                           T_env=10.0, T_max=20.0,
                           clip_enabled=False, integrator='euler')
    assert node.heating_rate == 0.5
    assert node.cooling_rate == 0.1
    assert node.T_env == 10.0
    assert node.T_max == 20.0
    assert node.temperature == 10.0  # 初期 T = T_env


def test_reset_resets_T_to_T_env():
    """reset() で T が T_env に戻る (前提 1: T が primary)。"""
    node = TemperatureNode(T_env=5.0, T_max=10.0, clip_enabled=False)
    for _ in range(100):
        node.update(input_value=1, dt=0.1)
    assert node.temperature > 5.0
    node.reset()
    assert node.temperature == 5.0
    assert node.weight == 0.0


def test_invalid_integrator():
    """integrator が 'euler' 'rk4' 以外で ValueError。"""
    with pytest.raises(ValueError):
        TemperatureNode(integrator='heun')
    with pytest.raises(ValueError):
        TemperatureNode(integrator='RK4')  # 大文字小文字


def test_T_max_le_T_env_rejected():
    """T_max <= T_env で ValueError (前提 3: 物理的境界として妥当)。"""
    with pytest.raises(ValueError):
        TemperatureNode(T_env=1.0, T_max=1.0)
    with pytest.raises(ValueError):
        TemperatureNode(T_env=1.0, T_max=0.5)


def test_input_value_bool_rejected():
    """bool 型 input は明示的に拒否。"""
    node = TemperatureNode()
    with pytest.raises(ValueError):
        node.update(input_value=True, dt=0.01)
    with pytest.raises(ValueError):
        node.update(input_value=False, dt=0.01)


def test_input_value_invalid_int_rejected():
    """0 または 1 以外で ValueError。"""
    node = TemperatureNode()
    with pytest.raises(ValueError):
        node.update(input_value=2, dt=0.01)
    with pytest.raises(ValueError):
        node.update(input_value=-1, dt=0.01)


def test_input_value_string_rejected():
    """文字列 input は ValueError。"""
    node = TemperatureNode()
    with pytest.raises(ValueError):
        node.update(input_value="1", dt=0.01)


def test_dt_must_be_positive():
    """dt <= 0 で ValueError。"""
    node = TemperatureNode()
    with pytest.raises(ValueError):
        node.update(input_value=1, dt=0.0)
    with pytest.raises(ValueError):
        node.update(input_value=1, dt=-0.01)


def test_temperature_is_primary_state():
    """前提 1: T が primary な状態変数 (内部表現で T が直接更新される)。"""
    node = TemperatureNode()
    initial_T = node.temperature
    node.update(input_value=1, dt=0.1)
    assert node.temperature != initial_T  # T が変化


def test_weight_is_derived_property():
    """前提 1: w は派生量 (T から計算)。setter なし。"""
    node = TemperatureNode()
    # weight プロパティに直接代入できない (read-only)
    with pytest.raises(AttributeError):
        node.weight = 0.5  # type: ignore[misc]


def test_euler_step_matches_analytical():
    """Euler 1 ステップが手計算と一致。
    T_0=0, input=1: dT/dt = 0.1, new_T = 0 + 0.1·0.1 = 0.01。"""
    node = TemperatureNode(integrator='euler')
    node.update(input_value=1, dt=0.1)
    assert abs(node.temperature - 0.01) < 1e-15


def test_rk4_step_matches_analytical():
    """RK4 1 ステップが解析解と高精度に一致。"""
    import math
    node = TemperatureNode(integrator='rk4')
    node.update(input_value=1, dt=1.0)
    # 解析: T_eq + (T_0 - T_eq)·exp(-β·t) = 2 + (0-2)·exp(-0.05)
    expected = 2.0 - 2.0 * math.exp(-0.05)
    assert abs(node.temperature - expected) < 1e-6
