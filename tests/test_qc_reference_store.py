"""Tests for QC reference image store."""
import pytest
from src.merchandiser.qc.qc_reference_store import (
    add_reference_image, get_reference_images, deactivate_reference_image, QCReferenceImage
)

_PROJECT = "PROJ-REF-STORE-01"

def test_add_reference_image_returns_ref_image():
    ref = add_reference_image(
        project_id=_PROJECT,
        image_path="tests/fixtures/multimodal/red_square.png",
        uploaded_by_actor_id="ACT-BUYER-001",
        milestone_type="final_qc",
        description="Golden sample",
    )
    assert isinstance(ref, QCReferenceImage)
    assert ref.ref_image_id.startswith("REF-")
    assert ref.project_id == _PROJECT
    assert ref.milestone_type == "final_qc"
    assert ref.is_active is True

def test_get_reference_images_returns_added():
    project = "PROJ-REF-GET-01"
    add_reference_image(project, "tests/fixtures/multimodal/red_square.png", "ACT-001", "final_qc")
    refs = get_reference_images(project)
    assert len(refs) >= 1
    assert all(r.project_id == project for r in refs)

def test_get_reference_images_filters_by_milestone_type():
    project = "PROJ-REF-FILTER-01"
    add_reference_image(project, "tests/fixtures/multimodal/red_square.png", "ACT-001", "final_qc")
    add_reference_image(project, "tests/fixtures/multimodal/red_square.png", "ACT-001", "in_process_qc")
    final_refs = get_reference_images(project, milestone_type="final_qc")
    assert all(r.milestone_type == "final_qc" for r in final_refs)

def test_deactivate_reference_image():
    project = "PROJ-REF-DEACT-01"
    ref = add_reference_image(project, "tests/fixtures/multimodal/red_square.png", "ACT-001")
    result = deactivate_reference_image(ref.ref_image_id)
    assert result is True
    refs = get_reference_images(project)
    assert all(r.ref_image_id != ref.ref_image_id for r in refs)

def test_deactivate_nonexistent_returns_false():
    result = deactivate_reference_image("REF-NONEXISTENT")
    assert result is False

def test_reference_image_has_created_at():
    ref = add_reference_image("PROJ-REF-TS-01", "path.png", "ACT-001")
    assert ref.created_at != ""
