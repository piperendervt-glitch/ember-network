"""
test_clip_behavior: clip 付き実装の検証 (KR-S3)

- clip 付き実装で weight が [0, 1] に制限される
- clip 発動時刻が t = 20·ln(2) ≈ 13.8629 と一致 (誤差 < 0.1)
- clip 後の安定性 (t > t_clip で weight = 1.0)
"""

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from continuous_node import ContinuousNode  # noqa: E402
from scenarios import run_constant_input_scenario  # noqa: E402


T_CLIP_ANALYTICAL = 20.0 * np.log(2.0)  # ≈ 13.8629436...


def test_clip_keeps_weight_in_unit_interval():
    """clip 付き実装で weight が [0, 1] の範囲内に制限される。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=True)
    times, weights = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1
    )
    assert np.all(weights >= 0.0)
    assert np.all(weights <= 1.0)


def test_clip_activation_time_matches_analytical():
    """KR-S3: clip 発動時刻 (weight が 1.0 - 1e-10 を超えた最初の時刻) が
    解析的予測 t = 20·ln(2) ≈ 13.8629 と一致 (誤差 < 0.1)。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=True)
    dt = 0.01
    times, weights = run_constant_input_scenario(
        node, total_time=30.0, dt=dt, input_value=1
    )

    # weight >= 1.0 - 1e-10 を満たす最初の時刻を探す
    threshold = 1.0 - 1e-10
    indices = np.where(weights >= threshold)[0]
    assert len(indices) > 0, "clip never activated within t<=30"
    t_clip_measured = times[indices[0]]

    error = abs(t_clip_measured - T_CLIP_ANALYTICAL)
    assert error < 0.1, (
        f"t_clip 誤差 {error:.4f} > 0.1 "
        f"(measured={t_clip_measured}, analytical={T_CLIP_ANALYTICAL:.6f})"
    )


def test_weight_stable_at_one_after_clip():
    """KR-S3: t > t_clip で weight = 1.0 で安定する。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=True)
    times, weights = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1
    )

    # t_clip 確実に過ぎた t=15 以降は weight=1.0 で一定
    after_clip_idx = np.where(times >= 15.0)[0]
    assert len(after_clip_idx) > 0
    for i in after_clip_idx:
        assert weights[i] == 1.0, (
            f"t={times[i]:.4f}: weight={weights[i]} != 1.0"
        )


def test_clip_disabled_overshoots_one():
    """clip_enabled=False で同じシナリオは weight が 1.0 を超える。"""
    node = ContinuousNode(integrator='rk4', clip_enabled=False)
    times, weights = run_constant_input_scenario(
        node, total_time=30.0, dt=0.01, input_value=1
    )
    # 解析的に t=20·ln(2) で w=1.0 に到達、その後 w_eq=2.0 に向かって増加
    # t=30 では w ≈ 2 - 2·exp(-1.5) ≈ 1.554
    assert weights[-1] > 1.0
    # 解析値 1.5537 と一致 (RK4 精度)
    expected = 2.0 - 2.0 * np.exp(-0.05 * 30.0)
    assert abs(weights[-1] - expected) < 1e-6


def test_clip_difference_between_enabled_and_disabled():
    """clip 有効/無効で挙動が分岐するのは clip 発動時刻以降。"""
    node_clip = ContinuousNode(integrator='rk4', clip_enabled=True)
    node_no_clip = ContinuousNode(integrator='rk4', clip_enabled=False)

    times_clip, w_clip = run_constant_input_scenario(
        node_clip, total_time=30.0, dt=0.01, input_value=1
    )
    times_no_clip, w_no_clip = run_constant_input_scenario(
        node_no_clip, total_time=30.0, dt=0.01, input_value=1
    )

    # t < t_clip では完全一致
    pre_clip_idx = np.where(times_clip < T_CLIP_ANALYTICAL - 0.1)[0]
    assert np.allclose(w_clip[pre_clip_idx], w_no_clip[pre_clip_idx],
                       atol=1e-10)

    # t > t_clip では clip 付きの方が小さい (1.0 で頭打ち)
    post_clip_idx = np.where(times_clip > T_CLIP_ANALYTICAL + 0.1)[0]
    assert np.all(w_clip[post_clip_idx] < w_no_clip[post_clip_idx])
    assert np.all(w_clip[post_clip_idx] == 1.0)
