"""Shared fixtures for building_blocks tests."""
from __future__ import annotations

import pytest

from building_blocks.context import add_storey, create_ifc_project


@pytest.fixture
def ifc_setup():
    """Create a fresh IFC file with project/site/building/storey for testing."""
    ifc, contexts = create_ifc_project(
        project_name="Test Project",
        site_name="Test Site",
        building_name="Test Building",
    )
    storey = add_storey(ifc, contexts["building"], name="Ground Floor", elevation=0.0)
    return ifc, contexts, storey
