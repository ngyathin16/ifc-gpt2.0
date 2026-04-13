"""
Unified validation runner.

Combines three validation layers:
  1. Plan-level checks (pre-build) — catches geometry/logic errors in the BuildingPlan
  2. Schema validation — ifcopenshell.validate against IFC4 schema
  3. IDS checks — ifctester against IDS specification files
  4. Semantic checks — custom spatial/geometry rules on the generated IFC

Returns a single consolidated result dict used by the agent validate/repair nodes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_ids(ifc_path: str | Path, ids_paths: list[str | Path]) -> dict[str, Any]:
    """
    Validate the IFC file against each IDS specification.

    Returns:
        {
            "passed": bool,
            "total": int,
            "failed": int,
            "results": [{"ids_file": str, "specs": [...]}]
        }
    """
    import ifcopenshell
    import ifctester

    ifc_path = Path(ifc_path)
    ifc_file = ifcopenshell.open(str(ifc_path))
    results = []
    total = 0
    failed = 0

    for ids_path in ids_paths:
        ids_path = Path(ids_path)
        ids = ifctester.open(str(ids_path))
        ids.validate(ifc_file)
        spec_results = []
        for spec in ids.specifications:
            total += 1
            passed = bool(spec.status)
            if not passed:
                failed += 1
            spec_results.append({
                "name": getattr(spec, "name", "unnamed"),
                "passed": passed,
            })
        results.append({"ids_file": ids_path.name, "specs": spec_results})

    return {
        "passed": failed == 0,
        "total": total,
        "failed": failed,
        "results": results,
    }


def validate_all(
    ifc_path: str | Path,
    ids_paths: list[str | Path] | None = None,
    plan_dict: dict | None = None,
) -> dict[str, Any]:
    """Run all validation layers and return a consolidated result.

    Args:
        ifc_path: Path to the generated IFC file.
        ids_paths: Optional list of IDS specification files.
        plan_dict: Optional BuildingPlan dict for plan-level checks.

    Returns:
        {
            "passed": bool,
            "plan": {...} or None,
            "schema": {...},
            "ids": {...} or None,
            "semantic": {...},
            "all_errors": [str, ...],   # flat list of error messages for repair prompt
        }
    """
    import ifcopenshell

    all_errors: list[str] = []

    # Open IFC file ONCE and share across all validation layers
    ifc_file: ifcopenshell.file | None = None
    try:
        ifc_file = ifcopenshell.open(str(ifc_path))
    except Exception as e:
        logger.error(f"[validate_all] Could not open IFC file: {e}")
        return {
            "passed": False,
            "plan": None,
            "schema": {"valid": False, "error_count": 1, "error": str(e)},
            "ids": None,
            "semantic": {"valid": False, "error_count": 1, "error": str(e)},
            "all_errors": [f"[file] Could not open IFC: {e}"],
        }

    # 1. Plan-level validation (if plan_dict provided)
    plan_result: dict[str, Any] | None = None
    if plan_dict is not None:
        try:
            from validation.plan_checks import validate_plan
            plan_result = validate_plan(plan_dict)
            for issue in plan_result.get("issues", []):
                if issue["severity"] == "error":
                    all_errors.append(f"[plan] {issue['message']}")
            logger.info(
                f"[validate_all] Plan: valid={plan_result['valid']}, "
                f"errors={plan_result['error_count']}, warnings={plan_result['warning_count']}"
            )
        except Exception as e:
            logger.error(f"[validate_all] Plan validation error: {e}")
            plan_result = {"valid": False, "error_count": 1, "issues": [], "error": str(e)}
            all_errors.append(f"[plan] Validation crashed: {e}")

    # 2. Schema validation (reuse ifc_file)
    schema_result: dict[str, Any] = {"valid": True, "error_count": 0, "warning_count": 0}
    try:
        from validation.schema_check import validate_schema
        schema_result = validate_schema(str(ifc_path), ifc_file=ifc_file)
        for err in schema_result.get("errors", []):
            msg = err.get("message", str(err))
            all_errors.append(f"[schema] {msg}")
        logger.info(
            f"[validate_all] Schema: valid={schema_result['valid']}, "
            f"errors={schema_result['error_count']}, warnings={schema_result['warning_count']}"
        )
    except Exception as e:
        logger.error(f"[validate_all] Schema validation error: {e}")
        schema_result = {"valid": False, "error_count": 1, "error": str(e)}
        all_errors.append(f"[schema] Validation crashed: {e}")

    # 3. IDS validation (reuse ifc_file)
    ids_result: dict[str, Any] | None = None
    if ids_paths:
        try:
            ids_result = validate_ids(ifc_path, ids_paths)
            for r in ids_result.get("results", []):
                for spec in r.get("specs", []):
                    if not spec["passed"]:
                        all_errors.append(f"[ids] {r['ids_file']}: {spec['name']} FAILED")
            logger.info(
                f"[validate_all] IDS: passed={ids_result['passed']}, "
                f"total={ids_result['total']}, failed={ids_result['failed']}"
            )
        except Exception as e:
            logger.error(f"[validate_all] IDS validation error: {e}")
            ids_result = {"passed": False, "total": 0, "failed": 0, "error": str(e)}
            all_errors.append(f"[ids] Validation crashed: {e}")

    # 4. Semantic checks (reuse ifc_file)
    semantic_result: dict[str, Any] = {"valid": True, "error_count": 0, "warning_count": 0}
    try:
        from validation.semantic_checks import run_all_checks
        semantic_result = run_all_checks(str(ifc_path), ifc_file=ifc_file)
        for issue in semantic_result.get("issues", []):
            if issue["severity"] == "error":
                all_errors.append(f"[semantic] {issue['message']}")
        logger.info(
            f"[validate_all] Semantic: valid={semantic_result['valid']}, "
            f"errors={semantic_result['error_count']}, warnings={semantic_result['warning_count']}"
        )
    except Exception as e:
        logger.error(f"[validate_all] Semantic validation error: {e}")
        semantic_result = {"valid": False, "error_count": 1, "error": str(e)}
        all_errors.append(f"[semantic] Validation crashed: {e}")

    # Combine
    passed = (
        (plan_result is None or plan_result.get("valid", True))
        and schema_result.get("valid", True)
        and (ids_result is None or ids_result.get("passed", True))
        and semantic_result.get("valid", True)
    )

    return {
        "passed": passed,
        "plan": plan_result,
        "schema": schema_result,
        "ids": ids_result,
        "semantic": semantic_result,
        "all_errors": all_errors,
    }
