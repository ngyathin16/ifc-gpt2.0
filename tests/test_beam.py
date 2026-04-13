"""Tests for building_blocks.primitives.beam."""
from __future__ import annotations

from building_blocks.primitives.beam import create_beam


def test_create_beam(ifc_setup):
    ifc, contexts, storey = ifc_setup
    beam = create_beam(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(6.0, 0.0),
        elevation=3.0,
        profile_type="RECTANGULAR",
        width=0.2, depth=0.4,
        name="Beam-A",
    )
    assert beam is not None
    assert beam.is_a("IfcBeam")
    assert beam.Name == "Beam-A"

    beams = ifc.by_type("IfcBeam")
    assert len(beams) == 1


def test_create_beam_i_section(ifc_setup):
    """Cover default I_SECTION profile path."""
    ifc, contexts, storey = ifc_setup
    beam = create_beam(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(6.0, 0.0),
        elevation=3.0,
        profile_type="I_SECTION",
        width=0.2, depth=0.4,
        name="Beam-I",
    )
    assert beam is not None
    assert beam.is_a("IfcBeam")


def test_create_beam_with_type(ifc_setup):
    """Cover the beam_type assignment branch (line 98)."""
    from building_blocks.types.beam_types import create_concrete_beam_type
    ifc, contexts, storey = ifc_setup
    bt = create_concrete_beam_type(ifc, name="BM-200x400")
    beam = create_beam(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(5.0, 0.0),
        beam_type=bt,
        name="Beam-Typed",
    )
    assert beam is not None
    assert beam.is_a("IfcBeam")


def test_create_beam_invalid_profile(ifc_setup):
    """Cover the ValueError branch for unknown profile_type (line 69)."""
    import pytest
    ifc, contexts, storey = ifc_setup
    with pytest.raises(ValueError, match="Unknown profile_type"):
        create_beam(
            ifc, contexts, storey,
            p1=(0.0, 0.0), p2=(5.0, 0.0),
            profile_type="HEXAGONAL",
        )
