"""Testes da CLI (click), usando CliRunner e um TTSService falso."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from tts_project.cli.main import cli
from tts_project.core.service import SynthesisResult


class FakeService:
    """Substitui TTSService nos testes de CLI: não sintetiza áudio de verdade."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def synthesize(self, text, output_path, parameters, progress_callback=None):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"")
        if progress_callback:
            for value in (25, 50, 100):
                progress_callback(value)
        from tts_project.core.models import SynthesisRecord

        record = SynthesisRecord(
            parameters=parameters,
            source_text_preview=text[:20],
            source_characters=len(text),
            detected_language=parameters.language or "pt-BR",
            audio_path=output_path,
        )
        return SynthesisResult(
            audio_path=output_path,
            detected_language=record.detected_language,
            record=record,
        )


@pytest.fixture(autouse=True)
def _patch_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tts_project.cli.main.TTSService", FakeService)


def test_synthesize_from_file(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("olá mundo", encoding="utf-8")
    output_path = tmp_path / "output.mp3"

    runner = CliRunner()
    result = runner.invoke(cli, ["synthesize", str(input_path), str(output_path)])

    assert result.exit_code == 0
    assert output_path.exists()
    assert "Áudio gerado" in result.output


def test_synthesize_from_stdin(tmp_path: Path) -> None:
    output_path = tmp_path / "output.wav"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["synthesize", "-", str(output_path)],
        input="texto vindo do stdin",
    )

    assert result.exit_code == 0
    assert output_path.exists()


def test_synthesize_with_options(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello world", encoding="utf-8")
    output_path = tmp_path / "output.mp3"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "synthesize",
            str(input_path),
            str(output_path),
            "--quality",
            "high",
            "--language",
            "en",
            "--speed",
            "1.5",
        ],
    )

    assert result.exit_code == 0
    assert "idioma: en" in result.output


def test_synthesize_rejects_invalid_quality(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("texto", encoding="utf-8")
    output_path = tmp_path / "output.mp3"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["synthesize", str(input_path), str(output_path), "--quality", "ultra"],
    )

    assert result.exit_code != 0
