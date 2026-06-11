import unittest

from backend.evaluators.safety import evaluate_query_safety
from backend.ingest.chunker import DocumentPage, chunk_pages
from backend.rag.service import (
    EvidenceRecord,
    InMemoryRetriever,
    RagService,
)


class ChunkerTests(unittest.TestCase):
    def test_chunks_preserve_pages_and_size(self) -> None:
        pages = [
            DocumentPage(page=1, text="ALCANCE\n\n" + ("Texto clínico. " * 140)),
            DocumentPage(page=2, text="RECOMENDACIONES\n\n" + ("Conducta. " * 140)),
        ]
        chunks = chunk_pages("guide", pages, max_tokens=120, overlap_tokens=20)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].page_start, 1)
        self.assertTrue(all(chunk.token_estimate > 0 for chunk in chunks))


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
        )
        self.service = RagService(InMemoryRetriever([record]))

    def test_abstains_without_evidence(self) -> None:
        result = self.service.query("mordedura de serpiente")
        self.assertTrue(result.abstained)

    def test_returns_source_for_matching_query(self) -> None:
        result = self.service.query("hipertensión arterial")
        self.assertFalse(result.abstained)
        self.assertEqual(result.sources[0].page, 11)

    def test_flags_time_dependent_query(self) -> None:
        flags = evaluate_query_safety("Dolor torácico con diaforesis")
        self.assertIn("possible_acute_coronary_syndrome", flags)


if __name__ == "__main__":
    unittest.main()

