from __future__ import annotations

import unicodedata


def _normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )


def evaluate_query_safety(query: str) -> list[str]:
    value = _normalize(query)
    flags: list[str] = []
    groups = {
        "possible_acute_coronary_syndrome": [
            "dolor toracico",
            "dolor precordial",
            "angina",
        ],
        "possible_suicide_risk": [
            "suicidio",
            "quiere morir",
            "hacerse dano",
        ],
        "possible_obstetric_emergency": [
            "gestante con cefalea",
            "embarazo con sangrado",
            "embarazo con fosfenos",
        ],
    }
    for flag, patterns in groups.items():
        if any(pattern in value for pattern in patterns):
            flags.append(flag)
    return flags

