# OpenSpec Change 013: Fase 6 — AI Engine, Multiagentes & MCP

- **ID:** `013-phase6-ai-engine-agents-mcp`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 6 — AI Engine, Multiagentes & MCP`
- **ADR Associada:** `ADR-009` em [DECISIONS.md](../../DECISIONS.md)
- **Capabilities Alvo:** `ai-agents` (`AI-01`, `AI-02`, `AI-03`, `MCP-01`), `game-factory`, `security` (`SEC-01`, `SEC-02`)

---

## 1. Explore & Propose

### 1.1 Auditoria Real de Ambiente e Hardware
- **Sistema / Python:** Windows 11 (`AMD64`), Python `3.13.18`, SQLite `3.53.1`, `8` threads lógicas, ~`11.74 GB` RAM física reportada (`5.7Gi` RAM + `2.0Gi` swap no WSL2), GPU integrada sem GPU dedicada CUDA (`nvidia-smi` ausente).
- **Ollama / Dependências Pip:** binário `ollama` ausente neste host; pacotes `langgraph`, `langchain`, `mcp`, `httpx`, `requests`, `pydantic` e `jsonschema` ausentes no runtime Python local.

### 1.2 Arquitetura Implementada (`Stdlib-First` — `ADR-009`)
1. `factory/playforge/security_utils.py`: mascaramento recursivo de segredos (`scrub_secrets`), detecção de marcadores de *prompt injection*, bloqueio de arquivos secretos (`.env`, `.keystore`, `.pem`, `.key`, `id_rsa`) e registro JSONL sanitizado.
2. `factory/playforge/ai/`:
   - `schemas.py`: catalogo de modelos local (`Tier S`, `Tier M`, `Tier L`), extrator estrito de JSON para saídas não confiáveis (`UntrustedOutputError`), telemetria padronizada e exceções `AIError`.
   - `model_router.py`: `inspect_environment()` com leitura real de hardware/Ollama, `OllamaClient` loopback-only (`urllib.request` + transporte injetável para testes) bloqueando endpoints externos (`PolicyViolationError`) e falhando fechado sem fallback pago (`ProviderUnavailableError`), e `ModelRouter` com gate de `Tier L` em CPU 12 GB e log em `data/logs/ai_router.jsonl`.
   - `agents.py`: `AgentRegistry` validando os **14 contratos oficiais** de `docs/AGENT_CONTRACTS.md` e aplicando `authorize_tool` por mínimo privilégio (sem wildcard `*`).
   - `orchestrator.py`: `SqliteCheckpointer` (`data/checkpoints/orchestrator.sqlite3`), `GraphOrchestrator` com anti-loop (`max_iterations`, `max_retries`, `timeout_seconds`), pausa em `APROVACAO_HUMANA_SPEC` e retomada via `workflow-resume`, incluindo o pipeline completo `build_mvp_generation_orchestrator`.
   - `cli_handlers.py` + `cli.py`: subcomandos `ai-health`, `agent-list`, `workflow-run`, `workflow-resume`, `mcp-list-tools`, `mcp-call`.
3. `factory/playforge/mcp/`:
   - `schemas.py` e `base_server.py`: `MCPServer` `JSON-RPC 2.0` (`initialize`, `tools/list`, `tools/call`, `serve_stdio`) com validação estrita de argumentos, autorização por `agent_id` e auditoria sanitizada em `data/logs/mcp_audit.jsonl`.
   - `servers.py`: 4 servidores confinados (`game-project-mcp`, `game-design-mcp`, `godot-mcp`, `testing-mcp`).
4. `factory/tests/test_ai_mcp.py`: 10 novos testes unitários e E2E cobrindo hardware gate, `SEC-01`, `SEC-02`, anti-loop, pause/resume até projeto Godot verificado em headless, `stdio` JSON-RPC e CLI completa.

---

## 2. Critérios de Aceitação (`Verify`) — Evidências

- [x] `ai-health` reporta hardware real (`11.74 GB` RAM, `8` threads, `DAEMON_UNAVAILABLE`) e `paid_fallback_enabled: false`.
- [x] `ModelRouter` bloqueia endpoints comerciais (`PolicyViolationError`), falha fechado com Ollama offline (`ProviderUnavailableError`), bloqueia `Tier L` sem GPU/24GB e rejeita JSON inválido/injetado (`UntrustedOutputError`).
- [x] Todos os 14 contratos de agentes passam validação estrita e aplicam mínimo privilégio em `authorize_tool`.
- [x] `GraphOrchestrator` + `SqliteCheckpointer` persistem checkpoints, pausam em gate humano, retomam até geração + verificação Godot 4.4 real e interrompem loops/timeouts com `LoopLimitExceededError`.
- [x] Servidores MCP atendem `JSON-RPC 2.0` via `stdio`, bloqueiam escrita em `zaikor`, fuga cross-project (`SEC-01`), `.env`/keystores e agentes não autorizados, mascarando segredos nos logs.
- [x] Suíte Python completa (`79` testes em `factory/tests/`) e suíte do jogo-âncora `Zaikor` (`playforge.ps1 test-win`) passam 100% após a última edição sem modificar `Zaikor`.
