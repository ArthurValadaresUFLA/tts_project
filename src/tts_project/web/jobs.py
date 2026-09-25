"""Gerenciamento de jobs assíncronos de síntese para a aplicação web.

O Flask (em modo de desenvolvimento/simples, sem fila externa como
Celery/Redis) atende cada requisição de forma síncrona; para que a
página possa mostrar uma barra de progresso enquanto o áudio é gerado,
cada sintetização roda em uma *thread* separada e seu estado fica
disponível em memória através de :class:`JobManager`.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from tts_project.core.exceptions import TTSProjectError
from tts_project.core.models import SynthesisParameters
from tts_project.core.service import TTSService


class JobStatus(str, Enum):
    """Estado do ciclo de vida de um job de síntese."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    """Estado de um job de síntese em andamento ou concluído."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    audio_path: Path | None = None
    detected_language: str | None = None
    error_message: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def to_dict(self) -> dict[str, object]:
        """Representação serializável do job, pronta para JSON."""
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.status.value,
                "progress": self.progress,
                "detected_language": self.detected_language,
                "error_message": self.error_message,
            }


class JobManager:
    """Cria e acompanha jobs de síntese executados em background.

    Args:
        service: Instância de :class:`TTSService` usada para realizar
            a síntese de fato.
        audio_dir: Diretório onde os áudios gerados pelos jobs são salvos.
    """

    def __init__(self, service: TTSService, audio_dir: Path) -> None:
        self._service = service
        self._audio_dir = audio_dir
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def submit(self, text: str, parameters: SynthesisParameters, output_format: str) -> str:
        """Cria um job e inicia a síntese em uma thread separada.

        Args:
            text: Texto a ser sintetizado.
            parameters: Parâmetros da síntese.
            output_format: Extensão desejada, sem o ponto (ex.: ``mp3``).

        Returns:
            O identificador (``job_id``) do job criado.
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = job

        output_path = self._audio_dir / f"{job_id}.{output_format.lstrip('.')}"

        thread = threading.Thread(
            target=self._run,
            args=(job, text, output_path, parameters),
            daemon=True,
        )
        thread.start()
        return job_id

    def get(self, job_id: str) -> Job | None:
        """Retorna o job pelo id, ou ``None`` se não existir."""
        with self._lock:
            return self._jobs.get(job_id)

    def _run(
        self,
        job: Job,
        text: str,
        output_path: Path,
        parameters: SynthesisParameters,
    ) -> None:
        job.status = JobStatus.RUNNING

        def on_progress(value: int) -> None:
            job.progress = value

        try:
            result = self._service.synthesize(
                text=text,
                output_path=output_path,
                parameters=parameters,
                progress_callback=on_progress,
            )
            job.audio_path = result.audio_path
            job.detected_language = result.detected_language
            job.progress = 100
            job.status = JobStatus.DONE
        except TTSProjectError as exc:
            job.status = JobStatus.ERROR
            job.error_message = str(exc)
        except Exception as exc:  # pragma: no cover - defensivo
            job.status = JobStatus.ERROR
            job.error_message = f"Erro inesperado: {exc}"
