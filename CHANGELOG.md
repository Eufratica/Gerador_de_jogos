# CHANGELOG.md — PlayForge Factory & Jogo-Âncora

O formato segue [Keep a Changelog](https://keepachangelog.com/) e **Semantic Versioning (`MAJOR.MINOR.PATCH`)** versionado separadamente entre a Fábrica, Templates, Game Specifications e Jogos.

---

## [Unreleased] — Fase 1: Ambiente Reproduzível (`OpenSpec 008`)

### Added
- `docker-compose.yml` (`db` `pgvector/pgvector:pg16` em `127.0.0.1:5434`; `valkey:8.0-alpine` profile `cache` em `127.0.0.1:6381`; `factory-runner` profile `tools`), `infrastructure/docker/factory.Dockerfile` (Python 3.12 + Godot 4.4-stable Linux headless), `.devcontainer/devcontainer.json`, `.env.example`.
- CLI padronizada `infrastructure/scripts/playforge.sh` e `playforge.ps1` (`test-win`, `test-linux`, `up`, `health`, `backup-db`, `restore-db` *fail-closed*).

---

## [Unreleased] — Fase 0: Governança & Diagnóstico da Fábrica (`OpenSpec 007`)

### Added
- Estrutura documental raiz da **PlayForge Factory**: `README.md`, `PROJECT.md`, `ROADMAP.md`, `TASKS.md`, `CHANGELOG.md`, `DECISIONS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `FREE_TIER_POLICY.md`.
- Documentação de arquitetura, fábrica, pipelines, QA/testes, agentes, modelo/IA, automação, MCP, banco, infraestrutura, segurança e licenças em `docs/`.
- Memória operacional persistente em `docs/SESSION_STATE.md`.
- Configuração `openspec/config.yaml`, capabilities em `openspec/specs/` e proposta `openspec/changes/007-phase0-factory-governance.md`.

### Changed
- `AGENTS.md` evoluído para governança dual **PlayForge Factory + Jogos Isolados**, mantendo intacto todo o código e as garantias *fail-closed* do jogo-âncora.
- Cabeçalho de `docs/ARQUITETURA.md` atualizado com remissão de preservação para `docs/ARCHITECTURE.md` e `DECISIONS.md`.

---

## Histórico Consolidado do Repositório (`cab6ee8` — Jogo-Âncora `Zaikor`)

*(Commits anteriores ocorreram antes da inicialização do repositório Git em `cab6ee8`; marcos documentados em `openspec/archive/` e `docs/ARQUITETURA.md`.)*

### `v0.4.0-playable-slice` — Sprint 4B (`OpenSpec 006`)
#### Added
- Cliente jogável Godot `4.4` (`1920x1080` lógico / janela `1280x720`) `Zaikor: Zenkai Infinite` (`project.godot`, `src/engine/main.tscn`, `src/engine/scenes/battle_arena.tscn`).
- Silhuetas 2D de alto contraste (`silhouette_warrior.gd`, `silhouette_enemy.gd`), cenários em paralaxe (`world_backdrop.gd`), VFX pool (`vfx_pool.gd`), 16 SFX sintéticos WAV em memória (`procedural_sfx.gd`), HUD PC + Touch (`game_hud.gd`), modal de Forja/Gacha/Baú Offline (`altar_forge_modal.gd`) e persistência local (`local_checkpoint_store.gd`).
- Teste headless `tests/integration/verify_engine_boot.gd`.

### `v0.3.0-core-action` — Sprint 4A (`OpenSpec 005`)
#### Added
- Configuração validada de 2 mundos e 8 salas interconectadas (`config/action_world_v1.json`, `src/core/action_world_config.gd`).
- Motor puro 2D lateral (`src/core/action_combat_core.gd`) com plataformas, dash/i-frames, combos, 4 magias, postura/QTE, Altares de Salvamento e snapshot.
- Simulador 20Hz (`src/factory/action_balance_verifier.gd` + `tests/integration/run_action_verifier.gd`) e suíte unitária `test_action_world_core.gd`.

### `v0.2.0-core-b` — Bloco 1 / Passo 2B (`OpenSpec 003`)
#### Added
- `SeededRng` (`src/core/seeded_rng.gd`), `IdleEconomy` (`src/core/idle_economy.gd`), `CombatFsm` (`src/core/combat_fsm.gd`) e verificador headless 72h (`src/factory/balance_verifier.gd` + `tests/integration/run_balance_verifier.gd`).
#### Security
- Correção do reset em `execute_prestige` preservando `best_stage_lifetime` e fechando exploit de repetição de Prestígio no estágio 1.

### `v0.1.0-core-a` — Bloco 1 / Passo 2A (`OpenSpec 002`)
#### Added
- Estrutura inicial (`AGENTS.md`, `.gitignore`, `docs/ARQUITETURA.md`, `openspec/changes/001`).
- `BigNum` (`src/core/big_num.gd`), `BalanceConfig` (`src/core/balance_config.gd` + `config/balance_v1.json`), `TerrainHeightmap` (`src/core/terrain_heightmap.gd`), `DDTankBallistics` (`src/core/ddtank_ballistics.gd`) e testes unitários puros.
