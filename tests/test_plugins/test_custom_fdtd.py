"""Tests for simplified custom FDTD plugin using native Tidy3D formats only."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import tidy3d as td
from tidy3d.components.data.sim_data import SimulationData
from tidy3d.plugins.custom_fdtd import CustomFDTDTask, webapi


@pytest.fixture
def basic_simulation():
    """Create a simple, valid Tidy3D simulation for testing."""
    return td.Simulation(
        size=(2.0, 2.0, 2.0),
        center=(0, 0, 0),
        run_time=1e-12,
        sources=[
            td.PlaneWave(
                size=(td.inf, td.inf, 0),
                center=(0, 0, -0.5),
                source_time=td.GaussianPulse(
                    freq0=2e14,
                    fwidth=4e13,
                ),
                direction="+",
                pol_angle=0,
            )
        ],
        monitors=[
            td.FieldMonitor(
                size=(1.0, 1.0, 0), center=(0, 0, 0), freqs=[2e14], name="field_monitor"
            )
        ],
        grid_spec=td.GridSpec.auto(wavelength=1.5e-6),
    )


class TestCustomFDTDTask:
    """Test simplified CustomFDTDTask using native formats."""

    def test_task_initialization(self, basic_simulation):
        """Test task creation with native simulation."""
        task = CustomFDTDTask(
            simulation=basic_simulation,
            task_name="test_task",
            solver_params={"solver_version": "v2.0", "max_iterations": 2000},
        )

        assert task.simulation == basic_simulation
        assert task.task_name == "test_task"
        assert task.solver_params["solver_version"] == "v2.0"
        assert task.solver_params["max_iterations"] == 2000

        # Check default parameters were set
        assert "convergence_threshold" in task.solver_params
        assert "timestep_factor" in task.solver_params

    def test_task_upload(self, basic_simulation):
        """Test simulation upload."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="upload_test")

        task_id = task.upload()
        assert task_id == task.task_id
        assert len(task_id) > 0

    def test_task_execute_returns_simulation_data(self, basic_simulation):
        """Test that execute returns standard SimulationData."""
        task = CustomFDTDTask(
            simulation=basic_simulation,
            task_name="execute_test",
            solver_params={"max_iterations": 500},
        )

        result = task.execute()

        # Should return standard SimulationData
        assert isinstance(result, SimulationData)
        assert result.simulation == basic_simulation

        # Should have solver info in log
        assert "[CUSTOM_FDTD]" in result.log
        assert "Iterations:" in result.log
        assert "Convergence:" in result.log
        assert task.task_id in result.log

    def test_solver_parameters_default_values(self, basic_simulation):
        """Test default solver parameters are set correctly."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="defaults_test")

        # Check all default parameters exist
        expected_defaults = {
            "solver_version": "v1.0",
            "max_iterations": 1000,
            "convergence_threshold": 1e-8,
            "timestep_factor": 0.5,
            "numerical_precision": "double",
        }

        for key, expected_value in expected_defaults.items():
            assert task.solver_params[key] == expected_value

    def test_custom_solver_parameters_override_defaults(self, basic_simulation):
        """Test custom parameters override defaults."""
        custom_params = {
            "solver_version": "v3.0",
            "max_iterations": 5000,
            "custom_param": "custom_value",
        }

        task = CustomFDTDTask(
            simulation=basic_simulation, task_name="custom_params_test", solver_params=custom_params
        )

        # Custom parameters should be present
        assert task.solver_params["solver_version"] == "v3.0"
        assert task.solver_params["max_iterations"] == 5000
        assert task.solver_params["custom_param"] == "custom_value"

        # Non-overridden defaults should still be present
        assert task.solver_params["convergence_threshold"] == 1e-8
        assert task.solver_params["timestep_factor"] == 0.5


class TestSimplifiedWebAPI:
    """Test simplified web API using native formats."""

    def test_webapi_run_basic(self, basic_simulation):
        """Test basic run functionality."""
        result = webapi.run(simulation=basic_simulation, task_name="webapi_test", verbose=False)

        assert isinstance(result, SimulationData)
        assert result.simulation == basic_simulation
        assert "[CUSTOM_FDTD]" in result.log

    def test_webapi_run_with_solver_params(self, basic_simulation):
        """Test run with custom solver parameters."""
        result = webapi.run(
            simulation=basic_simulation,
            task_name="webapi_params_test",
            solver_version="v2.5",
            max_iterations=3000,
            convergence_threshold=1e-10,
            custom_flag=True,
            verbose=False,
        )

        assert isinstance(result, SimulationData)
        assert "[CUSTOM_FDTD]" in result.log
        assert "v2.5" in result.log

    def test_webapi_submit_and_monitor(self, basic_simulation):
        """Test async workflow functions."""
        # Test submit
        task_id = webapi.submit(
            simulation=basic_simulation, task_name="async_test", solver_version="v1.5"
        )

        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # Test monitor
        status = webapi.monitor(task_id)
        assert status["task_id"] == task_id
        assert status["status"] == "completed"

    def test_webapi_error_handling(self, basic_simulation):
        """Test error handling in webapi."""
        with patch.object(CustomFDTDTask, "execute", side_effect=Exception("Mock API error")):
            with pytest.raises(Exception, match="Mock API error"):
                webapi.run(simulation=basic_simulation, task_name="error_test", verbose=False)


class TestFieldDataGeneration:
    """Test mock field data generation."""

    def test_field_data_structure(self, basic_simulation):
        """Test that generated field data has correct structure."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="field_test")

        result = task.execute()

        # Should have field monitor data
        assert "field_monitor" in result.monitor_data
        field_data = result["field_monitor"]

        # Check field data has required components
        assert hasattr(field_data, "Ex")
        assert hasattr(field_data, "Ey")
        assert hasattr(field_data, "Ez")
        assert hasattr(field_data, "Hx")
        assert hasattr(field_data, "Hy")
        assert hasattr(field_data, "Hz")

    def test_field_data_coordinates(self, basic_simulation):
        """Test field data has proper coordinate structure."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="coords_test")

        result = task.execute()
        field_data = result["field_monitor"]

        # Check coordinate structure
        Ex_data = field_data.Ex
        coords = Ex_data.coords

        assert "x" in coords
        assert "y" in coords
        assert "z" in coords
        assert "f" in coords

        # Check coordinate arrays are reasonable
        assert len(coords["x"]) > 0
        assert len(coords["y"]) > 0
        assert len(coords["f"]) > 0


class TestIntegrationWorkflow:
    """Test complete workflow integration."""

    def test_complete_workflow_native_simulation(self, basic_simulation):
        """Test complete workflow with native Tidy3D simulation."""
        # This should work without any validation errors
        result = webapi.run(
            simulation=basic_simulation,
            task_name="integration_test",
            solver_version="v2.0",
            max_iterations=1500,
            verbose=False,
        )

        # Verify results
        assert isinstance(result, SimulationData)
        assert result.simulation == basic_simulation

        # Check solver metadata in log
        assert "[CUSTOM_FDTD]" in result.log
        assert "v2.0" in result.log
        assert "Iterations:" in result.log
        assert "Convergence:" in result.log
        assert "Runtime:" in result.log

        # Verify field data exists and is accessible
        assert "field_monitor" in result.monitor_data
        field_data = result["field_monitor"]
        assert field_data.Ex.values.shape[3] == 1  # Single frequency

        # Test that we can use standard Tidy3D analysis
        # (This is the key benefit of using native formats)
        monitor_names = list(result.monitor_data.keys())
        assert "field_monitor" in monitor_names

    def test_multiple_monitors(self):
        """Test with multiple different monitor types."""
        sim = td.Simulation(
            size=(2.0, 2.0, 2.0),
            center=(0, 0, 0),
            run_time=1e-12,
            sources=[
                td.PlaneWave(
                    size=(td.inf, td.inf, 0),
                    center=(0, 0, -0.5),
                    source_time=td.GaussianPulse(freq0=2e14, fwidth=4e13),
                    direction="+",
                )
            ],
            monitors=[
                td.FieldMonitor(size=(1.0, 1.0, 0), center=(0, 0, 0), freqs=[2e14], name="field1"),
                td.FieldMonitor(
                    size=(0, 1.0, 1.0), center=(0.5, 0, 0), freqs=[2e14], name="field2"
                ),
            ],
            grid_spec=td.GridSpec.auto(wavelength=1.5e-6),
        )

        result = webapi.run(simulation=sim, task_name="multi_monitor_test", verbose=False)

        # Should have data for both monitors
        assert "field1" in result.monitor_data
        assert "field2" in result.monitor_data


class TestBackwardCompatibility:
    """Test backward compatibility and API consistency."""

    def test_api_similar_to_tidy3d_web(self, basic_simulation):
        """Test API is similar to tidy3d.web.run()."""
        # Should accept similar parameters to td.web.run()
        result = webapi.run(
            simulation=basic_simulation,
            task_name="compatibility_test",
            verbose=True,  # td.web.run() has verbose parameter
        )

        assert isinstance(result, SimulationData)

        # Should be able to access data like td.web.run() results
        field_data = result["field_monitor"]
        assert field_data is not None

    def test_result_compatible_with_tidy3d_analysis(self, basic_simulation):
        """Test results work with standard Tidy3D analysis tools."""
        result = webapi.run(simulation=basic_simulation, task_name="analysis_test", verbose=False)

        # Should work with standard data access patterns
        monitor_data = result["field_monitor"]
        assert monitor_data is not None

        # Should have standard field components
        Ex = monitor_data.Ex
        assert Ex is not None
        assert hasattr(Ex, "values")
        assert hasattr(Ex, "coords")
