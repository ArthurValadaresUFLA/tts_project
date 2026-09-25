"""Identificação de idioma.

Implementa o padrão *Strategy*: :class:`LanguageIdentifier` define a
interface e duas estratégias concretas são fornecidas.

Nota de design
---------------
O Whisper é um modelo de *reconhecimento de fala* (ASR): ele identifica
idioma a partir de **áudio**, não de texto puro. Por isso este projeto
usa duas estratégias complementares:

* :class:`TextLanguageIdentifier` — rápida, roda sobre o texto de
  entrada usando ``langdetect``. É a estratégia padrão.
* :class:`WhisperAudioLanguageIdentifier` — mais pesada: sintetiza uma
  pequena amostra do texto e roda o Whisper sobre o áudio resultante
  para *confirmar* o idioma detectado. É usada como uma verificação
  extra quando ``quality=HIGH`` e a identificação automática está
  ligada, atendendo ao requisito de um "modelo mais forte e pesado
  para identificar" o idioma.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from langdetect import LangDetectException, detect

from tts_project.core.exceptions import LanguageIdentificationError

logger = logging.getLogger(__name__)


class LanguageIdentifier(Protocol):
    """Interface comum a todas as estratégias de identificação de idioma."""

    def identify(self, text: str) -> str:
        """Retorna o código de idioma identificado a partir do texto."""
        ...


class TextLanguageIdentifier:
    """Identifica o idioma diretamente a partir do texto (``langdetect``)."""

    def identify(self, text: str) -> str:
        """Detecta o idioma do texto.

        Args:
            text: Texto de entrada.

        Returns:
            Código de idioma no formato do ``langdetect`` (ex.: ``pt``, ``en``).

        Raises:
            LanguageIdentificationError: Se o texto for vazio demais para
                que o detector consiga inferir um idioma.
        """
        try:
            return detect(text)
        except LangDetectException as exc:
            raise LanguageIdentificationError(
                "Não foi possível identificar o idioma do texto informado."
            ) from exc


class WhisperAudioLanguageIdentifier:
    """Confirma o idioma sintetizando uma amostra e rodando o Whisper nela.

    Esta estratégia é deliberadamente mais lenta e pesada: carrega um
    modelo Whisper (ex.: ``base``/``small``) e roda inferência sobre
    áudio. É pensada para o modo de qualidade alta, onde vale o custo
    extra em troca de maior confiança na detecção.
    """

    def __init__(self, model_name: str = "base") -> None:
        self._model_name = model_name
        self._model = None  # carregado sob demanda (lazy loading)

    def _load_model(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            import whisper  # import tardio: dependência pesada

            logger.info("Carregando modelo Whisper '%s'...", self._model_name)
            self._model = whisper.load_model(self._model_name)
        return self._model

    def identify_from_audio(self, audio_path: Path) -> str:
        """Detecta o idioma falado em um arquivo de áudio.

        Args:
            audio_path: Caminho de um arquivo de áudio (ex.: ``.wav``/``.mp3``).

        Returns:
            Código de idioma (ex.: ``pt``, ``en``) segundo o Whisper.

        Raises:
            LanguageIdentificationError: Se a inferência falhar.
        """
        try:
            import whisper

            model = self._load_model()
            audio = whisper.load_audio(str(audio_path))
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            _, probs = model.detect_language(mel)
            return max(probs, key=probs.get)
        except Exception as exc:  # pragma: no cover - depende de peso/IO real
            raise LanguageIdentificationError(
                f"Falha ao identificar idioma via Whisper: {exc}"
            ) from exc
