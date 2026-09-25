"""Configuração centralizada do projeto.

Todos os caminhos de dados (áudios gerados e o registro em CSV) são
resolvidos a partir de variáveis de ambiente, para que o ``Dockerfile``
(ou qualquer outro ambiente de execução) possa determinar onde os
arquivos ficam armazenados sem precisar alterar código.

Este módulo implementa um Singleton simples via ``functools.lru_cache``:
``get_settings()`` sempre retorna a mesma instância dentro do processo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Agrupa todos os caminhos e parâmetros configuráveis do projeto.

    Attributes:
        data_dir: Diretório raiz onde os dados persistentes ficam.
        audio_dir: Subdiretório onde os áudios sintetizados são salvos.
        registry_path: Caminho do CSV com o histórico de sintetizações.
        default_language: Idioma usado quando nenhum é informado e a
            identificação automática está desligada.
        whisper_model_name: Nome do modelo Whisper usado na identificação
            "pesada" de idioma (ex.: ``tiny``, ``base``, ``small``).
    """

    data_dir: Path
    audio_dir: Path
    registry_path: Path
    default_language: str
    whisper_model_name: str

    def ensure_directories(self) -> None:
        """Cria os diretórios de dados caso ainda não existam."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a configuração do projeto (instância única por processo).

    As variáveis de ambiente relevantes são:

    * ``TTS_DATA_DIR``: diretório raiz dos dados (padrão: ``./data``).
    * ``TTS_AUDIO_SUBDIR``: subpasta dos áudios (padrão: ``audio``).
    * ``TTS_REGISTRY_FILENAME``: nome do CSV de registro
      (padrão: ``registry.csv``).
    * ``TTS_DEFAULT_LANGUAGE``: idioma padrão (padrão: ``pt-BR``).
    * ``TTS_WHISPER_MODEL``: modelo do Whisper (padrão: ``base``).
    """
    data_dir = Path(os.environ.get("TTS_DATA_DIR", "./data")).resolve()
    audio_subdir = os.environ.get("TTS_AUDIO_SUBDIR", "audio")
    registry_filename = os.environ.get("TTS_REGISTRY_FILENAME", "registry.csv")

    settings = Settings(
        data_dir=data_dir,
        audio_dir=data_dir / audio_subdir,
        registry_path=data_dir / registry_filename,
        default_language=os.environ.get("TTS_DEFAULT_LANGUAGE", "pt-BR"),
        whisper_model_name=os.environ.get("TTS_WHISPER_MODEL", "base"),
    )
    settings.ensure_directories()
    return settings
