from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.ingest.chunker import (
    DEFAULT_MIN_TOKENS,
    Chunk,
    is_retrieval_eligible,
)
from backend.ingest.extractor import PDFExtractionReport
from backend.ingest.models import DownloadRecord, GuidelineManifestEntry


def chunk_payload(
    entry: GuidelineManifestEntry,
    download: DownloadRecord,
    chunk: Chunk,
) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "guideline_id": entry.id,
        "title": entry.title,
        "condition": entry.condition,
        "source_type": entry.source_type,
        "publisher": entry.publisher,
        "year": entry.year,
        "audience": entry.audience,
        "priority": entry.priority,
        "priority_rank": entry.priority_rank,
        "clinical_area": entry.clinical_area,
        "country": entry.country,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "heading": chunk.heading,
        "section_guess": chunk.section_guess,
        "recommendation_type_guess": chunk.recommendation_type_guess,
        "population": (
            chunk.population
            if chunk.population != "no_especificada"
            else (entry.population[0] if entry.population else chunk.population)
        ),
        "care_level": (
            chunk.care_level
            if chunk.care_level != "no_especificado"
            else (entry.care_level[0] if entry.care_level else chunk.care_level)
        ),
        "urgency": chunk.urgency,
        "retrieval_eligible": is_retrieval_eligible(chunk),
        "url": entry.url,
        "source_sha256": download.sha256,
        "content": chunk.text,
        "token_estimate": chunk.token_estimate,
    }


def write_chunks_jsonl(
    output_dir: str | Path,
    entry: GuidelineManifestEntry,
    download: DownloadRecord,
    chunks: list[Chunk],
    *,
    force: bool,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{entry.id}.jsonl"
    if target.exists() and not force:
        raise FileExistsError(
            f"{target} already exists. Pass --force to replace processed chunks."
        )
    temporary = target.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(
                json.dumps(
                    chunk_payload(entry, download, chunk),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    temporary.replace(target)
    return target


def write_ingestion_report(
    output_dir: str | Path,
    entry: GuidelineManifestEntry,
    download: DownloadRecord,
    extraction: PDFExtractionReport,
    chunks: list[Chunk],
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{entry.id}.json"
    sections = Counter(chunk.section_guess for chunk in chunks)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "guideline": entry.metadata(),
        "download": asdict(download),
        "extraction": {
            **asdict(extraction),
            "text_coverage": round(extraction.text_coverage, 6),
        },
        "chunking": {
            "count": len(chunks),
            "token_estimate_total": sum(chunk.token_estimate for chunk in chunks),
            "token_estimate_min": min(
                (chunk.token_estimate for chunk in chunks), default=0
            ),
            "token_estimate_max": max(
                (chunk.token_estimate for chunk in chunks), default=0
            ),
            "sections": dict(sorted(sections.items())),
            "retrieval_eligible": sum(
                is_retrieval_eligible(chunk) for chunk in chunks
            ),
        },
        "review_flags": review_flags(entry, extraction, chunks),
    }
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def review_flags(
    entry: GuidelineManifestEntry,
    extraction: PDFExtractionReport,
    chunks: list[Chunk],
) -> list[str]:
    flags: list[str] = []
    if (
        entry.expected_pages is not None
        and extraction.pages_total != entry.expected_pages
    ):
        flags.append(
            f"page_count_mismatch:{extraction.pages_total}!={entry.expected_pages}"
        )
    relevant_empty_pages = [
        page
        for page in extraction.empty_pages
        if page >= entry.content_start_page
    ]
    if relevant_empty_pages:
        flags.append(f"empty_pages:{len(relevant_empty_pages)}")
    if extraction.warnings:
        flags.append(
            f"extraction_warnings:{sum(extraction.warnings.values())}"
        )
    if not any(chunk.section_guess == "diagnostico" for chunk in chunks):
        flags.append("missing_section:diagnostico")
    if not any(
        chunk.section_guess.startswith("tratamiento") for chunk in chunks
    ):
        flags.append("missing_section:tratamiento")
    if max((chunk.token_estimate for chunk in chunks), default=0) > 1_200:
        flags.append("oversized_chunks")
    undersized_retrievable = sum(
        chunk.token_estimate < DEFAULT_MIN_TOKENS
        and is_retrieval_eligible(chunk)
        for chunk in chunks
    )
    if undersized_retrievable:
        flags.append(
            f"undersized_retrieval_chunks:{undersized_retrievable}"
        )
    return flags
