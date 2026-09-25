"""Registro (histórico) das sintetizações realizadas.

Cada síntese de áudio gera uma linha em um arquivo CSV contendo o texto
original (resumido), os parâmetros usados e o caminho do áudio gerado,
conforme exigido pelo projeto.
"""

from __future__ import annotations

import csv
import threading
from pathlib import Path

from tts_project.core.models import SynthesisRecord

_PREVIEW_LENGTH = 120


class AudioRegistry:
    """Persiste :class:`SynthesisRecord` em um arquivo CSV.

    A escrita é protegida por um *lock* para permitir uso seguro a
    partir de múltiplas threads (o servidor web processa sintetizações
    em segundo plano).
    """

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._lock = threading.Lock()
        self._ensure_header()

    @property
    def csv_path(self) -> Path:
        """Caminho do arquivo CSV de registro."""
        return self._csv_path

    def _ensure_header(self) -> None:
        if not self._csv_path.exists():
            self._csv_path.parent.mkdir(parents=True, exist_ok=True)
            with self._csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=SynthesisRecord.csv_fieldnames())
                writer.writeheader()

    def add(self, record: SynthesisRecord) -> None:
        """Adiciona um novo registro ao CSV."""
        with self._lock:
            with self._csv_path.open("a", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=SynthesisRecord.csv_fieldnames())
                writer.writerow(record.to_csv_row())

    def all_rows(self) -> list[dict[str, str]]:
        """Lê e retorna todas as linhas já registradas."""
        if not self._csv_path.exists():
            return []
        with self._csv_path.open("r", newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    @staticmethod
    def build_preview(text: str) -> str:
        """Trunca o texto para um resumo curto, usado na coluna de preview."""
        cleaned = " ".join(text.split())
        if len(cleaned) <= _PREVIEW_LENGTH:
            return cleaned
        return cleaned[:_PREVIEW_LENGTH].rstrip() + "..."
