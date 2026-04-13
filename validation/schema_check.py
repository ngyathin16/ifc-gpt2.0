"""
IFC schema validation wrapper.

Runs ifcopenshell.validate against a generated IFC file and returns
structured error/warning results suitable for the agent repair loop.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.validate


def validate_schema(
    ifc_path: str | Path,
    ifc_file: ifcopenshell.file | None = None,
) -> dict[str, Any]:
    """Validate IFC file against its declared schema.

    Args:
        ifc_path: Path to IFC file (used only if ifc_file is None).
        ifc_file: Pre-opened IFC file object to avoid redundant I/O.

    Returns:
        {
            "valid": bool,
            "schema": str,          # e.g. "IFC4"
            "errors": [...],        # List of error dicts
            "warnings": [...],      # List of warning dicts
            "error_count": int,
            "warning_count": int,
        }
    """
    if ifc_file is None:
        ifc_file = ifcopenshell.open(str(ifc_path))
    schema = ifc_file.schema

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc_file, logger)

    errors: list[dict[str, Any]] = [
        e for e in logger.statements if e.get("severity") == "Error"
    ]
    warnings: list[dict[str, Any]] = [
        w for w in logger.statements if w.get("severity") == "Warning"
    ]

    return {
        "valid": len(errors) == 0,
        "schema": schema,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
