"""Simplified Custom FDTD Plugin using native Tidy3D formats.

This plugin provides a simple interface to run Tidy3D simulations using a custom FDTD solver backend.
All operations use native Tidy3D formats for maximum compatibility.

Key Features:
- Works with standard td.Simulation objects
- Returns standard td.SimulationData
- Simple parameter passing via dictionaries
- Compatible with all Tidy3D analysis tools
- No custom pydantic validation issues

Example usage:
    >>> import tidy3d as td
    >>> from tidy3d.plugins import custom_fdtd
    >>>
    >>> # Create standard simulation
    >>> sim = td.Simulation(...)
    >>>
    >>> # Run with custom solver
    >>> result = custom_fdtd.run(
    ...     simulation=sim,
    ...     task_name="my_simulation",
    ...     solver_version="v2.0",
    ...     max_iterations=2000
    ... )
    >>>
    >>> # Use with standard Tidy3D analysis
    >>> field_data = result["field_monitor"]
"""

from __future__ import annotations

from .task import CustomFDTDTask
from .webapi import download, monitor, run, submit

__all__ = ["CustomFDTDTask", "download", "monitor", "run", "submit"]
