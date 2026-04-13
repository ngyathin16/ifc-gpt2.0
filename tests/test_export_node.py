"""Tests for agent/nodes/export.py — summary stats and status."""
from __future__ import annotations

from agent.nodes.export import export


class TestExportStatus:
    def test_error_state_returns_error_status(self):
        state = {"error": "Something broke"}
        result = export(state)
        assert result["status"] == "error"

    def test_no_ifc_path_returns_error(self):
        state = {}
        result = export(state)
        assert result["status"] == "error"
        assert "No IFC file" in result["error"]

    def test_success_returns_complete(self):
        state = {"final_ifc_path": "/tmp/test.ifc"}
        result = export(state)
        assert result["status"] == "complete"


class TestExportSummary:
    def test_includes_summary_on_success(self):
        state = {
            "final_ifc_path": "/tmp/test.ifc",
            "ifc_entities": {"wall_1": "W1", "slab_1": "S1", "door_1": "D1"},
            "validation_result": {
                "all_errors": [],
                "schema": {"error_count": 0, "warning_count": 2},
                "semantic": {"error_count": 0, "warning_count": 1},
            },
            "repair_attempts": 1,
        }
        result = export(state)
        assert result["status"] == "complete"
        summary = result["summary"]
        assert summary["element_count"] == 3
        assert summary["repair_attempts"] == 1
        assert summary["validation_warnings"] >= 0

    def test_summary_absent_on_error(self):
        state = {"error": "fail"}
        result = export(state)
        assert "summary" not in result or result.get("summary") is None

    def test_summary_with_zero_entities(self):
        state = {"final_ifc_path": "/tmp/test.ifc"}
        result = export(state)
        assert result["status"] == "complete"
        summary = result["summary"]
        assert summary["element_count"] == 0
