# Capability Specification: `ai-agents`

- **Capability ID:** `ai-agents`
- **Status:** `IMPLEMENTED_PHASE_6` *(Model Router local Zero Cost, 14 contratos de agentes, GraphOrchestrator com checkpoint SQLite e 4 servidores MCP confinados)*
- **ADR Associada:** `ADR-009` em [DECISIONS.md](../../DECISIONS.md)
- **Referências Técnicas:** [docs/MODEL_ROUTER.md](../../docs/MODEL_ROUTER.md) | [docs/AGENT_CONTRACTS.md](../../docs/AGENT_CONTRACTS.md) | [docs/MCP.md](../../docs/MCP.md) | [security](../security/spec.md)

## Contratos Ativos

1. **Roteamento Local Fail-Closed (`AI-01` / `SEC-02`):**
   - Apenas endpoints loopback (`127.0.0.1`, `localhost`, `::1`) do **Ollama local** são aceitos por `OllamaClient` (`PolicyViolationError` para endpoints comerciais/externos).
   - Indisponibilidade do daemon local resulta em `ProviderUnavailableError` sem qualquer fallback pago.
   - Roteamento por hardware libera apenas tiers compatíveis (`S` / `M` no host atual `11.74 GB` sem GPU dedicada; `Tier L` bloqueado sem hardware compatível).
   - Saídas de LLM são tratadas como conteúdo não confiável (`UntrustedOutputError` em JSON inválido, campos proibidos ou marcadores de *prompt injection*).
   - Telemetria estruturada gravada em `data/logs/ai_router.jsonl` sem segredos.
2. **Contratos dos 14 Agentes (`AI-02`):**
   - Todos os 14 papéis oficiais (`orchestrator`, `research`, `game-design`, `architecture`, `gameplay`, `ui-ux`, `art-asset`, `audio`, `content`, `balance`, `qa`, `auditor`, `build`, `analytics`) registrados em `AgentRegistry` com `allowed_tools` explícitos (wildcard `*` proibido), limites anti-loop e `audit_log_enabled=True`.
3. **Orquestração Checkpointed em SQLite (`AI-03`):**
   - `GraphOrchestrator` + `SqliteCheckpointer` (`data/checkpoints/orchestrator.sqlite3`) garantem persistência passo a passo, pausa determinística em `APROVACAO_HUMANA_*`, retomada exata via `workflow-resume` e bloqueio de ciclos/timeouts (`LoopLimitExceededError`).
4. **Servidores MCP Confinados (`MCP-01` / `SEC-01`):**
   - Transporte `JSON-RPC 2.0` (`initialize`, `tools/list`, `tools/call`, `serve_stdio`) implementado para `game-project-mcp`, `game-design-mcp`, `godot-mcp`, `testing-mcp` (com ferramentas `qa_*` para `balance`, `qa` e `auditor`), `asset-mcp` e `audio-mcp`.
   - Toda ferramenta de mutação exige `project_id` válido, bloqueia `zaikor` (`ProtectedProject`), impede travessia cross-project (`WorkspaceEscape`), recusa arquivos secretos (`.env`, `.keystore`, chaves privadas) e grava auditoria sanitizada em `data/logs/mcp_audit.jsonl`.

## Cenários Verificáveis

- **Cenário `AI-01` (Hardware & Ollama Offline):** `ai-health` reporta RAM/CPU reais e `DAEMON_UNAVAILABLE` com `paid_fallback_enabled: false` quando Ollama está ausente; invocações falham fechado com `ProviderUnavailableError`.
- **Cenário `MCP-01` (Confinamento por `project_id`):** Tentativa de escrita em `../outro-jogo/`, em `zaikor` ou por agente sem permissão no contrato falha fechado com `MCPAccessDenied` (JSON-RPC `-32003`) e registro auditado sem expor credenciais.
