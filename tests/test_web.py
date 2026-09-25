"""Testes da aplicação Flask, usando um TTSService com sintetizador falso."""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from tts_project.core.models import Quality
from tts_project.core.service import TTSService
from tts_project.web.jobs import JobManager
from tts_project.web.routes import bp

from .conftest import FakeSynthesizer, FakeTextLanguageIdentifier


@pytest.fixture
def app(settings, registry) -> Flask:
    settings.ensure_directories()
    service = TTSService(
        settings=settings,
        text_identifier=FakeTextLanguageIdentifier(),
        registry=registry,
        synthesizer_factory=lambda quality: FakeSynthesizer(),
    )
    flask_app = Flask(__name__, template_folder=_templates_dir())
    flask_app.extensions["job_manager"] = JobManager(
        service=service, audio_dir=settings.audio_dir
    )
    flask_app.register_blueprint(bp)
    flask_app.testing = True
    return flask_app


def _templates_dir() -> str:
    from tts_project.web import app as web_app_module

    return str(Path(web_app_module.__file__).parent / "templates")


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def test_index_page_loads(client: FlaskClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"TTS Project" in response.data


def test_synthesize_rejects_empty_text(client: FlaskClient) -> None:
    response = client.post("/api/synthesize", data={"text": ""})
    assert response.status_code == 400


def test_synthesize_job_completes_successfully(client: FlaskClient) -> None:
    response = client.post(
        "/api/synthesize",
        data={
            "text": "olá mundo",
            "quality": Quality.LOW.value,
            "language": "pt-BR",
            "output_format": "mp3",
            "speed": "1.0",
        },
    )
    assert response.status_code == 202
    job_id = response.get_json()["job_id"]

    # A síntese roda em thread separada; aguarda concluir usando o próprio
    # endpoint de status (o FakeSynthesizer é instantâneo, então poucas
    # tentativas bastam).
    import time

    for _ in range(50):
        status_response = client.get(f"/api/status/{job_id}")
        data = status_response.get_json()
        if data["status"] == "done":
            break
        time.sleep(0.05)

    assert data["status"] == "done"

    audio_response = client.get(f"/api/audio/{job_id}")
    assert audio_response.status_code == 200


def test_status_returns_404_for_unknown_job(client: FlaskClient) -> None:
    response = client.get("/api/status/does-not-exist")
    assert response.status_code == 404
