# CHANGELOG.md — PlayForge Factory & Jogo-Âncora

O formato segue [Keep a Changelog](https://keepachangelog.com/) e **Semantic Versioning (`MAJOR.MINOR.PATCH`)** versionado separadamente entre a Fábrica, Templates, Game Specifications e Jogos.

---

## [1.0.0] — Evolução Multi-Engine (`P1`–`P5`), Build Manager (`Fase 10`) & Telemetria/RAG (`Fase 11`) (`OpenSpec 017`–`021`)

### Added
- **P1 (`OpenSpec 017` — `factory/playforge/engine_orchestrator/`):**
  - `EngineSelector` com pontuação ponderada nos 14 critérios oficiais e geração de relatório justificativo JSON + Markdown cruzando hardware local real.
  - Contrato extensível `EngineAdapter` + `EngineAdapterRegistry` com `GodotEngineAdapter` (execução headless real), `UnityEngineAdapter` e `UnrealEngineAdapter` (scaffold + detecção real no host + bloqueio *fail-closed* quando ausentes) e subcomandos CLI `engine-*`.
  - Evolução retrocompatível da `GameSpecification` (`spec_schema_version = 2` aceitando `godot|unity|unreal`, `tools_required`, `camera_spec`, `physics_spec`, `inventory_spec`, `quests_spec`, `engine_selection_report`, mantendo `v1` estrito para `godot`).
- **P2 (`OpenSpec 018` — `factory/playforge/asset_pipeline/`):**
  - Inspetores binários/estruturais *fail-closed* e sintetizadores `stdlib` para `glTF 2.0`, `GLB 2.0`, `OBJ`, `FBX` (assinatura), `JPEG`, `MP3` e conjuntos de mapas PBR (`albedo`, `normal`, `roughness`, `metallic`, `ao`).
  - `AssetRegistry.generate_3d_pbr_pack()`, auditoria de `duplicate_hashes`, `models_missing_materials` e `animations_missing_rig`, além de descoberta de `Blender 5.3` / `FFmpeg 9.0.2` instalados no host e subcomandos CLI `asset-generate-3d-pack` e `tool-status`.
- **P3 / Fase 10 (`OpenSpec 019` — `factory/playforge/build_system/`):**
  - `BuildManager` multi-plataforma com inspeção real de toolchains (`probe_build_toolchains`), geração determinística de pacotes (`structural-source-bundle`) por alvo e versão com hashes SHA-256 por arquivo e pacote, smoke test headless Godot, bloqueio de segredos/órfãos/`zaikor`, reverificação de integridade (`verify_build`) e aprovação humana de release (`approve_release` com `published_externally: false`) via CLI `build-*`.
- **P4 (`OpenSpec 020` — `factory/playforge/gameplay_systems/` + `factory/playforge/ai/agents.py`):**
  - Catálogo reutilizável de 8 sistemas modulares injetados sob demanda para Godot (`.gd` puro), Unity (`.cs` puro) e Unreal (`.h`), CLI `gameplay-catalog` e `gameplay-inject`.
  - Mapeamento formal dos 13 papéis da Seção 10 (`SPECIALIZED_ENGINEERING_ROLE_MAP` + `get_engineering_role_catalog` + CLI `agent-roles`) preservando os 14 contratos originais de `AgentRegistry`.
- **P5 / Fase 11 (`OpenSpec 021` — `factory/playforge/evolution/`):**
  - `LocalRagMemory` (índice TF-IDF + cosseno local em `data/rag/knowledge_index.json` com bloqueio anti-*prompt-injection*), `OptimizationAdvisor` com gate humano e `FactoryDashboard` consolidado + CLI `evolution-*`.
- **Qualidade & Documentação:** `VERSION` em `1.0.0`, suítes unitárias em `factory/tests/` ampliadas para **136 testes Python** aprovados, preservando `Zaikor` intacto na raiz.

---

## [0.9.0] — Fase 9: Automação (`n8n Community`) (`OpenSpec 016`)

### Added
- Pacote Python `factory/playforge/automation/` (`schemas.py`, `exporter.py`, `validator.py`, `runner.py`, `cli_handlers.py`):
  - Catálogo oficial `OFFICIAL_WORKFLOW_CATALOG` (`WF-001`..`WF-020`) e exports versionados determinísticos em `automation/exports/` (`WF-001_project_initialization.json` a `WF-020_factory_monitoring.json`), todos com `active: false` e **100% livres de credenciais**.
  - Validador *fail-closed* (`validate_workflow_export`, `validate_exports_directory`) bloqueando credenciais preenchidas, literais secretos (`sk-`, `ghp_`, `AIza`, `Bearer`, PEM), domínios pagos/externos, arquivos órfãos, `.env`/chaves e desvios estruturais.
  - `AutomationEngine` conectando os 20 workflows aos módulos da fábrica com proteção anti-*prompt-injection*, bloqueio do jogo-âncora `zaikor`, checkpoints SQLite para `Human-in-the-Loop` (`WF-004`/`WF-014`/`WF-016`), gate `QAEngine` antes de `WF-015` e monitoramento *read-only* `WF-020`.
  - `AutomationWebhookServer` HTTP loopback (`127.0.0.1`) expondo `/health` e `/webhook/<workflow_id>` com rejeição de *bind* externo e limite de payload.
- Subcomandos CLI `automation-list`, `automation-export`, `automation-validate`, `automation-trigger`, `automation-approve` e `automation-serve` em `factory/playforge/cli.py`.
- Serviço opcional `n8n` Community em `docker-compose.yml` (`profiles: ["automation"]`, porta `127.0.0.1:${PLAYFORGE_N8N_PORT:-5679}:5678` preservando porta `5678` do host), variáveis em `.env.example` e comando `up-automation` em `playforge.sh` / `playforge.ps1`.
- Suíte `factory/tests/test_automation.py` (`6` novos testes; `100` testes Python totais aprovados), capability `openspec/specs/automation/spec.md` (`IMPLEMENTED_PHASE_9`) e Change `016` arquivada.

---

## [Unreleased] — Fase 8: Game QA & Balance Engine (`OpenSpec 015`)

### Added
- Pacote Python `factory/playforge/qa_engine/` (`schemas.py`, `static_analyzer.py`, `balance_verifier.py`, `runner.py`, `cli_handlers.py`):
  - `StaticAnalyzer` multi-projeto (incluindo auditoria *read-only* no `zaikor`) validando pureza de `src/core/*.gd` com filtragem de comentários (`GT-01`), referências `res://` (`GT-03`), higiene de segredos/keystores e checksums contra `generation_manifest.json`.
  - `BalanceVerifierEngine` determinístico multi-perfil (`F2P_PURE`, `CASUAL_OPTIMAL`, `HARDCORE_STRESS`) parametrizado para todos os 11 gêneros suportados (`GT-04`), além de integração com `run_action_verifier.gd` do `Zaikor`.
  - `QAEngine` orquestrando os 4 pilares do QA (`static`, `balance`, `godot_suites` + probe real `godot_profile` via `Performance` com detecção de nós órfãos `GT-02`, e `assets`), gerando `specs/qa_report.json`.
- Novas tools confinados `qa_run_static_audit`, `qa_run_balance_audit`, `qa_run_full_pipeline` e `qa_read_report` em `testing-mcp`, contratos atualizados para `balance`/`qa`/`auditor` e subcomandos CLI `qa-static`, `qa-balance`, `qa-profile` e `qa-run`.
- Suíte `factory/tests/test_qa_balance_engine.py` com 9 novos testes (`94` testes Python totais aprovados).
- Capability `game-testing` promovida para `IMPLEMENTED_PHASE_8` e Change `015` arquivada.

---

## [Unreleased] — Fase 7: Asset & Audio Pipeline (`OpenSpec 014`)

### Added
- Pacote Python `factory/playforge/asset_pipeline/` (`schemas.py`, `validator.py`, `synthesizer.py`, `registry.py`, `cli_handlers.py`):
  - `AssetRegistry` isolado em `games/<project_id>/assets/asset_registry.json` com contrato completo de 20 campos, proteção de `zaikor` (`ProtectedProject`) e confinamento estrito em `assets/` e `audio/`.
  - Validadores binários sem dependências externas (`inspect_png`, `inspect_wav` com detecção/bloqueio de clipping PCM16, `inspect_ogg`) e validador de licenças/proveniência *fail-closed* (`AssetLicenseError` contra `-NC`, `UNKNOWN`, `ALL_RIGHTS_RESERVED`, atribuição ausente ou IA sem modelo/seed).
  - Sintetizadores procedurais gratuitos em stdlib (`synthesize_png_sprite` e `synthesize_wav_audio` sem clipping) + `generate_default_pack` e `audit_project_assets` contra adulteração de SHA-256, arquivos órfãos/temporários e decodificação real no **Godot 4.4 headless**.
- Servidores MCP `asset-mcp` (4 tools) e `audio-mcp` (3 tools) integrados em `factory/playforge/mcp/servers.py` e contratos `art-asset`, `audio`, `qa` e `auditor` atualizados em `factory/playforge/ai/agents.py`.
- Subcomandos CLI `asset-toolchain`, `asset-generate-pack`, `asset-register`, `asset-list`, `asset-audit` e `audio-inspect` em `factory/playforge/cli.py`.
- Suíte `factory/tests/test_asset_audio_pipeline.py` com 6 novos testes (85 testes Python totais aprovados).
- Capability `asset-audio` criada (`IMPLEMENTED_PHASE_7`) e Change `014` arquivada.

---

## [Unreleased] — Fase 6: AI Engine, Multiagentes & MCP (`OpenSpec 013` / `ADR-009`)

### Added
- Módulo compartilhado `factory/playforge/security_utils.py` com mascaramento recursivo de segredos (`scrub_secrets`), detecção de marcadores de *prompt injection*, bloqueio de arquivos sensíveis (`.env`, `.keystore`, chaves privadas) e append JSONL sanitizado.
- Pacote Python `factory/playforge/ai/` (`schemas.py`, `model_router.py`, `agents.py`, `orchestrator.py`, `cli_handlers.py`):
  - `inspect_environment`, `OllamaClient` loopback-only (`urllib.request` + transporte injetável) e `ModelRouter` com detecção real de hardware/Ollama, bloqueio `fail-closed` de APIs externas/offline sem fallback pago (`SEC-02`), gate de `Tier L` por hardware, parser JSON estrito (`UntrustedOutputError`) e telemetria em `data/logs/ai_router.jsonl`.
  - `AgentRegistry` registrando e validando todos os **14 contratos oficiais** de `docs/AGENT_CONTRACTS.md` com verificação explícita de mínimo privilégio (`authorize_tool`).
  - `SqliteCheckpointer` (`data/checkpoints/orchestrator.sqlite3`) e `GraphOrchestrator` com proteção anti-loop (`max_iterations`, `max_retries`, `timeout_seconds`), pausa determinística em `APROVACAO_HUMANA_SPEC`, retomada persistente e grafo `mvp-generation`.
- Pacote Python `factory/playforge/mcp/` (`schemas.py`, `base_server.py`, `servers.py`):
  - Servidor `JSON-RPC 2.0` (`initialize`, `tools/list`, `tools/call`, `serve_stdio`) e 4 servidores confinados por `project_id` (`game-project-mcp`, `game-design-mcp`, `godot-mcp`, `testing-mcp`) com bloqueio de `zaikor`/cross-project/segredos (`SEC-01`) e auditoria mascarada em `data/logs/mcp_audit.jsonl`.
  - Subcomandos CLI `ai-health`, `agent-list`, `workflow-run`, `workflow-resume`, `mcp-list-tools` e `mcp-call` integrados em `factory/playforge/cli.py`.
- Suíte `factory/tests/test_ai_mcp.py` com 10 testes unitários e E2E reais (`79` testes Python totais aprovados).
- Capability `ai-agents` criada (`IMPLEMENTED_PHASE_6`), `ADR-009` registrada em `DECISIONS.md` e Change `013` arquivada.

---

## [Unreleased] — Fase 5: Game Generator MVP (`OpenSpec 012`)

### Added
- Pacote Python `factory/playforge/generator/` (`schemas.py`, `config_mapper.py`, `game_generator.py`, `cli_handlers.py`):
  - `GameGenerator` gerando projetos Godot isolados em `games/<project_id>/` com `games/.gdignore`, bloqueio de `zaikor` (`ProtectedProject`), exigência de `GameSpecification` aprovada (`ApprovalRequired`) e template `ACTIVE` compatível testado (`TPL-01`).
  - Mapeamento determinístico `render_project_godot` e `map_spec_to_runtime_config` (com normalização automática de sobrevivência de campanha para impedir soft-lock estrutural) + gerador da suíte `tests/unit/verify_generated_game.gd` (18 assertions headless).
  - Idempotência (`UP_TO_DATE`), detecção de divergência/adulteração sem `--force` (`GenerationConflictError`), verificação real via `Godot 4.4 --headless` (`verify_generated_project`) e artefato local determinístico `.zip` + `.sha256` + `-preview-report.json` em `games/<project_id>/builds/` (`package_preview_artifact`).
  - Subcomandos CLI `game-generate`, `game-verify` e `game-package` integrados em `factory/playforge/cli.py`.
- Suíte `factory/tests/test_game_generator.py` com 7 testes unitários e E2E reais com Godot 4.4 headless (69 testes Python totais aprovados).
- Capability `game-factory` promovida para `IMPLEMENTED_PHASE_5` e Change `012` arquivada.

---

## [Unreleased] — Fase 4: Game Template Registry (`OpenSpec 011`)

### Added
- Diretório `templates/` isolado do jogo-âncora via `templates/.gdignore` e primeiro template validado `templates/godot-2d-action-rpg/1.0.0/`:
  - `template_manifest.json` (schema v1, licença `MIT`, suporte a `action-rpg`/`idle-rpg` em `android`/`windows`/`linux`, Godot `4.4-stable`).
  - `skeleton/` e `demo/` com módulos puros extraídos (`big_num.gd`, `seeded_rng.gd`, `game_loop_core.gd`), persistência *fail-closed* (`local_checkpoint_store.gd`), cena `main.tscn` + `main.gd` e suíte `run_template_tests.gd` (< 1s em Godot headless).
- Pacote Python `factory/playforge/template_registry/` (`schemas.py`, `validator.py`, `registry.py`, `cli_handlers.py`):
  - `TemplateValidator` *fail-closed* com bloqueio de campos desconhecidos, prevenção `bool`➔`int`, validação estrita de licença livre, anti-path-traversal, proibição de arquivos não declarados ou extensões não permitidas em `skeleton/`, checksum `SHA-256` e runner isolado `run_demo_tests` via Godot CLI headless.
  - `TemplateRegistry` com listagem/busca SemVer, checagem de compatibilidade e seleção determinística vinculada a `GameSpecification` aprovada (`specs/template_selection.json`), comparação de versões e depreciação versionada (`DEPRECATED`) sem apagar arquivos ou quebrar projetos existentes.
  - Subcomandos CLI `template-list`, `template-show`, `template-validate`, `template-select`, `template-compare` e `template-deprecate` em `factory/playforge/cli.py`.
- Suíte `factory/tests/test_template_registry.py` com 15 testes (incluindo execução real de `Godot_v4.4-stable_win64_console.exe` no template demo; 62 testes Python totais passando).
- Capability `game-templates` promovida para `IMPLEMENTED_PHASE_4` e Change `011` arquivada.

---

## [Unreleased] — Fase 3: Game Specification Engine (`OpenSpec 010`)

### Added
- Pacote Python `factory/playforge/spec_engine/` (`schemas.py`, `validator.py`, `generator.py`):
  - Schemas tipados e versionados (`SPEC_SCHEMA_VERSION = 1`, `GDD_SCHEMA_VERSION = 1`) cobrindo 34 campos contratuais da `GameSpecification` e 25 seções obrigatórias do `GDD`.
  - `SpecificationValidator` *fail-closed* com bloqueio de campos desconhecidos, prevenção de coerção `bool`➔`int`, validação SemVer, consistência semântica (`gacha_rates == 1.0`, `total_rooms`, conexões de salas) e `check_compatibility`.
  - `SpecificationGenerator` gravando atomicamente `specs/game_specification.json`, `gdd/gdd.json` e `gdd/gdd.md` isolados por `project_id`, protegendo `zaikor`, e fluxo de aprovação humana com registro de hash SHA-256 (`specs/spec_approval.json`, `approve_specification`, `verify_spec_approved`).
  - Subcomandos CLI `spec-validate`, `spec-generate`, `gdd-generate` e `spec-approve` em `factory/playforge/cli.py`.
- Suíte `factory/tests/test_spec_engine.py` com 28 testes dedicados (total de 47 testes unitários Python passando em 1.285s).
- Capability `game-specification` promovida para `IMPLEMENTED_PHASE_3` e Change `010` arquivada.

---

## [Unreleased] — Fase 2: Core da Fábrica & Multi-Projeto (`OpenSpec 009`)

### Added
- Pacote Python `factory/playforge/` (`models.py`, `logging_utils.py`, `registry.py`, `cli.py`):
  - `ProjectManager` com persistência atômica em `data/registry/projects.json` e manifesto local `games/<project_id>/project_manifest.json`.
  - Confinamento estrito de workspace (*anti-path-traversal* via `WorkspaceEscape`).
  - Proteção imutável do jogo-âncora `zaikor` na raiz (`ProtectedProject`).
  - Máquina de estados sequencial de 20 etapas (`IDEIA` até `OTIMIZACAO`) com exigência obrigatória de evidência (`EvidenceRequired`) e bloqueio *fail-closed* nas etapas de aprovação humana (`APROVACAO_HUMANA_ARQUITETURA` e `APROVACAO_HUMANA_PREVIEW` via `ApprovalRequired`).
  - `StructuredLogger` gravando eventos auditáveis em formato JSON Lines (`data/logs/factory.jsonl`).
  - CLI `playforge-core` com subcomandos `init`, `list`, `show`, `create`, `approve`, `advance`.
- Suíte `factory/tests/test_factory_core.py` com 19 testes unitários automatizados (0.692s, 0 falhas, 0 erros).
- Atualização das capabilities `game-factory` e `game-projects` para `IMPLEMENTED_PHASE_2`.

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
