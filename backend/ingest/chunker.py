from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    page_start: int
    page_end: int
    heading: str | None
    text: str
    token_estimate: int


HEADING_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ,:;/()-]{5,}$"
)


def estimate_tokens(text: str) -> int:
    """Conservative estimator used before provider-specific tokenization."""
    return max(1, round(len(text) / 4))


def normalize_paragraphs(text: str) -> list[str]:
    value = re.sub(r"-\s*\n\s*", "", text)
    value = re.sub(r"(?<!\n)\n(?!\n)", " ", value)
    return [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n{2,}", value)
        if paragraph.strip()
    ]


def chunk_pages(
    document_id: str,
    pages: list[DocumentPage],
    max_tokens: int = 700,
    overlap_tokens: int = 90,
) -> list[Chunk]:
    if max_tokens <= overlap_tokens:
        raise ValueError("max_tokens must be greater than overlap_tokens")

    chunks: list[Chunk] = []
    buffer: list[str] = []
    current_heading: str | None = None
    page_start = pages[0].page if pages else 1
    current_page = page_start

    def flush() -> None:
        nonlocal buffer, page_start
        text = "\n\n".join(buffer).strip()
        if not text:
            return
        chunks.append(
            Chunk(
                id=f"{document_id}-{len(chunks) + 1:04d}",
                page_start=page_start,
                page_end=current_page,
                heading=current_heading,
                text=text,
                token_estimate=estimate_tokens(text),
            )
        )
        overlap_chars = overlap_tokens * 4
        buffer = [text[-overlap_chars:]] if overlap_chars and text else []
        page_start = current_page

    for page in pages:
        current_page = page.page
        for paragraph in normalize_paragraphs(page.text):
            if HEADING_PATTERN.match(paragraph) and len(paragraph) < 140:
                if estimate_tokens("\n\n".join(buffer)) > max_tokens // 2:
                    flush()
                current_heading = paragraph

            projected = "\n\n".join([*buffer, paragraph])
            if buffer and estimate_tokens(projected) > max_tokens:
                flush()
            buffer.append(paragraph)

    flush()
    return chunks

