# TTS Project

Ferramenta de conversão de texto em voz (Text-to-Speech) com duas
interfaces — linha de comando e aplicação web — construída como uma
**camada fina de integração ("cola")** entre bibliotecas Python já
existentes: [`pyttsx3`](https://pypi.org/project/pyttsx3/),
[`gTTS`](https://pypi.org/project/gTTS/),
[`langdetect`](https://pypi.org/project/langdetect/),
[`openai-whisper`](https://github.com/openai/whisper),
[`click`](https://click.palletsprojects.com/) e
[`Flask`](https://flask.palletsprojects.com/).

## Sumário

- [Arquitetura e design](#arquitetura-e-design)
- [Nota de design: por que Whisper em um projeto de TTS](#nota-de-design-por-que-whisper-em-um-projeto-de-tts)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Instalação e uso com `uv`](#instalação-e-uso-com-uv)
- [Uso da CLI](#uso-da-cli)
- [Uso da interface Web](#uso-da-interface-web)
- [Docker](#docker)
- [Registro de sintetizações (CSV)](#registro-de-sintetizações-csv)
- [Testes](#testes)
- [pre-commit](#pre-commit)
- [Documentação do código](#documentação-do-código)
- [CI/CD (GitHub Actions)](#cicd-github-actions)
- [Limitações conhecidas](#limitações-conhecidas)

## Arquitetura e design

O projeto segue uma separação clássica em três módulos, todos dentro
do pacote `tts_project`:

| Módulo | Responsabilidade                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `core` | Regras de negócio, independente de interface: parâmetros, motores de síntese, identificação de idioma, registro CSV e o serviço de fachada. |
| `cli`  | Interface de linha de comando (`click`), fina — apenas traduz argumentos em chamadas ao `core`.                                             |
| `web`  | Aplicação Flask (API + página HTML), também fina — delega tudo ao `core`.                                                                   |

Padrões de projeto usados (mantendo o código extensível sem
complicá-lo):

- **Strategy** — `Synthesizer` (`Pyttsx3Synthesizer` / `GTTSSynthesizer`)
  e `LanguageIdentifier` (`TextLanguageIdentifier` /
  `WhisperAudioLanguageIdentifier`) são interfaces intercambiáveis;
  novas engines podem ser adicionadas sem alterar o restante do código.
- **Factory** — `SynthesizerFactory` decide qual `Synthesizer`
  instanciar a partir de `Quality.LOW`/`Quality.HIGH`.
- **Facade** — `TTSService` é o único ponto de entrada usado por CLI e
  Web, evitando duplicar a lógica de identificação de
  idioma → síntese → registro entre as duas interfaces.
- **Application Factory** (Flask) — `create_app()` cria e configura a
  aplicação, facilitando testes com dependências isoladas.
- **Injeção de dependência** — `TTSService` recebe suas colaborações
  (`Settings`, identificador de idioma, fábrica de sintetizador,
  registro) via construtor, o que permite testá-lo com dublês
  (_fakes_) sem depender de motores de TTS reais.

## Nota de design: por que Whisper em um projeto de TTS

O Whisper é um modelo de **reconhecimento de fala** (ASR): ele
identifica idioma a partir de **áudio**, não de texto puro — portanto
ele não substitui um detector de idioma de texto. Para atender ao
requisito de uma opção de "identificar idioma" e de um "modelo mais
forte e pesado para identificar", o projeto usa **duas estratégias
complementares**, escolhidas automaticamente conforme a qualidade
pedida:

1. **Detecção rápida (padrão)** — `TextLanguageIdentifier`, baseada em
   `langdetect`, roda diretamente sobre o texto de entrada.
2. **Confirmação pesada (`--quality high` + `--identify-language`)** —
   `WhisperAudioLanguageIdentifier` sintetiza uma pequena amostra do
   texto (com o motor leve) e roda o **Whisper** sobre o áudio
   resultante para confirmar/corrigir o idioma detectado no passo 1.
   Essa etapa é propositalmente mais lenta, pois carrega um modelo
   Whisper (`base` por padrão, configurável).

Isso mantém o uso do Whisper genuíno e funcional (ele de fato roda
inferência sobre áudio, sua função real), em vez de forçá-lo a fazer
algo para o qual não foi desenhado.

## Estrutura do projeto

```
tts_project/
├── pyproject.toml
├── Dockerfile.cpu    # Imagem Docker para modelo executado na cpu
├── Dockerfile.gpu    # Imagem Docker separada para modelo executado em GPU, em vista do tamanho da biblioteca CUDA
├── docker-compose.yml
├── docker-compose.gpu.yaml
├── .pre-commit-config.yaml
├── .github/workflows/
│   ├── tests.yml        # PR de dev -> master: mypy + ruff + pytest
│   └── build.yml        # push em master: build/push da imagem Docker
├── docs/
│   └── generate_docs.sh # gera documentação HTML (pdoc) a partir dos docstrings
├── src/tts_project/
│   ├── core/
│   │   ├── config.py       # Settings (caminhos via variáveis de ambiente)
│   │   ├── models.py       # SynthesisParameters, SynthesisRecord, Quality
│   │   ├── exceptions.py
│   │   ├── language.py     # Strategy: identificação de idioma
│   │   ├── synthesizer.py  # Strategy + Factory: motores de TTS
│   │   ├── registry.py     # histórico em CSV
│   │   └── service.py      # Facade: TTSService
│   ├── cli/
│   │   └── main.py         # comando `tts synthesize`
│   └── web/
│       ├── app.py          # application factory Flask
│       ├── routes.py       # endpoints /, /api/synthesize, /api/status, /api/audio
│       ├── jobs.py         # jobs em background com progresso
│       ├── templates/index.html
│       └── static/{style.css,app.js}
└── tests/
    ├── conftest.py         # fakes de sintetizador/identificador (sem áudio real)
    ├── test_language.py
    ├── test_registry.py
    ├── test_synthesizer.py
    ├── test_service.py
    ├── test_cli.py
    └── test_web.py
```

## Instalação e uso com `uv`

```bash
# Instala as dependências (runtime + dev) em um .venv local
uv sync --extra dev

# Ativa o ambiente (opcional; `uv run` já usa o venv automaticamente)
source .venv/bin/activate
```

> **Nota sobre `pyttsx3`**: em Linux ele depende do `espeak-ng`
> instalado no sistema (`apt install espeak-ng`); a imagem Docker já
> inclui essa dependência.

## Uso da CLI

```bash
# A partir de um arquivo, com fallback pt-BR (nenhum --language informado)
uv run tts synthesize texto.txt saida.mp3

# Lendo do stdin (pipeline), com detecção automática de idioma
cat artigo.txt | uv run tts synthesize - saida.wav --identify-language

# Qualidade alta, idioma explícito e velocidade reduzida
uv run tts synthesize texto.txt saida.mp3 --quality high --language en --speed 0.8

# Qualidade alta + identificação automática: usa langdetect no texto e
# confirma com o Whisper sobre uma amostra sintetizada
uv run tts synthesize texto.txt saida.mp3 --quality high --identify-language
```

Opções disponíveis:

| Opção                 | Atalho | Descrição                                                                                                                          |
| --------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `--quality`           | `-q`   | `low` (padrão, offline/rápido) ou `high` (mais natural, requer internet).                                                          |
| `--language`          | `-l`   | Código do idioma (ex.: `pt-BR`, `en`, `es`). Se omitido, usa `pt-BR` como fallback — a menos que `--identify-language` seja usado. |
| `--identify-language` | `-i`   | Detecta o idioma automaticamente em vez de usar `--language`/fallback.                                                             |
| `--speed`             | `-s`   | Fator de velocidade da fala (`1.0` = normal).                                                                                      |

O formato do áudio de saída (`.mp3` ou `.wav`) é inferido pela
extensão do arquivo de saída.

## Uso da interface Web

```bash
uv run flask --app tts_project.web.app:app run
# ou, em desenvolvimento:
uv run python -m tts_project.web.app
```

Abra `http://localhost:5000`: a página permite colar texto ou enviar
um `.txt`, escolher as mesmas opções da CLI (qualidade, idioma,
identificação automática, velocidade, formato), mostra uma barra de
progresso enquanto o job roda em segundo plano e, ao concluir, carrega
o áudio em um player para reprodução direta na página.

A UI usa [Pico.css](https://picocss.com/) via CDN — uma folha de
estilo pronta e _classless_ — para manter o front-end simples sem
precisar de um framework de build.

Endpoints da API usados pela página (podem também ser chamados
diretamente):

| Método | Rota                   | Descrição                                                                |
| ------ | ---------------------- | ------------------------------------------------------------------------ |
| `POST` | `/api/synthesize`      | Recebe `text` ou `text_file`, mais as opções; retorna `{"job_id": ...}`. |
| `GET`  | `/api/status/<job_id>` | Retorna `{status, progress, detected_language, error_message}`.          |
| `GET`  | `/api/audio/<job_id>`  | Serve o áudio gerado, quando `status == "done"`.                         |

## Docker

O `Dockerfile` usa build multi-stage com `uv` para instalar as
dependências e definir, de forma centralizada, os caminhos de dados
via variáveis de ambiente:

```dockerfile
ENV TTS_DATA_DIR=/data \
    TTS_AUDIO_SUBDIR=audio \
    TTS_REGISTRY_FILENAME=registry.csv \
    TTS_DEFAULT_LANGUAGE=pt-BR \
    TTS_WHISPER_MODEL=base
```

```bash
# Build
docker build -t tts-project Dockerfile.cpu # Build da imagem para CPU

docker build -t tts-project Dockerfile.gpu # Build da imagem para GPU

# Rodar a aplicação web, persistindo os dados em ./data
docker run --rm -p 5000:5000 -v "$(pwd)/data:/data" tts-project

# Rodar a CLI dentro do mesmo container
docker run --rm -v "$(pwd)/data:/data" -v "$(pwd):/input" tts-project \
  tts synthesize /input/texto.txt /data/audio/saida.mp3

# Ou, de forma equivalente, com docker-compose
docker compose up --build # CPU

docker compose -f docker-compose.yml -f docker-compose.gpu.yml up #GPU
```

## Registro de sintetizações (CSV)

Cada chamada a `TTSService.synthesize` grava uma linha em
`$TTS_DATA_DIR/registry.csv` (via `AudioRegistry`) com:

`id, created_at, source_text_preview, source_characters, quality, requested_language, identify_language, speed, detected_language, audio_path`

O texto original é resumido (`source_text_preview`, até ~120
caracteres) para o CSV não crescer sem controle com textos longos; o
número total de caracteres fica registrado em `source_characters`. Os
áudios gerados ficam em `$TTS_DATA_DIR/audio/`.

## Testes

```bash
uv run pytest
```

Os testes cobrem `language`, `registry`, `synthesizer` (seleção e
validação de formato), `service` (orquestração/Facade), `cli`
(`CliRunner`) e `web` (`Flask` test client). Em nenhum teste o
**conteúdo do áudio** é verificado — os motores reais (`pyttsx3`,
`gTTS`) e o Whisper são substituídos por dublês (_fakes_) injetados via
construtor, conforme pedido.

## pre-commit

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

Hooks configurados em `.pre-commit-config.yaml`:

- Hooks básicos de higiene (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, ...).
- `ruff` (lint + format).
- `mypy` — checagem de tipagem estática do pacote `src`.
- `pytest` — roda a suíte de testes com cobertura (`--cov`), configurado
  para o estágio `pre-push` (para não deixar cada commit lento).

## Documentação do código

O código é documentado com _docstrings_ no estilo Google em todos os
módulos, classes e funções públicas. Para gerar um site HTML de
referência, usei [`pdoc`](https://pdoc.dev/):

```bash
make docs
```

## CI/CD (GitHub Actions)

Dois workflows em `.github/workflows/`:

- **`tests.yml`** — roda em todo Pull Request contra `master`/`main`
  (o caso de uso descrito: merge de `dev` em `master`): `mypy`, `ruff`
  e `pytest --cov`.
- **`build.yml`** — roda em todo `push` para `master`/`main` (ou seja,
  quando o merge de fato acontece): builda a imagem Docker e a publica
  no GitHub Container Registry (`ghcr.io`).

## Limitações conhecidas

- `gTTS` (qualidade `high`) requer acesso à internet; sem rede, use
  `--quality low` (offline, via `pyttsx3`).
- A confirmação de idioma via Whisper adiciona latência perceptível
  (carrega um modelo de ML) — por isso só é ativada quando
  `--quality high` **e** `--identify-language` são usados juntos.
- Os jobs da interface web são mantidos em memória (processo único);
  reiniciar o servidor descarta o histórico de jobs em andamento (o
  CSV de registro e os áudios já gerados, por outro lado, persistem em
  disco).
