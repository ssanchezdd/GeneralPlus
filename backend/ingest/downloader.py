from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.ingest.models import (
    ALLOWED_SOURCE_HOSTS,
    DownloadRecord,
    GuidelineManifestEntry,
)


PDF_MAGIC = b"%PDF-"
DEFAULT_MAX_BYTES = 150 * 1024 * 1024
USER_AGENT = "CriterioGuidelineIngest/0.2 (+https://github.com/ssanchezdd/GeneralPlus)"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_pdf(path: Path, content_type: str) -> None:
    with path.open("rb") as handle:
        magic = handle.read(len(PDF_MAGIC))
    if magic != PDF_MAGIC:
        raise ValueError(f"Downloaded file is not a PDF: {path.name}")
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"application/pdf", "application/octet-stream"}:
        raise ValueError(f"Unexpected PDF content type: {content_type}")


def _archive_existing(path: Path, guideline_id: str, digest: str) -> None:
    archive = path.parent / ".versions" / guideline_id / f"{digest}.pdf"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        shutil.copy2(path, archive)


def download_guideline(
    entry: GuidelineManifestEntry,
    destination_dir: str | Path,
    existing_record: DownloadRecord | None = None,
    *,
    force: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[DownloadRecord, bool]:
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / entry.filename

    if target.exists() and not force:
        digest = sha256_file(target)
        if existing_record and digest == existing_record.sha256:
            return existing_record, False
        if entry.expected_sha256 and digest == entry.expected_sha256:
            adopted = DownloadRecord(
                guideline_id=entry.id,
                url=entry.url,
                final_url=entry.url,
                filename=entry.filename,
                sha256=digest,
                bytes=target.stat().st_size,
                content_type="application/pdf",
                downloaded_at=datetime.fromtimestamp(
                    target.stat().st_mtime, tz=UTC
                ).isoformat(),
            )
            return adopted, False
        raise FileExistsError(
            f"{target} exists but is not represented by the lock file. "
            "Inspect it and pass --force to archive and replace it."
        )

    request = Request(
        entry.url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"},
        method="GET",
    )
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=90) as response:
            final_url = response.geturl()
            final_host = urlparse(final_url).hostname
            if (
                not final_url.startswith("https://")
                or final_host not in ALLOWED_SOURCE_HOSTS
            ):
                raise ValueError(f"Unsafe redirect target: {final_url}")

            content_type = response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > max_bytes:
                raise ValueError(
                    f"PDF exceeds download limit ({declared_size} > {max_bytes})"
                )

            temporary_path = destination / (
                f".{entry.id}-{uuid.uuid4().hex}.part"
            )
            with temporary_path.open("xb") as temporary:
                digest = hashlib.sha256()
                downloaded = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    downloaded += len(block)
                    if downloaded > max_bytes:
                        raise ValueError(
                            f"PDF exceeds download limit ({downloaded} > {max_bytes})"
                        )
                    digest.update(block)
                    temporary.write(block)

            _validate_pdf(temporary_path, content_type)
            checksum = digest.hexdigest()
            if entry.expected_sha256 and checksum != entry.expected_sha256:
                raise ValueError(
                    f"SHA-256 mismatch for {entry.id}: "
                    f"{checksum} != {entry.expected_sha256}"
                )

            if target.exists():
                _archive_existing(target, entry.id, sha256_file(target))
            temporary_path.replace(target)
            temporary_path = None
            return (
                DownloadRecord(
                    guideline_id=entry.id,
                    url=entry.url,
                    final_url=final_url,
                    filename=entry.filename,
                    sha256=checksum,
                    bytes=downloaded,
                    content_type=content_type,
                    downloaded_at=datetime.now(UTC).isoformat(),
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                ),
                True,
            )
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
