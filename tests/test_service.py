"""Testes do TTSService (Facade), usando dublês de sintetizador e identificador."""

from __future__ import annotations

from pathlib import Path

import pytest

from tts_project.core.exceptions import EmptyInputError, UnsupportedFormatError
from tts_project.core.models import Quality, SynthesisParameters
from tts_project.core.service import TTSService


def test_synthesize_creates_audio_file_and_record(
    service: TTSService, settings, tmp_path: Path
) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW, language="pt-BR")

    result = service.synthesize("olá mundo", output_path, params)

    assert result.audio_path.exists()
    assert result.detected_language == "pt-BR"
    rows = service._registry.all_rows()
    assert len(rows) == 1
    assert rows[0]["detected_language"] == "pt-BR"


def test_synthesize_uses_explicit_language_over_detection(
    service: TTSService, settings
) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW, language="es", identify_language=True)

    result = service.synthesize("hello there", output_path, params)

    assert result.detected_language == "es"


def test_synthesize_falls_back_to_default_language(service: TTSService, settings) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW)  # sem language, sem identify

    result = service.synthesize("hello there", output_path, params)

    assert result.detected_language == settings.default_language


def test_synthesize_uses_identifier_when_requested(service: TTSService, settings) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW, identify_language=True)

    result = service.synthesize("hello there", output_path, params)

    # FakeTextLanguageIdentifier (ver conftest) sempre retorna "en"
    assert result.detected_language == "en"


def test_synthesize_raises_on_empty_text(service: TTSService, settings) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW)

    with pytest.raises(EmptyInputError):
        service.synthesize("   ", output_path, params)


def test_synthesize_raises_on_unsupported_format(service: TTSService, settings) -> None:
    output_path = settings.audio_dir / "out.ogg"
    params = SynthesisParameters(quality=Quality.LOW)

    with pytest.raises(UnsupportedFormatError):
        service.synthesize("texto", output_path, params)


def test_synthesize_reports_progress(service: TTSService, settings) -> None:
    output_path = settings.audio_dir / "out.mp3"
    params = SynthesisParameters(quality=Quality.LOW, language="pt-BR")
    reported: list[int] = []

    service.synthesize("olá", output_path, params, progress_callback=reported.append)

    assert reported[0] < reported[-1]
    assert reported[-1] == 100
