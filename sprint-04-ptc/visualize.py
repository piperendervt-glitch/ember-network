"""
visualize.py: Sprint 4 (PTC) の結果プロット生成

Sprint 4 で確立された物理的観察を視覚化する 6 プロットを
results/plots/ に生成する:

1. plot_critical_curve.png        - α_PTC × input の臨界曲線 (b=0)
2. plot_alpha_sweep_evolution.png - 5 つの α_PTC 値での T(t) 進化 (KR-S2)
3. plot_clip_deterrence.png       - clip on/off の deterrence 機能比較 (α=1)
4. plot_mms_accuracy.png          - MMS の精度 (3 製造解 × 4 α_PTC)
5. plot_mutation_kill_rate.png    - Mutation Testing kill rate サマリ
6. plot_sprint3_continuity.png    - Sprint 3 → Sprint 4 連続性 (α=0 で bit-perfect)
"""

import importlib.util
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


# =============================================================================
# Plot 1: 臨界曲線 (α_PTC × input、b = α·h·u - c = 0)
# =============================================================================

def plot_critical_curve() -> Path:
    """α_PTC × input パラメータ空間における臨界曲線 b=0 と 3 領域。"""
    alphas = np.linspace(0, 1.5, 200)
    inputs = np.linspace(0.0, 1.0, 200)
    A, U = np.meshgrid(alphas, inputs)
    B = A * HEATING_RATE * U - COOLING_RATE  # b の符号

    fig, ax = plt.subplots(figsize=(8, 6))

    # 領域カラーマップ
    levels = [-COOLING_RATE - 0.01, -1e-6, 1e-6, COOLING_RATE * 2]
    colors = ["#9ec5fe", "#ffe39d", "#f5a8a8"]  # subcrit, crit, supercrit
    cs = ax.contourf(A, U, B, levels=levels, colors=colors, alpha=0.7)

    # 臨界曲線 b=0: α·u = c/h = 0.5
    crit_alpha = np.linspace(0.5, 1.5, 100)
    crit_input = COOLING_RATE / (HEATING_RATE * crit_alpha)
    crit_input = np.clip(crit_input, 0, 1)
    ax.plot(crit_alpha, crit_input, color="black", linewidth=2.5,
            label=r"$b = 0$ (critical curve: $\alpha_{PTC}\cdot u = 0.5$)")

    # KR-S2 / KR-S6 で使用した α 値をマーク
    kr_s2_alphas = [0.0, 0.1, 0.4, 0.6, 1.0]
    for alpha in kr_s2_alphas:
        ax.axvline(x=alpha, color="gray", linewidth=0.5,
                   linestyle="--", alpha=0.6)
    ax.scatter([1.0, 0.6], [0.5, 0.83333],
               s=80, color="red", marker="x", linewidths=2.5,
               label=r"runaway test points ($\alpha\cdot u > 0.5$)", zorder=5)

    # 領域ラベル
    ax.text(0.2, 0.5, "subcritical\n(b<0, asymptotic)",
            fontsize=10, ha="center", style="italic", color="#1c4587")
    ax.text(1.2, 0.85, "supercritical\n(b>0, runaway)",
            fontsize=10, ha="center", style="italic", color="#7a1f1f")
    ax.text(0.7, 0.97, "b≈0",
            fontsize=9, ha="center", style="italic", color="#6f5e1c")

    ax.set_xlabel(r"$\alpha_{PTC}$ (PTC coefficient)")
    ax.set_ylabel(r"input value $u$")
    ax.set_title(r"Sprint 4: $\alpha_{PTC} \times u$ critical curve "
                 r"(heating=0.1, cooling=0.05)")
    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(True, alpha=0.3)

    cb = fig.colorbar(cs, ax=ax, ticks=[-0.04, 0, 0.05])
    cb.set_label(r"$b = \alpha\cdot h\cdot u - c$")

    out_path = PLOTS_DIR / "plot_critical_curve.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# Plot 2: 5 つの α_PTC 値での T(t) 進化 (KR-S2)
# =============================================================================

def plot_alpha_sweep_evolution() -> Path:
    """KR-S2 の 5 つの α_PTC で温度時系列を比較。"""
    alpha_values = [0.0, 0.1, 0.4, 0.6, 1.0]
    total_times = [100.0, 100.0, 100.0, 30.0, 12.0]  # supercritical は短く
    colors = plt.get_cmap("viridis")(np.linspace(0.1, 0.9, len(alpha_values)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    for alpha, total_time, color in zip(alpha_values, total_times, colors):
        node = TemperatureNode(
            heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE,
            T_env=T_ENV, T_max=T_MAX, alpha_PTC=alpha,
            clip_enabled=False, integrator='rk4',
        )
        times, T_num = run_constant_input_scenario(
            node, total_time=total_time, dt=DT, input_value=1.0
        )
        T_anal = analytical_temperature(
            times, T_0=T_ENV, input_value=1.0,
            heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE,
            T_env=T_ENV, alpha_PTC=alpha,
        )
        b = alpha * HEATING_RATE * 1.0 - COOLING_RATE
        regime = ("subcritical" if b < -1e-9
                  else "critical" if abs(b) < 1e-9
                  else "supercritical")
        label = (rf"$\alpha={alpha}$  ($b={b:+.3f}$, {regime})")

        # ax1: full timeseries (linear)
        ax1.plot(times, T_num, color=color, linewidth=2, label=label)
        ax1.plot(times, T_anal, color=color, linestyle=":",
                 linewidth=1, alpha=0.6)

    ax1.axhline(y=T_MAX, color="orange", linestyle="-.",
                linewidth=0.8, alpha=0.5, label=r"$T_{max}=1$")
    ax1.set_xlabel("time")
    ax1.set_ylabel(r"temperature $T$")
    ax1.set_title(r"KR-S2: $T(t)$ for 5 $\alpha_{PTC}$ values "
                  r"(input=1, RK4, clip off)")
    ax1.set_xlim(0, 100)
    ax1.set_ylim(-0.1, 4.5)
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ax2: log scale で発散 vs 漸近の差を強調
    for alpha, total_time, color in zip(alpha_values, total_times, colors):
        node = TemperatureNode(
            heating_rate=HEATING_RATE, cooling_rate=COOLING_RATE,
            T_env=T_ENV, T_max=T_MAX, alpha_PTC=alpha,
            clip_enabled=False, integrator='rk4',
        )
        times, T_num = run_constant_input_scenario(
            node, total_time=total_time, dt=DT, input_value=1.0
        )
        ax2.semilogy(times, np.maximum(T_num, 1e-6),
                     color=color, linewidth=2,
                     label=rf"$\alpha={alpha}$")

    ax2.set_xlabel("time")
    ax2.set_ylabel(r"$\log_{10} T$")
    ax2.set_title(r"Same data on log scale (runaway $\alpha=1.0$ visible)")
    ax2.set_xlim(0, 100)
    ax2.legend(loc="lower right", fontsize=9)
    ax2.grid(True, which="both", alpha=0.3)

    out_path = PLOTS_DIR / "plot_alpha_sweep_evolution.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# Plot 3: clip の deterrence 機能 (α=1.0, clip on vs off)
# =============================================================================

def plot_clip_deterrence() -> Path:
    """α=1 (supercritical) における clip の deterrence 機能を比較。"""
    total_time = 15.0
    alpha = 1.0

    node_clip = TemperatureNode(
        alpha_PTC=alpha, clip_enabled=True, integrator='rk4',
    )
    times_c, T_c = run_constant_input_scenario(
        node_clip, total_time=total_time, dt=DT, input_value=1.0,
    )
    node_no_clip = TemperatureNode(
        alpha_PTC=alpha, clip_enabled=False, integrator='rk4',
    )
    times_nc, T_nc = run_constant_input_scenario(
        node_no_clip, total_time=total_time, dt=DT, input_value=1.0,
    )

    # clip 発動時刻 (T が T_max に到達した時点)
    indices_clip = np.where(T_c >= T_MAX - 1e-10)[0]
    t_clip = times_c[indices_clip[0]] if len(indices_clip) > 0 else None

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(times_nc, T_nc, color="red", linewidth=2,
            label=r"clip OFF: exponential runaway", alpha=0.85)
    ax.plot(times_c, T_c, color="blue", linewidth=2,
            label=r"clip ON: bounded by $T_{max}$ (deterrence)", alpha=0.85)
    ax.axhline(y=T_MAX, color="orange", linestyle="-.",
               linewidth=1.0, alpha=0.6,
               label=rf"$T_{{max}}={T_MAX}$ (damage threshold)")

    if t_clip is not None:
        ax.axvline(x=t_clip, color="purple", linestyle=":",
                   linewidth=1.0, alpha=0.6,
                   label=rf"$t_{{clip}}\approx {t_clip:.2f}$ "
                         f"(first hit on $T_{{max}}$)")
        ax.text(t_clip + 0.3, 0.5,
                f"clip activates\n(deterrence engages)",
                fontsize=9, color="purple", style="italic")

    ax.text(
        0.55, 0.05,
        r"At $\alpha=1.0$, $b=\alpha\cdot h\cdot u - c = 0.05 > 0$"
        "\n→ exponential runaway without clip"
        "\n→ clip provides hard physical bound for deterrence",
        transform=ax.transAxes, fontsize=9, verticalalignment="bottom",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    ax.set_xlabel("time")
    ax.set_ylabel(r"temperature $T$")
    ax.set_title(r"Sprint 4: Clip as deterrence mechanism "
                 r"($\alpha_{PTC}=1.0$ supercritical)")
    ax.set_xlim(0, total_time)
    ax.set_ylim(-0.1, max(T_nc) * 1.05)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_clip_deterrence.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# Plot 4: MMS 精度 (3 製造解 × 4 α_PTC)
# =============================================================================

def plot_mms_accuracy() -> Path:
    """MMS の数値解と製造解の最大誤差 (12 組合せ)。"""
    def make_polynomial():
        return manufactured_polynomial([0.1, 0.0, 0.5])  # T=0.1+0.5t^2

    def make_trigonometric():
        return manufactured_trigonometric(0.3, 0.2, 0.5)

    def make_exponential():
        return manufactured_exponential(1.0, 0.05, 0.0)

    manufactured_solutions = [
        ("polynomial", make_polynomial),
        ("trigonometric", make_trigonometric),
        ("exponential", make_exponential),
    ]
    alpha_values = [0.0, 0.3, 0.5, 1.0]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    markers = ["o", "s", "^"]

    for (name, mfg_fn), marker in zip(manufactured_solutions, markers):
        errors = []
        for alpha in alpha_values:
            T_sym, t_sym = mfg_fn()
            T_callable = manufactured_to_callable(T_sym, t_sym)
            source_func = compute_source_term(
                T_sym, t_sym,
                heating_rate=HEATING_RATE,
                cooling_rate=COOLING_RATE,
                T_env=T_ENV,
                input_value=1.0,
                alpha_PTC=alpha,
                T_ref=T_ENV,
            )
            times, T_num = integrate_with_source(
                T_0=float(T_callable(0.0)),
                t_span=(0.0, 1.0),
                dt=0.001,
                heating_rate=HEATING_RATE,
                cooling_rate=COOLING_RATE,
                T_env=T_ENV,
                input_value=1.0,
                source_func=source_func,
                alpha_PTC=alpha,
                T_ref=T_ENV,
                integrator='rk4',
            )
            T_exact = np.array([T_callable(t) for t in times])
            max_err = float(np.max(np.abs(T_num - T_exact)))
            errors.append(max_err)
        ax.semilogy(alpha_values, errors, marker=marker,
                    markersize=9, linewidth=1.5,
                    label=f"manufactured: {name}")

    ax.axhline(y=1e-6, color="red", linestyle="--", linewidth=1.0,
               alpha=0.6, label=r"KR-S7 acceptance: $\epsilon < 10^{-6}$")

    ax.set_xlabel(r"$\alpha_{PTC}$")
    ax.set_ylabel(r"max $|T_{num} - T_{exact}|$ (log scale)")
    ax.set_title(r"KR-S7: MMS verification accuracy "
                 r"(3 manufactured solutions $\times$ 4 $\alpha_{PTC}$)")
    ax.set_xticks(alpha_values)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    out_path = PLOTS_DIR / "plot_mms_accuracy.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# Plot 5: Mutation Testing kill rate (タスク 16 KR-S8)
# =============================================================================

def plot_mutation_kill_rate() -> Path:
    """Mutation Testing kill rate サマリ (全体 + 生存カテゴリ別)。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # ax1: 全体 kill / survive / timeout の円グラフ
    sizes = [304, 76, 1]
    labels = ["killed (304, 79.79%)",
              "survived (76, 19.95%)",
              "timeout (1, 0.26%)"]
    colors = ["#5cb85c", "#f0ad4e", "#d9534f"]
    explode = (0.02, 0.05, 0.05)

    wedges, texts, autotexts = ax1.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct=lambda p: f"{p:.1f}%" if p > 1 else "",
        startangle=90, wedgeprops=dict(edgecolor="white", linewidth=1.5),
        textprops=dict(fontsize=9),
    )
    ax1.set_title("Sprint 4 Mutation Testing: 381 mutants total\n"
                  "(WSL Ubuntu 24.04, mutmut 3.5.0)",
                  fontsize=11)
    # Tripwire #8 アノテーション
    ax1.text(
        0, -1.45,
        "Tripwire #8: kill rate < 50% → would trigger halt-and-confirm\n"
        f"Actual: 79.79% (well above 50%, no trigger)",
        ha="center", fontsize=9, style="italic",
        bbox=dict(boxstyle="round", facecolor="#dff0d8",
                  edgecolor="#5cb85c", alpha=0.7),
    )

    # ax2: 生存 mutant のカテゴリ別棒グラフ
    categories = [
        ("default args", 8, "#a8d4ff"),
        ("error msg", 12, "#a8d4ff"),
        ("< vs <=", 5, "#a8d4ff"),
        ("T_env=0 dep", 3, "#ff8c8c"),  # 真の coverage gap
        ("dt branch", 1, "#ff8c8c"),    # 真の coverage gap
        ("MMS internal", 25, "#ffcc99"),  # 手法限界
        ("misc", 22, "#cccccc"),
    ]
    names = [c[0] for c in categories]
    counts = [c[1] for c in categories]
    bar_colors = [c[2] for c in categories]

    bars = ax2.bar(names, counts, color=bar_colors,
                   edgecolor="black", linewidth=0.8)
    for bar, n in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width() / 2, n + 0.5, str(n),
                 ha="center", fontsize=9)

    ax2.set_ylabel("survived mutants count")
    ax2.set_title(
        "Survived mutant categories (76 total)\n"
        "blue=equivalent, red=true gap, orange=method limit, gray=other",
        fontsize=11,
    )
    ax2.set_ylim(0, 30)
    ax2.grid(True, axis="y", alpha=0.3)
    plt.setp(ax2.get_xticklabels(), rotation=20, ha="right", fontsize=9)

    out_path = PLOTS_DIR / "plot_mutation_kill_rate.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# Plot 6: Sprint 3 → Sprint 4 連続性 (α=0 で bit-perfect)
# =============================================================================

def plot_sprint3_continuity() -> Path:
    """α_PTC=0 で Sprint 3 と bit-perfect 一致することの demonstration。"""
    s3 = ROOT.parent / "sprint-03-temperature"
    spec_node = importlib.util.spec_from_file_location(
        "s3_temperature_node", s3 / "src" / "temperature_node.py"
    )
    s3_node_mod = importlib.util.module_from_spec(spec_node)
    sys.path.insert(0, str(s3 / "src"))
    sys.path.insert(0, str(s3))
    spec_node.loader.exec_module(s3_node_mod)
    Sprint3Node = s3_node_mod.TemperatureNode

    spec_scen = importlib.util.spec_from_file_location(
        "s3_scenarios", s3 / "scenarios.py"
    )
    s3_scen = importlib.util.module_from_spec(spec_scen)
    spec_scen.loader.exec_module(s3_scen)

    total_time = 100.0

    # Sprint 3 (no PTC concept)
    s3_node = Sprint3Node(clip_enabled=False, integrator='rk4')
    times_3, T_3 = s3_scen.run_constant_input_scenario(
        s3_node, total_time=total_time, dt=DT, input_value=1
    )

    # Sprint 4 with α=0 (PTC disabled)
    s4_node = TemperatureNode(alpha_PTC=0.0, clip_enabled=False, integrator='rk4')
    times_4, T_4 = run_constant_input_scenario(
        s4_node, total_time=total_time, dt=DT, input_value=1
    )

    # Sprint 4 with α=0.3 (default PTC active)
    s4_node_ptc = TemperatureNode(alpha_PTC=0.3, clip_enabled=False, integrator='rk4')
    _, T_4_ptc = run_constant_input_scenario(
        s4_node_ptc, total_time=total_time, dt=DT, input_value=1
    )

    bit_perfect = bool(np.array_equal(T_3, T_4))
    max_diff_alpha_zero = float(np.max(np.abs(T_3 - T_4)))
    max_diff_ptc = float(np.max(np.abs(T_3 - T_4_ptc)))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(times_3, T_3, color="black", linewidth=2.5,
            label="Sprint 3 (linear, no PTC)", alpha=0.9)
    ax.plot(times_4, T_4, color="cyan", linestyle="--", linewidth=1.5,
            label=rf"Sprint 4 with $\alpha_{{PTC}}=0$ "
                  rf"(bit-perfect: max diff = {max_diff_alpha_zero:.0e})",
            alpha=0.85)
    ax.plot(times_4, T_4_ptc, color="red", linestyle=":", linewidth=2,
            label=rf"Sprint 4 with $\alpha_{{PTC}}=0.3$ "
                  rf"(PTC raises $T_{{eq}}$: 2.0 $\to$ 5.0, "
                  rf"max diff = {max_diff_ptc:.2f})",
            alpha=0.85)

    ax.text(
        0.05, 0.95,
        f"KR-S1 verification:\n"
        f"  np.array_equal(Sprint3, Sprint4_α=0) = {bit_perfect}\n"
        f"  max|Δ| at α=0   = {max_diff_alpha_zero:.3e}\n"
        f"  max|Δ| at α=0.3 = {max_diff_ptc:.3f}",
        transform=ax.transAxes, fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  edgecolor="gray", alpha=0.9),
    )

    ax.set_xlabel("time")
    ax.set_ylabel(r"temperature $T$")
    ax.set_title(r"KR-S1: Sprint 3 $\leftrightarrow$ Sprint 4 ($\alpha_{PTC}=0$) "
                 r"bit-perfect continuity")
    ax.set_xlim(0, total_time)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3)

    out_path = PLOTS_DIR / "plot_sprint3_continuity.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


# =============================================================================
# main
# =============================================================================

def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating Sprint 4 plots to {PLOTS_DIR}")
    for fn in (plot_critical_curve,
               plot_alpha_sweep_evolution,
               plot_clip_deterrence,
               plot_mms_accuracy,
               plot_mutation_kill_rate,
               plot_sprint3_continuity):
        out = fn()
        size_kb = out.stat().st_size / 1024
        print(f"  {fn.__name__:32s} -> {out.name} ({size_kb:.1f} KB)")
    print("Done.")


if __name__ == "__main__":
    main()
