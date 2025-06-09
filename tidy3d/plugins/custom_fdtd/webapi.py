"""Simplified Custom FDTD Web API using native Tidy3D formats."""

from __future__ import annotations

from typing import Any

from tidy3d.components.data.sim_data import SimulationData
from tidy3d.components.simulation import Simulation
from tidy3d.log import log

from .task import CustomFDTDTask


def run(
    simulation: Simulation, task_name: str, verbose: bool = True, **solver_params: Any
) -> SimulationData:
    """Run a Tidy3D simulation using custom FDTD solver backend.

    This function provides a familiar interface similar to tidy3d.web.run(),
    but routes the simulation to a custom FDTD solver via API.

    Parameters
    ----------
    simulation : Simulation
        Standard Tidy3D simulation to run with custom solver.
    task_name : str
        Name for the simulation task.
    verbose : bool = True
        Whether to print progress information.
    **solver_params : Any
        Additional solver-specific parameters such as:
        - solver_version: str = "v1.0"
        - max_iterations: int = 1000
        - convergence_threshold: float = 1e-8
        - timestep_factor: float = 0.5
        - numerical_precision: str = "double"

    Returns
    -------
    SimulationData
        Standard Tidy3D simulation results with additional solver metadata.

    Example
    -------
    >>> import tidy3d as td
    >>> from tidy3d.plugins import custom_fdtd
    >>>
    >>> # Create standard simulation
    >>> sim = td.Simulation(...)
    >>>
    >>> # Run with custom solver
    >>> data = custom_fdtd.run(
    ...     simulation=sim,
    ...     task_name="my_simulation",
    ...     solver_version="v2.0",
    ...     max_iterations=2000,
    ...     verbose=True
    ... )
    >>>
    >>> # Use results with standard Tidy3D tools
    >>> field_data = data["field_monitor"]
    """

    if verbose:
        log.info(f"Submitting simulation '{task_name}' to custom FDTD backend...")

    # Create task with solver parameters
    task = CustomFDTDTask(simulation=simulation, task_name=task_name, solver_params=solver_params)

    try:
        # Upload simulation to backend
        if verbose:
            log.info("Uploading simulation...")
        task.upload()

        if verbose:
            log.info(f"Simulation uploaded successfully. Task ID: {task.task_id}")

        # Execute simulation
        if verbose:
            log.info("Executing simulation...")
        result = task.execute()

        if verbose:
            log.info("Simulation completed successfully!")

        return result

    except Exception as e:
        log.error(f"Custom FDTD simulation failed: {e!s}")
        raise


# For backward compatibility
def submit(simulation: Simulation, task_name: str, **solver_params: Any) -> str:
    """Submit simulation and return task ID (for async workflows)."""
    task = CustomFDTDTask(simulation=simulation, task_name=task_name, solver_params=solver_params)
    task.upload()
    return task.task_id


def monitor(task_id: str) -> dict[str, Any]:
    """Monitor simulation status."""
    # This would connect to real API to check status
    # For now, return mock status
    return {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "message": "Simulation completed successfully",
    }


def download(task_id: str) -> SimulationData:
    """Download simulation results."""
    # This would connect to real API to download results
    # For now, return mock results
    raise NotImplementedError("Direct download not implemented - use run() instead")
