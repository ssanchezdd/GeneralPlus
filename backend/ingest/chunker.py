from __future__ import annotations

import re
import unicodedata
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
    section_guess: str = "general"
    recommendation_type_guess: str = "informacion"
    population: str = "no_especificada"
    care_level: str = "no_especificado"
    urgency: str = "no_especificada"


@dataclass(frozen=True)
class ParagraphBlock:
    page: int
    text: str
    heading: str | None
    section_guess: str


DEFAULT_MIN_TOKENS = 700
DEFAULT_MAX_TOKENS = 1_200
DEFAULT_OVERLAP_TOKENS = 120


HEADING_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?"
    r"[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ,:;/()\-]{4,}$"
)
NUMBERED_HEADING_PATTERN = re.compile(
    r"^\d{1,2}(?:\.\d+){0,4}[.)]?\s+[A-ZÁÉÍÓÚÑa-záéíóúñ].{3,120}$"
)

SECTION_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "alcance",
        (
            "alcance",
            "población a la que se dirige",
            "fuera del alcance",
            "se excluyen",
            "esta guía no incluye",
        ),
    ),
    (
        "metodologia",
        (
            "metodología",
            "sistema grade",
            "consenso de expertos",
            "extracción de datos",
            "síntesis de resultados",
            "declaración de intereses",
        ),
    ),
    (
        "signos_de_alarma",
        (
            "signos de alarma",
            "señales de alarma",
            "banderas rojas",
            "emergencia",
        ),
    ),
    (
        "remision",
        (
            "remisión",
            "remitir",
            "referencia",
            "derivación",
            "nivel de atención",
        ),
    ),
    (
        "contraindicaciones",
        (
            "contraindicaciones",
            "contraindicado",
            "precauciones",
            "no se recomienda",
        ),
    ),
    (
        "poblaciones_especiales",
        (
            "poblaciones especiales",
            "embarazo",
            "gestante",
            "adulto mayor",
            "enfermedad renal",
            "pediátrica",
        ),
    ),
    (
        "seguimiento",
        (
            "seguimiento",
            "monitorización",
            "monitoreo",
            "control",
            "reevaluación",
        ),
    ),
    (
        "tratamiento_farmacologico",
        (
            "tratamiento farmacológico",
            "terapia farmacológica",
            "medicamento",
            "fármaco",
            "dosis",
        ),
    ),
    (
        "tratamiento_no_farmacologico",
        (
            "tratamiento no farmacológico",
            "intervención no farmacológica",
            "estilo de vida",
            "actividad física",
            "alimentación",
            "dieta",
        ),
    ),
    (
        "diagnostico",
        (
            "diagnóstico",
            "detección",
            "tamización",
            "tamizaje",
            "prueba diagnóstica",
        ),
    ),
    (
        "criterios",
        (
            "criterios",
            "clasificación",
            "definición",
            "punto de corte",
        ),
    ),
    (
        "errores_frecuentes",
        (
            "errores frecuentes",
            "barreras",
            "implementación",
            "uso inapropiado",
        ),
    ),
]


def normalize_for_match(value: str) -> str:
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"\s+", " ", normalized).strip()


def estimate_tokens(text: str) -> int:
    """Conservative estimate used before provider-specific tokenization."""
    return max(1, round(len(text) / 4))


def normalize_paragraphs(text: str) -> list[str]:
    value = re.sub(r"(?<=[a-záéíóúñ])- *\n *(?=[a-záéíóúñ])", "", text)
    lines = [line.strip() for line in value.splitlines()]
    paragraphs: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            paragraphs.append(re.sub(r"\s+", " ", " ".join(buffer)).strip())
            buffer.clear()

    for line in lines:
        if not line:
            flush()
            continue
        if is_heading(line):
            flush()
            paragraphs.append(line)
            continue
        buffer.append(line)
    flush()
    return [paragraph for paragraph in paragraphs if paragraph]


def is_heading(value: str) -> bool:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) < 5 or len(compact) > 140:
        return False
    if HEADING_PATTERN.fullmatch(compact) or NUMBERED_HEADING_PATTERN.fullmatch(
        compact
    ):
        return True
    words = compact.split()
    return (
        len(words) <= 12
        and not compact.endswith((".", ";"))
        and sum(word[:1].isupper() for word in words) / len(words) >= 0.75
    )


def guess_section(value: str, fallback: str = "general") -> str:
    normalized = normalize_for_match(value)
    for section, terms in SECTION_RULES:
        if any(normalize_for_match(term) in normalized for term in terms):
            return section
    return fallback


def guess_recommendation_type(section: str, content: str) -> str:
    normalized = normalize_for_match(content)
    if section in {"signos_de_alarma", "contraindicaciones"}:
        return "seguridad"
    if section == "remision":
        return "remision"
    if section.startswith("tratamiento"):
        return "tratamiento"
    if section in {"diagnostico", "criterios"}:
        return "diagnostico"
    if section == "seguimiento":
        return "seguimiento"
    if "no se recomienda" in normalized:
        return "recomendacion_en_contra"
    if "recomendamos" in normalized or "se recomienda" in normalized:
        return "recomendacion"
    return "informacion"


def guess_population(content: str, default: str = "no_especificada") -> str:
    normalized = normalize_for_match(content)
    populations = [
        ("gestantes", ("embarazo", "gestante", "puerperio")),
        ("pediatrica", ("niños", "niñas", "pediatr")),
        ("adultos_mayores", ("adulto mayor", "anciano", "mayores de 65")),
        ("adultos", ("adultos", "mayores de 18")),
    ]
    for population, terms in populations:
        if any(normalize_for_match(term) in normalized for term in terms):
            return population
    return default


def guess_care_level(content: str, default: str = "no_especificado") -> str:
    normalized = normalize_for_match(content)
    levels = [
        ("urgencias", ("urgencias", "servicio de emergencia")),
        (
            "atencion_especializada",
            ("especialista", "alta complejidad", "tercer nivel"),
        ),
        (
            "primer_nivel",
            ("primer nivel", "atencion primaria", "baja complejidad"),
        ),
    ]
    for care_level, terms in levels:
        if any(normalize_for_match(term) in normalized for term in terms):
            return care_level
    return default


def guess_urgency(content: str) -> str:
    normalized = normalize_for_match(content)
    if any(
        term in normalized
        for term in (
            "atencion inmediata",
            "urgencias",
            "emergencia",
            "riesgo vital",
        )
    ):
        return "urgente"
    if any(term in normalized for term in ("seguimiento", "control ambulatorio")):
        return "no_urgente"
    return "no_especificada"


def is_retrieval_eligible(chunk: Chunk) -> bool:
    return chunk.section_guess not in {"general", "metodologia"}


def _paragraph_blocks(pages: list[DocumentPage]) -> list[ParagraphBlock]:
    blocks: list[ParagraphBlock] = []
    heading: str | None = None
    current_section = "general"
    for page in pages:
        for paragraph in normalize_paragraphs(page.text):
            if is_heading(paragraph):
                heading = paragraph
                current_section = guess_section(heading, "general")
                continue
            content_section = guess_section(paragraph[:500], "general")
            paragraph_section = (
                content_section
                if content_section
                in {
                    "alcance",
                    "metodologia",
                    "signos_de_alarma",
                    "contraindicaciones",
                    "remision",
                }
                else (
                    current_section
                    if current_section != "general"
                    else content_section
                )
            )
            blocks.append(
                ParagraphBlock(
                    page=page.page,
                    text=paragraph,
                    heading=heading,
                    section_guess=paragraph_section,
                )
            )
            current_section = paragraph_section
    return blocks


def _overlap_blocks(
    blocks: list[ParagraphBlock], overlap_tokens: int
) -> list[ParagraphBlock]:
    overlap: list[ParagraphBlock] = []
    token_count = 0
    for block in reversed(blocks):
        if overlap and block.section_guess != overlap[0].section_guess:
            break
        overlap.insert(0, block)
        token_count += estimate_tokens(block.text)
        if token_count >= overlap_tokens:
            break
    return overlap


def _block_tokens(blocks: list[ParagraphBlock]) -> int:
    return estimate_tokens("\n\n".join(block.text for block in blocks))


def _dominant_section(blocks: list[ParagraphBlock]) -> str:
    weights: dict[str, int] = {}
    for block in blocks:
        weights[block.section_guess] = (
            weights.get(block.section_guess, 0) + estimate_tokens(block.text)
        )
    return max(weights, key=weights.get, default="general")


def _split_oversized_block(
    block: ParagraphBlock, max_tokens: int
) -> list[ParagraphBlock]:
    if estimate_tokens(block.text) <= max_tokens:
        return [block]

    sentences = re.split(r"(?<=[.!?;:])\s+", block.text)
    pieces: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            pieces.append(" ".join(buffer).strip())
            buffer.clear()

    for sentence in sentences:
        if estimate_tokens(sentence) > max_tokens:
            flush()
            words = sentence.split()
            word_buffer: list[str] = []
            for word in words:
                projected = " ".join([*word_buffer, word])
                if word_buffer and estimate_tokens(projected) > max_tokens:
                    pieces.append(" ".join(word_buffer))
                    word_buffer = []
                word_buffer.append(word)
            if word_buffer:
                pieces.append(" ".join(word_buffer))
            continue

        projected = " ".join([*buffer, sentence])
        if buffer and estimate_tokens(projected) > max_tokens:
            flush()
        buffer.append(sentence)
    flush()
    return [
        ParagraphBlock(
            page=block.page,
            text=piece,
            heading=block.heading,
            section_guess=block.section_guess,
        )
        for piece in pieces
        if piece
    ]


def _merge_chunks(
    document_id: str,
    left: Chunk,
    right: Chunk,
    *,
    prefer_right_section: bool,
) -> Chunk:
    content = f"{left.text}\n\n{right.text}".strip()
    section = right.section_guess if prefer_right_section else left.section_guess
    return Chunk(
        id=f"{document_id}-pending",
        page_start=left.page_start,
        page_end=right.page_end,
        heading=right.heading if prefer_right_section else left.heading,
        text=content,
        token_estimate=estimate_tokens(content),
        section_guess=section,
        recommendation_type_guess=guess_recommendation_type(section, content),
        population=guess_population(content),
        care_level=guess_care_level(content),
        urgency=guess_urgency(content),
    )


def _merge_small_chunks(
    document_id: str,
    chunks: list[Chunk],
    *,
    min_tokens: int,
    max_tokens: int,
) -> list[Chunk]:
    merged: list[Chunk] = []
    pending: Chunk | None = None
    for chunk in chunks:
        if pending is not None:
            if pending.token_estimate + chunk.token_estimate <= max_tokens:
                chunk = _merge_chunks(
                    document_id,
                    pending,
                    chunk,
                    prefer_right_section=True,
                )
                pending = None
            else:
                merged.append(pending)
                pending = None

        if chunk.token_estimate < min_tokens:
            pending = chunk
        else:
            merged.append(chunk)

    if pending is not None:
        if (
            merged
            and merged[-1].token_estimate + pending.token_estimate <= max_tokens
        ):
            merged[-1] = _merge_chunks(
                document_id,
                merged[-1],
                pending,
                prefer_right_section=False,
            )
        else:
            merged.append(pending)

    return [
        Chunk(
            id=f"{document_id}-{index:05d}",
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            heading=chunk.heading,
            text=chunk.text,
            token_estimate=chunk.token_estimate,
            section_guess=chunk.section_guess,
            recommendation_type_guess=chunk.recommendation_type_guess,
            population=chunk.population,
            care_level=chunk.care_level,
            urgency=chunk.urgency,
        )
        for index, chunk in enumerate(merged, start=1)
    ]


def chunk_pages(
    document_id: str,
    pages: list[DocumentPage],
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    if max_tokens < 200:
        raise ValueError("max_tokens must be at least 200")
    if min_tokens < 80 or min_tokens >= max_tokens:
        raise ValueError("min_tokens must be at least 80 and below max_tokens")
    if overlap_tokens < 0 or max_tokens <= overlap_tokens:
        raise ValueError("max_tokens must be greater than overlap_tokens")

    chunks: list[Chunk] = []
    buffer: list[ParagraphBlock] = []

    def flush(*, preserve_overlap: bool) -> None:
        nonlocal buffer
        if not buffer:
            return
        content = "\n\n".join(block.text for block in buffer).strip()
        section = _dominant_section(buffer)
        heading = next(
            (
                block.heading
                for block in reversed(buffer)
                if block.heading and block.section_guess == section
            ),
            next(
                (
                    block.heading
                    for block in reversed(buffer)
                    if block.heading
                ),
                None,
            ),
        )
        chunks.append(
            Chunk(
                id=f"{document_id}-{len(chunks) + 1:05d}",
                page_start=buffer[0].page,
                page_end=buffer[-1].page,
                heading=heading,
                text=content,
                token_estimate=estimate_tokens(content),
                section_guess=section,
                recommendation_type_guess=guess_recommendation_type(
                    section, content
                ),
                population=guess_population(content),
                care_level=guess_care_level(content),
                urgency=guess_urgency(content),
            )
        )
        buffer = _overlap_blocks(buffer, overlap_tokens) if preserve_overlap else []

    for source_block in _paragraph_blocks(pages):
        for block in _split_oversized_block(source_block, max_tokens):
            if (
                buffer
                and block.section_guess != _dominant_section(buffer)
                and _block_tokens(buffer) >= min_tokens
            ):
                flush(preserve_overlap=False)

            projected = "\n\n".join([*(item.text for item in buffer), block.text])
            if buffer and estimate_tokens(projected) > max_tokens:
                flush(preserve_overlap=True)
                projected = "\n\n".join(
                    [*(item.text for item in buffer), block.text]
                )
                if buffer and estimate_tokens(projected) > max_tokens:
                    flush(preserve_overlap=False)
            buffer.append(block)

    flush(preserve_overlap=False)
    return _merge_small_chunks(
        document_id,
        chunks,
        min_tokens=min_tokens,
        max_tokens=max_tokens,
    )
