"""Serviço de alto nível (padrão *Facade*).

:class:`TTSService` é o único ponto de entrada usado tanto pela CLI
quanto pela aplicação web, evitando duplicação de lógica entre as duas
interfaces. Ele injeta suas dependências (fábrica de sintetizadores,
identificador de idioma e registro), o que facilita testes com dublês
(*mocks*/*fakes*).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tts_project.core.config import Settings, get_settings
from tts_project.core.exceptions import EmptyInputError
from tts_project.core.language import (
    LanguageIdentifier,
    TextLanguageIdentifier,
    WhisperAudioLanguageIdentifier,
)
from tts_project.core.models import Quality, SynthesisParameters, SynthesisRecord
from tts_project.core.registry import AudioRegistry
from tts_project.core.synthesizer import (
    Synthesizer,
    SynthesizerFactory,
    validate_output_format,
)

logger = logging.getLogger(__name__)

# Callback opcional de progresso: recebe um valor de 0 a 100.
ProgressCallback = Callable[[int], None]


@dataclass
class SynthesisResult:
    """Resultado de uma chamada a :meth:`TTSService.synthesize`."""

    audio_path: Path
    detected_language: str
    record: SynthesisRecord


class TTSService:
    """Orquestra identificação de idioma, síntese de voz e registro.

    Args:
        settings: Configuração do projeto (caminhos de dados). Usa
            :func:`get_settings` por padrão.
        text_identifier: Estratégia de identificação de idioma a partir
            do texto. Usa :class:`TextLanguageIdentifier` por padrão.
        whisper_identifier_factory: Fábrica (lazy) do identificador
            baseado em Whisper, usado apenas quando ``quality=HIGH`` e
            a identificação automática está ligada.
        registry: Registro em CSV. Criado automaticamente a partir de
            ``settings`` por padrão.
        synthesizer_factory: Função que, dada uma :class:`Quality`,
            retorna um :class:`Synthesizer`. Usa
            :meth:`SynthesizerFactory.create` por padrão; pode ser
            substituída em testes para evitar motores reais de TTS.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        text_identifier: LanguageIdentifier | None = None,
        whisper_identifier_factory: Callable[[], WhisperAudioLanguageIdentifier] | None = None,
        registry: AudioRegistry | None = None,
        synthesizer_factory: Callable[[Quality], Synthesizer] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._text_identifier = text_identifier or TextLanguageIdentifier()
        self._whisper_identifier_factory = whisper_identifier_factory or (
            lambda: WhisperAudioLanguageIdentifier(self._settings.whisper_model_name)
        )
        self._registry = registry or AudioRegistry(self._settings.registry_path)
        self._synthesizer_factory = synthesizer_factory or SynthesizerFactory.create

    def synthesize(
        self,
        text: str,
        output_path: Path,
        parameters: SynthesisParameters,
        progress_callback: ProgressCallback | None = None,
    ) -> SynthesisResult:
        """Executa o fluxo completo de síntese de voz.

        Args:
            text: Texto a ser convertido em áudio.
            output_path: Caminho do arquivo de áudio de saída.
            parameters: Parâmetros da síntese (qualidade, idioma, etc.).
            progress_callback: Chamado com valores 0-100 conforme o
                processamento avança (opcional; usado pela interface web).

        Returns:
            :class:`SynthesisResult` com o caminho do áudio, o idioma
            efetivamente usado e o registro persistido.

        Raises:
            EmptyInputError: Se ``text`` estiver vazio.
            UnsupportedFormatError: Se a extensão de ``output_path`` não
                for suportada.
            SynthesisError: Se a síntese falhar.
        """
        text = text.strip()
        if not text:
            raise EmptyInputError("O texto de entrada está vazio.")

        validate_output_format(output_path)
        self._report(progress_callback, 5)

        language = self._resolve_language(text, parameters)
        self._report(progress_callback, 30)

        synthesizer = self._synthesizer_factory(parameters.quality)
        synthesizer.synthesize(
            text=text,
            language=language,
            speed=parameters.speed,
            output_path=output_path,
        )
        self._report(progress_callback, 85)

        record = SynthesisRecord(
            parameters=parameters,
            source_text_preview=AudioRegistry.build_preview(text),
            source_characters=len(text),
            detected_language=language,
            audio_path=output_path,
        )
        self._registry.add(record)
        self._report(progress_callback, 100)

        return SynthesisResult(
            audio_path=output_path, detected_language=language, record=record
        )

    def _resolve_language(self, text: str, parameters: SynthesisParameters) -> str:
        """Decide qual idioma usar, seguindo a regra de precedência do projeto.

        1. Idioma explicitamente informado -> usado diretamente.
        2. ``identify_language=True`` -> detecta a partir do texto e,
           se ``quality=HIGH``, confirma sintetizando uma amostra e
           rodando o Whisper sobre ela.
        3. Nenhum dos dois -> usa o idioma padrão (fallback ``pt-BR``).
        """
        if parameters.language:
            return parameters.language

        if not parameters.identify_language:
            return self._settings.default_language

        detected = self._text_identifier.identify(text)

        if parameters.quality is Quality.HIGH:
            detected = self._confirm_with_whisper(text, detected)

        return detected

    def _confirm_with_whisper(self, text: str, fallback_language: str) -> str:
        """Confirma o idioma sintetizando uma amostra curta e usando Whisper."""
        import tempfile

        sample_text = text[:200]
        identifier = self._whisper_identifier_factory()
        synthesizer = self._synthesizer_factory(Quality.LOW)

        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_path = Path(tmp_dir) / "sample.wav"
            try:
                synthesizer.synthesize(
                    text=sample_text,
                    language=fallback_language,
                    speed=1.0,
                    output_path=sample_path,
                )
                return identifier.identify_from_audio(sample_path)
            except Exception:  # pragma: no cover - fallback defensivo
                logger.warning(
                    "Confirmação via Whisper falhou; mantendo idioma detectado "
                    "pelo texto ('%s').",
                    fallback_language,
                )
                return fallback_language

    @staticmethod
    def _report(callback: ProgressCallback | None, value: int) -> None:
        if callback is not None:
            callback(value)
