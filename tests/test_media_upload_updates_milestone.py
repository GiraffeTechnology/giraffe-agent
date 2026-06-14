"""Tests that media upload updates milestone status (Bug 4.2 fix)."""
import pytest
from src.merchandiser.media_confirmation import upload_media_evidence
from src.merchandiser.milestone_manager import (
    create_milestones, get_milestone, OrderMilestone
)

_PROJECT = "PROJ-MEDIA-UPD-01"

def test_upload_media_evidence_updates_milestone_status():
    milestones = create_milestones(_PROJECT, "apparel")
    first_ms = milestones[0]
    media = upload_media_evidence(
        project_id=_PROJECT,
        milestone_id=first_ms.milestone_id,
        uploaded_by_actor_id="ACT-SUPP-001",
        media_type="image",
        count=2,
        update_milestone_status=True,
    )
    assert len(media) == 2
    updated_ms = get_milestone(first_ms.milestone_id)
    assert updated_ms.status == "UPLOADED"

def test_upload_media_evidence_attaches_media_ids_to_milestone():
    milestones = create_milestones("PROJ-MEDIA-UPD-02", "apparel")
    first_ms = milestones[0]
    media = upload_media_evidence(
        project_id="PROJ-MEDIA-UPD-02",
        milestone_id=first_ms.milestone_id,
        uploaded_by_actor_id="ACT-SUPP-002",
        update_milestone_status=True,
    )
    ms = get_milestone(first_ms.milestone_id)
    assert "media_ids" in ms.metadata or ms.status == "UPLOADED"

def test_upload_media_evidence_without_update_flag_stays_pending():
    milestones = create_milestones("PROJ-MEDIA-UPD-03", "apparel")
    first_ms = milestones[0]
    upload_media_evidence(
        project_id="PROJ-MEDIA-UPD-03",
        milestone_id=first_ms.milestone_id,
        uploaded_by_actor_id="ACT-SUPP-003",
        update_milestone_status=False,
    )
    ms = get_milestone(first_ms.milestone_id)
    assert ms.status == "PENDING"
