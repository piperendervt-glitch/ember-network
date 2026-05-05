import pytest
import numpy as np

# TODO: Adjust the import path to match your project's structure.
from temperature_node import TemperatureNode


def create_node(**kwargs):
    """Helper to create TemperatureNode with sensible defaults for advanced tests."""
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


def analytical_rhs(T: float, input_val: float, heating_rate: float, cooling_rate: float,
                   alpha_PTC: float, T_ref: float, T_env: float) -> float:
    """Exact right-hand side of the ODE as defined in the model (for RHS fidelity checks)."""
    R_ratio = 1.0 + alpha_PTC * (T - T_ref)
    return R_ratio * heating_rate * input_val - cooling_rate * (T - T_env)


class TestTemperatureNodeAdvanced:
    """Advanced pytest suite for TemperatureNode (Grok III / Stage II).
    
    Focus areas:
    - Mutation testing (catches sign errors, missing PTC factor, wrong clipping, etc.)
    - RHS fidelity via finite-difference verification
    - alpha_PTC boundaries near thermal runaway threshold
    - Combinations of PTC + fractional inputs + arbitrary T_initial + dt=0
    - Physical interpretations (deterrence via T_max, runaway instability)
    """

    def test_rhs_fidelity_ptc_and_no_ptc(self):
        """RHS fidelity: numerical derivative from tiny dt must match analytical ODE RHS.
        
        Mutation-sensitive: fails if PTC term is missing, wrong sign, or R(T) factor incorrect.
        """
        node = create_node(
            heating_rate=0.25,
            cooling_rate=0.08,
            alpha_PTC=0.4,
            T_ref=0.15,
            T_initial=0.4,
            clip_enabled=False,
        )
        test_cases = [
            (0.0, 0.37),   # fractional input
            (0.0, 1.0),
            (0.0, -0.2),   # negative input (extra cooling)
            (0.8, 0.65),   # PTC active + fractional input
        ]

        dt = 1e-6
        for T_init, inp in test_cases:
            node.temperature = T_init  # force state for isolated check
            rhs_analytic = analytical_rhs(
                T_init, inp,
                node._heating_rate if hasattr(node, '_heating_rate') else 0.25,  # fallback
                node._cooling_rate if hasattr(node, '_cooling_rate') else 0.08,
                node._alpha_PTC if hasattr(node, '_alpha_PTC') else 0.4,
                node._T_ref if hasattr(node, '_T_ref') else 0.15,
                node._T_env if hasattr(node, '_T_env') else 0.0,
            )

            T0 = node.temperature
            node.update(inp, dt)
            T1 = node.temperature
            rhs_numeric = (T1 - T0) / dt

            assert np.isclose(rhs_numeric, rhs_analytic, rtol=1e-4, atol=1e-6), (
                f"RHS mismatch at T={T_init}, input={inp}: "
                f"numeric={rhs_numeric:.8f}, analytic={rhs_analytic:.8f}"
            )

    def test_thermal_runaway_boundary_alpha_ptc(self):
        """alpha_PTC boundary around thermal runaway threshold.
        
        Critical alpha = cooling_rate / (heating_rate * input).
        - Below: converges to steady state
        - At/above: exponential growth (runaway) when clip=False
        Physical interpretation: PTC feedback as inherent instability for deterrence hardware.
        """
        heating_rate = 0.2
        cooling_rate = 0.05
        input_val = 0.8
        alpha_crit = cooling_rate / (heating_rate * input_val)  # exact threshold

        dt = 0.02
        n_steps = 800

        # Case 1: sub-critical (stable)
        node_stable = create_node(
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            alpha_PTC=0.95 * alpha_crit,
            T_initial=0.1,
            clip_enabled=False,
        )
        for _ in range(n_steps):
            node_stable.update(input_val, dt)
        assert node_stable.temperature < 2.0, "Sub-critical should not runaway"

        # Case 2: super-critical (runaway)
        node_runaway = create_node(
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            alpha_PTC=1.05 * alpha_crit,
            T_initial=0.1,
            clip_enabled=False,
        )
        for _ in range(n_steps):
            node_runaway.update(input_val, dt)
        assert node_runaway.temperature > 10.0, "Super-critical PTC must exhibit runaway"

        # Case 3: exactly critical (linear growth, no steady state)
        node_crit = create_node(
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            alpha_PTC=alpha_crit,
            T_initial=0.1,
            clip_enabled=False,
        )
        T_before = node_crit.temperature
        for _ in range(n_steps):
            node_crit.update(input_val, dt)
        delta_T = node_crit.temperature - T_before
        assert delta_T > 1.0, "Critical alpha should show unbounded linear growth"

    def test_ptc_fractional_input_initial_temp_dt_zero_combination(self):
        """Combination test: PTC + fractional input + arbitrary T_initial + dt=0 no-op.
        
        Ensures all new features interact correctly (mutation catch for state handling).
        """
        node = create_node(
            alpha_PTC=0.35,
            T_ref=0.25,
            T_initial=0.6,
            clip_enabled=False,
        )
        initial_temp = node.temperature
        assert np.isclose(initial_temp, 0.6)

        # dt=0 must remain no-op regardless of fractional input
        node.update(0.314, 0.0)
        assert np.isclose(node.temperature, initial_temp)

        # Now evolve with fractional input
        dt = 0.01
        for _ in range(50):
            node.update(0.314, dt)

        # Should increase (PTC heating dominates initially)
        assert node.temperature > initial_temp + 0.01

    def test_mutation_clipping_with_high_ptc(self):
        """Mutation test: clipping must prevent runaway even when alpha_PTC would cause instability.
        
        Physical deterrence: T_max acts as hard material damage threshold.
        """
        node = create_node(
            heating_rate=0.3,
            cooling_rate=0.02,
            alpha_PTC=2.0,          # far above critical
            T_initial=0.4,
            T_max=0.75,
            clip_enabled=True,
        )
        dt = 0.05
        for _ in range(400):
            node.update(1.0, dt)

        assert np.isclose(node.temperature, 0.75, atol=1e-5)
        assert np.isclose(node.weight, 1.0)
        # weight must saturate exactly at T_max

    def test_physical_deterence_interpretation_weight_saturation(self):
        """Physical interpretation: weight == 1.0 exactly when T reaches T_max (deterrence signal).
        
        Must hold even when PTC + strong heating would otherwise explode.
        """
        node = create_node(
            heating_rate=1.0,
            cooling_rate=0.01,
            alpha_PTC=1.5,
            T_max=0.9,
            clip_enabled=True,
            T_initial=0.0,
        )
        dt = 0.1
        for _ in range(300):
            node.update(1.0, dt)

        assert np.isclose(node.temperature, 0.9, atol=1e-5)
        assert np.isclose(node.weight, 1.0, atol=1e-8)

        # Now disable clipping → runaway should resume from T_max
        node.clip_enabled = False  # if mutable, or recreate
        # (recreate for strict interface compliance)
        node = create_node(  # fresh node
            heating_rate=1.0,
            cooling_rate=0.01,
            alpha_PTC=1.5,
            T_max=0.9,
            clip_enabled=False,
            T_initial=0.9,
        )
        for _ in range(100):
            node.update(1.0, dt)
        assert node.temperature > 1.5, "Without clip, runaway resumes above T_max"

    def test_negative_alpha_ptc_stability(self):
        """Boundary: negative alpha_PTC (NTC-like) must remain unconditionally stable.
        
        Mutation catch for PTC formula polarity.
        """
        node = create_node(
            alpha_PTC=-0.5,
            T_initial=0.3,
            clip_enabled=False,
        )
        dt = 0.1
        prev_T = node.temperature
        for _ in range(200):
            node.update(1.0, dt)
            assert node.temperature > prev_T  # still heats but slower
            prev_T = node.temperature
        # converges (no runaway)
        assert node.temperature < 3.0

    def test_rhs_fidelity_at_tmax_with_clipping(self):
        """RHS fidelity right at clipping boundary (clip_enabled=True).
        
        Even if analytical RHS > 0, update must not exceed T_max.
        """
        node = create_node(
            heating_rate=2.0,
            cooling_rate=0.001,
            alpha_PTC=0.0,
            T_initial=0.999,
            T_max=1.0,
            clip_enabled=True,
        )
        dt = 1e-4
        T0 = node.temperature
        node.update(1.0, dt)
        assert np.isclose(node.temperature, 1.0, atol=1e-8)

        # Effective numerical RHS must be zero once clipped
        rhs_effective = (node.temperature - T0) / dt
        assert np.isclose(rhs_effective, 0.0, atol=1e-5)