from __future__ import annotations

from backend.rag.service import ScoredSource


def format_citation(source: ScoredSource) -> str:
    page = (
        str(source.page)
        if source.page_end in {None, source.page}
        else f"{source.page}-{source.page_end}"
    )
    publisher = source.publisher or "Editor no registrado"
    year = str(source.year) if source.year else "año no registrado"
    return f"{source.title}, {publisher}, {year}, página(s) {page}"
