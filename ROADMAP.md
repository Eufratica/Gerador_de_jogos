# ROADMAP.md — PlayForge Factory

Roadmap incremental em **12 fases (Fase 0 a Fase 11)** mais os incrementos arquiteturais multi-engine (`P1`–`P5`, `ADR-010`) com gates obrigatórios entre fases.

---

## Estado Atual por Fase & Incremento

| Fase / Incremento | Nome | Status Atual | Critério de Saída |
| :--- | :--- | :--- | :--- |
| **Fase 0** | Governança e Diagnóstico | **CONCLUÍDA & ARQUIVADA (`007`)** | Documentação, OpenSpec, auditoria real do repo/jogo-âncora e ADRs `005`–`008` aprovados pelo operador. |
| **Fase 1** | Ambiente Reproduzível | **CONCLUÍDA & ARQUIVADA (`008`)** | WSL2/Ubuntu 24.04, Docker/Compose, Dev Containers, Python, Godot CLI e scripts padronizados funcionando e testados. |
| **Fase 2** | Core da Fábrica & Multi-Projeto | **CONCLUÍDA & ARQUIVADA (`009`)** | `Factory Core`, `Project Manager`, registro/isolamento de múltiplos projetos, versionamento e logs estruturados testados (`19` testes unitários). |
| **Fase 3** | Game Specification Engine | **CONCLUÍDA & ARQUIVADA (`010`)** | Schemas JSON versionados, validador *fail-closed*, gerador de `Game Specification` e `GDD` + fluxo de aprovação SHA-256 testados (`28` novos testes). |
| **Fase 4** | Game Template Registry | **CONCLUÍDA & ARQUIVADA (`011`)** | Template `godot-2d-action-rpg` (`1.0.0`) isolado, demo Godot 4.4 headless e CLI testados (`15` novos testes). |
| **Fase 5** | Game Generator (**MVP**) | **CONCLUÍDA & ARQUIVADA (`012`)** | Geração isolada e idempotente de projeto Godot funcional, verificação Godot 4.4 headless e preview `.zip` + `.sha256` (`7` novos testes). |
| **Fase 6** | AI Engine, Multiagentes & MCP | **CONCLUÍDA & ARQUIVADA (`013`)** | Auditoria de hardware, `ModelRouter` Zero Cost, `14` contratos de agentes, `GraphOrchestrator` SQLite e `4` servidores MCP iniciais (`10` novos testes). |
| **Fase 7** | Asset & Audio Pipeline | **CONCLUÍDA & ARQUIVADA (`014`)** | `AssetRegistry`, validadores binários PNG/WAV/OGG + licenças, sintetizadores stdlib, `asset-mcp`/`audio-mcp` e auditoria Godot (`6` novos testes). |
| **Fase 8** | Game QA & Balance Engine | **CONCLUÍDA & ARQUIVADA (`015`)** | `StaticAnalyzer`, `BalanceVerifierEngine` (11 gêneros), `QAEngine` 4 pilares + profiling Godot 4.4 (`9` novos testes). |
| **Fase 9** | Automação (`n8n Community`) | **CONCLUÍDA & ARQUIVADA (`016`)** | 20 exports `WF-001`..`WF-020` livres de credenciais, validador *fail-closed*, `AutomationEngine`, servidor webhook loopback e service Compose `n8n` (`6` novos testes). |
| **Incremento P1 (`ADR-010`)** | Engine Selection & Orchestration System | **CONCLUÍDO & ARQUIVADO (`017`)** | Seleção por 14 critérios + relatório justificativo, interface `EngineAdapter` (`GodotAdapter`, `UnityAdapter`, `UnrealAdapter` fail-closed), Spec `v2` retrocompatível (`10` novos testes). |
| **Incremento P2 (`ADR-010`)** | Orquestração de Ferramentas & Assets 3D/PBR | **CONCLUÍDO & ARQUIVADO (`018`)** | Inspetores/sintetizadores `glTF`/`GLB`/`OBJ`/`FBX`/`JPEG`/`MP3`/PBR, auditoria de `has_rig`/`has_materials`, `FMOD`/`Wwise` opcionais (`10` novos testes). |
| **Fase 10 (`P3`)** | Build & Distribuição Multi-Plataforma | **CONCLUÍDA & ARQUIVADA (`019`)** | `BuildManager` com pacotes SHA-256 verificáveis (`structural-source-bundle`), smoke test Godot pós-build, auditoria de segredos/assets e gate humano `RELEASE_APPROVED` (`7` novos testes). |
| **Incremento P4 (`ADR-010`)** | Sistemas Modulares de Gameplay & Agentes Seção 10 | **CONCLUÍDO & ARQUIVADO (`020`)** | Catálogo sob demanda de 8 módulos Godot/Unity/Unreal (`GameplaySystemInjector`) e alinhamento formal dos 13 papéis da Seção 10 (`5` novos testes). |
| **Fase 11 (`P5`)** | Gestão, Telemetria, RAG Local & Otimização | **CONCLUÍDA & ARQUIVADA (`021`)** | `LocalRagMemory` (TF-IDF + cosseno offline), `OptimizationAdvisor` com aprovação humana e `FactoryDashboard` multi-projeto (`4` novos testes; `136` totais). |

---

## Trilha Paralela do Jogo-Âncora (`Zaikor: Zenkai Infinite`)

Preservado intacto na raiz (`ADR-006`) até eventual autorização explícita do operador:
- `Bloco 1 (002 & 003)` — Arquivado (`BigNum`, `BalanceConfig`, `TerrainHeightmap`, `DDTankBallistics`, `IdleEconomy`, `CombatFsm`, `BalanceVerifier`).
- `Sprint 4A (005)` — Arquivado (`ActionWorldConfig`, `ActionCombatCore`, `ActionBalanceVerifier`).
- `Sprint 4B (006)` — Arquivado (`project.godot` + cliente jogável 2D Dark Fantasy + `verify_engine_boot.gd`).
- `Sprint 4C (007)` — **Não iniciado** (*Ports & Adapters* externos e export comercial `.aab` aguardando contratação/decisão humana).
