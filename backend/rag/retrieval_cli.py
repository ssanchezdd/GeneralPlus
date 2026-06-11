from __future__ import annotations

import argparse
import sys

from backend.rag.local_index import LocalLexicalIndex, infer_condition


REFUSAL_MESSAGE = (
    "No encontré una fuente suficiente en las guías cargadas. "
    "No puedo responder con seguridad."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate retrieval against prepared guideline chunks."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--chunks-dir", default="data/processed_chunks")
    parser.add_argument("--condition")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--minimum-score", type=float, default=1.0)
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    index = LocalLexicalIndex.from_directory(arguments.chunks_dir)
    results = index.search(
        arguments.query,
        top_k=arguments.top_k,
        condition=arguments.condition or infer_condition(arguments.query),
        minimum_score=arguments.minimum_score,
    )
    if not results:
        print(REFUSAL_MESSAGE)
        raise SystemExit(2)

    print(f"Consulta: {arguments.query}")
    print("\nFragmentos recuperados:")
    for position, result in enumerate(results, start=1):
        chunk = result.chunk
        page = (
            str(chunk["page_start"])
            if chunk["page_start"] == chunk["page_end"]
            else f"{chunk['page_start']}-{chunk['page_end']}"
        )
        print(
            f"{position}. score={result.score:.3f} "
            f"section={chunk['section_guess']} pages={page}\n"
            f"   {chunk['content'][:280].replace(chr(10), ' ')}..."
        )

    print("\nBasado en:")
    seen: set[tuple[str, int, int]] = set()
    for result in results:
        chunk = result.chunk
        key = (
            chunk["guideline_id"],
            chunk["page_start"],
            chunk["page_end"],
        )
        if key in seen:
            continue
        seen.add(key)
        page = (
            str(chunk["page_start"])
            if chunk["page_start"] == chunk["page_end"]
            else f"{chunk['page_start']}-{chunk['page_end']}"
        )
        print(
            f"- {chunk['title']}, {chunk['publisher']}, "
            f"{chunk['year']}, página(s) {page}: {chunk['url']}"
        )


if __name__ == "__main__":
    main()
