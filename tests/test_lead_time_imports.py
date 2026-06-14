"""
Tests verifying that src.lead_time imports correctly and exposes all required symbols.

Covers:
1. import src.lead_time passes
2. path_enumerator module exists and is importable
3. path_ranker module exists and is importable
4. All __all__ exports are resolvable
5. No missing module errors
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLeadTimeImports:
    def test_import_src_lead_time(self):
        import src.lead_time  # noqa: F401

    def test_path_enumerator_importable(self):
        from src.lead_time.path_enumerator import enumerate_delivery_paths  # noqa: F401
        assert callable(enumerate_delivery_paths)

    def test_path_ranker_importable(self):
        from src.lead_time.path_ranker import rank_paths, assign_labels  # noqa: F401
        assert callable(rank_paths)
        assert callable(assign_labels)

    def test_models_importable(self):
        from src.lead_time.models import (  # noqa: F401
            LeadTimeComponent,
            LeadTimePath,
            LeadTimeScenario,
            ProductionCapacity,
        )

    def test_lead_time_calculator_importable(self):
        from src.lead_time.lead_time_calculator import calculate_lead_time_path  # noqa: F401
        assert callable(calculate_lead_time_path)

    def test_evidence_importable(self):
        from src.lead_time.evidence import (  # noqa: F401
            make_evidence_ref,
            validate_component_has_evidence,
            EVIDENCE_TYPE_SUPPLIER_STATED,
            EVIDENCE_TYPE_AI_CALCULATED,
            EVIDENCE_TYPE_HUMAN_CONFIRMED,
            EVIDENCE_TYPE_DEFAULT_ASSUMPTION,
        )

    def test_all_exports_from_init(self):
        import src.lead_time as lt
        required = [
            "LeadTimeComponent",
            "LeadTimePath",
            "LeadTimeScenario",
            "ProductionCapacity",
            "calculate_lead_time_path",
            "enumerate_delivery_paths",
            "rank_paths",
            "assign_labels",
            "make_evidence_ref",
            "validate_component_has_evidence",
            "EVIDENCE_TYPE_SUPPLIER_STATED",
            "EVIDENCE_TYPE_AI_CALCULATED",
            "EVIDENCE_TYPE_HUMAN_CONFIRMED",
            "EVIDENCE_TYPE_DEFAULT_ASSUMPTION",
        ]
        for name in required:
            assert hasattr(lt, name), f"src.lead_time missing export: {name}"

    def test_enumerate_delivery_paths_signature(self):
        from src.lead_time.path_enumerator import enumerate_delivery_paths
        import inspect
        sig = inspect.signature(enumerate_delivery_paths)
        params = list(sig.parameters.keys())
        assert "project_id" in params
        assert "supplier_responses" in params

    def test_rank_paths_signature(self):
        from src.lead_time.path_ranker import rank_paths
        import inspect
        sig = inspect.signature(rank_paths)
        params = list(sig.parameters.keys())
        assert "paths" in params

    def test_assign_labels_signature(self):
        from src.lead_time.path_ranker import assign_labels
        import inspect
        sig = inspect.signature(assign_labels)
        params = list(sig.parameters.keys())
        assert "paths" in params

    def test_no_import_errors_on_repeated_import(self):
        # Ensure no state corruption on repeated import
        if "src.lead_time" in sys.modules:
            del sys.modules["src.lead_time"]
        import src.lead_time  # noqa: F401
        import src.lead_time  # noqa: F401 (second import)

    def test_lead_time_path_enumerator_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "lead_time" / "path_enumerator.py").exists()

    def test_lead_time_path_ranker_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "lead_time" / "path_ranker.py").exists()

    def test_lead_time_models_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "lead_time" / "models.py").exists()

    def test_lead_time_calculator_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "lead_time" / "lead_time_calculator.py").exists()

    def test_lead_time_evidence_file_exists(self):
        repo_root = Path(__file__).parent.parent
        assert (repo_root / "src" / "lead_time" / "evidence.py").exists()
