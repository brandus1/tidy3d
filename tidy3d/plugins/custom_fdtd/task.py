"""Custom FDTD Task for production API communication."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

import numpy as np
import requests

from tidy3d.components.data.data_array import ScalarFieldDataArray
from tidy3d.components.data.monitor_data import FieldData
from tidy3d.components.data.sim_data import SimulationData
from tidy3d.components.simulation import Simulation
from tidy3d.log import log

from .config import get_config


class CustomFDTDTask:
    """Task for running simulations with custom FDTD backend.

    This class handles communication with the custom FDTD solver API,
    working directly with standard Tidy3D Simulation objects.
    """

    def __init__(
        self, simulation: Simulation, task_name: str, solver_params: Optional[dict[str, Any]] = None
    ):
        """Initialize custom FDTD task.

        Parameters
        ----------
        simulation : Simulation
            Standard Tidy3D simulation to run.
        task_name : str
            Name for this simulation task.
        solver_params : Dict[str, Any], optional
            Solver-specific parameters like:
            - solver_version: str = "v1.0"
            - max_iterations: int = 1000
            - convergence_threshold: float = 1e-8
            - timestep_factor: float = 0.5
            - numerical_precision: str = "double"
        """
        self.simulation = simulation
        self.task_name = task_name
        self.solver_params = solver_params or {}
        self.task_id = str(uuid.uuid4())

        # Set default solver parameters
        self.solver_params.setdefault("solver_version", "v1.0")
        self.solver_params.setdefault("max_iterations", 1000)
        self.solver_params.setdefault("convergence_threshold", 1e-8)
        self.solver_params.setdefault("timestep_factor", 0.5)
        self.solver_params.setdefault("numerical_precision", "double")

    def upload(self) -> str:
        """Upload simulation to custom FDTD backend.

        Returns
        -------
        str
            Task ID for the uploaded simulation.
        """
        log.info(f"Uploading simulation '{self.task_name}' to custom FDTD API...")
        log.info(f"Solver parameters: {self.solver_params}")

        # Prepare simulation data for API
        simulation_data = {
            "task_name": self.task_name,
            "simulation": self._serialize_simulation(),
            "solver_params": self.solver_params,
        }

        # Make API call
        response = self._api_call("POST", "/simulations", json=simulation_data)

        # Extract task ID from response
        if "task_id" in response:
            self.task_id = response["task_id"]
            log.info(f"Upload complete. Task ID: {self.task_id}")
            return self.task_id
        else:
            raise ValueError(f"Invalid API response: {response}")

    def _serialize_simulation(self) -> dict[str, Any]:
        """Serialize Tidy3D simulation for API transmission.

        In a real implementation, this would convert the simulation
        to your backend's expected format.
        """
        # For demo purposes, we'll extract key properties
        # In reality, you'd use simulation.json() or custom serialization
        return {
            "size": list(self.simulation.size),
            "center": list(self.simulation.center),
            "run_time": float(self.simulation.run_time),
            "boundary_spec": str(self.simulation.boundary_spec),
            "grid_spec": str(self.simulation.grid_spec),
            "num_sources": len(self.simulation.sources),
            "num_monitors": len(self.simulation.monitors),
            "num_structures": len(self.simulation.structures),
            # Add more fields as needed for your backend
        }

    def execute(self) -> SimulationData:
        """Execute simulation and return results.

        Returns
        -------
        SimulationData
            Standard Tidy3D simulation results.
        """
        log.info("Executing custom FDTD simulation via API...")
        log.info(f"Using solver version: {self.solver_params['solver_version']}")
        log.info(f"Max iterations: {self.solver_params['max_iterations']}")

        # Step 1: Upload simulation
        self.upload()

        # Step 2: Wait for completion
        self.wait_for_completion()

        # Step 3: Download results
        return self._download_results()

    def _download_results(self) -> SimulationData:
        """Download simulation results from API."""
        log.info("Downloading simulation results...")

        # Get download information
        response = self._api_call("GET", f"/simulations/{self.task_id}/results")

        # In a real implementation, this would:
        # 1. Download HDF5/binary data from the provided URL
        # 2. Parse the results into Tidy3D format
        # 3. Return SimulationData object

        download_url = response.get("download_url")
        if not download_url:
            raise ValueError("No download URL provided in API response")

        # Download the actual results file
        results_response = requests.get(download_url, timeout=get_config().timeout)
        results_response.raise_for_status()

        # Parse results (this would be custom to your backend format)
        # For now, this is a placeholder that would need implementation
        return self._parse_results(results_response.content)

    def _parse_results(self, results_data: bytes) -> SimulationData:
        """Parse downloaded results into SimulationData.

        This is where you'd implement the actual parsing logic
        for your backend's output format.
        """
        # This is a placeholder - implement based on your backend's format
        # For now, generate minimal valid data to show the structure
        monitor_data_list = []

        for monitor in self.simulation.monitors:
            if hasattr(monitor, "fields"):  # FieldMonitor
                field_data = self._create_field_data_from_backend(monitor, results_data)
                monitor_data_list.append(field_data)

        # Extract solver info from results (backend-specific)
        solver_info = self._extract_solver_info(results_data)

        # Create log content
        log_content = "[CUSTOM_FDTD] Simulation completed successfully.\n"
        log_content += f"Solver: {solver_info.get('solver_version', 'unknown')}\n"
        log_content += f"Iterations: {solver_info.get('iterations', 'unknown')}\n"
        log_content += f"Convergence: {solver_info.get('convergence', 'unknown')}\n"
        log_content += f"Runtime: {solver_info.get('runtime', 'unknown')}\n"
        log_content += f"Task ID: {self.task_id}"

        return SimulationData(
            simulation=self.simulation, data=tuple(monitor_data_list), log=log_content
        )

    def _create_field_data_from_backend(self, monitor, results_data: bytes) -> FieldData:
        """Create FieldData from backend results.

        This would parse your backend's actual field data format.
        """
        # Placeholder implementation - replace with actual parsing logic
        x_coords = np.linspace(-1, 1, 10)
        y_coords = np.linspace(-1, 1, 10)
        z_coords = np.array([0.0])
        f_coords = np.array([2e14])

        # In real implementation, extract this from results_data
        Ex_data = np.random.random(
            (len(x_coords), len(y_coords), len(z_coords), len(f_coords))
        ) + 1j * np.random.random((len(x_coords), len(y_coords), len(z_coords), len(f_coords)))

        Ex_array = ScalarFieldDataArray(
            Ex_data, coords={"x": x_coords, "y": y_coords, "z": z_coords, "f": f_coords}
        )

        return FieldData(
            monitor=monitor,
            Ex=Ex_array,
            Ey=Ex_array * 0.5,  # Placeholder
            Ez=Ex_array * 0.2,  # Placeholder
            Hx=Ex_array * 0.1,  # Placeholder
            Hy=Ex_array * 0.1,  # Placeholder
            Hz=Ex_array * 0.1,  # Placeholder
        )

    def _extract_solver_info(self, results_data: bytes) -> dict[str, Any]:
        """Extract solver metadata from results."""
        # Placeholder - extract from your backend's format
        return {
            "solver_version": self.solver_params["solver_version"],
            "iterations": 150,  # Extract from results_data
            "convergence": 1e-10,  # Extract from results_data
            "runtime": 45.2,  # Extract from results_data
        }

    @property
    def status(self) -> str:
        """Get current simulation status."""
        response = self._api_call("GET", f"/simulations/{self.task_id}/status")
        return response.get("status", "unknown")

    def get_status_details(self) -> dict[str, Any]:
        """Get detailed status information."""
        return self._api_call("GET", f"/simulations/{self.task_id}/status")

    def wait_for_completion(self, poll_interval: float = 10.0, max_wait: float = 3600.0) -> str:
        """Wait for simulation to complete.

        Parameters
        ----------
        poll_interval : float
            How often to check status (seconds).
        max_wait : float
            Maximum time to wait (seconds).

        Returns
        -------
        str
            Final status.
        """
        start_time = time.time()

        while True:
            status_info = self.get_status_details()
            status = status_info.get("status", "unknown")

            log.info(f"Status: {status}, Progress: {status_info.get('progress', 0)}%")

            if status in ["completed", "success"]:
                log.info("Simulation completed successfully!")
                return status
            elif status in ["failed", "error"]:
                error_msg = status_info.get("error", "Unknown error")
                raise RuntimeError(f"Simulation failed: {error_msg}")
            elif status == "cancelled":
                raise RuntimeError("Simulation was cancelled")

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Simulation did not complete within {max_wait} seconds")

            # Wait before next poll
            time.sleep(poll_interval)

    def _api_call(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP API call with retries and error handling."""
        config = get_config()
        url = f"{config.api_endpoint.rstrip('/')}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "tidy3d-custom-fdtd-plugin/1.0",
        }

        # Add authentication
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        # Add headers from kwargs
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        log.debug(f"[HTTP] {method} {url}")

        # Retry logic
        last_exception = None
        for attempt in range(config.retry_attempts + 1):
            try:
                response = requests.request(
                    method=method, url=url, headers=headers, timeout=config.timeout, **kwargs
                )

                # Log response status
                log.debug(f"[HTTP] Response: {response.status_code}")

                # Handle different response codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise ValueError(
                        "Authentication failed. Check your CUSTOM_FDTD_API_KEY environment variable."
                    )
                elif response.status_code == 404:
                    raise ValueError(f"API endpoint not found: {endpoint}")
                elif response.status_code >= 500:
                    raise requests.RequestException(f"Server error: {response.status_code}")
                else:
                    response.raise_for_status()

            except (requests.RequestException, ValueError) as e:
                last_exception = e
                if attempt < config.retry_attempts:
                    wait_time = config.retry_delay * (2**attempt)  # Exponential backoff
                    log.warning(
                        f"[HTTP] Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    log.error(f"[HTTP] All retry attempts failed: {e}")
                    raise

        # This shouldn't be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Unexpected error in API call")
