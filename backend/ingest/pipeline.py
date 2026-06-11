from __future__ import annotations

"""Compatibility imports for the manifest-driven ingestion pipeline."""

from backend.ingest.runner import (
    GuidelineRunResult,
    assert_clinically_approved,
    print_results,
    run_ingestion,
)

__all__ = [
    "GuidelineRunResult",
    "assert_clinically_approved",
    "print_results",
    "run_ingestion",
]
