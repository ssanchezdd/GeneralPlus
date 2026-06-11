from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from backend.ingest.artifacts import (
    review_flags,
    write_chunks_jsonl,
    write_ingestion_report,
)
from backend.ingest.chunker import chunk_pages
from backend.ingest.cleaner import clean_pages
from backend.ingest.downloader import download_guideline
from backend.ingest.embeddings import OpenAIEmbeddingProvider
from backend.ingest.extractor import PDFExtractor
from backend.ingest.models import (
    DownloadRecord,
    GuidelineManifestEntry,
    load_lock,
    load_manifest,
    write_lock,
)
from backend.ingest.repository import PgVectorGuidelineRepository


@dataclass(frozen=True)
class GuidelineRunResult:
    guideline_id: str
    downloaded: bool
    pages: int
    chunks: int
    indexed: bool
    sha256: str


def assert_clinically_approved(
    entries: list[GuidelineManifestEntry],
) -> None:
    blocked = [
        f"{entry.id}:{entry.clinical_review_status}"
        for entry in entries
        if entry.clinical_review_status != "approved"
    ]
    if blocked:
        raise RuntimeError(
            "Indexing is blocked until clinical review is approved: "
            + ", ".join(blocked)
        )


def run_ingestion(
    *,
    manifest_path: str | Path,
    lock_path: str | Path,
    raw_dir: str | Path,
    processed_dir: str | Path,
    reports_dir: str | Path,
    selected_ids: set[str] | None,
    prepare_only: bool,
    download_only: bool,
    force: bool,
    min_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
    database_url: str | None,
    initialize_schema: bool,
    schema_path: str | Path,
    embedding_model: str,
    embedding_dimensions: int,
) -> list[GuidelineRunResult]:
    entries = load_manifest(manifest_path)
    if selected_ids:
        known_ids = {entry.id for entry in entries}
        unknown = selected_ids - known_ids
        if unknown:
            raise ValueError(f"Unknown guideline ids: {', '.join(sorted(unknown))}")
        entries = [entry for entry in entries if entry.id in selected_ids]
    entries = [entry for entry in entries if entry.status == "active"]

    lock_records = load_lock(lock_path)
    repository: PgVectorGuidelineRepository | None = None
    embedding_provider: OpenAIEmbeddingProvider | None = None
    if not prepare_only and not download_only:
        assert_clinically_approved(entries)
        database_url = database_url or os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is required for indexing. "
                "Use --prepare-only to download, clean, chunk, and validate."
            )
        repository = PgVectorGuidelineRepository(database_url)
        if initialize_schema:
            repository.initialize_schema(schema_path)
        embedding_provider = OpenAIEmbeddingProvider(
            model=embedding_model,
            dimensions=embedding_dimensions,
        )

    extractor = PDFExtractor()
    results: list[GuidelineRunResult] = []
    for entry in entries:
        download, downloaded = download_guideline(
            entry,
            raw_dir,
            lock_records.get(entry.id),
            force=force,
        )
        lock_records[entry.id] = download
        write_lock(lock_path, lock_records)

        if download_only:
            results.append(
                GuidelineRunResult(
                    guideline_id=entry.id,
                    downloaded=downloaded,
                    pages=0,
                    chunks=0,
                    indexed=False,
                    sha256=download.sha256,
                )
            )
            continue

        pdf_path = Path(raw_dir) / entry.filename
        raw_pages, extraction = extractor.extract_with_report(str(pdf_path))
        if (
            entry.expected_pages is not None
            and extraction.pages_total != entry.expected_pages
        ):
            raise ValueError(
                f"{entry.id} page count changed: "
                f"{extraction.pages_total} != {entry.expected_pages}"
            )
        cleaned_pages = clean_pages(raw_pages)
        clinical_pages = [
            page
            for page in cleaned_pages
            if page.page >= entry.content_start_page
        ]
        chunks = chunk_pages(
            entry.id,
            clinical_pages,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        if not chunks:
            raise ValueError(f"No chunks were produced for {entry.id}")

        write_chunks_jsonl(
            processed_dir,
            entry,
            download,
            chunks,
            force=force or downloaded,
        )
        write_ingestion_report(
            reports_dir, entry, download, extraction, chunks
        )

        indexed = False
        if repository and embedding_provider:
            if entry.clinical_review_status != "approved":
                raise RuntimeError(
                    f"{entry.id} is not clinically approved for indexing "
                    f"(status={entry.clinical_review_status})"
                )
            flags = review_flags(entry, extraction, chunks)
            if flags:
                raise RuntimeError(
                    f"{entry.id} has unresolved ingestion review flags: "
                    f"{', '.join(flags)}"
                )
            existing, existing_sha = repository.is_ingested(entry.id)
            if existing and not force:
                raise RuntimeError(
                    f"{entry.id} is already indexed with SHA-256 "
                    f"{existing_sha}; pass --force to replace it"
                )
            vectors = embedding_provider.embed([chunk.text for chunk in chunks])
            repository.upsert(
                entry,
                download,
                extraction,
                chunks,
                vectors,
                embedding_model=embedding_provider.model,
                force=force,
            )
            indexed = True

        results.append(
            GuidelineRunResult(
                guideline_id=entry.id,
                downloaded=downloaded,
                pages=extraction.pages_total,
                chunks=len(chunks),
                indexed=indexed,
                sha256=download.sha256,
            )
        )

    return results


def print_results(results: list[GuidelineRunResult]) -> None:
    print(
        json.dumps(
            [result.__dict__ for result in results],
            ensure_ascii=False,
            indent=2,
        )
    )
