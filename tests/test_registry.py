"""Testes do módulo core.registry (histórico em CSV)."""

from __future__ import annotations

from pathlib import Path

from tts_project.core.models import Quality, SynthesisParameters, SynthesisRecord
from tts_project.core.registry import AudioRegistry


def _make_record(tmp_path: Path, text: str = "olá mundo") -> SynthesisRecord:
    return SynthesisRecord(
        parameters=SynthesisParameters(quality=Quality.LOW, language="pt-BR"),
        source_text_preview=AudioRegistry.build_preview(text),
        source_characters=len(text),
        detected_language="pt-BR",
        audio_path=tmp_path / "out.mp3",
    )


def test_creates_csv_with_header_on_init(tmp_path: Path) -> None:
    csv_path = tmp_path / "registry.csv"
    AudioRegistry(csv_path)

    assert csv_path.exists()
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == SynthesisRecord.csv_fieldnames()


def test_add_appends_row(tmp_path: Path) -> None:
    registry = AudioRegistry(tmp_path / "registry.csv")
    record = _make_record(tmp_path)

    registry.add(record)
    rows = registry.all_rows()

    assert len(rows) == 1
    assert rows[0]["id"] == record.record_id
    assert rows[0]["detected_language"] == "pt-BR"


def test_add_multiple_rows_preserves_order(tmp_path: Path) -> None:
    registry = AudioRegistry(tmp_path / "registry.csv")
    first = _make_record(tmp_path, "primeiro texto")
    second = _make_record(tmp_path, "segundo texto")

    registry.add(first)
    registry.add(second)
    rows = registry.all_rows()

    assert [row["id"] for row in rows] == [first.record_id, second.record_id]


def test_build_preview_truncates_long_text() -> None:
    long_text = "a" * 500
    preview = AudioRegistry.build_preview(long_text)

    assert len(preview) <= 123  # 120 + "..."
    assert preview.endswith("...")


def test_build_preview_keeps_short_text_untouched() -> None:
    assert AudioRegistry.build_preview("texto curto") == "texto curto"
