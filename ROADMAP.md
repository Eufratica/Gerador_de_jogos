# ROADMAP.md — PlayForge Factory

Roadmap incremental em **12 fases (Fase 0 a Fase 11)** com gates obrigatórios entre fases.  
**Regra:** Não avançar para uma fase posterior ignorando dependências ou validações da fase anterior.

---

## Estado Atual por Fase

| Fase | Nome | Status Atual | Critério de Saída |
| :--- | :--- | :--- | :--- |
| **Fase 0** | Governança e Diagnóstico | **CONCLUÍDA & ARQUIVADA (`007`)** | Documentação, OpenSpec, auditoria real do repo/jogo-âncora e ADRs `005`–`008` aprovados pelo operador. |
| **Fase 1** | Ambiente Reproduzível | **CONCLUÍDA & ARQUIVADA (`008`) — aguardando aprovação para Fase 2** | WSL2/Ubuntu 24.04, Docker/Compose, Dev Containers, Python, Godot CLI e scripts padronizados funcionando e testados. |
| **Fase 2** | Core da Fábrica & Multi-Projeto | **PLANEJADA** | `Factory Core`, `Project Manager`, registro/isolamento de múltiplos projetos, versionamento e logs estruturados testados. |
| **Fase 3** | Game Specification Engine | **PLANEJADA** | Schemas JSON versionados, validador *fail-closed*, gerador de `Game Specification` e `GDD` + fluxo de aprovação. |
| **Fase 4** | Game Template Registry | **PLANEJADA** | Auditoria final do jogo-âncora convertida em 1º template validado (`godot-2d-action-idle` ou similar) com contrato, testes e demo. |
| **Fase 5** | Game Generator (**MVP**) | **PLANEJADA** | Geração isolada e idempotente de um **2º projeto Godot funcional** a partir de spec aprovada + template validado. |
| **Fase 6** | AI Engine, Multiagentes & MCP | **PLANEJADA** | `Ollama` local (compatível com hardware real), `Model Router`, `LangGraph` com checkpointing e primeiros servidores MCP. |
| **Fase 7** | Asset & Audio Pipeline | **PLANEJADA** | `Asset Registry`, checagem de licença/procedência/hash, pipelines locais gratuitos e importação validada no Godot. |
| **Fase 8** | Game QA & Balance Engine | **PLANEJADA** | QA Engine reutilizável (static, unit, headless engine, gameplay, assets, perf) + Balance Verifiers por gênero. |
| **Fase 9** | Automação (`n8n Community`) | **PLANEJADA** | Workflows `WF-001`..`WF-020` versionados, exportáveis sem credenciais, integrando LangGraph/MCP e aprovações humanas. |
| **Fase 10** | Build & Distribuição | **PLANEJADA** | Build Engine multi-plataforma incremental, hashes, verificação de assinaturas/permissões e gate de aprovação pré-release. |
| **Fase 11** | Gestão, Telemetria & Evolução | **PLANEJADA** | Dashboard de gestão, coleta de métricas, memória `pgvector`/RAG e propostas de otimização assistidas e auditadas. |

---

## Trilha Paralela do Jogo-Âncora (`Zaikor: Zenkai Infinite`)

Antes da reformulação como fábrica completa, o repositório entregou até o **Sprint 4B (`OpenSpec 006`)**:
- `Bloco 1 (002 & 003)` — Arquivado (`BigNum`, `BalanceConfig`, `TerrainHeightmap`, `DDTankBallistics`, `IdleEconomy`, `CombatFsm`, `BalanceVerifier`).
- `Sprint 4A (005)` — Arquivado (`ActionWorldConfig`, `ActionCombatCore`, `ActionBalanceVerifier`).
- `Sprint 4B (006)` — Arquivado (`project.godot` + cliente jogável 2D Dark Fantasy + `verify_engine_boot.gd`).
- `Sprint 4C (007)` — **Não iniciado** (*Ports & Adapters* em `src/adapters/`: AdMob+UMP, Play Billing v6+, CloudSave HMAC, export `.aab`).

> **Decisão Pendente (`PEND-001` em [DECISIONS.md](DECISIONS.md)):** O operador deve decidir se a prioridade imediata após a Fase 1 (ou em paralelo controlado) será seguir diretamente pela **Fase 2 da PlayForge Factory** ou concluir antes o **Sprint 4C** do `Zaikor`.
