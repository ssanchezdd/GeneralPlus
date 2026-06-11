import io
import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from backend.evaluators.safety import evaluate_query_safety
from backend.app.main import QueryRequest, health, query
from backend.ingest.chunker import DocumentPage, chunk_pages
from backend.ingest.cleaner import clean_pages
from backend.ingest.downloader import download_guideline
from backend.ingest.extractor import PDFExtractor
from backend.ingest.models import GuidelineManifestEntry, load_manifest
from backend.ingest.runner import assert_clinically_approved
from backend.rag.local_index import LocalLexicalIndex, infer_condition
from backend.rag.service import (
    EvidenceRecord,
    InMemoryRetriever,
    RagService,
)

TEST_TEMP_ROOT = Path(".test-tmp")
TEST_TEMP_ROOT.mkdir(exist_ok=True)


@contextmanager
def workspace_directory(prefix: str):
    directory = TEST_TEMP_ROOT / f"{prefix}-{uuid.uuid4().hex}"
    directory.mkdir()
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def manifest_entry(**overrides) -> GuidelineManifestEntry:
    value = {
        "id": "col-gpc-test-2026",
        "title": "Guía de prueba",
        "condition": "hipertension_arterial",
        "source_type": "GPC",
        "country": "Colombia",
        "publisher": "Ministerio de Salud",
        "year": 2026,
        "audience": "profesionales",
        "priority": "alta",
        "priority_rank": 1,
        "clinical_area": "medicina_general",
        "url": "https://www.minsalud.gov.co/test.pdf",
        "filename": "test.pdf",
    }
    value.update(overrides)
    return GuidelineManifestEntry.from_dict(value)


class ManifestTests(unittest.TestCase):
    def test_loads_and_sorts_valid_manifest(self) -> None:
        with workspace_directory("manifest") as directory:
            path = directory / "manifest.json"
            first = manifest_entry(priority_rank=2).metadata()
            second = manifest_entry(
                id="col-gpc-second-2026",
                filename="second.pdf",
                priority_rank=1,
            ).metadata()
            path.write_text(
                json.dumps([first, second], ensure_ascii=False),
                encoding="utf-8",
            )
            entries = load_manifest(path)
        self.assertEqual(entries[0].id, "col-gpc-second-2026")

    def test_rejects_non_official_host(self) -> None:
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            manifest_entry(url="https://example.com/guide.pdf")

    def test_approved_manifest_requires_reviewer_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "reviewer and date"):
            manifest_entry(clinical_review_status="approved")

    def test_pending_guideline_cannot_be_indexed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "clinical review"):
            assert_clinically_approved([manifest_entry()])

    def test_approved_manifest_rejects_invalid_review_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "reviewed_at"):
            manifest_entry(
                clinical_review_status="approved",
                reviewed_by="Dra. Revisión",
                reviewed_at="11/06/2026",
            )


class FakeResponse(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": str(len(content)),
            "ETag": '"test"',
        }

    def geturl(self) -> str:
        return "https://www.minsalud.gov.co/test.pdf"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class DownloaderTests(unittest.TestCase):
    def test_downloads_pdf_and_refuses_unlocked_overwrite(self) -> None:
        content = b"%PDF-1.7\ncontrolled-test-pdf"
        entry = manifest_entry()
        with workspace_directory("download") as directory:
            with patch(
                "backend.ingest.downloader.urlopen",
                return_value=FakeResponse(content),
            ):
                record, downloaded = download_guideline(entry, directory)
            self.assertTrue(downloaded)
            self.assertEqual(record.bytes, len(content))
            self.assertEqual((directory / "test.pdf").read_bytes(), content)

            with self.assertRaises(FileExistsError):
                download_guideline(entry, directory, existing_record=None)

    def test_rejects_unexpected_sha256(self) -> None:
        content = b"%PDF-1.7\ncontrolled-test-pdf"
        entry = manifest_entry(expected_sha256="0" * 64)
        with workspace_directory("checksum") as directory:
            with patch(
                "backend.ingest.downloader.urlopen",
                return_value=FakeResponse(content),
            ):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    download_guideline(entry, directory)
            self.assertFalse((directory / "test.pdf").exists())


class ExtractorSecurityTests(unittest.TestCase):
    def test_rejects_pdf_with_javascript(self) -> None:
        from pypdf import PdfWriter

        with workspace_directory("active-pdf") as directory:
            path = directory / "active.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.add_js("app.alert('blocked')")
            with path.open("wb") as handle:
                writer.write(handle)
            with self.assertRaisesRegex(ValueError, "active or embedded"):
                PDFExtractor().extract_with_report(str(path))


class CleanerTests(unittest.TestCase):
    def test_removes_repeated_margins_and_repairs_hyphenation(self) -> None:
        pages = [
            DocumentPage(
                page=number,
                text=(
                    "GUÍA CLÍNICA 2026\n"
                    f"Texto de la página {number} con hiper-\n"
                    "tensión arterial.\n"
                    f"{number}\n"
                    "MINISTERIO DE SALUD"
                ),
            )
            for number in range(1, 6)
        ]
        cleaned = clean_pages(pages)
        self.assertNotIn("GUÍA CLÍNICA", cleaned[0].text)
        self.assertNotIn("MINISTERIO DE SALUD", cleaned[0].text)
        self.assertIn("hipertensión", cleaned[0].text)


class ChunkerTests(unittest.TestCase):
    def test_chunks_preserve_pages_size_and_clinical_sections(self) -> None:
        pages = [
            DocumentPage(
                page=1,
                text=(
                    "DIAGNÓSTICO\n\n"
                    + ("Confirmar la presión arterial con técnica adecuada. " * 80)
                ),
            ),
            DocumentPage(
                page=2,
                text=(
                    "TRATAMIENTO FARMACOLÓGICO\n\n"
                    + ("Se recomienda individualizar el tratamiento. " * 80)
                ),
            ),
        ]
        chunks = chunk_pages(
            "guide",
            pages,
            min_tokens=120,
            max_tokens=240,
            overlap_tokens=30,
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].page_start, 1)
        self.assertTrue(all(chunk.token_estimate >= 120 for chunk in chunks))
        self.assertTrue(all(chunk.token_estimate <= 240 for chunk in chunks))
        self.assertIn("diagnostico", {chunk.section_guess for chunk in chunks})
        self.assertIn(
            "tratamiento_farmacologico",
            {chunk.section_guess for chunk in chunks},
        )


class LocalIndexTests(unittest.TestCase):
    def test_retrieves_source_and_filters_condition(self) -> None:
        chunks = [
            {
                "id": "hta-1",
                "condition": "hipertension_arterial",
                "content": "Manejo inicial y diagnóstico de hipertensión arterial.",
                "url": "https://www.minsalud.gov.co/hta.pdf",
            },
            {
                "id": "dm2-1",
                "condition": "diabetes_mellitus_tipo_2",
                "content": "Diagnóstico y seguimiento de diabetes mellitus.",
                "url": "https://www.minsalud.gov.co/dm2.pdf",
            },
        ]
        index = LocalLexicalIndex(chunks)
        results = index.search(
            "manejo de hipertensión",
            condition="hipertension_arterial",
            minimum_score=0.1,
        )
        self.assertEqual(results[0].chunk["id"], "hta-1")

    def test_infers_condition_from_clinical_query(self) -> None:
        self.assertEqual(
            infer_condition(
                "manejo inicial de hipertensión arterial en primer nivel"
            ),
            "hipertension_arterial",
        )
        self.assertIsNone(infer_condition("manejo inicial en primer nivel"))


class RagServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        record = EvidenceRecord(
            id="hta",
            disease_id="hypertension",
            source_type="GPC",
            title="Hipertensión arterial primaria",
            text="La guía excluye la urgencia hipertensiva.",
            source_url="https://example.test/hta.pdf",
            page=11,
            scope="Adultos con HTA primaria.",
            publisher="Ministerio de Salud",
            year=2017,
            guideline_id="col-gpc-hta-2017-profesionales",
        )
        self.service = RagService(InMemoryRetriever([record]))

    def test_abstains_without_evidence_using_required_message(self) -> None:
        result = self.service.query("mordedura de serpiente")
        self.assertTrue(result.abstained)
        self.assertEqual(
            result.summary,
            "No encontré una fuente suficiente en las guías cargadas. "
            "No puedo responder con seguridad.",
        )
        self.assertEqual(result.sources, [])

    def test_returns_source_for_matching_query(self) -> None:
        result = self.service.query("hipertensión arterial")
        self.assertFalse(result.abstained)
        self.assertEqual(result.sources[0].page, 11)
        self.assertEqual(result.sources[0].year, 2017)

    def test_flags_time_dependent_query(self) -> None:
        flags = evaluate_query_safety("Dolor torácico con diaforesis")
        self.assertIn("possible_acute_coronary_syndrome", flags)


class ApiContractTests(unittest.TestCase):
    def test_health_exposes_retrieval_mode(self) -> None:
        self.assertEqual(health()["retrieval_mode"], "demonstration")

    def test_query_includes_formatted_sources(self) -> None:
        response = query(
            QueryRequest(query="alcance de hipertensión arterial primaria")
        )
        self.assertFalse(response.abstained)
        self.assertIn("Ministerio de Salud", response.based_on[0])
        self.assertIn("página(s) 11-12", response.based_on[0])


if __name__ == "__main__":
    unittest.main()
