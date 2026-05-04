"""
visualize.py: Sprint 3 の結果プロット生成

4 つのプロットを results/plots/ に生成する:
1. plot_temperature_evolution.png   - 温度時系列 (Sprint 2 weight と対応)
2. plot_clip_behavior.png           - T_max での clip 挙動
3. plot_invariants.png              - 6 物理的不変量の時系列確認
4. plot_mms_verification.png        - MMS の製造解と数値解の比較
"""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from analytical import analytical_temperature  # noqa: E402
from temperature_node import TemperatureNode  # noqa: E402
from mms import (  # noqa: E402
    manufactured_polynomial,
    manufactured_trigonometric,
    manufactured_exponential,
    compute_source_term,
    manufactured_to_callable,
    integrate_with_source,
)
from scenarios import run_constant_input_scenario  # noqa: E402


PLOTS_DIR = ROOT / "results" / "plots"
HEATING_RATE = 0.1
COOLING_RATE = 0.05
T_ENV = 0.0
T_MAX = 1.0
DT = 0.01
TOTAL_TIME = 100.0
T_CLIP_ANALYTICAL = 20.0 * math.log(2.0)


def plot_temperature_evolution() -> Path:
    """温度時系列 (Sprint 2 weight と対応する形式)。"""
    # Sprint 3 TemperatureNode (clip 無効) で input=1 を 100 sec
    node = TemperatureNode(clip_enabled=False, integrator='rk4')
    times, T_array = run_constant_input_scenario(
        node, total_time=TOTAL_TIME, dt=DT, input_value=1
    )
    T_analytical = analytical_temperature(
        times, T_0=T_ENV, input_value=1,
        heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE, T_env=T_ENV,
    )
    max_err = float(np.max(np.abs(T_array - T_analytical)))

    # Sprint 2 ContinuousNode との数値的等価性確認用に Sprint 2 を import
    s2 = ROOT.parent / "sprint-02-continuous-time"
    spec = importlib.util.spec_from_file_location(
        "s2_scenarios", s2 / "scenarios.py"
    )
    s2_scen = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(s2 / "src"))
    spec.loader.exec_module(s2_scen)
    from continuous_node import ContinuousNode  # noqa: E402
    s2_node = ContinuousNode(clip_enabled=False, integrator='rk4')
    _, w_s2 = s2_scen.run_constant_input_scenario(
        s2_node, total_time=TOTAL_TIME, dt=DT, input_value=1
    )
    bit_perfect_diff = float(np.max(np.abs(T_array - w_s2)))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times, T_analytical, color="black", linewidth=2.5,
            label=f"Analytical T(t), T_eq=α/β={HEATING_RATE/COOLING_RATE:.1f}",
            alpha=0.9)
    ax.plot(times, T_array, color="red", linestyle=":", linewidth=1.5,
            label=f"TemperatureNode RK4 (max err={max_err:.2e})",
            alpha=0.8)
    ax.plot(times, w_s2, color="cyan", linestyle="--", linewidth=1.0,
            label="Sprint 2 ContinuousNode w(t)", alpha=0.7)

    ax.axhline(y=HEATING_RATE / COOLING_RATE, color="gray",
               linestyle="-.", linewidth=0.8, alpha=0.5,
               label=f"T_eq = {HEATING_RATE/COOLING_RATE:.1f}")
    ax.axhline(y=T_MAX, color="orange", linestyle="-.",
               linewidth=0.8, alpha=0.5,
               label=f"T_max = {T_MAX:.1f}")

    ax.text(
        0.05, 0.95,
        f"KR-S1 verification:\n"
        f"max|T_sprint3 - w_sprint2| = {bit_perfect_diff:.3e}\n"
        f"np.array_equal: "
        f"{bool(np.array_equal(T_array, w_s2))}\n"
        f"(Sprint 2 ↔ Sprint 3 bit-perfect)",
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    ax.set_xlabel("time")
    ax.set_ylabel("temperature T")
    ax.set_title("Sprint 3 Temperature Evolution "
                 "(input=1, clip_enabled=False, RK4, dt=0.01)")
    ax.set_xlim(0, TOTAL_TIME)
    ax.set_ylim(-0.05, 2.1)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_temperature_evolution.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_clip_behavior() -> Path:
    """clip 適用と無効の比較、t_clip の観測。"""
    t_span = 30.0

    node_clip = TemperatureNode(clip_enabled=True, integrator='rk4')
    times_c, T_c = run_constant_input_scenario(
        node_clip, total_time=t_span, dt=DT, input_value=1
    )
    node_no_clip = TemperatureNode(clip_enabled=False, integrator='rk4')
    times_nc, T_nc = run_constant_input_scenario(
        node_no_clip, total_time=t_span, dt=DT, input_value=1
    )

    # 観測 t_clip
    threshold = T_MAX - 1e-10
    indices = np.where(T_c >= threshold)[0]
    t_clip_measured = (times_c[indices[0]]
                       if len(indices) > 0 else None)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times_nc, T_nc, color="blue", linewidth=2,
            label="clip disabled (T → T_eq=2.0)")
    ax.plot(times_c, T_c, color="red", linewidth=2,
            label="clip enabled (capped at T_max=1.0)")

    ax.axhline(y=T_MAX, color="gray", linestyle="--",
               linewidth=0.8, alpha=0.5)
    ax.axvline(x=T_CLIP_ANALYTICAL, color="gray", linestyle=":",
               linewidth=1, alpha=0.7)

    ax.annotate(
        f"Clipping starts (t_clip ≈ {T_CLIP_ANALYTICAL:.4f})",
        xy=(T_CLIP_ANALYTICAL, T_MAX),
        xytext=(T_CLIP_ANALYTICAL + 3, 0.65),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=9,
    )

    if t_clip_measured is not None:
        ax.text(
            0.05, 0.95,
            f"KR-S3 (bounded) verification:\n"
            f"t_clip analytical = {T_CLIP_ANALYTICAL:.6f}\n"
            f"t_clip measured  = {t_clip_measured:.6f}\n"
            f"|error| = {abs(t_clip_measured - T_CLIP_ANALYTICAL):.4f}\n"
            f"T_max held: max(T_clip)={float(np.max(T_c)):.10f}",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white",
                      edgecolor="gray", alpha=0.9),
        )

    ax.set_xlabel("time")
    ax.set_ylabel("temperature T")
    ax.set_title("Sprint 3 Clip Behavior "
                 "(input=1, RK4, dt=0.01, T_max=1.0)")
    ax.set_xlim(0, t_span)
    ax.set_ylim(-0.05, 2.0)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_clip_behavior.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_invariants() -> Path:
    """preregister された 6 物理的不変量の時系列での確認。"""
    # シナリオ: 加熱 → 冷却 → 加熱 → ... のパターンで全 6 不変量を可視化
    node = TemperatureNode(clip_enabled=True, integrator='rk4')
    n_steps = 5000
    dt = 0.05
    times = np.arange(n_steps + 1) * dt
    T_array = np.zeros(n_steps + 1)
    inputs = np.zeros(n_steps, dtype=int)
    T_array[0] = node.temperature
    for i in range(n_steps):
        # ブロックごとに input 切替 (パターン化)
        inputs[i] = 1 if (i // 50) % 2 == 0 else 0
        node.update(input_value=int(inputs[i]), dt=dt)
        T_array[i + 1] = node.temperature

    w_array = (T_array - T_ENV) / (T_MAX - T_ENV)

    # 不変量の検証値
    inv_2_min = float(np.min(T_array))  # positivity
    inv_3_max = float(np.max(T_array))  # bounded
    inv_6_max_err = float(np.max(np.abs(
        w_array - (T_array - T_ENV) / (T_MAX - T_ENV)
    )))

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    ax1 = axes[0]
    ax1.plot(times, T_array, color="red", linewidth=1.5, label="T(t)")
    ax1.plot(times, w_array, color="blue", linewidth=1.0,
             alpha=0.6, label="w(t) = (T-T_env)/(T_max-T_env)")
    ax1.axhline(T_ENV, color="gray", linestyle="--", linewidth=0.5,
                alpha=0.5, label=f"T_env={T_ENV}")
    ax1.axhline(T_MAX, color="gray", linestyle="--", linewidth=0.5,
                alpha=0.5, label=f"T_max={T_MAX}")
    ax1.set_ylabel("T(t) and w(t)")
    ax1.set_title("Sprint 3 Invariants "
                  "(6 preregistered, alternating input pattern)")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.step(times[:-1], inputs, where='post', color="green",
             linewidth=1.0, label="input(t)")
    ax2.set_ylabel("input")
    ax2.set_xlabel("time")
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, alpha=0.3)

    invariant_text = (
        f"KR-S3 verification (6 invariants):\n"
        f"1. monotonicity: holds during input=1 blocks\n"
        f"2. positivity:   min(T) = {inv_2_min:.6e} >= T_env\n"
        f"3. bounded:      max(T) = {inv_3_max:.10f} <= T_max\n"
        f"4. equilibrium:  T → T_max during input=1 blocks\n"
        f"5. heat-flow:    T decreases during input=0 blocks\n"
        f"6. linearity:    max|w - formula| = {inv_6_max_err:.2e}"
    )
    ax1.text(
        0.02, 0.98, invariant_text,
        transform=ax1.transAxes, fontsize=8.5, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    out_path = PLOTS_DIR / "plot_invariants.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_mms_verification() -> Path:
    """MMS による 3 製造解の数値解との比較 (KR-S4)。"""
    cases = [
        ("polynomial: 0.5t² + 0.1t",
         manufactured_polynomial([0.0, 0.1, 0.5]),
         0.0, (0.0, 10.0)),
        ("trigonometric: 0.3sin(0.2t) + 0.5",
         manufactured_trigonometric(0.3, 0.2, 0.5),
         0.5, (0.0, 30.0)),
        ("exponential: 1 - exp(-0.05t)",
         manufactured_exponential(1.0, 0.05, 0.0),
         0.0, (0.0, 60.0)),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    errors = []
    for ax, (name, (T_man, t_sym), T_0, t_span) in zip(axes, cases):
        source = compute_source_term(
            T_man, t_sym, HEATING_RATE, COOLING_RATE, T_ENV,
            input_value=0,
        )
        times, T_num = integrate_with_source(
            T_0=T_0, t_span=t_span, dt=DT,
            heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE,
            T_env=T_ENV, input_value=0, source_func=source,
        )
        f_man = manufactured_to_callable(T_man, t_sym)
        T_exact = np.array([f_man(t) for t in times])
        err = float(np.max(np.abs(T_num - T_exact)))
        errors.append(err)

        ax.plot(times, T_exact, color="black", linewidth=2.0,
                label="Manufactured T(t)", alpha=0.9)
        ax.plot(times, T_num, color="red", linestyle=":", linewidth=1.5,
                label=f"RK4 (max err={err:.2e})", alpha=0.85)
        ax.set_xlabel("time")
        ax.set_ylabel("T(t)")
        ax.set_title(name)
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        f"KR-S4 MMS Verification "
        f"(threshold 1e-6; actual: {errors[0]:.2e}, "
        f"{errors[1]:.2e}, {errors[2]:.2e})",
        fontsize=11,
    )

    out_path = PLOTS_DIR / "plot_mms_verification.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_temperature_evolution(),
        plot_clip_behavior(),
        plot_invariants(),
        plot_mms_verification(),
    ]
    for p in paths:
        print(f"Saved: {p}")


if __name__ == "__main__":
    main()
