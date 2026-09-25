"""Interface de linha de comando do projeto (baseada em ``click``).

Exemplos:
    Ler de um arquivo e gerar um mp3 com qualidade alta::

        tts synthesize texto.txt saida.mp3 --quality high --language en

    Ler do stdin (pipeline) e deixar o idioma ser detectado::

        cat texto.txt | tts synthesize - saida.wav --identify-language

    Sem informar idioma nem pedir identificação -> usa o fallback pt-BR::

        tts synthesize texto.txt saida.mp3
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import click.decorators

from tts_project.core.exceptions import TTSProjectError
from tts_project.core.models import Quality, SynthesisParameters
from tts_project.core.service import TTSService


@click.group()
@click.version_option(package_name="tts-project")
def cli() -> None:
    """Ferramenta de linha de comando para síntese de texto em voz (TTS)."""


@cli.command()
@click.argument("input_file", type=click.File("r", encoding="utf-8"), default="-")
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--quality",
    "-q",
    type=click.Choice([q.value for q in Quality]),
    default=Quality.LOW.value,
    show_default=True,
    help="Nível de qualidade do modelo de síntese ('low' = leve/offline, "
    "'high' = mais forte/natural, requer internet).",
)
@click.option(
    "--language",
    "-l",
    default=None,
    help="Idioma de entrada (ex.: pt-BR, en, es). Se omitido, usa pt-BR "
    "como fallback, a menos que --identify-language seja usado.",
)
@click.option(
    "--identify-language",
    "-i",
    is_flag=True,
    default=False,
    help="Detecta automaticamente o idioma do texto em vez de usar "
    "--language ou o fallback pt-BR. Em conjunto com --quality high, "
    "a detecção é confirmada com o Whisper sobre uma amostra sintetizada.",
)
@click.option(
    "--speed",
    "-s",
    type=float,
    default=1.0,
    show_default=True,
    help="Fator de velocidade da fala (1.0 = normal).",
)
def synthesize(
    input_file: click.utils.LazyFile,
    output_file: Path,
    quality: str,
    language: str | None,
    identify_language: bool,
    speed: float,
) -> None:
    """Sintetiza o texto de INPUT_FILE (ou stdin, com '-') em OUTPUT_FILE.

    O formato do áudio de saída é inferido pela extensão de OUTPUT_FILE
    (``.mp3`` ou ``.wav``).
    """
    text = input_file.read()

    parameters = SynthesisParameters(
        quality=Quality(quality),
        language=language,
        identify_language=identify_language,
        speed=speed,
    )

    service = TTSService()

    try:
        with click.progressbar(range(100), label="Sintetizando áudio") as bar:
            last_value = 0

            def on_progress(value: int) -> None:
                nonlocal last_value
                bar.update(value - last_value)
                last_value = value

            result = service.synthesize(
                text=text,
                output_path=output_file,
                parameters=parameters,
                progress_callback=on_progress,
            )
    except TTSProjectError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Áudio gerado em '{result.audio_path}' (idioma: {result.detected_language}).")


def main() -> int:
    """Ponto de entrada usado pelo script instalado (``tts``)."""
    cli(prog_name="tts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
