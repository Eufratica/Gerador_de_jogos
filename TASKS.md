# TASKS.md — Backlog Rastreável da PlayForge Factory

## 1. Fase Concluída: `FASE 0 — GOVERNANÇA E DIAGNÓSTICO` (`007` Arquivada)

- [x] **T-000 a T-005:** Inspeção Git/ambiente, execução da linha de base (`229` unitários + `ActionBalanceVerifier` + `verify_engine_boot`), auditorias do jogo-âncora e fábrica, OpenSpec e documentação completa.
- [x] **T-006:** Decisões `PEND-001` a `PEND-005` aprovadas pelo operador (`ADR-005` a `ADR-008` em [DECISIONS.md](DECISIONS.md)).

---

## 2. Fase Concluída: `FASE 1 — AMBIENTE REPRODUZÍVEL` (`OpenSpec 008` Arquivada; aguardando aprovação para Fase 2)

- [x] **T-101:** Inspecionado fora do sandbox hardware real (`Windows 11 Pro`, `i5-1135G7`, `12 GB RAM`, `Intel Iris Xe`, `~155 GB` livres em `C:`), WSL2 `Ubuntu-24.04` (`5.7Gi` RAM, `Docker Compose v5.3.1`, `Python 3.12.3`), portas ocupadas (`8000`, `5678`, `6333`, `1880`).
- [x] **T-102:** Especificação [008-phase1-reproducible-environment.md](openspec/changes/008-phase1-reproducible-environment.md) e [openspec/specs/infrastructure/spec.md](openspec/specs/infrastructure/spec.md) criadas.
- [x] **T-103:** Criar `docker-compose.yml` incremental com portas sem conflito (`pgvector/pgvector:pg16` na `${PLAYFORGE_PG_PORT:-5434}`, `valkey` sob profile `cache`, `factory.Dockerfile` com Python `3.12` + Godot `4.4-stable` Linux CLI).
- [x] **T-104:** Criar `.env.example`, `.devcontainer/devcontainer.json` e scripts padronizados em `infrastructure/scripts/` (`playforge.ps1` + `playforge.sh`).
- [x] **T-105:** Atualizar [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) com diagnóstico real, comandos de operação, backup/restore e recuperação.
- [x] **T-106:** Executar validação real no Docker/WSL2 (`build`, `up`, `health`, teste de extensão `pgvector`, execução da suíte Godot headless dentro do container Linux e no Windows).

---

## 3. Histórico Preservado do Jogo-Âncora (`OpenSpec 001–006`)

- [x] `001` — Arquitetura Core, Economia Data-Driven e Balística DDTank (`APPROVED`).
- [x] `002` — `BigNum`, `BalanceConfig`, `TerrainHeightmap`, `DDTankBallistics` (`ARCHIVED` — `v0.1.0-core-a`).
- [x] `003` — `SeededRng`, `IdleEconomy`, `CombatFsm`, `BalanceVerifier` 72h (`ARCHIVED` — `v0.2.0-core-b`).
- [x] `004` — Pivô focado Jogo 1 Action Dark Fantasy 2D (`APPROVED_IN_EXECUTION`).
- [x] `005` — `ActionWorldConfig`, `ActionCombatCore`, `ActionBalanceVerifier` (`ARCHIVED` — `v0.3.0-core-action`).
- [x] `006` — Cliente jogável Godot 4.4 `Zaikor: Zenkai Infinite` (`ARCHIVED` — `v0.4.0-playable-slice`).
- [ ] `Sprint 4C` — Ports/Adapters (`src/adapters/` ainda vazio com `.gitkeep`) & export `.aab` *(aguarda conclusão do MVP da fábrica conforme `ADR-005`)*.

---

## 4. Próxima Fase Planejada: `FASE 2 — CORE DA FÁBRICA & MULTI-PROJETO`

- [ ] Definir ADR + SDD para `factory/core` e `factory/projects` em Python + schema PostgreSQL inicial e plano controlado para isolamento de `Zaikor` (`ADR-006`).
