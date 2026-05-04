"""
visualize.py: Sprint 2 の結果プロット生成

3 つのプロットを results/plots/ に生成する:
1. plot_analytical_vs_numerical.png - KR-S1 (解析解 vs Euler vs RK4)
2. plot_clip_behavior.png           - KR-S3 (clip 付き vs 無効)
3. plot_convergence.png             - KR-S4 (収束次数 log-log)
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from analytical import analytical_solution  # noqa: E402
from continuous_node import ContinuousNode  # noqa: E402
from integrators import integrate_euler, integrate_rk4  # noqa: E402
from scenarios import run_constant_input_scenario  # noqa: E402


PLOTS_DIR = ROOT / "results" / "plots"
ALPHA = 0.1
BETA = 0.05
DT_DEFAULT = 0.01
TOTAL_TIME = 100.0
T_CLIP_ANALYTICAL = 20.0 * np.log(2.0)


def _dwdt(t: float, w: float, input_value: int) -> float:
    return ALPHA * input_value - BETA * w


def _const_input_one(t: float) -> int:
    return 1


def plot_analytical_vs_numerical() -> Path:
    """KR-S1 のプロットを生成 (解析解 vs Euler vs RK4)。"""
    dt = DT_DEFAULT

    t_e, w_e = integrate_euler(_dwdt, 0.0, (0.0, TOTAL_TIME), dt,
                               _const_input_one)
    t_r, w_r = integrate_rk4(_dwdt, 0.0, (0.0, TOTAL_TIME), dt,
                             _const_input_one)
    ana = analytical_solution(t_r, 0.0, 1, ALPHA, BETA)

    err_e = float(np.max(np.abs(w_e - analytical_solution(t_e, 0.0, 1))))
    err_r = float(np.max(np.abs(w_r - ana)))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t_r, ana, color="black", linewidth=2.5,
            label=f"Analytical (w_eq=α/β={ALPHA / BETA:.1f})", alpha=0.9)
    ax.plot(t_e, w_e, color="blue", linestyle="--", linewidth=1.5,
            label=f"Euler (dt={dt}, max err={err_e:.2e})", alpha=0.8)
    ax.plot(t_r, w_r, color="red", linestyle=":", linewidth=1.5,
            label=f"RK4 (dt={dt}, max err={err_r:.2e})", alpha=0.8)

    ax.axhline(y=ALPHA / BETA, color="gray", linestyle="-.", linewidth=0.8,
               alpha=0.5, label=f"w_eq = {ALPHA / BETA:.1f}")

    ax.text(
        0.05, 0.95,
        f"KR-S1 (RK4, dt=0.01):\nmax|w_num - w_ana| = {err_r:.2e}\n"
        f"threshold = 1e-6  →  {'PASS' if err_r < 1e-6 else 'FAIL'}",
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    ax.set_xlabel("time")
    ax.set_ylabel("weight")
    ax.set_title("KR-S1: Analytical vs Numerical (clip disabled, input=1)")
    ax.set_xlim(0, TOTAL_TIME)
    ax.set_ylim(-0.05, 2.1)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_analytical_vs_numerical.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_clip_behavior() -> Path:
    """KR-S3 のプロットを生成 (clip 付き vs 無効)。"""
    dt = DT_DEFAULT
    t_span = 30.0

    node_clip = ContinuousNode(integrator='rk4', clip_enabled=True)
    times_clip, w_clip = run_constant_input_scenario(
        node_clip, total_time=t_span, dt=dt, input_value=1
    )

    node_no_clip = ContinuousNode(integrator='rk4', clip_enabled=False)
    times_nc, w_nc = run_constant_input_scenario(
        node_no_clip, total_time=t_span, dt=dt, input_value=1
    )

    # 観測 t_clip
    threshold = 1.0 - 1e-10
    indices = np.where(w_clip >= threshold)[0]
    t_clip_measured = times_clip[indices[0]] if len(indices) > 0 else None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times_nc, w_nc, color="blue", linewidth=2,
            label="clip disabled (overshoot to w_eq=2.0)")
    ax.plot(times_clip, w_clip, color="red", linewidth=2,
            label="clip enabled (cap at 1.0)")

    ax.axhline(y=1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axvline(x=T_CLIP_ANALYTICAL, color="gray", linestyle=":",
               linewidth=1, alpha=0.7)

    ax.annotate(
        f"Clipping starts (t ≈ {T_CLIP_ANALYTICAL:.4f})",
        xy=(T_CLIP_ANALYTICAL, 1.0),
        xytext=(T_CLIP_ANALYTICAL + 3, 0.65),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=9,
    )

    if t_clip_measured is not None:
        ax.text(
            0.05, 0.95,
            f"KR-S3 verification:\n"
            f"t_clip analytical = {T_CLIP_ANALYTICAL:.6f}\n"
            f"t_clip measured  = {t_clip_measured:.6f}\n"
            f"|error| = {abs(t_clip_measured - T_CLIP_ANALYTICAL):.4f}\n"
            f"threshold = 0.1  →  "
            f"{'PASS' if abs(t_clip_measured - T_CLIP_ANALYTICAL) < 0.1 else 'FAIL'}",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white",
                      edgecolor="gray", alpha=0.9),
        )

    ax.set_xlabel("time")
    ax.set_ylabel("weight")
    ax.set_title("KR-S3: Clip behavior (input=1, RK4, dt=0.01)")
    ax.set_xlim(0, t_span)
    ax.set_ylim(-0.05, 2.0)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_clip_behavior.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_convergence() -> Path:
    """KR-S4 のプロットを生成 (log-log での収束次数)。"""
    dt_list = [1.0, 0.5, 0.1, 0.05, 0.01]

    err_euler = []
    err_rk4 = []
    for dt in dt_list:
        t_e, w_e = integrate_euler(_dwdt, 0.0, (0.0, TOTAL_TIME), dt,
                                   _const_input_one)
        t_r, w_r = integrate_rk4(_dwdt, 0.0, (0.0, TOTAL_TIME), dt,
                                 _const_input_one)
        err_euler.append(
            float(np.max(np.abs(w_e - analytical_solution(t_e, 0.0, 1))))
        )
        err_rk4.append(
            float(np.max(np.abs(w_r - analytical_solution(t_r, 0.0, 1))))
        )

    # log-log slope (RK4 は dt=0.01 を除外、FP 限界のため)
    log_dt = np.log(dt_list)
    log_e = np.log(err_euler)
    slope_e, _ = np.polyfit(log_dt, log_e, 1)

    log_dt_rk4 = np.log(dt_list[:-1])  # exclude dt=0.01
    log_r = np.log(err_rk4[:-1])
    slope_r, _ = np.polyfit(log_dt_rk4, log_r, 1)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.loglog(dt_list, err_euler, "o-", color="blue", linewidth=2,
              markersize=8, label=f"Euler (slope ≈ {slope_e:.2f})")
    ax.loglog(dt_list, err_rk4, "s-", color="red", linewidth=2,
              markersize=8, label=f"RK4 (slope ≈ {slope_r:.2f}, "
              f"dt≥0.05 only)")

    # 理論線
    ref_e = err_euler[0] * (np.array(dt_list) / dt_list[0]) ** 1
    ref_r = err_rk4[0] * (np.array(dt_list) / dt_list[0]) ** 4
    ax.loglog(dt_list, ref_e, "--", color="blue", alpha=0.4,
              label="O(dt) theoretical")
    ax.loglog(dt_list, ref_r, "--", color="red", alpha=0.4,
              label="O(dt^4) theoretical")

    ax.text(
        0.05, 0.05,
        f"KR-S4 verification:\n"
        f"Euler slope = {slope_e:.3f} (expected ≈ 1)\n"
        f"RK4   slope = {slope_r:.3f} (expected ≈ 4)\n"
        f"RK4 at dt=0.01 hits FP precision limit (~1e-14)",
        transform=ax.transAxes, fontsize=9, verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    ax.set_xlabel("dt (time step)")
    ax.set_ylabel("max |w_num - w_ana|")
    ax.set_title("KR-S4: Convergence order (input=1, t=0..100)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    out_path = PLOTS_DIR / "plot_convergence.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_analytical_vs_numerical(),
        plot_clip_behavior(),
        plot_convergence(),
    ]
    for p in paths:
        print(f"Saved: {p}")


if __name__ == "__main__":
    main()
