"""Rotas HTTP da aplicação web (Blueprint Flask).

Endpoints:
    ``GET  /``                    -> página HTML com a UI de síntese.
    ``POST /api/synthesize``      -> inicia um job de síntese, retorna job_id.
    ``GET  /api/status/<job_id>`` -> status/progresso do job.
    ``GET  /api/audio/<job_id>``  -> serve o áudio gerado (quando pronto).
"""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)
from flask.typing import ResponseReturnValue

from tts_project.core.exceptions import TTSProjectError
from tts_project.core.models import Quality, SynthesisParameters
from tts_project.web.jobs import JobManager, JobStatus

bp = Blueprint("web", __name__)

_ALLOWED_FORMATS = {"mp3", "wav"}


def _job_manager() -> JobManager:
    manager = current_app.extensions.get("job_manager")
    if manager is None:  # pragma: no cover - erro de configuração
        raise RuntimeError("JobManager não configurado na aplicação Flask.")
    return manager


@bp.get("/")
def index() -> str:
    """Renderiza a página principal (formulário + player de áudio)."""
    return render_template("index.html")


@bp.post("/api/synthesize")
def synthesize() -> ResponseReturnValue:
    """Recebe texto (campo ou arquivo) e opções, inicia um job em background."""
    text = request.form.get("text", "").strip()

    uploaded = request.files.get("text_file")
    if uploaded and uploaded.filename:
        text = uploaded.read().decode("utf-8").strip()

    if not text:
        return jsonify({"error": "Nenhum texto foi enviado."}), 400

    quality = request.form.get("quality", Quality.LOW.value)
    language = request.form.get("language") or None
    identify_language = request.form.get("identify_language") == "on"
    output_format = request.form.get("output_format", "mp3").lower()
    try:
        speed = float(request.form.get("speed", "1.0"))
    except ValueError:
        return jsonify({"error": "Velocidade inválida."}), 400

    if output_format not in _ALLOWED_FORMATS:
        return jsonify({"error": f"Formato '{output_format}' não suportado."}), 400

    try:
        parameters = SynthesisParameters(
            quality=Quality(quality),
            language=language,
            identify_language=identify_language,
            speed=speed,
        )
    except (ValueError, TTSProjectError) as exc:
        return jsonify({"error": str(exc)}), 400

    job_id = _job_manager().submit(text, parameters, output_format)
    return jsonify({"job_id": job_id}), 202


@bp.get("/api/status/<job_id>")
def status(job_id: str) -> ResponseReturnValue:
    """Retorna o status e o progresso (0-100) de um job."""
    job = _job_manager().get(job_id)
    if job is None:
        return jsonify({"error": "Job não encontrado."}), 404
    return jsonify(job.to_dict()), 200


@bp.get("/api/audio/<job_id>")
def audio(job_id: str) -> ResponseReturnValue:
    """Serve o arquivo de áudio de um job concluído."""
    job = _job_manager().get(job_id)
    if job is None:
        return jsonify({"error": "Job não encontrado."}), 404
    if job.status is not JobStatus.DONE or job.audio_path is None:
        return jsonify({"error": "Áudio ainda não está pronto."}), 409
    return send_file(job.audio_path, as_attachment=False)
