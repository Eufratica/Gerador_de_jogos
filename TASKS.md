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

## 4. Fase Concluída: `FASE 2 — CORE DA FÁBRICA & MULTI-PROJETO` (`OpenSpec 009` Arquivada)

- [x] **T-201:** `factory/playforge/models.py` (constantes, ciclo de vida de 20 etapas, exceções *fail-closed* herdando de `FactoryError`).
- [x] **T-202:** `factory/playforge/logging_utils.py` (`StructuredLogger` gravando JSON Lines com relógio injetável).
- [x] **T-203:** `factory/playforge/registry.py` (`ProjectManager` com persistência atômica, anti-path-traversal `_ensure_within`, manifesto isolado em `games/<project_id>/project_manifest.json`, proteção do jogo-âncora `zaikor` e máquina de estados com evidência obrigatória e bloqueio de aprovação humana).
- [x] **T-204:** `factory/playforge/cli.py` (CLI `playforge-core` com subcomandos `init`, `list`, `show`, `create`, `approve`, `advance`).
- [x] **T-205:** `factory/tests/test_factory_core.py` (suíte com 19 testes unitários aprovados em 0.692s com 0 falhas e 0 erros).
- [x] **T-206:** Atualização de capabilities OpenSpec (`game-factory`, `game-projects`) e arquivamento de `009-phase2-factory-core-multiproject.md`.

---

## 5. Fase Concluída: `FASE 3 — GAME SPECIFICATION ENGINE` (`OpenSpec 010` Arquivada)

- [x] **T-301:** `factory/playforge/spec_engine/schemas.py` (`SPEC_SCHEMA_VERSION`, `GDD_SCHEMA_VERSION`, `SEMVER_RE`, 34 campos contratuais da `GameSpecification` e 25 seções obrigatórias do `GDD`).
- [x] **T-302:** `factory/playforge/spec_engine/validator.py` (`SpecificationValidator` *fail-closed* com bloqueio de campos desconhecidos, guarda `bool` vs `int`, validações semânticas de salas/gacha e `check_compatibility` / `compute_spec_digest`).
- [x] **T-303:** `factory/playforge/spec_engine/generator.py` (`SpecificationGenerator` gerando atomicamente `specs/game_specification.json`, `gdd/gdd.json`, `gdd/gdd.md` e fluxo de aprovação SHA-256 `specs/spec_approval.json` com proteção do jogo-âncora `zaikor`).
- [x] **T-304:** Subcomandos CLI `spec-validate` (arquivo ou `--project`), `spec-generate`, `gdd-generate` e `spec-approve` em `factory/playforge/cli.py`.
- [x] **T-305:** `factory/tests/test_spec_engine.py` (28 testes dedicados; suíte Python total em 47 testes aprovados em 1.285s, 0 falhas, 0 erros) + atualização de `openspec/specs/game-specification/spec.md` e arquivamento da Change `010`.

---

## 6. Fase 4 Concluída: `FASE 4 — GAME TEMPLATE REGISTRY` (`OpenSpec 011`)

- [x] `T-401` — Definir SDD para o `Template Registry` ([011-phase4-game-template-registry.md](openspec/archive/011-phase4-game-template-registry.md)) com base em [docs/GAME_TEMPLATES.md](docs/GAME_TEMPLATES.md) e isolar `templates/.gdignore`.
- [x] `T-402` — Extrair primeiro template `godot-2d-action-rpg` (`1.0.0`) com `template_manifest.json`, `skeleton/` desacoplado do `Zaikor` e `demo/` validado em Godot 4.4 headless sem quebrar a raiz `res://`.
- [x] `T-403` — Implementar `factory/playforge/template_registry/` (`schemas.py`, `validator.py`, `registry.py`, `cli_handlers.py`) com validação *fail-closed*, checksum SHA-256, compatibilidade com `GameSpecification`, comparação e depreciação versionada.
- [x] `T-404` — Integrar subcomandos CLI `template-*` em `factory/playforge/cli.py` e validar suíte `factory/tests/test_template_registry.py` (15 novos testes; 62 total Python + runner real Godot headless).

## 7. Fase 5 Concluída: `FASE 5 — GAME GENERATOR (MVP)` (`OpenSpec 012`)

- [x] `T-501` — Definir SDD do `Game Generator (MVP)` ([012-phase5-game-generator-mvp.md](openspec/archive/012-phase5-game-generator-mvp.md)) integrando Spec aprovada + Template validado (`TPL-01`, `GF-03`).
- [x] `T-502` — Implementar `factory/playforge/generator/` (`schemas.py`, `config_mapper.py`, `game_generator.py`, `cli_handlers.py`) com parametrização de `project.godot`/`template_defaults.json`, guarda de jogabilidade, `games/.gdignore`, manifesto `SHA-256` e idempotência com detecção de conflito.
- [x] `T-503` — Gerar e executar suíte dedicada `tests/unit/verify_generated_game.gd` (18 assertions em Godot 4.4 headless `< 1s`) + empacotamento reproduzível `.zip` + `.sha256` + `-preview-report.json` em `builds/`.
- [x] `T-504` — Integrar subcomandos CLI `game-generate`, `game-verify`, `game-package` e aprovar `factory/tests/test_game_generator.py` (7 novos testes E2E reais; 69 testes Python totais).

## 8. Fase 6 Concluída: `FASE 6 — AI ENGINE, MULTIAGENTES & MCP` (`OpenSpec 013` / `ADR-009`)

- [x] `T-601` — Auditar ambiente/hardware real (`11.74 GB` RAM, `8` threads, GPU integrada, `ollama` ausente, zero pacotes pip externos) e formalizar [013-phase6-ai-engine-agents-mcp.md](openspec/archive/013-phase6-ai-engine-agents-mcp.md) + `ADR-009`.
- [x] `T-602` — Implementar `factory/playforge/security_utils.py` e `factory/playforge/ai/` (`schemas.py`, `model_router.py`) com cliente HTTP local `Ollama`, bloqueio *fail-closed* de endpoints pagos/offline (`SEC-02`), gate de `Tier L`, extração JSON estrita contra conteúdo não confiável e telemetria JSONL sanitizada.
- [x] `T-603` — Implementar `AgentRegistry` (`agents.py`) para os **14 contratos oficiais** e `GraphOrchestrator` + `SqliteCheckpointer` (`orchestrator.py`) com limites anti-loop, pausa/retomada em gates humanos e pipeline `mvp-generation`.
- [x] `T-604` — Implementar `factory/playforge/mcp/` (`schemas.py`, `base_server.py`, `servers.py`) com `JSON-RPC 2.0` via `stdio`, 4 servidores confinados por `project_id` (`game-project-mcp`, `game-design-mcp`, `godot-mcp`, `testing-mcp`), bloqueio de `zaikor`/travessia/segredos (`SEC-01`), auditoria JSONL, CLI (`ai-health`, `agent-list`, `workflow-run`, `workflow-resume`, `mcp-list-tools`, `mcp-call`) e 10 novos testes em `factory/tests/test_ai_mcp.py` (`79` testes Python totais aprovados).

## 9. Fase 7 Concluída: `FASE 7 — ASSET & AUDIO PIPELINE` (`OpenSpec 014`)

- [x] `T-701` — Auditar toolchain de mídia (`ffmpeg`/`blender`/`krita`/`gimp`/`magick`/`sox` ausentes; Godot 4.4 `Image.load_from_file` e `AudioStreamWAV.load_from_file` verificados) e formalizar [014-phase7-asset-audio-pipeline.md](openspec/archive/014-phase7-asset-audio-pipeline.md).
- [x] `T-702` — Implementar `factory/playforge/asset_pipeline/` (`schemas.py`, `validator.py`, `synthesizer.py`, `registry.py`, `cli_handlers.py`) com inspeção binária PNG/WAV/OGG sem dependências pagas, governança estrita de licenças/proveniência IA, bloqueio de clipping/órfãos/temporários e verificação headless real no Godot 4.4.
- [x] `T-703` — Adicionar servidores confinados `asset-mcp` e `audio-mcp` (`factory/playforge/mcp/servers.py`), permissões de menor privilégio em `agents.py`, subcomandos CLI `asset-*`/`audio-*` e suíte `factory/tests/test_asset_audio_pipeline.py` (6 novos testes; 85 testes Python totais aprovados).

## 10. Fase 8 Concluída: `FASE 8 — GAME QA & BALANCE ENGINE` (`OpenSpec 015`)

- [x] `T-801` — Definir SDD do QA & Balance Engine ([015-phase8-game-qa-balance-engine.md](openspec/archive/015-phase8-game-qa-balance-engine.md)) e implementar `factory/playforge/qa_engine/` (`schemas.py`, `static_analyzer.py`, `balance_verifier.py`, `runner.py`, `cli_handlers.py`).
- [x] `T-802` — Integrar subcomandos CLI (`qa-static`, `qa-balance`, `qa-profile`, `qa-run`), adicionar tools `qa_*` em `testing-mcp` (`factory/playforge/mcp/servers.py`) e atualizar permissões mínimas em `balance`, `qa` e `auditor` (`factory/playforge/ai/agents.py`).
- [x] `T-803` — Validar auditoria *read-only* no `Zaikor` (sem pré-inicializar `data/`), detecção `fail-closed` de `src/core/`, `res://`, segredos, nós órfãos no Godot 4.4 (`OBJECT_ORPHAN_NODE_COUNT`) e simulação dos 11 gêneros em `factory/tests/test_qa_balance_engine.py` (`9` novos testes; `94` testes Python totais aprovados).

## 11. Fase 9 Concluída: `FASE 9 — AUTOMAÇÃO (n8n COMMUNITY)` (`OpenSpec 016`)

- [x] `T-901` — Implementar `factory/playforge/automation/` (`schemas.py`, `exporter.py`, `validator.py`, `runner.py`, `cli_handlers.py`) e gerar/validar os 20 exports `WF-001`..`WF-020` livres de credenciais em `automation/exports/`.
- [x] `T-902` — Integrar subcomandos CLI `automation-*` em `factory/playforge/cli.py`, adicionar serviço opcional `n8n` (`profiles: ["automation"]`, porta `127.0.0.1:5679`) em `docker-compose.yml`, `.env.example` e comando `up-automation` em `playforge.sh` / `playforge.ps1`.
- [x] `T-903` — Aprovar `factory/tests/test_automation.py` cobrindo `AUT-01`..`AUT-04`, bloqueios *fail-closed* (credenciais/tokens/URLs/órfãos/anti-injection/`zaikor`), servidor webhook HTTP loopback e ciclo real `WF-001`..`WF-020` (`6` novos testes; `100` testes Python totais aprovados) e arquivar `OpenSpec 016`.

## 12. Fase 10, Fase 11 e Evolução Multi-Engine (`OpenSpec 017–021` / `ADR-010`)

- [x] **T-1001..T-1003 (`OpenSpec 017` — `P1`):** Implementar `factory/playforge/engine_orchestrator/` (14 critérios de seleção + `EngineAdapterRegistry` + `GodotEngineAdapter` / `UnityEngineAdapter` / `UnrealEngineAdapter`), evoluir `spec_engine` (`v2` retrocompatível com `v1`) e arquivar `test_engine_orchestrator.py` (`10` testes).
- [x] **T-1101..T-1103 (`OpenSpec 018` — `P2`):** Expandir `asset_pipeline/` com `glTF`/`GLB`/`OBJ`/`FBX`/`JPEG`/`MP3`/PBR, `generate_3d_pbr_pack`, auditoria `has_materials`/`has_rig`/`duplicate_hashes`, descoberta real de `Blender 5.3` / `FFmpeg 9.0.2` / `Ollama 0.40.16`, CLI `asset-generate-3d-pack` / `tool-status` e `test_tool_and_3d_assets.py` (`10` testes).
- [x] **T-1201..T-1203 (`OpenSpec 019` — Fase 10 / `P3`):** Implementar `factory/playforge/build_system/` (`BuildManager` com `probe_build_toolchains`, `build_target`, `verify_build`, `approve_release`, guarda de segredos/assets/`zaikor`, smoke test Godot real) + CLI `build-*` + `test_build_system.py` (`7` testes).
- [x] **T-1301..T-1302 (`OpenSpec 020` — `P4`):** Implementar `factory/playforge/gameplay_systems/` (8 sistemas sob demanda para Godot GDScript, Unity C# e Unreal C++ headers), mapear os 13 papéis da Seção 10 em `ai/agents.py` (`get_engineering_role_catalog`, `agent-roles`), CLI `gameplay-*` e `test_gameplay_and_agents.py` (`5` testes).
- [x] **T-1401..T-1403 (`OpenSpec 021` — Fase 11 / `P5`):** Implementar `factory/playforge/evolution/` (`LocalRagMemory` TF-IDF local anti-injection, `OptimizationAdvisor` com aprovação humana e `FactoryDashboard`), CLI `evolution-*` e `test_evolution_phase11.py` (`4` testes; `136` testes totais na fábrica).
- [ ] **Pendências Externas Opcionais (fora do Free First automático):** Instalação manual de Unity Hub/Editor, Unreal Engine 5 (requer Workstation >= `32 GB RAM` + GPU DX12 >= `8 GB VRAM` e conta Epic), Android SDK/Keystore para compilação binária nativa e contratação opcional de serviços de loja no `Sprint 4C`.
