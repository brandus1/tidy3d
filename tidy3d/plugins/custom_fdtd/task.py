"""Simplified Custom FDTD Task using native Tidy3D formats."""

from __future__ import annotations

import uuid
from typing import Any, Optional

import numpy as np

from tidy3d.components.data.data_array import ScalarFieldDataArray
from tidy3d.components.data.monitor_data import FieldData
from tidy3d.components.data.sim_data import SimulationData
from tidy3d.components.simulation import Simulation
from tidy3d.log import log


class CustomFDTDTask:
    """Task for running simulations with custom FDTD backend using native Tidy3D formats.

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
        # In real implementation, this would:
        # 1. Serialize simulation to JSON/HDF5
        # 2. POST to /simulations endpoint
        # 3. Return task ID from response

        log.info(f"[MOCK] Uploading simulation '{self.task_name}' to custom FDTD API...")
        log.info(f"[MOCK] Solver parameters: {self.solver_params}")
        log.info(f"[MOCK] Upload complete. Task ID: {self.task_id}")

        return self.task_id

    def execute(self) -> SimulationData:
        """Execute simulation and return results.

        Returns
        -------
        SimulationData
            Standard Tidy3D simulation results.
        """
        log.info("[MOCK] Executing custom FDTD simulation...")
        log.info(f"[MOCK] Using solver version: {self.solver_params['solver_version']}")
        log.info(f"[MOCK] Max iterations: {self.solver_params['max_iterations']}")

        # Generate mock field data for monitors
        monitor_data_list = []

        for monitor in self.simulation.monitors:
            if hasattr(monitor, "fields"):  # FieldMonitor
                # Create mock field data
                field_data = self._generate_mock_field_data(monitor)
                monitor_data_list.append(field_data)

        # Generate solver metadata for logging
        solver_info = {
            "solver_version": self.solver_params["solver_version"],
            "iterations": np.random.randint(50, self.solver_params["max_iterations"]),
            "convergence": np.random.random() * self.solver_params["convergence_threshold"],
            "runtime": np.random.uniform(10.0, 300.0),
            "backend": "custom_fdtd",
            "task_id": self.task_id,
        }

        # Create standard SimulationData with solver info in log
        log_content = "[CUSTOM_FDTD] Simulation completed successfully.\n"
        log_content += f"Solver: {solver_info['solver_version']}\n"
        log_content += f"Iterations: {solver_info['iterations']}\n"
        log_content += f"Convergence: {solver_info['convergence']:.2e}\n"
        log_content += f"Runtime: {solver_info['runtime']:.1f}s\n"
        log_content += f"Task ID: {solver_info['task_id']}"

        result = SimulationData(
            simulation=self.simulation, data=tuple(monitor_data_list), log=log_content
        )

        log.info(f"[MOCK] Simulation completed in {solver_info['iterations']} iterations")
        log.info(f"[MOCK] Final convergence: {solver_info['convergence']:.2e}")

        return result

    def _generate_mock_field_data(self, monitor) -> FieldData:
        """Generate mock field data for a monitor."""
        # Create minimal mock field data
        # In real implementation, this would be the actual field data from solver

        # Get monitor geometry for data shape
        x_coords = np.linspace(-1, 1, 10)
        y_coords = np.linspace(-1, 1, 10)
        z_coords = np.array([0.0])  # Single plane for simplicity
        f_coords = np.array([2e14])  # Single frequency

        # Create mock field arrays
        Ex_data = np.random.random(
            (len(x_coords), len(y_coords), len(z_coords), len(f_coords))
        ) + 1j * np.random.random((len(x_coords), len(y_coords), len(z_coords), len(f_coords)))

        # Create ScalarFieldDataArray for Ex component
        Ex_array = ScalarFieldDataArray(
            Ex_data, coords={"x": x_coords, "y": y_coords, "z": z_coords, "f": f_coords}
        )

        # Create similar arrays for other components (simplified)
        Ey_array = ScalarFieldDataArray(
            Ex_data * 0.5,  # Different mock data
            coords={"x": x_coords, "y": y_coords, "z": z_coords, "f": f_coords},
        )

        Ez_array = ScalarFieldDataArray(
            Ex_data * 0.2,  # Different mock data
            coords={"x": x_coords, "y": y_coords, "z": z_coords, "f": f_coords},
        )

        # Create FieldData with all components
        field_data = FieldData(
            monitor=monitor,
            Ex=Ex_array,
            Ey=Ey_array,
            Ez=Ez_array,
            Hx=Ex_array * 0.1,  # Mock H-field data
            Hy=Ey_array * 0.1,
            Hz=Ez_array * 0.1,
        )

        return field_data

    @property
    def status(self) -> str:
        """Get current simulation status."""
        # In real implementation, this would query the API
        return "completed"

    def _mock_api_call(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Mock API call for testing."""
        if method == "POST" and "simulations" in endpoint:
            return {
                "task_id": self.task_id,
                "status": "uploaded",
                "message": "Simulation uploaded successfully",
            }
        elif method == "GET" and "status" in endpoint:
            return {
                "task_id": self.task_id,
                "status": "completed",
                "progress": 100,
                "iterations": 150,
                "convergence": 1e-10,
            }
        elif method == "GET" and "results" in endpoint:
            return {
                "task_id": self.task_id,
                "download_url": f"https://api.example.com/results/{self.task_id}",
            }
        else:
            return {"error": f"Unknown endpoint: {endpoint}"}
