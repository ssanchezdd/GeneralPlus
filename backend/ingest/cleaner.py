from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from backend.ingest.chunker import DocumentPage


PAGE_NUMBER_PATTERN = re.compile(
    r"^\s*(?:p[áa]gina\s+)?(?:\d+\s*(?:de|/)\s*\d+|\d+)\s*$",
    re.IGNORECASE,
)


def _line_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"\d+", "#", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _candidate_margin_lines(text: str, width: int = 4) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) <= (width * 2) + 2:
        return [*lines[:1], *lines[-1:]]
    return [*lines[:width], *lines[-width:]]


def find_repeated_margin_lines(pages: list[DocumentPage]) -> set[str]:
    counts: Counter[str] = Counter()
    for page in pages:
        page_candidates = {
            _line_key(line)
            for line in _candidate_margin_lines(page.text)
            if 3 <= len(line) <= 180
        }
        counts.update(page_candidates)
    threshold = max(3, math.ceil(len(pages) * 0.25))
    return {
        line
        for line, count in counts.items()
        if count >= threshold and not PAGE_NUMBER_PATTERN.fullmatch(line)
    }


def clean_page_text(text: str, repeated_lines: set[str]) -> str:
    kept_lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = unicodedata.normalize("NFKC", raw_line).strip()
        if not line:
            kept_lines.append("")
            continue
        if PAGE_NUMBER_PATTERN.fullmatch(line):
            continue
        if _line_key(line) in repeated_lines:
            continue
        kept_lines.append(line)

    value = "\n".join(kept_lines)
    value = re.sub(
        r"(?<=[a-záéíóúñ])- *\n *(?=[a-záéíóúñ])",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def clean_pages(pages: list[DocumentPage]) -> list[DocumentPage]:
    repeated = find_repeated_margin_lines(pages)
    return [
        DocumentPage(page=page.page, text=clean_page_text(page.text, repeated))
        for page in pages
    ]
