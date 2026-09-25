"""Modelos de dados (value objects) usados em todo o projeto.

Usar ``dataclasses`` mantém o projeto simples — sem depender de um
framework de validação extra — como pede o requisito de manter o
projeto apenas como "cola" entre ferramentas já existentes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path


class Quality(str, Enum):
    """Nível de qualidade/força do modelo de síntese.

    ``LOW`` usa um motor leve e totalmente offline (pyttsx3).
    ``HIGH`` usa um motor mais robusto, com voz mais natural (gTTS),
    mais pesado por depender de uma chamada de rede.
    """

    LOW = "low"
    HIGH = "high"


@dataclass(frozen=True)
class SynthesisParameters:
    """Parâmetros que controlam uma síntese de voz.

    Attributes:
        quality: Nível de qualidade do modelo (:class:`Quality`).
        language: Código do idioma (ex.: ``pt-BR``, ``en``). Pode ser
            ``None`` quando ``identify_language`` é ``True``.
        identify_language: Se ``True``, o idioma deve ser detectado
            automaticamente a partir do texto (e, opcionalmente,
            confirmado via Whisper quando ``quality`` é ``HIGH``).
        speed: Fator de velocidade da fala (1.0 = velocidade normal).
    """

    quality: Quality = Quality.LOW
    language: str | None = None
    identify_language: bool = False
    speed: float = 1.0

    def __post_init__(self) -> None:
        if self.speed <= 0:
            raise ValueError("speed deve ser um número positivo")


@dataclass(frozen=True)
class SynthesisRecord:
    """Registro de uma sintetização, persistido no CSV de histórico.

    Attributes:
        record_id: Identificador único (UUID4) da sintetização.
        created_at: Momento (UTC) em que a sintetização foi concluída.
        source_text_preview: Trecho inicial do texto original (para o
            CSV não crescer sem controle com textos longos).
        source_characters: Número total de caracteres do texto original.
        parameters: Parâmetros usados na síntese.
        detected_language: Idioma efetivamente usado (informado ou
            detectado automaticamente).
        audio_path: Caminho do arquivo de áudio gerado.
    """

    parameters: SynthesisParameters
    source_text_preview: str
    source_characters: int
    detected_language: str
    audio_path: Path
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_csv_row(self) -> dict[str, str]:
        """Converte o registro em um dicionário pronto para ``csv.DictWriter``."""
        return {
            "id": self.record_id,
            "created_at": self.created_at.isoformat(),
            "source_text_preview": self.source_text_preview,
            "source_characters": str(self.source_characters),
            "quality": self.parameters.quality.value,
            "requested_language": self.parameters.language or "",
            "identify_language": str(self.parameters.identify_language),
            "speed": str(self.parameters.speed),
            "detected_language": self.detected_language,
            "audio_path": str(self.audio_path),
        }

    @staticmethod
    def csv_fieldnames() -> list[str]:
        """Retorna a ordem das colunas usadas no CSV de registro."""
        return [
            "id",
            "created_at",
            "source_text_preview",
            "source_characters",
            "quality",
            "requested_language",
            "identify_language",
            "speed",
            "detected_language",
            "audio_path",
        ]
