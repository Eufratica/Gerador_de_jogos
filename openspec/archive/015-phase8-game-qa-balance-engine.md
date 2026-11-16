# OpenSpec Change 015: Fase 8 — Game QA & Balance Engine

- **ID:** `015-phase8-game-qa-balance-engine`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 8 — Game QA & Balance Engine`
- **Capabilities Alvo:** `game-testing` (`GT-01`, `GT-02`, `GT-03`, `GT-04`), `ai-agents`, `security` (`SEC-01`, `SEC-02`)

---

## 1. Resumo da Implementação

1. **Pacote `factory/playforge/qa_engine/`:**
   - `schemas.py`: contratos de versão (`QA_REPORT_SCHEMA_VERSION = 1`, `BALANCE_REPORT_SCHEMA_VERSION = 1`), exceções `QAError`, `QAValidationError`, `BalanceVerificationError` e tabelas de regras estáticas.
   - `static_analyzer.py`: `StaticAnalyzer` + `ensure_auditable_project` / `collect_project_files` / `stage_isolated_godot_project`. Audita qualquer projeto (incluindo `zaikor` em modo *read-only* mesmo antes de `playforge init`), removendo comentários `#` antes de validar pureza estrita de `src/core/*.gd` (`GT-01`), checando integridade de referências `res://` (`GT-03`), bloqueando arquivos/credenciais proibidas e verificando hashes contra `specs/generation_manifest.json`.
   - `balance_verifier.py`: `BalanceVerifierEngine` — simulador determinístico multi-perfil (`F2P_PURE`, `CASUAL_OPTIMAL`, `HARDCORE_STRESS`) com 4 famílias parametrizáveis cobrindo todos os **11 gêneros suportados** em `GameSpecification`, bloqueando campanhas invencíveis, soft-locks, gacha inválido (`sum != 1.0`) e `NaN`/`Inf` (`GT-04`), além de integração opcional com o runner GDScript `run_action_verifier.gd` do `Zaikor`.
   - `runner.py`: `QAEngine` — integra os **4 pilares do QA** (`static`, `balance`, `godot_suites` + `godot_profile` via probe headless real com `Performance` monitors e verificação *fail-closed* de `OBJECT_ORPHAN_NODE_COUNT == 0` — `GT-02`, e `assets` via `AssetRegistry`), gravando `specs/qa_report.json` em projetos mutáveis e mantendo `zaikor` intacto.
   - `cli_handlers.py` + `cli.py`: subcomandos `qa-static`, `qa-balance`, `qa-profile` e `qa-run`.
2. **Servidores MCP & Contratos de Agentes:** adicionadas `qa_run_static_audit`, `qa_run_balance_audit`, `qa_run_full_pipeline` e `qa_read_report` em `testing-mcp` (`factory/playforge/mcp/servers.py`), e permissões de menor privilégio atualizadas para `balance`, `qa` e `auditor` (`factory/playforge/ai/agents.py`).
3. **Suíte de Testes:** `factory/tests/test_qa_balance_engine.py` (9 novos testes: auditoria estática real no `Zaikor`, violações `GT-01`/`GT-03`/segredos/hashes, simulação determinística dos 11 gêneros, rejeição de campanha invencível/gacha inválido `GT-04`, runner Godot do `Zaikor`, pipeline completo dos 4 pilares + assets + Godot 4.4, detecção real de leak de nós órfãos `GT-02`, profiling real do `Zaikor`, MCP e CLI; `94` testes Python totais).

---

## 2. Critérios de Aceitação (`Verify`) — Evidências

- [x] `qa-static zaikor --strict` valida `zaikor` em modo *read-only* (`43` arquivos escaneados, `9` scripts `src/core/`, `37` referências `res://`, `0` violações).
- [x] Injeção de `FileAccess` em `src/core/`, `preload("res://...")` inexistente, chave literal, `.env` ou hash adulterado falha fechado (`GT-01`, `GT-03`).
- [x] Todos os 11 gêneros de `SUPPORTED_GENRES` simulam deterministicamente com 3 perfis; campanhas invencíveis e gacha `!= 1.0` falham fechado (`GT-04`).
- [x] `qa-profile zaikor` e projetos gerados coletam métricas reais do `Performance` do Godot 4.4 headless (`boot_ms`, `frame_ms_avg`, `static_memory_bytes`, `orphan_nodes_after_free == 0`), enquanto nó órfão injetado via `Node.new()` é reprovado com `QAValidationError` (`GT-02`).
- [x] `qa-run zaikor --frames 3 --strict` e `qa-e2e` (com pacote de assets + Godot 4.4) passam nos 4 pilares.
- [x] Suíte Python (`94` testes em `factory/tests/`) e jogo-âncora `Zaikor` (`playforge.ps1 test-win`) passam 100% após a última edição sem modificar `Zaikor`.
