from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ALLOWED_SOURCE_HOSTS = {
    "www.minsalud.gov.co",
    "minsalud.gov.co",
    "www.sispro.gov.co",
    "sispro.gov.co",
    "www.ins.gov.co",
    "ins.gov.co",
}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,100}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _validate_iso_date(value: str | None, field_name: str, entry_id: str) -> None:
    if not value:
        return
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid {field_name} date for {entry_id}: {value}"
        ) from error


@dataclass(frozen=True)
class GuidelineManifestEntry:
    id: str
    title: str
    condition: str
    source_type: str
    country: str
    publisher: str
    year: int
    audience: str
    priority: str
    priority_rank: int
    clinical_area: str
    url: str
    filename: str
    population: list[str] = field(default_factory=list)
    care_level: list[str] = field(default_factory=list)
    status: str = "active"
    expected_pages: int | None = None
    content_start_page: int = 1
    source_verified_at: str | None = None
    scope_note: str | None = None
    expected_sha256: str | None = None
    clinical_review_status: str = "pending"
    reviewed_by: str | None = None
    reviewed_at: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GuidelineManifestEntry":
        required = {
            "id",
            "title",
            "condition",
            "source_type",
            "country",
            "publisher",
            "year",
            "audience",
            "priority",
            "priority_rank",
            "clinical_area",
            "url",
            "filename",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(f"Manifest entry is missing: {', '.join(missing)}")

        entry = cls(**value)
        entry.validate()
        return entry

    def validate(self) -> None:
        if not ID_PATTERN.fullmatch(self.id):
            raise ValueError(f"Invalid guideline id: {self.id}")
        if Path(self.filename).name != self.filename or not self.filename.endswith(
            ".pdf"
        ):
            raise ValueError(f"Unsafe PDF filename: {self.filename}")
        parsed = urlparse(self.url)
        if parsed.scheme != "https":
            raise ValueError(f"Guideline URL must use HTTPS: {self.url}")
        if parsed.hostname not in ALLOWED_SOURCE_HOSTS:
            raise ValueError(f"Guideline host is not allowlisted: {parsed.hostname}")
        if self.expected_sha256 and not SHA256_PATTERN.fullmatch(
            self.expected_sha256
        ):
            raise ValueError(f"Invalid expected SHA-256 for {self.id}")
        if self.year < 1990 or self.year > datetime.now(UTC).year:
            raise ValueError(f"Invalid publication year for {self.id}: {self.year}")
        if self.expected_pages is not None and self.expected_pages < 1:
            raise ValueError(f"Invalid expected page count for {self.id}")
        if self.content_start_page < 1:
            raise ValueError(f"Invalid clinical content start page for {self.id}")
        if (
            self.expected_pages is not None
            and self.content_start_page > self.expected_pages
        ):
            raise ValueError(
                f"Clinical content start exceeds page count for {self.id}"
            )
        if self.clinical_review_status not in {"pending", "approved", "rejected"}:
            raise ValueError(
                f"Invalid clinical review status for {self.id}: "
                f"{self.clinical_review_status}"
            )
        if self.clinical_review_status == "approved" and not (
            self.reviewed_by and self.reviewed_at
        ):
            raise ValueError(
                f"Approved guideline {self.id} must include reviewer and date"
            )
        _validate_iso_date(
            self.source_verified_at, "source_verified_at", self.id
        )
        _validate_iso_date(self.reviewed_at, "reviewed_at", self.id)

    def metadata(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DownloadRecord:
    guideline_id: str
    url: str
    final_url: str
    filename: str
    sha256: str
    bytes: int
    content_type: str
    downloaded_at: str
    etag: str | None = None
    last_modified: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DownloadRecord":
        record = cls(**value)
        if not SHA256_PATTERN.fullmatch(record.sha256):
            raise ValueError(f"Invalid lock SHA-256 for {record.guideline_id}")
        return record


def load_manifest(path: str | Path) -> list[GuidelineManifestEntry]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Guideline manifest must contain a JSON array")
    entries = [GuidelineManifestEntry.from_dict(item) for item in payload]
    ids = [entry.id for entry in entries]
    filenames = [entry.filename for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Guideline manifest contains duplicate ids")
    if len(filenames) != len(set(filenames)):
        raise ValueError("Guideline manifest contains duplicate filenames")
    return sorted(entries, key=lambda entry: entry.priority_rank)


def load_lock(path: str | Path) -> dict[str, DownloadRecord]:
    lock_path = Path(path)
    if not lock_path.exists():
        return {}
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    documents = payload.get("documents", {})
    if not isinstance(documents, dict):
        raise ValueError("Guideline lock documents must be a JSON object")
    return {
        guideline_id: DownloadRecord.from_dict(record)
        for guideline_id, record in documents.items()
    }


def write_lock(path: str | Path, records: dict[str, DownloadRecord]) -> None:
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "documents": {
            key: asdict(records[key]) for key in sorted(records.keys())
        },
    }
    temporary = lock_path.with_suffix(f"{lock_path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(lock_path)
