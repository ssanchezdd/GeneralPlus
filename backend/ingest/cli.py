from __future__ import annotations

import argparse

from backend.ingest.runner import print_results, run_ingestion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download, verify, extract, clean, chunk, embed, and index "
            "Colombian clinical guidelines."
        )
    )
    parser.add_argument(
        "--manifest", default="data/guidelines_manifest.json"
    )
    parser.add_argument("--lock", default="data/guidelines_lock.json")
    parser.add_argument("--raw-dir", default="data/raw_guidelines")
    parser.add_argument("--processed-dir", default="data/processed_chunks")
    parser.add_argument("--reports-dir", default="data/ingestion_reports")
    parser.add_argument("--id", action="append", dest="ids")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--min-tokens", type=int, default=700)
    parser.add_argument("--max-tokens", type=int, default=1_200)
    parser.add_argument("--overlap-tokens", type=int, default=120)
    parser.add_argument("--database-url")
    parser.add_argument("--init-schema", action="store_true")
    parser.add_argument("--schema", default="backend/schema.sql")
    parser.add_argument(
        "--embedding-model", default="text-embedding-3-small"
    )
    parser.add_argument("--embedding-dimensions", type=int, default=1_536)
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    if arguments.download_only and arguments.prepare_only:
        raise SystemExit("--download-only and --prepare-only are mutually exclusive")
    results = run_ingestion(
        manifest_path=arguments.manifest,
        lock_path=arguments.lock,
        raw_dir=arguments.raw_dir,
        processed_dir=arguments.processed_dir,
        reports_dir=arguments.reports_dir,
        selected_ids=set(arguments.ids) if arguments.ids else None,
        prepare_only=arguments.prepare_only,
        download_only=arguments.download_only,
        force=arguments.force,
        min_tokens=arguments.min_tokens,
        max_tokens=arguments.max_tokens,
        overlap_tokens=arguments.overlap_tokens,
        database_url=arguments.database_url,
        initialize_schema=arguments.init_schema,
        schema_path=arguments.schema,
        embedding_model=arguments.embedding_model,
        embedding_dimensions=arguments.embedding_dimensions,
    )
    print_results(results)


if __name__ == "__main__":
    main()
