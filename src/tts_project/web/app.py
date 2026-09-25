"""Application factory da aplicação Flask.

Uso::

    from tts_project.web.app import create_app
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
"""

from __future__ import annotations

from flask import Flask

from tts_project.core.config import get_settings
from tts_project.core.service import TTSService
from tts_project.web.jobs import JobManager
from tts_project.web.routes import bp


def create_app() -> Flask:
    """Cria e configura a aplicação Flask (padrão *Application Factory*)."""
    app = Flask(__name__)

    settings = get_settings()
    service = TTSService(settings=settings)
    job_manager = JobManager(service=service, audio_dir=settings.audio_dir)

    # Guardamos dependências compartilhadas em app.extensions, o local
    # convencional do Flask para isso (evita globais no módulo de rotas).
    app.extensions["job_manager"] = job_manager

    app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
