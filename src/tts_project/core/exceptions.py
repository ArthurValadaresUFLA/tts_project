"""Exceções específicas do domínio de síntese de voz."""

from __future__ import annotations


class TTSProjectError(Exception):
    """Classe base para todas as exceções do projeto."""


class UnsupportedFormatError(TTSProjectError):
    """Levantada quando a extensão do arquivo de saída não é suportada."""


class SynthesisError(TTSProjectError):
    """Levantada quando a síntese de voz falha."""


class EmptyInputError(TTSProjectError):
    """Levantada quando nenhum texto foi fornecido (arquivo, stdin ou campo)."""


class LanguageIdentificationError(TTSProjectError):
    """Levantada quando a identificação automática de idioma falha."""
