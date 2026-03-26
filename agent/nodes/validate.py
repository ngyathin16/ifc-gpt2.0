"""
Validate node: runs all validation layers against the generated IFC file.

Layers:
  1. Plan-level checks (geometry/logic on the BuildingPlan dict)
  2. Schema validation (ifcopenshell.validate)
  3. IDS checks (ifctester)
  4. Semantic checks (spatial containment, floating openings, etc.)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _collect_valid_ids_files() -> list[Path]:
    """Find IDS files that contain at least one specification."""
    ids_dir = Path(os.getenv("IDS_DIR", "./validation/ids"))
    if not ids_dir.exists():
        return []

    valid: list[Path] = []
    for ids_path in ids_dir.glob("*.ids"):
        try:
            import ifctester
            ids_obj = ifctester.open(str(ids_path))
            if ids_obj.specifications:
                valid.append(ids_path)
            else:
                logger.info(f"[validate] Skipping empty IDS file: {ids_path.name}")
        except Exception as e:
            logger.warning(f"[validate] Skipping invalid IDS file {ids_path.name}: {e}")
    return valid


def validate(state: dict[str, Any]) -> dict[str, Any]:
    """
    Run all validation layers on the generated IFC file (and optionally the plan).

    Expected state keys:
        - final_ifc_path: str
        - building_plan_json: dict (optional, for plan-level checks)

    Produces:
        - validation_result: dict — consolidated results from all layers
        - validation_passed: bool
    """
    ifc_path = state.get("final_ifc_path")
    if not ifc_path or not Path(ifc_path).exists():
        return {
            **state,
            "validation_result": {"passed": False, "all_errors": ["IFC file not found"]},
            "validation_passed": False,
        }

    plan_dict = state.get("building_plan_json")
    ids_files = _collect_valid_ids_files()

    try:
        from validation.runner import validate_all

        result = validate_all(
            ifc_path=ifc_path,
            ids_paths=ids_files or None,
            plan_dict=plan_dict,
        )

        error_count = len(result.get("all_errors", []))
        logger.info(
            f"[validate] Overall: passed={result['passed']}, "
            f"total_errors={error_count}"
        )
        if result.get("all_errors"):
            for err in result["all_errors"][:10]:
                logger.info(f"[validate]   {err}")

    except Exception as e:
        logger.error(f"[validate] Validation error: {e}")
        result = {"passed": False, "all_errors": [str(e)]}

    return {
        **state,
        "validation_result": result,
        "validation_passed": result.get("passed", False),
    }
