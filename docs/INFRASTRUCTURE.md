# INFRASTRUCTURE.md — Ambiente Real, Arquitetura e Operação (Fase 1 — `OpenSpec 008`)

## 1. Diagnóstico Real do Ambiente (inspecionado fora do sandbox na Fase 1)

| Recurso | Observado |
| :--- | :--- |
| Host | Windows 11 Pro (`10.0.26200`), `i5-1135G7` (4 núcleos / 8 threads), ~12 GB RAM, `Intel Iris Xe` (sem GPU dedicada), ~155 GB livres em `C:` |
| Windows | `winget v1.29.380`, `Python 3.8.7`, `code.cmd` (VS Code). **Ausentes:** `node`, `docker`, `ollama`, `openspec`, `py`, `java`, `adb` |
| WSL2 | `Ubuntu-24.04` (kernel `6.18.58.1`), `5.7Gi` RAM, `2.0Gi` swap, `904G` livres em `/`, `Python 3.12.3` (sem `pip`), `Docker Compose v5.3.1` |
| Godot Windows | `tools/godot/Godot_v4.4-stable_win64_console.exe` (`4.4.stable.official.4c311cbee`) |
| Workspace | Único: `C:\Jogo_Android` = `/mnt/c/Jogo_Android` (montado em `/workspace` no container; sem cópia duplicada) |

### Mapa de portas (WSL2)

| Porta | Dono | Observação |
| :--- | :--- | :--- |
| `8000`, `5678`, `1880`, `6333/6334`, `5433`, `6380` | Containers/serviços **pré-existentes do usuário** | **Não tocar** |
| `127.0.0.1:5434` | `playforge_db` (`pgvector/pgvector:pg16`, `pgvector 0.8.7`) | PlayForge |
| `127.0.0.1:6381` | `playforge_valkey` (`valkey/valkey:8.0-alpine`, profile `cache`) | PlayForge (`6380` estava ocupada; ver erro de bind registrado em `008`) |
| `127.0.0.1:5679` | `playforge_n8n` (`docker.n8n.io/n8nio/n8n:1.95.3`, profile `automation`) | PlayForge (`5678` ocupada no host; mapeamento `5679->5678`, opcional via `up-automation`) |
| `127.0.0.1:8787` | Ponte HTTP Webhook PlayForge (`automation-serve`) | Loopback local para `WF-001`..`WF-020` |

## 2. Artefatos Entregues

- [docker-compose.yml](../docker-compose.yml): `db` (`mem_limit 512m`, volume nomeado `playforge_pgdata`, healthcheck `pg_isready`), `valkey` (profile `cache`, `128m`), `factory-runner` (profile `tools`, `1024m`, bind `.:/workspace`).
- [infrastructure/docker/factory.Dockerfile](../infrastructure/docker/factory.Dockerfile): `python:3.12-slim-bookworm` + Godot `4.4-stable` Linux headless (oficial, MIT).
- [.devcontainer/devcontainer.json](../.devcontainer/devcontainer.json): conecta VS Code ao serviço `factory-runner`.
- [.env.example](../.env.example): defaults locais sem segredos (`.env` é ignorado pelo Git).
- [infrastructure/scripts/playforge.sh](../infrastructure/scripts/playforge.sh) (Linux/WSL2) e [infrastructure/scripts/playforge.ps1](../infrastructure/scripts/playforge.ps1) (Windows; delega Docker ao WSL2 `Ubuntu-24.04`).

> PostgreSQL usa **volume nomeado Docker** (nunca bind em NTFS) para permissões/desempenho Linux.

## 3. Operação

```powershell
.\infrastructure\scripts\playforge.ps1 test-win      # suíte Godot nativa Windows
.\infrastructure\scripts\playforge.ps1 env-init      # cria .env (não sobrescreve)
.\infrastructure\scripts\playforge.ps1 build-runner  # imagem factory-runner
.\infrastructure\scripts\playforge.ps1 up            # PostgreSQL + pgvector
.\infrastructure\scripts\playforge.ps1 up-cache      # + Valkey
.\infrastructure\scripts\playforge.ps1 up-automation # + n8n Community (127.0.0.1:5679, opcional)
.\infrastructure\scripts\playforge.ps1 health        # pg_isready + extensão vector
.\infrastructure\scripts\playforge.ps1 test-linux    # suíte Godot no container Linux
.\infrastructure\scripts\playforge.ps1 status | down | restart | logs
.\infrastructure\scripts\playforge.ps1 backup-db [arquivo.sql]   # padrão: build/backups/ (ignorado)
.\infrastructure\scripts\playforge.ps1 restore-db <arquivo.sql> -ConfirmRestore
```

- `restore-db` é *fail-closed*: sem `-ConfirmRestore` (`--confirm-restore` no `.sh`) retorna erro e não toca o banco.
- `down` **não** usa `-v`: volumes de dados são preservados. Apagar volumes exige comando manual explícito.
- Nota (sandbox do agente): chamadas a `wsl`/Docker exigem execução fora do sandbox (`Wsl/E_ACCESSDENIED`). Em terminal normal do usuário isso não se aplica.
- Nota: `test-win` redireciona `APPDATA` para um diretório temporário, pois o Godot precisa criar `user://` mesmo em modo headless.

## 4. Fora de Escopo na Fase 1

FastAPI (Fase 2), Ollama/LangGraph/MCP (Fase 6), n8n (Fase 9). Portas e containers existentes do usuário não foram alterados.
