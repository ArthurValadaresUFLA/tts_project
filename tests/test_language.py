"""Testes do módulo core.language (sem tocar em áudio nem no Whisper)."""

from __future__ import annotations

import pytest

from tts_project.core.exceptions import LanguageIdentificationError
from tts_project.core.language import TextLanguageIdentifier


def test_identify_detects_portuguese() -> None:
    identifier = TextLanguageIdentifier()
    result = identifier.identify(
        "Este é um texto em português para teste de identificação de idioma."
    )
    assert result == "pt"


def test_identify_detects_english() -> None:
    identifier = TextLanguageIdentifier()
    result = identifier.identify(
        "This is an English sentence used to test language identification."
    )
    assert result == "en"


def test_identify_raises_on_empty_text() -> None:
    identifier = TextLanguageIdentifier()
    with pytest.raises(LanguageIdentificationError):
        identifier.identify("")
