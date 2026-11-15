# OpenSpec Change 008: Fase 1 — Ambiente Reproduzível (WSL2 + Docker Compose + DevContainer + Godot 4.4 CLI)

- **ID:** `008-phase1-reproducible-environment`
- **Status:** `ARCHIVED` *(2026-11-15; autorizado por `ADR-007`)*
- **Fase SDLC:** `Fase 1 — Ambiente Reproduzível`
- **Documentação operacional:** [docs/INFRASTRUCTURE.md](../../docs/INFRASTRUCTURE.md)

---

## 1. Escopo Entregue

`.env.example`, `infrastructure/docker/factory.Dockerfile`, `docker-compose.yml`, `.devcontainer/devcontainer.json`, `infrastructure/scripts/playforge.sh` e `playforge.ps1`, `docs/INFRASTRUCTURE.md`. Jogo-âncora não modificado.

## 2. Critérios de Aceitação e Evidências Observadas

- [x] `docker compose config` válido (`playforge.sh config` → exit `0`, profiles default/cache/tools).
- [x] `db` (`pgvector/pgvector:pg16`) `Up (healthy)` em `127.0.0.1:5434`; `pg_isready` aceitando conexões; `CREATE EXTENSION vector` OK (`vector 0.8.7`).
- [x] `factory-runner` construído (`python:3.12-slim-bookworm`, `Python 3.12.16`, Godot `4.4.stable.official.4c311cbee`); no container Linux: `229 assertions | Failed: 0` (`512.40 ms`), `ACTION BALANCE GATE PASSED` (`502.15 ms`, 0 soft-locks), boot gate `14 assertions | Failed: 0`.
- [x] Windows (`playforge.ps1 test-win`): `229 assertions | Failed: 0` (`325.44 ms`), `ACTION BALANCE GATE PASSED` (`412.05 ms`), boot gate `14 assertions | Failed: 0`.
- [x] Scripts validados: `config`, `build-runner`, `up`, `up-cache`, `status`, `health`, `test-linux`, `test-win`, `env-init`, `backup-db`; `restore-db` bloqueado sem `-ConfirmRestore` e executado com sucesso com a confirmação.
- [x] Profile `cache`: `playforge_valkey` `Up (healthy)` em `127.0.0.1:6381`.
- [x] Jogo-âncora intacto (verificação final registrada em `docs/SESSION_STATE.md`).

## 3. Desvios e Lições

- Porta `6380` estava ocupada no WSL2 (bind falhou: *port is already allocated*); `valkey` movido para `6381`.
- `Godot` no Windows falha com crash (signal 11) se `user://` não puder ser criado; `test-win` redireciona `APPDATA` para pasta temporária.
- `wsl`/Docker exigem execução fora do sandbox do agente (`Wsl/E_ACCESSDENIED`).
