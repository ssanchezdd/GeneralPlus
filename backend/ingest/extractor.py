from __future__ import annotations

import logging
from collections import Counter
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from backend.ingest.chunker import DocumentPage


@dataclass(frozen=True)
class PDFExtractionReport:
    path: str
    pages_total: int
    pages_with_text: int
    empty_pages: list[int]
    characters: int
    title: str | None
    author: str | None
    warnings: dict[str, int]
    warning_pages: dict[str, list[int]]
    security_flags: list[str]

    @property
    def text_coverage(self) -> float:
        if self.pages_total == 0:
            return 0.0
        return self.pages_with_text / self.pages_total


class PDFExtractor:
    def extract(self, location: str) -> list[DocumentPage]:
        pages, _ = self.extract_with_report(location)
        return pages

    def extract_with_report(
        self, location: str
    ) -> tuple[list[DocumentPage], PDFExtractionReport]:
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError(
                "pypdf is required. Install backend/requirements.txt."
            ) from error

        path = Path(location)
        warning_counts: Counter[str] = Counter()
        warning_pages: defaultdict[str, set[int]] = defaultdict(set)
        current_page = 0

        class WarningCounter(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                message = record.getMessage()
                warning_counts[message] += 1
                if current_page:
                    warning_pages[message].add(current_page)

        pypdf_logger = logging.getLogger("pypdf")
        previous_propagate = pypdf_logger.propagate
        handler = WarningCounter(level=logging.WARNING)
        pypdf_logger.addHandler(handler)
        pypdf_logger.propagate = False
        try:
            with path.open("rb") as handle:
                reader = PdfReader(handle, strict=False)
                if reader.is_encrypted:
                    try:
                        unlocked = reader.decrypt("")
                    except Exception as error:
                        raise ValueError(
                            f"Encrypted PDF cannot be read: {path}"
                        ) from error
                    if not unlocked:
                        raise ValueError(f"Encrypted PDF cannot be read: {path}")

                root = reader.trailer["/Root"]
                if hasattr(root, "get_object"):
                    root = root.get_object()
                security_flags: list[str] = []
                for key in ("/OpenAction", "/AA"):
                    if root.get(key) is not None:
                        security_flags.append(key)
                names = root.get("/Names")
                if names is not None and hasattr(names, "get_object"):
                    names = names.get_object()
                if names:
                    for key in ("/JavaScript", "/EmbeddedFiles"):
                        if names.get(key) is not None:
                            security_flags.append(f"/Names{key}")
                if security_flags:
                    raise ValueError(
                        "PDF contains active or embedded content requiring "
                        f"manual security review: {', '.join(security_flags)}"
                    )

                pages: list[DocumentPage] = []
                empty_pages: list[int] = []
                character_count = 0
                for number, page in enumerate(reader.pages, start=1):
                    current_page = number
                    text = page.extract_text(extraction_mode="layout") or ""
                    text = text.replace("\x00", "").strip()
                    if len(text) < 30:
                        empty_pages.append(number)
                    else:
                        character_count += len(text)
                    pages.append(DocumentPage(page=number, text=text))

                metadata = reader.metadata or {}
                report = PDFExtractionReport(
                    path=str(path),
                    pages_total=len(pages),
                    pages_with_text=len(pages) - len(empty_pages),
                    empty_pages=empty_pages,
                    characters=character_count,
                    title=getattr(metadata, "title", None),
                    author=getattr(metadata, "author", None),
                    warnings=dict(warning_counts),
                    warning_pages={
                        message: sorted(pages)
                        for message, pages in warning_pages.items()
                    },
                    security_flags=security_flags,
                )
        finally:
            pypdf_logger.removeHandler(handler)
            pypdf_logger.propagate = previous_propagate

        if report.text_coverage < 0.8:
            raise ValueError(
                f"PDF text coverage is too low ({report.text_coverage:.1%}); "
                "OCR and human review are required."
            )
        return pages, report
