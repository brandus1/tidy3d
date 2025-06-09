"""Comprehensive tests for Custom FDTD plugin."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest

import tidy3d as td
from tidy3d.components.data.sim_data import SimulationData
from tidy3d.plugins.custom_fdtd import (
    CustomFDTDConfig,
    CustomFDTDTask,
    reset_config,
    set_config,
    webapi,
)


# Set up mock environment for all tests
@pytest.fixture(autouse=True)
def mock_environment():
    """Set up mock environment variables for all tests."""
    with patch.dict(
        os.environ,
        {
            "CUSTOM_FDTD_API_KEY": "test_api_key_123",
            "CUSTOM_FDTD_API_ENDPOINT": "https://api.test.example.com",
            "CUSTOM_FDTD_TIMEOUT": "30",
            "CUSTOM_FDTD_RETRY_ATTEMPTS": "2",
            "CUSTOM_FDTD_RETRY_DELAY": "0.1",
        },
    ):
        # Reset config before each test to ensure clean state
        reset_config()
        yield
        # Reset config after each test
        reset_config()


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
            )
        ],
        monitors=[
            td.FieldMonitor(
                size=(2.0, 2.0, 0),
                center=(0, 0, 0),
                freqs=[2e14],
                name="field_monitor",
            )
        ],
    )


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return CustomFDTDConfig(
        api_endpoint="https://api.test.example.com",
        api_key="test_api_key_123",
        timeout=30,
        retry_attempts=2,
        retry_delay=0.1,
    )


class TestCustomFDTDConfig:
    """Test configuration management."""

    def test_config_from_environment(self):
        """Test configuration loading from environment variables."""
        with patch.dict(
            os.environ,
            {
                "CUSTOM_FDTD_API_ENDPOINT": "https://test-api.example.com",
                "CUSTOM_FDTD_API_KEY": "test_key_123",
                "CUSTOM_FDTD_TIMEOUT": "600",
            },
        ):
            reset_config()  # Force reload from environment
            config = CustomFDTDConfig.from_environment()

            assert config.api_endpoint == "https://test-api.example.com"
            assert config.api_key == "test_key_123"
            assert config.timeout == 600

    def test_config_validation_success(self):
        """Test that valid configuration passes validation."""
        config = CustomFDTDConfig(api_endpoint="https://api.example.com", api_key="valid_key")
        # Should not raise
        config.validate()

    def test_config_validation_missing_api_key(self):
        """Test that missing API key fails validation."""
        config = CustomFDTDConfig(api_endpoint="https://api.example.com", api_key=None)

        with pytest.raises(ValueError, match="API key is required"):
            config.validate()

    def test_config_validation_empty_endpoint(self):
        """Test that empty endpoint fails validation."""
        config = CustomFDTDConfig(api_endpoint="", api_key="valid_key")

        with pytest.raises(ValueError, match="API endpoint cannot be empty"):
            config.validate()

    def test_set_custom_config(self):
        """Test setting a custom configuration."""
        custom_config = CustomFDTDConfig(
            api_endpoint="https://custom.example.com", api_key="custom_key", timeout=120
        )

        set_config(custom_config)

        # Verify config was set
        assert custom_config.api_endpoint == "https://custom.example.com"


class TestCustomFDTDTask:
    """Test the CustomFDTDTask class with proper mocking."""

    def test_task_initialization(self, basic_simulation):
        """Test basic task initialization."""
        task = CustomFDTDTask(
            simulation=basic_simulation,
            task_name="test_task",
            solver_params={"solver_version": "v2.0", "max_iterations": 500},
        )

        assert task.simulation == basic_simulation
        assert task.task_name == "test_task"
        assert task.solver_params["solver_version"] == "v2.0"
        assert task.solver_params["max_iterations"] == 500
        assert task.solver_params["convergence_threshold"] == 1e-8  # default
        assert isinstance(task.task_id, str)

    def test_task_default_parameters(self, basic_simulation):
        """Test that default solver parameters are set correctly."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")

        expected_defaults = {
            "solver_version": "v1.0",
            "max_iterations": 1000,
            "convergence_threshold": 1e-8,
            "timestep_factor": 0.5,
            "numerical_precision": "double",
        }

        for key, value in expected_defaults.items():
            assert task.solver_params[key] == value

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_upload_success(self, mock_request, basic_simulation):
        """Test successful simulation upload."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "test_task_id_123", "status": "uploaded"}
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task_id = task.upload()

        assert task_id == "test_task_id_123"
        assert task.task_id == "test_task_id_123"

        # Verify API call was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert "simulations" in call_args[1]["url"]
        assert "Authorization" in call_args[1]["headers"]

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_upload_failure(self, mock_request, basic_simulation):
        """Test upload failure handling."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")

        with pytest.raises(ValueError):
            task.upload()

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_get_status(self, mock_request, basic_simulation):
        """Test status checking."""
        # Mock status response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "task_id": "test_task_id",
            "status": "running",
            "progress": 75,
        }
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task.task_id = "test_task_id"

        status = task.status
        assert status == "running"

        details = task.get_status_details()
        assert details["progress"] == 75

    @patch("tidy3d.plugins.custom_fdtd.task.requests.get")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_download_results(self, mock_request, mock_get, basic_simulation):
        """Test results download."""
        # Mock API response for getting download URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "download_url": "https://example.com/results/test_task_id"
        }
        mock_request.return_value = mock_response

        # Mock actual file download
        mock_file_response = Mock()
        mock_file_response.content = b"fake_results_data"
        mock_file_response.raise_for_status.return_value = None
        mock_get.return_value = mock_file_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task.task_id = "test_task_id"

        # Mock the parse_results method since we're not testing the parsing logic
        with patch.object(task, "_parse_results") as mock_parse:
            mock_parse.return_value = Mock(spec=SimulationData)
            result = task._download_results()

            mock_parse.assert_called_once_with(b"fake_results_data")

    @patch("tidy3d.plugins.custom_fdtd.task.CustomFDTDTask.wait_for_completion")
    @patch("tidy3d.plugins.custom_fdtd.task.CustomFDTDTask._download_results")
    @patch("tidy3d.plugins.custom_fdtd.task.CustomFDTDTask.upload")
    def test_execute_workflow(self, mock_upload, mock_download, mock_wait, basic_simulation):
        """Test complete execution workflow."""
        # Setup mocks
        mock_upload.return_value = "test_task_id"
        mock_wait.return_value = "completed"
        mock_result = Mock(spec=SimulationData)
        mock_download.return_value = mock_result

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        result = task.execute()

        # Verify workflow
        mock_upload.assert_called_once()
        mock_wait.assert_called_once()
        mock_download.assert_called_once()
        assert result == mock_result

    @patch("tidy3d.plugins.custom_fdtd.task.time.sleep")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_wait_for_completion_success(self, mock_request, mock_sleep, basic_simulation):
        """Test waiting for completion - success case."""
        # Mock status progression: running -> completed
        status_responses = [
            {"status": "running", "progress": 50},
            {"status": "running", "progress": 90},
            {"status": "completed", "progress": 100},
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = status_responses
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task.task_id = "test_task_id"

        final_status = task.wait_for_completion(poll_interval=0.1, max_wait=1.0)
        assert final_status == "completed"

    def test_simulation_serialization(self, basic_simulation):
        """Test simulation serialization for API transmission."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        serialized = task._serialize_simulation()

        # Check required fields
        assert "size" in serialized
        assert "center" in serialized
        assert "run_time" in serialized
        assert "num_sources" in serialized
        assert "num_monitors" in serialized
        assert "num_structures" in serialized

        # Check values
        assert serialized["size"] == list(basic_simulation.size)
        assert serialized["num_sources"] == len(basic_simulation.sources)
        assert serialized["num_monitors"] == len(basic_simulation.monitors)


class TestHTTPClientIntegration:
    """Test HTTP client functionality with different scenarios."""

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_real_api_mode_success(self, mock_request, basic_simulation):
        """Test real API calls with successful response."""
        # Mock successful HTTP responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"task_id": "test-task-123", "status": "uploaded"}
        mock_request.return_value = mock_response

        task = CustomFDTDTask(
            simulation=basic_simulation,
            task_name="test_real_api",
            solver_params={"solver_version": "v1.5"},
        )

        # Test upload
        task_id = task.upload()
        assert task_id == "test-task-123"

        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "simulations" in call_args[1]["url"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_api_key_123"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_real_api_authentication_error(self, mock_request, basic_simulation):
        """Test handling of authentication errors."""
        # Mock 401 authentication error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test_auth_error")

        with pytest.raises(ValueError, match="Authentication failed"):
            task.upload()

    @patch("tidy3d.plugins.custom_fdtd.task.time.sleep")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_real_api_retry_logic(self, mock_request, mock_sleep, basic_simulation):
        """Test retry logic on server errors."""
        # Mock server error then success
        error_response = Mock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = Exception("Server error")

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"task_id": "retry-success", "status": "uploaded"}

        mock_request.side_effect = [error_response, success_response]

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test_retry")

        # Should succeed after retry
        task_id = task.upload()
        assert task_id == "retry-success"

        # Verify retry happened
        assert mock_request.call_count == 2


class TestWebAPI:
    """Test the web API functions with proper mocking."""

    @patch("tidy3d.plugins.custom_fdtd.webapi.CustomFDTDTask")
    def test_run_function(self, mock_task_class, basic_simulation):
        """Test the run function."""
        # Mock task instance
        mock_task = Mock()
        mock_task.task_id = "test_task_id"
        mock_task.execute.return_value = Mock(spec=SimulationData)
        mock_task.upload.return_value = "test_task_id"
        mock_task_class.return_value = mock_task

        result = webapi.run(
            simulation=basic_simulation,
            task_name="test_simulation",
            solver_version="v2.0",
            max_iterations=500,
        )

        # Verify task was created correctly
        mock_task_class.assert_called_once_with(
            simulation=basic_simulation,
            task_name="test_simulation",
            solver_params={"solver_version": "v2.0", "max_iterations": 500},
        )

        # Verify workflow
        mock_task.upload.assert_called_once()
        mock_task.execute.assert_called_once()

    @patch("tidy3d.plugins.custom_fdtd.webapi.CustomFDTDTask")
    def test_submit_function(self, mock_task_class, basic_simulation):
        """Test the submit function."""
        # Mock task instance
        mock_task = Mock()
        mock_task.upload.return_value = "test_task_id_123"
        mock_task.task_id = "test_task_id_123"  # Set the task_id property
        mock_task_class.return_value = mock_task

        task_id = webapi.submit(
            simulation=basic_simulation, task_name="test_simulation", solver_version="v1.5"
        )

        assert task_id == "test_task_id_123"
        mock_task.upload.assert_called_once()

    def test_monitor_function(self, basic_simulation):
        """Test the monitor function."""
        # This function returns mock data for now
        result = webapi.monitor("test_task_id")

        assert result["task_id"] == "test_task_id"
        assert "status" in result
        assert "progress" in result

    def test_download_function(self, basic_simulation):
        """Test the download function."""
        # This should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            webapi.download("test_task_id")


class TestFieldDataGeneration:
    """Test field data generation and parsing."""

    def test_field_data_structure(self, basic_simulation):
        """Test that generated field data has correct structure."""
        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        monitor = basic_simulation.monitors[0]

        # Test the field data creation method
        field_data = task._create_field_data_from_backend(monitor, b"fake_data")

        # Verify structure
        assert hasattr(field_data, "Ex")
        assert hasattr(field_data, "Ey")
        assert hasattr(field_data, "Ez")
        assert hasattr(field_data, "Hx")
        assert hasattr(field_data, "Hy")
        assert hasattr(field_data, "Hz")
        assert field_data.monitor == monitor

        # Verify data array properties
        assert field_data.Ex.shape == (10, 10, 1, 1)  # Based on mock coordinates
        assert "x" in field_data.Ex.coords
        assert "y" in field_data.Ex.coords
        assert "z" in field_data.Ex.coords
        assert "f" in field_data.Ex.coords


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_config_validation_missing_api_key(self):
        """Test configuration validation with missing API key."""
        with pytest.raises(ValueError, match="API key is required"):
            config = CustomFDTDConfig(api_endpoint="https://example.com", api_key=None)
            config.validate()

    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_api_authentication_error(self, mock_request, basic_simulation):
        """Test API authentication error handling."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")

        with pytest.raises(ValueError, match="Authentication failed"):
            task._api_call("GET", "/test")

    @patch("tidy3d.plugins.custom_fdtd.task.time.sleep")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_api_retry_logic(self, mock_request, mock_sleep, basic_simulation):
        """Test API retry logic."""
        # Mock failed requests followed by success
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = Exception("Server error")

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"status": "ok"}

        mock_request.side_effect = [mock_response_fail, mock_response_success]

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")

        with patch("tidy3d.plugins.custom_fdtd.task.time.sleep"):  # Speed up test
            result = task._api_call("GET", "/test")
            assert result["status"] == "ok"

        # Should have made 2 calls (1 failure + 1 success)
        assert mock_request.call_count == 2

    @patch("tidy3d.plugins.custom_fdtd.task.time.sleep")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_wait_for_completion_timeout(self, mock_request, mock_sleep, basic_simulation):
        """Test waiting for completion - timeout case."""
        # Mock status that never completes
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "running", "progress": 50}
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task.task_id = "test_task_id"

        with pytest.raises(TimeoutError, match="did not complete within"):
            task.wait_for_completion(poll_interval=0.1, max_wait=0.2)

    @patch("tidy3d.plugins.custom_fdtd.task.time.sleep")
    @patch("tidy3d.plugins.custom_fdtd.task.requests.request")
    def test_wait_for_completion_failure(self, mock_request, mock_sleep, basic_simulation):
        """Test waiting for completion - failure case."""
        # Mock status that indicates failure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "failed",
            "progress": 75,
            "error": "Simulation diverged",
        }
        mock_request.return_value = mock_response

        task = CustomFDTDTask(simulation=basic_simulation, task_name="test")
        task.task_id = "test_task_id"

        with pytest.raises(RuntimeError, match="Simulation failed: Simulation diverged"):
            task.wait_for_completion(poll_interval=0.1, max_wait=1.0)


class TestProductionWorkflow:
    """Test complete production workflow scenarios."""

    def setup_method(self):
        """Set up for production-like testing."""
        reset_config()

    def test_environment_based_configuration(self):
        """Test that configuration works via environment variables."""
        with patch.dict(
            os.environ,
            {
                "CUSTOM_FDTD_API_ENDPOINT": "https://prod-api.fdtd.com",
                "CUSTOM_FDTD_API_KEY": "prod_key_123",
                "CUSTOM_FDTD_TIMEOUT": "1800",
                "CUSTOM_FDTD_RETRY_ATTEMPTS": "5",
            },
        ):
            reset_config()
            config = CustomFDTDConfig.from_environment()

            assert config.api_endpoint == "https://prod-api.fdtd.com"
            assert config.api_key == "prod_key_123"
            assert config.timeout == 1800
            assert config.retry_attempts == 5

    def test_development_vs_production_mode_config(self, basic_simulation):
        """Test switching between development and production configurations."""
        # Development mode config
        dev_config = CustomFDTDConfig(api_endpoint="https://dev-api.example.com", api_key="dev_key")
        set_config(dev_config)

        from tidy3d.plugins.custom_fdtd import get_config

        current_config = get_config()
        assert current_config.api_endpoint == "https://dev-api.example.com"

        # Production mode config
        prod_config = CustomFDTDConfig(
            api_endpoint="https://prod-api.example.com", api_key="prod_key"
        )
        set_config(prod_config)

        # Verify config is set correctly
        current_config = get_config()
        assert current_config.api_endpoint == "https://prod-api.example.com"
