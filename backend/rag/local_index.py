from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONDITION_ALIASES = {
    "hipertension_arterial": (
        "hipertension",
        "hipertensiva",
        "presion arterial",
        "hta",
    ),
    "diabetes_mellitus_tipo_2": (
        "diabetes",
        "diabetico",
        "diabetica",
        "dm2",
        "dmt2",
    ),
}


def normalize_text(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )


def infer_condition(query: str) -> str | None:
    normalized = normalize_text(query)
    matches = [
        condition
        for condition, aliases in CONDITION_ALIASES.items()
        if any(alias in normalized for alias in aliases)
    ]
    return matches[0] if len(matches) == 1 else None


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9/]+", normalized):
        if len(token) <= 2:
            continue
        if token.endswith("iones") and len(token) > 7:
            token = f"{token[:-5]}ion"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.append(token)
    return tokens


@dataclass(frozen=True)
class LocalSearchResult:
    score: float
    chunk: dict[str, Any]


class LocalLexicalIndex:
    """Credential-free quality check. It is not the production vector index."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.term_frequencies = [
            Counter(tokenize(chunk["content"])) for chunk in chunks
        ]
        self.document_frequencies: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            self.document_frequencies.update(frequencies.keys())
        self.average_length = (
            sum(sum(frequencies.values()) for frequencies in self.term_frequencies)
            / max(1, len(self.term_frequencies))
        )

    @classmethod
    def from_directory(cls, directory: str | Path) -> "LocalLexicalIndex":
        chunks: list[dict[str, Any]] = []
        for path in sorted(Path(directory).glob("*.jsonl")):
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise ValueError(
                            f"Invalid JSONL at {path}:{line_number}"
                        ) from error
                    if not chunk.get("content") or not chunk.get("url"):
                        raise ValueError(
                            f"Chunk is missing content or source at "
                            f"{path}:{line_number}"
                        )
                    chunks.append(chunk)
        if not chunks:
            raise FileNotFoundError(
                f"No processed chunk JSONL files found in {directory}"
            )
        return cls(chunks)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        condition: str | None = None,
        minimum_score: float = 1.0,
    ) -> list[LocalSearchResult]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        total_documents = len(self.chunks)
        k1 = 1.5
        b = 0.75
        results: list[LocalSearchResult] = []
        for chunk, frequencies in zip(
            self.chunks, self.term_frequencies, strict=True
        ):
            if chunk.get("retrieval_eligible") is False:
                continue
            if condition and chunk.get("condition") != condition:
                continue
            document_length = sum(frequencies.values())
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if frequency == 0:
                    continue
                document_frequency = self.document_frequencies.get(term, 0)
                inverse_frequency = math.log(
                    1
                    + (total_documents - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                denominator = frequency + k1 * (
                    1
                    - b
                    + b * document_length / max(1.0, self.average_length)
                )
                score += inverse_frequency * (frequency * (k1 + 1) / denominator)
            score *= self._metadata_multiplier(query_terms, chunk)
            if score >= minimum_score:
                results.append(LocalSearchResult(score=score, chunk=chunk))
        return sorted(results, key=lambda result: result.score, reverse=True)[
            :top_k
        ]

    @staticmethod
    def _metadata_multiplier(
        query_terms: list[str], chunk: dict[str, Any]
    ) -> float:
        terms = set(query_terms)
        section = chunk.get("section_guess", "general")
        multiplier = 0.7 if section == "general" else 1.0
        intent_sections = [
            (
                {"remitir", "remision", "urgencia", "emergencia"},
                {
                    "alcance",
                    "remision",
                    "signos_de_alarma",
                    "contraindicaciones",
                },
                1.8,
            ),
            (
                {"tratamiento", "manejo", "farmacologico", "medicamento"},
                {"tratamiento_farmacologico", "tratamiento_no_farmacologico"},
                1.5,
            ),
            (
                {"diagnostico", "diagnosticar", "criterios"},
                {"diagnostico", "criterios"},
                1.5,
            ),
            (
                {"seguimiento", "control", "monitoreo"},
                {"seguimiento"},
                1.4,
            ),
        ]
        for intent_terms, preferred_sections, boost in intent_sections:
            if terms & intent_terms and section in preferred_sections:
                multiplier *= boost
        if {"primer", "nivel"} <= terms and chunk.get("care_level") == "primer_nivel":
            multiplier *= 1.25
        return multiplier
