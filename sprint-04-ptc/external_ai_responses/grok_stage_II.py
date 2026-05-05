import pytest
import numpy as np

# TODO: Adjust the import path to match your project's structure.
# For example: from your_thermal_model import TemperatureNode
from temperature_node import TemperatureNode


def create_node(**kwargs):
    """Helper to create TemperatureNode with sensible defaults for tests."""
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


class TestTemperatureNode:
    def test_initialization_defaults(self):
        """Test default constructor sets correct initial temperature and weight."""
        node = create_node()
        assert np.isclose(node.temperature, 0.0)
        assert np.isclose(node.weight, 0.0)

    def test_dt_zero_no_op(self):
        """dt=0 must be a no-op; temperature and weight unchanged."""
        node = create_node(T_initial=0.5, clip_enabled=False)
        initial_temp = node.temperature
        node.update(0.7, 0.0)
        assert np.isclose(node.temperature, initial_temp)
        assert np.isclose(node.weight, 0.5)

    def test_cooling_to_env_input_zero(self):
        """With input=0, temperature decays exponentially to T_env (PTC irrelevant)."""
        T_init = 0.8
        cooling_rate = 0.1
        total_time = 20.0
        dt = 0.05
        n_steps = int(total_time / dt)

        node = create_node(
            cooling_rate=cooling_rate,
            T_initial=T_init,
            alpha_PTC=0.0,
            clip_enabled=False,
        )

        for _ in range(n_steps):
            node.update(0.0, dt)

        # Analytical solution: T(t) = T_env + (T_init - T_env) * exp(-cooling_rate * t)
        expected = 0.0 + (T_init - 0.0) * np.exp(-cooling_rate * total_time)
        assert np.isclose(node.temperature, expected, atol=1e-4)

    def test_steady_state_no_ptc(self):
        """Steady-state equilibrium without PTC (alpha_PTC=0) matches analytical solution."""
        heating_rate = 0.2
        cooling_rate = 0.1
        input_val = 0.8
        T_env = 0.0
        T_max = 10.0  # large enough to avoid clipping

        node = create_node(
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            T_env=T_env,
            T_max=T_max,
            alpha_PTC=0.0,
            clip_enabled=False,
        )

        dt = 0.05
        for _ in range(2000):  # long enough to reach equilibrium (~100 time units)
            node.update(input_val, dt)

        # Analytical steady-state: T_ss = T_env + (heating_rate * input_val) / cooling_rate
        k = heating_rate * input_val
        T_ss_expected = T_env + k / cooling_rate
        assert np.isclose(node.temperature, T_ss_expected, atol=0.01)

    def test_steady_state_with_ptc(self):
        """Steady-state with PTC (temperature-dependent resistance) matches analytical solution."""
        heating_rate = 0.1
        cooling_rate = 0.05
        alpha = 0.3
        input_val = 1.0
        T_ref = 0.2
        T_env = 0.0

        node = create_node(
            heating_rate=heating_rate,
            cooling_rate=cooling_rate,
            alpha_PTC=alpha,
            T_ref=T_ref,
            T_env=T_env,
            clip_enabled=False,
        )

        dt = 0.02
        for _ in range(3000):  # sufficient simulation time to converge
            node.update(input_val, dt)

        # Analytical equilibrium from setting dT/dt = 0:
        # k * (1 + alpha*(T_ss - T_ref)) = cooling_rate * (T_ss - T_env)
        # => T_ss = [k*(1 - alpha*T_ref) + cooling_rate*T_env] / (cooling_rate - k*alpha)
        k = heating_rate * input_val
        numerator = k * (1 - alpha * T_ref) + cooling_rate * T_env
        denominator = cooling_rate - k * alpha
        T_ss_expected = numerator / denominator
        assert np.isclose(node.temperature, T_ss_expected, atol=0.005)

    def test_clipping_enabled(self):
        """When clip_enabled=True and heating is strong, temperature caps at T_max; weight == 1.0."""
        node = create_node(
            heating_rate=2.0,
            cooling_rate=0.01,
            T_max=0.7,
            alpha_PTC=0.0,
            clip_enabled=True,
        )

        dt = 0.1
        for _ in range(300):
            node.update(1.0, dt)

        assert np.isclose(node.temperature, 0.7, atol=1e-5)
        assert np.isclose(node.weight, 1.0)

    def test_no_clipping_allows_exceed_tmax(self):
        """When clip_enabled=False, temperature can exceed T_max (physical realism check)."""
        node = create_node(
            heating_rate=1.0,
            cooling_rate=0.01,
            T_max=0.5,
            alpha_PTC=0.0,
            clip_enabled=False,
        )

        dt = 0.1
        for _ in range(150):
            node.update(1.0, dt)

        assert node.temperature > 0.5 + 0.1

    def test_weight_property(self):
        """weight = (T - T_env) / (T_max - T_env) works for any T (including outside [T_env, T_max])."""
        T_env = 10.0
        T_max = 30.0
        node_inside = create_node(T_env=T_env, T_max=T_max, T_initial=20.0, clip_enabled=False)
        assert np.isclose(node_inside.weight, 0.5)

        node_above = create_node(T_env=T_env, T_max=T_max, T_initial=45.0, clip_enabled=False)
        assert np.isclose(node_above.weight, 1.75)

    def test_edge_cases_initial_extremes_and_input(self):
        """Edge: negative T_initial allowed (no implicit clipping on construction), input outside [0,1]."""
        # Negative initial temperature (model permits)
        node = create_node(T_initial=-0.3, clip_enabled=False)
        assert np.isclose(node.temperature, -0.3)

        # Update with input > 1 (extra heating) and input < 0 (extra cooling)
        node.update(1.5, 0.1)
        assert node.temperature > -0.3
        node.update(-0.5, 0.1)
        assert node.temperature < node.temperature + 0.01  # directionally correct

        # dt=0 with extreme input still no-op
        temp_before = node.temperature
        node.update(10.0, 0.0)
        assert np.isclose(node.temperature, temp_before)