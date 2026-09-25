"""Motores de síntese de voz (padrões *Strategy* + *Factory*).

Cada motor concreto encapsula uma biblioteca de terceiros diferente,
mantendo o projeto como "cola" fina entre ferramentas já existentes:

* :class:`Pyttsx3Synthesizer` — offline, leve, usado como o modelo
  "low" (rápido, porém mais robótico).
* :class:`GTTSSynthesizer` — usa a API do Google (via ``gTTS``),
  produz voz mais natural; usado como o modelo "high".

:class:`SynthesizerFactory` decide qual estratégia instanciar a partir
de :class:`~tts_project.core.models.Quality`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tts_project.core.exceptions import SynthesisError
from tts_project.core.models import Quality

SUPPORTED_FORMATS = {".mp3", ".wav"}


class Synthesizer(Protocol):
    """Interface comum a todo motor de síntese de voz."""

    def synthesize(self, text: str, language: str, speed: float, output_path: Path) -> Path:
        """Sintetiza ``text`` em ``language`` e grava o áudio em ``output_path``."""
        ...


class Pyttsx3Synthesizer:
    """Motor leve e offline, baseado em ``pyttsx3``.

    Usa a engine de TTS nativa do sistema operacional através do
    ``pyttsx3``. Não requer conexão com a internet.
    """

    def synthesize(self, text: str, language: str, speed: float, output_path: Path) -> Path:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            base_rate = engine.getProperty("rate")
            engine.setProperty("rate", int(base_rate * speed))

            for voice in engine.getProperty("voices"):
                voice_languages = getattr(voice, "languages", [])
                if any(language.split("-")[0] in str(lang) for lang in voice_languages):
                    engine.setProperty("voice", voice.id)
                    break

            output_path.parent.mkdir(parents=True, exist_ok=True)
            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
            return output_path
        except Exception as exc:  # pragma: no cover - depende de engine do SO
            raise SynthesisError(f"Falha no motor pyttsx3: {exc}") from exc


class GTTSSynthesizer:
    """Motor de qualidade mais alta, baseado no Google Text-to-Speech.

    Requer acesso à internet. A "velocidade" do ``gTTS`` é limitada a
    normal/lenta; valores de ``speed`` abaixo de 1.0 ativam o modo lento.
    """

    def synthesize(self, text: str, language: str, speed: float, output_path: Path) -> Path:
        try:
            from gtts import gTTS

            lang_code = language.split("-")[0]
            tts = gTTS(text=text, lang=lang_code, slow=speed < 1.0)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tts.save(str(output_path))
            return output_path
        except Exception as exc:  # pragma: no cover - depende de rede
            raise SynthesisError(f"Falha no motor gTTS: {exc}") from exc


class SynthesizerFactory:
    """Fábrica que escolhe o motor de síntese de acordo com a qualidade."""

    _registry: dict[Quality, type] = {
        Quality.LOW: Pyttsx3Synthesizer,
        Quality.HIGH: GTTSSynthesizer,
    }

    @classmethod
    def create(cls, quality: Quality) -> Synthesizer:
        """Instancia o motor de síntese associado à qualidade informada."""
        engine_cls = cls._registry.get(quality)
        if engine_cls is None:  # pragma: no cover - defensivo
            raise SynthesisError(f"Qualidade não suportada: {quality}")
        return engine_cls()


def validate_output_format(output_path: Path) -> None:
    """Garante que a extensão do arquivo de saída é suportada.

    Raises:
        UnsupportedFormatError: Se a extensão não estiver em
            :data:`SUPPORTED_FORMATS`.
    """
    from tts_project.core.exceptions import UnsupportedFormatError

    if output_path.suffix.lower() not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Formato '{output_path.suffix}' não suportado. "
            f"Use um dos seguintes: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
