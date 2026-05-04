"""
test_convergence: 数値積分手法の収束性検証 (KR-S4)

- Euler 法の誤差が dt に対して 1 次の収束性 (slope ≈ 1)
- RK4 法の誤差が dt に対して 4 次の収束性 (slope ≈ 4)
- 複数の dt = {1.0, 0.5, 0.1, 0.05, 0.01} で測定

Notes
-----
RK4 は dt が小さくなるにつれ float 精度限界に到達する。dt=0.01 では
誤差が ~5e-15 (machine epsilon に近い) となり収束次数測定の妥当性が
低下する。本テストでは dt=0.05 までを slope 計算に使い、dt=0.01 は
floor effect を documenting する目的で残す。
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analytical import analytical_solution  # noqa: E402
from integrators import integrate_euler, integrate_rk4  # noqa: E402


ALPHA = 0.1
BETA = 0.05
DT_LIST = [1.0, 0.5, 0.1, 0.05, 0.01]


def _dwdt(t: float, w: float, input_value: int) -> float:
    return ALPHA * input_value - BETA * w


def _const_input_one(t: float) -> int:
    return 1


def _measure_max_error(integrator, dt: float) -> float:
    """指定された integrator と dt で input=1, t=0..100 を実行し、
    解析解との最大誤差を返す。"""
    t, w = integrator(_dwdt, 0.0, (0.0, 100.0), dt, _const_input_one)
    ana = analytical_solution(t, 0.0, 1, ALPHA, BETA)
    return float(np.max(np.abs(w - ana)))


def _fit_log_log_slope(dts: list, errors: list) -> float:
    """log(dt) vs log(error) の最小二乗線形回帰で slope を返す。"""
    log_dt = np.log(np.asarray(dts, dtype=float))
    log_err = np.log(np.asarray(errors, dtype=float))
    slope, _ = np.polyfit(log_dt, log_err, 1)
    return float(slope)


def test_euler_first_order_convergence():
    """KR-S4: Euler 法の収束次数が 1 ± 0.1。"""
    errors = [_measure_max_error(integrate_euler, dt) for dt in DT_LIST]
    slope = _fit_log_log_slope(DT_LIST, errors)
    assert 0.9 < slope < 1.1, (
        f"Euler slope = {slope:.3f}, expected ≈ 1.0\n"
        f"errors = {errors}"
    )


def test_rk4_fourth_order_convergence():
    """KR-S4: RK4 法の収束次数が 4 ± 0.5 (FP 限界に達した dt=0.01 を除外)。"""
    # dt=0.01 では誤差が machine epsilon に近づき収束次数測定が不正確に
    # なるため、dt >= 0.05 のみを使う
    dts_use = [dt for dt in DT_LIST if dt >= 0.05]
    errors = [_measure_max_error(integrate_rk4, dt) for dt in dts_use]
    slope = _fit_log_log_slope(dts_use, errors)
    assert 3.5 < slope < 4.5, (
        f"RK4 slope = {slope:.3f}, expected ≈ 4.0\n"
        f"dts = {dts_use}, errors = {errors}"
    )


def test_rk4_more_accurate_than_euler():
    """KR-S4 補助: 同じ dt で RK4 が Euler より高精度。"""
    for dt in DT_LIST:
        err_euler = _measure_max_error(integrate_euler, dt)
        err_rk4 = _measure_max_error(integrate_rk4, dt)
        assert err_rk4 < err_euler, (
            f"dt={dt}: RK4 error {err_rk4:.3e} >= Euler error {err_euler:.3e}"
        )


def test_rk4_floor_effect_at_small_dt():
    """RK4 は dt=0.01 で float 精度限界 (~1e-14) に到達する。

    Notes
    -----
    これは収束次数測定の妥当性を制限する数値解析的事実の documenting。
    実装の bug ではなく、float64 の有効桁数 (~16 桁) の物理的制約。
    """
    err_at_005 = _measure_max_error(integrate_rk4, 0.05)
    err_at_001 = _measure_max_error(integrate_rk4, 0.01)
    # 理論的には dt=0.05→0.01 で 5^4 = 625 倍の改善のはず
    # しかし FP 限界で 100 倍以下しか改善しない
    actual_ratio = err_at_005 / err_at_001
    assert actual_ratio < 625, (
        f"想定外: dt=0.05→0.01 の誤差比 {actual_ratio:.1f} >= 625 "
        f"(FP 限界に到達していない可能性)"
    )
    # 精度限界の証拠として、誤差自体が 1e-13 以下
    assert err_at_001 < 1e-13


def test_kr_s4_quantitative_summary():
    """KR-S4 の達成判定: 全 dt での誤差を測定し、収束性パターンが期待通り。"""
    summary = []
    for dt in DT_LIST:
        err_e = _measure_max_error(integrate_euler, dt)
        err_r = _measure_max_error(integrate_rk4, dt)
        summary.append((dt, err_e, err_r))

    # Euler: dt が半分になるごとに誤差も半分 (1 次収束)
    # 例: dt=1.0 -> dt=0.5 で誤差比 ≈ 0.5
    err_dt1 = summary[0][1]    # dt=1.0
    err_dt05 = summary[1][1]   # dt=0.5
    ratio_e = err_dt05 / err_dt1
    assert 0.45 < ratio_e < 0.55, (
        f"Euler dt=1.0→0.5 誤差比 {ratio_e:.3f} は 0.5 から離れている"
    )

    # RK4: dt が半分になるごとに誤差は 1/16 (4 次収束)
    err_dt1_r = summary[0][2]
    err_dt05_r = summary[1][2]
    ratio_r = err_dt05_r / err_dt1_r
    assert 0.04 < ratio_r < 0.10, (
        f"RK4 dt=1.0→0.5 誤差比 {ratio_r:.4f} は 1/16 ≈ 0.0625 から離れている"
    )
