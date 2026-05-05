import pytest
import numpy as np

# TODO: Adjust the import path to match your project's structure.
from temperature_node import TemperatureNode


def create_node(**kwargs):
    """Helper to create TemperatureNode with sensible defaults for gap-filling tests."""
    defaults = {
        "heating_rate": 0.1,
        "cooling_rate": 0.05,
        "T_env": 0.0,
        "T_max": 1.0,
        "alpha_PTC": 0.3,
        "T_ref": 0.0,
        "T_initial": 0.0,
        "clip_enabled": True,
    }
    defaults.update(kwargs)
    return TemperatureNode(**defaults)


class TestTemperatureNodeGaps:
    """Additional pytest suite (Grok I) targeting gaps in existing Claude-written tests.
    
    Covers:
    - Mutations missed by prior suites (T_ref mismatch, non-zero T_env, degenerate T_max)
    - Overlooked edge cases (T_initial > T_max, T_max == T_env)
    - Untested combinations (dynamic input switching + PTC + clipping)
    - Physical deterrence interpretations (cool-down from clipped state, negative weight)
    - Zero-parameter physical limits (zero heating/cooling)
    """

    def test_nonzero_tenv_physical_ambient(self):
        """Non-zero T_env: cooling/heating must be relative to realistic ambient temperature.
        
        Mutation catch: tests if cooling term wrongly assumes T_env=0.
        Physical meaning: system equilibrates to room temperature, not absolute zero.
        """
        T_env = 25.0
        T_initial = 30.0
        node = create_node(
            T_env=T_env,
            T_initial=T_initial,
            alpha_PTC=0.0,   # disable PTC for clean exponential test
            clip_enabled=False,
        )

        dt = 0.1
        for _ in range(300):
            node.update(0.0, dt)  # pure cooling

        # Analytical: T(t) → T_env
        assert np.isclose(node.temperature, T_env, atol=0.01)
        assert np.isclose(node.weight, 0.0)  # weight must be zero at ambient

    def test_tref_different_from_tenv_and_initial(self):
        """T_ref ≠ T_env (and ≠ T_initial): PTC reference must be independent.
        
        Mutation-sensitive: fails if code hard-codes T_ref = T_env internally.
        """
        node = create_node(
            T_env=0.0,
            T_ref=0.5,
            T_initial=0.2,
            alpha_PTC=0.4,
            clip_enabled=False,
        )
        dt = 0.05
        for _ in range(400):
            node.update(1.0, dt)

        # Analytical steady-state with offset T_ref
        k = 0.1 * 1.0
        alpha = 0.4
        numerator = k * (1 - alpha * 0.5)
        denom = 0.05 - k * alpha
        T_ss = numerator / denom
        assert np.isclose(node.temperature, T_ss, atol=0.01)

    def test_tmax_equal_tenv_degenerate_weight(self):
        """T_max == T_env: weight must be identically zero (no division-by-zero crash).
        
        Edge case overlooked in basic suites; tests numerical robustness.
        """
        node = create_node(
            T_env=1.0,
            T_max=1.0,
            T_initial=1.5,
            clip_enabled=True,
        )
        assert np.isclose(node.weight, 0.0)  # must not raise ZeroDivisionError

        node.update(1.0, 0.1)
        assert np.isclose(node.weight, 0.0)
        assert np.isclose(node.temperature, 1.0)  # clipped

    def test_initial_above_tmax_with_clip_enabled(self):
        """T_initial > T_max + clip_enabled=True: constructor vs update clipping.
        
        Physical deterrence: hardware must never exceed damage threshold, even at t=0.
        (Tests whether clipping is applied on construction or only on update.)
        """
        node = create_node(
            T_initial=1.8,
            T_max=0.9,
            clip_enabled=True,
        )
        # Either constructor clips immediately or first update does
        assert node.temperature <= 0.9 + 1e-8
        assert np.isclose(node.weight, 1.0)

    def test_dynamic_input_switching_ptc_clipping(self):
        """Dynamic input (0 → 1 → 0) with PTC + clipping: cool-down after saturation.
        
        Physical interpretation: deterrence signal (weight=1) must decay when power is removed.
        Combination not tested in prior constant-input suites.
        """
        node = create_node(
            heating_rate=0.5,
            cooling_rate=0.1,
            alpha_PTC=0.6,
            T_max=0.8,
            clip_enabled=True,
        )

        # Phase 1: strong heating → clip
        for _ in range(200):
            node.update(1.0, 0.02)
        assert np.isclose(node.temperature, 0.8)
        assert np.isclose(node.weight, 1.0)

        # Phase 2: sudden power off → cool to ambient
        for _ in range(300):
            node.update(0.0, 0.02)
        assert node.temperature < 0.8 - 0.1
        assert node.weight < 0.9

    def test_negative_weight_below_ambient(self):
        """T < T_env → negative weight allowed (physical over-cooling).
        
        Mutation catch: if weight formula clamps to [0,1] silently.
        """
        node = create_node(
            T_env=0.5,
            T_initial=0.0,
            clip_enabled=False,
        )
        assert node.weight < 0.0  # must be negative

        # Further cooling with negative input
        node.update(-1.0, 0.1)
        assert node.weight < -0.1

    def test_zero_heating_rate_and_zero_cooling_rate(self):
        """Zero heating_rate or zero cooling_rate: physical invariants.
        
        - heating_rate=0 → temperature only cools (or stays)
        - cooling_rate=0 → pure heating (runaway unless clipped)
        """
        # Case A: no heating
        node_noheat = create_node(heating_rate=0.0, T_initial=0.7, clip_enabled=False)
        T0 = node_noheat.temperature
        node_noheat.update(1.0, 10.0)
        assert np.isclose(node_noheat.temperature, T0 - 0.05 * 10.0 * 0.7)  # pure cooling

        # Case B: no cooling (adiabatic heating + PTC)
        node_nocool = create_node(cooling_rate=0.0, clip_enabled=True, T_max=0.6)
        for _ in range(100):
            node_nocool.update(1.0, 0.05)
        assert np.isclose(node_nocool.temperature, 0.6)
        assert np.isclose(node_nocool.weight, 1.0)

    def test_large_dt_stability_and_dt_negative_ignored(self):
        """Large dt and negative dt: numerical robustness + spec compliance.
        
        dt < 0 must be treated as no-op (per interface contract).
        Large dt tests Euler-step stability under extreme conditions.
        """
        node = create_node(T_initial=0.4, clip_enabled=False)

        # Negative dt → no-op
        T_before = node.temperature
        node.update(1.0, -0.1)
        assert np.isclose(node.temperature, T_before)

        # Very large dt (should not explode unrealistically)
        node.update(1.0, 50.0)  # 50 time units in one step
        # With PTC + clipping off, expect large but finite increase
        assert node.temperature > 0.4
        assert np.isfinite(node.temperature)