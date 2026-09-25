"""Fixtures compartilhadas entre os testes.

Nenhum teste toca engines reais de TTS (pyttsx3/gTTS) ou o Whisper —
conforme exigido, o *conteúdo* do áudio nunca é testado. Usamos dublês
(fakes) que apenas gravam um arquivo vazio para simular a saída.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tts_project.core.config import Settings
from tts_project.core.models import Quality, SynthesisParameters
from tts_project.core.registry import AudioRegistry
from tts_project.core.service import TTSService


class FakeSynthesizer:
    """Sintetizador falso: apenas cria um arquivo vazio no destino."""

    def synthesize(self, text: str, language: str, speed: float, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"")
        return output_path


class FakeTextLanguageIdentifier:
    """Identificador de idioma falso e determinístico."""

    def __init__(self, language: str = "en") -> None:
        self.language = language

    def identify(self, text: str) -> str:
        return self.language


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        audio_dir=data_dir / "audio",
        registry_path=data_dir / "registry.csv",
        default_language="pt-BR",
        whisper_model_name="base",
    )


@pytest.fixture
def registry(settings: Settings) -> AudioRegistry:
    settings.ensure_directories()
    return AudioRegistry(settings.registry_path)


@pytest.fixture
def service(settings: Settings, registry: AudioRegistry) -> TTSService:
    """TTSService com identificador de idioma e sintetizador falsos.

    Nenhum motor real de TTS é chamado: `synthesizer_factory` sempre
    retorna um `FakeSynthesizer`, que apenas grava um arquivo vazio.
    """
    settings.ensure_directories()
    return TTSService(
        settings=settings,
        text_identifier=FakeTextLanguageIdentifier(),
        registry=registry,
        synthesizer_factory=lambda quality: FakeSynthesizer(),
    )


@pytest.fixture
def default_parameters() -> SynthesisParameters:
    return SynthesisParameters(quality=Quality.LOW)
