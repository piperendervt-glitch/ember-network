"""
visualize.py: Sprint 1 の結果プロット生成

3 つのプロットを results/plots/ に生成する:
1. plot_constant_input.png  - KR-S1 (一定入力下での飽和)
2. plot_input_cessation.png - KR-S2 (入力停止後の線形減衰)
3. plot_reproducibility.png - KR-S3 (5 シードでの bit-perfect 一致)
"""

import random
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from binary_node import BinaryNode  # noqa: E402


PLOTS_DIR = ROOT / "results" / "plots"
SEEDS = [0, 1, 2, 3, 42]
LEARNING_RATE = 0.1
FORGETTING_RATE = 0.05
TOTAL_STEPS = 100
CESSATION_SWITCH = 50


def run_constant_input(steps: int = TOTAL_STEPS) -> np.ndarray:
    """input=1 を steps 回提示して weight 時系列を返す (t=0 を含む)。"""
    node = BinaryNode(
        learning_rate=LEARNING_RATE, forgetting_rate=FORGETTING_RATE
    )
    trajectory = [node.weight]
    for _ in range(steps):
        node.update(1)
        trajectory.append(node.weight)
    return np.array(trajectory)


def run_input_cessation(
    steps: int = TOTAL_STEPS, switch_at: int = CESSATION_SWITCH
) -> np.ndarray:
    """前半 input=1, 後半 input=0 の weight 時系列を返す。"""
    node = BinaryNode(
        learning_rate=LEARNING_RATE, forgetting_rate=FORGETTING_RATE
    )
    trajectory = [node.weight]
    for t in range(1, steps + 1):
        inp = 1 if t <= switch_at else 0
        node.update(inp)
        trajectory.append(node.weight)
    return np.array(trajectory)


def run_with_seed(seed: int) -> np.ndarray:
    """指定シードで constant input シナリオを実行し weight 時系列を返す。"""
    random.seed(seed)
    np.random.seed(seed)
    return run_constant_input()


def theory_constant_input(steps: int = TOTAL_STEPS) -> np.ndarray:
    """constant input シナリオの理論値: 0.05*t (clip 前)、1.0 (clip 後)。"""
    t = np.arange(steps + 1)
    weight = (LEARNING_RATE - FORGETTING_RATE) * t
    return np.clip(weight, 0.0, 1.0)


def theory_input_cessation(
    steps: int = TOTAL_STEPS, switch_at: int = CESSATION_SWITCH
) -> np.ndarray:
    """input cessation シナリオの理論値。"""
    t = np.arange(steps + 1)
    weight = np.where(
        t <= switch_at,
        (LEARNING_RATE - FORGETTING_RATE) * t,
        1.0 - FORGETTING_RATE * (t - switch_at),
    )
    return np.clip(weight, 0.0, 1.0)


def plot_constant_input() -> Path:
    """KR-S1 のプロットを生成。"""
    measured = run_constant_input()
    theory = theory_constant_input()
    t = np.arange(len(measured))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, measured, color="blue", linewidth=2, label="Measured")
    ax.plot(
        t,
        theory,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="Theory: 0.05*t, then 1.0",
    )
    ax.axvline(x=20, color="gray", linestyle=":", linewidth=1)
    ax.annotate(
        "Clipping starts (t=20)",
        xy=(20, 1.0),
        xytext=(30, 0.6),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
    ax.set_xlabel("time step")
    ax.set_ylabel("weight")
    ax.set_title("KR-S1: Constant input (input=1 for 100 steps)")
    ax.set_xlim(0, TOTAL_STEPS)
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_constant_input.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_input_cessation() -> Path:
    """KR-S2 のプロットを生成。"""
    measured = run_input_cessation()
    theory = theory_input_cessation()
    t = np.arange(len(measured))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, measured, color="blue", linewidth=2, label="Measured")
    ax.plot(
        t,
        theory,
        color="red",
        linestyle="--",
        linewidth=1.5,
        label="Theory",
    )
    ax.axvline(x=50, color="gray", linestyle=":", linewidth=1)
    ax.axvline(x=70, color="gray", linestyle=":", linewidth=1)
    ax.annotate(
        "Input ceases (t=50)",
        xy=(50, 1.0),
        xytext=(55, 0.85),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
    ax.annotate(
        "Decay completes (t=70)",
        xy=(70, 0.0),
        xytext=(72, 0.2),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
    ax.set_xlabel("time step")
    ax.set_ylabel("weight")
    ax.set_title(
        "KR-S2: Input cessation (input=1 for 50 steps, then input=0)"
    )
    ax.set_xlim(0, TOTAL_STEPS)
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_input_cessation.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_reproducibility() -> Path:
    """KR-S3 のプロットを生成 (5 シードでの完全一致を視覚化)。

    視覚的な「重なり」だけでは判別困難なため、5 軌跡間の最大絶対差分
    `max(|diff|)` をプロット内テキストとして表示し、bit-perfect 一致を
    数値証拠として示す。
    """
    trajectories = {seed: run_with_seed(seed) for seed in SEEDS}
    t = np.arange(TOTAL_STEPS + 1)

    reference = trajectories[SEEDS[0]]
    max_diff = max(
        float(np.max(np.abs(traj - reference)))
        for traj in trajectories.values()
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    linestyles = ["-", "--", "-.", ":", (0, (5, 10))]
    colors = ["blue", "orange", "green", "red", "purple"]
    for (seed, traj), ls, col in zip(
        trajectories.items(), linestyles, colors
    ):
        ax.plot(
            t,
            traj,
            color=col,
            linestyle=ls,
            linewidth=1.5,
            label=f"seed={seed}",
            alpha=0.7,
        )

    ax.text(
        0.05, 0.95,
        f"Numerical evidence:\nmax(|diff|) across 5 seeds = {max_diff:.2e}",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor="gray",
            alpha=0.9,
        ),
    )

    ax.set_xlabel("time step")
    ax.set_ylabel("weight")
    ax.set_title(
        "KR-S3: Reproducibility across 5 seeds "
        "(deterministic model: lines overlap)"
    )
    ax.set_xlim(0, TOTAL_STEPS)
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_reproducibility.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_constant_input(),
        plot_input_cessation(),
        plot_reproducibility(),
    ]
    for p in paths:
        print(f"Saved: {p}")


if __name__ == "__main__":
    main()
