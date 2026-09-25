"""Testes do módulo core.synthesizer — apenas a lógica de seleção/validação,
nunca o conteúdo de áudio gerado por motores reais.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tts_project.core.exceptions import UnsupportedFormatError
from tts_project.core.models import Quality
from tts_project.core.synthesizer import (
    GTTSSynthesizer,
    Pyttsx3Synthesizer,
    SynthesizerFactory,
    validate_output_format,
)


def test_factory_returns_pyttsx3_for_low_quality() -> None:
    engine = SynthesizerFactory.create(Quality.LOW)
    assert isinstance(engine, Pyttsx3Synthesizer)


def test_factory_returns_gtts_for_high_quality() -> None:
    engine = SynthesizerFactory.create(Quality.HIGH)
    assert isinstance(engine, GTTSSynthesizer)


@pytest.mark.parametrize("suffix", [".mp3", ".wav", ".MP3"])
def test_validate_output_format_accepts_supported_formats(tmp_path: Path, suffix: str) -> None:
    validate_output_format(tmp_path / f"out{suffix}")  # não deve levantar


def test_validate_output_format_rejects_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFormatError):
        validate_output_format(tmp_path / "out.ogg")
