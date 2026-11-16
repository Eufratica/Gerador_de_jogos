# OpenSpec Change 016: Fase 9 — Automação (`n8n Community`)

- **ID:** `016-phase9-automation-n8n`
- **Status:** `[ARCHIVED]` *(concluída em `2026-11-15`; promovida para [openspec/specs/automation/spec.md](../specs/automation/spec.md))*
- **Fase SDLC:** `Fase 9 — Automação (n8n Community)`
- **Capabilities Entregues:** `automation` (`AUT-01`..`AUT-04`), `security` (`SEC-01`, `SEC-02`), `infrastructure`
- **Referências:** [docs/AUTOMATION.md](../../docs/AUTOMATION.md) | [docs/INFRASTRUCTURE.md](../../docs/INFRASTRUCTURE.md) | [LICENSE_COMPLIANCE.md](../../LICENSE_COMPLIANCE.md) | [FREE_TIER_POLICY.md](../../FREE_TIER_POLICY.md)

---

## 1. Resumo da Entrega

1. **Biblioteca Exportável `automation/exports/` (`WF-001` .. `WF-020`):**
   - 20 arquivos JSON n8n Community determinísticos (`WF-001_project_initialization.json` a `WF-020_factory_monitoring.json`), todos com `active: false`, `meta.schemaVersion: 1`, sem credenciais e apontando apenas para loopback (`http://127.0.0.1:8787/webhook/WF-xxx`).
2. **Pacote `factory/playforge/automation/`:**
   - [schemas.py](../../factory/playforge/automation/schemas.py): `OFFICIAL_WORKFLOW_CATALOG` (`WF-001`..`WF-020`), `AUTOMATION_SCHEMA_VERSION = 1`, `ALLOWED_LOOPBACK_HOSTS`, `FORBIDDEN_COMMERCIAL_DOMAINS` e exceções *fail-closed* (`AutomationError`, `WorkflowValidationError`, `HumanGateBlockedError`).
   - [exporter.py](../../factory/playforge/automation/exporter.py): `build_workflow_export` e `generate_official_exports`.
   - [validator.py](../../factory/playforge/automation/validator.py): `validate_workflow_export` e `validate_exports_directory(..., strict=True)` bloqueando credenciais, segredos/tokens, domínios comerciais, URLs não-loopback, arquivos órfãos, arquivos proibidos (`.env`/chaves) e ausência de itens do catálogo.
   - [runner.py](../../factory/playforge/automation/runner.py):
     - `AutomationEngine`: executa `WF-001`..`WF-020` sobre módulos reais da fábrica, sanitiza *prompt injection* (`scan_prompt_injection`), protege `zaikor` (`ProtectedProject`), integra gates humanos (`WF-004` via `APROVACAO_HUMANA_ARQUITETURA`, `WF-014` via `SqliteCheckpointer`, `WF-016` via `APROVACAO_HUMANA_PREVIEW`, `spec` via `SpecificationGenerator.approve_specification`), audita em `data/logs/automation_audit.jsonl` (preservando leituras de `WF-020`/`WF-017` sem sujar `data/`) e valida `WF-015` com `QAEngine` antes de empacotar.
     - `AutomationWebhookServer`: servidor HTTP `127.0.0.1` em stdlib (`GET /health`, `POST /webhook/<workflow_id>`) com bloqueio explícito de bind externo, limite de payload de 1 MiB e modo background seguro por thread.
   - [cli_handlers.py](../../factory/playforge/automation/cli_handlers.py) + [cli.py](../../factory/playforge/cli.py): subcomandos `automation-list`, `automation-export`, `automation-validate`, `automation-trigger`, `automation-approve`, `automation-serve`.
3. **Infraestrutura Opcional Containerizada:**
   - [docker-compose.yml](../../docker-compose.yml): serviço `n8n` (`docker.n8n.io/n8nio/n8n:1.95.3`, `profiles: ["automation"]`, container `playforge_n8n`) em `127.0.0.1:${PLAYFORGE_N8N_PORT:-5679}:5678` (preservando porta `5678` ocupada no host), telemetria desativada, volume nomeado `playforge_n8ndata` e mount somente leitura `./automation/exports:/workspace/automation/exports:ro`.
   - [.env.example](../../.env.example), [playforge.sh](../../infrastructure/scripts/playforge.sh) e [playforge.ps1](../../infrastructure/scripts/playforge.ps1): variáveis `PLAYFORGE_N8N_PORT=5679`, `PLAYFORGE_AUTOMATION_BRIDGE_PORT=8787` e comando `up-automation`.
4. **Testes Entregues (`factory/tests/test_automation.py`):**
   - Cobertura completa de `AUT-01`..`AUT-04`: validação estrita dos 20 exports reais, rejeição *fail-closed* de credenciais/tokens/URLs/órfãos, anti-injection/proteção `zaikor`/bloqueio `0.0.0.0`, ciclo ponta a ponta dos 20 workflows (`WF-001`..`WF-020`) com Godot 4.4 headless real, `AutomationWebhookServer` HTTP real e roundtrip CLI (`6` novos testes; `100` testes Python totais aprovados).
   - Nota de ambiente: container `playforge_n8n` e `docker compose config` via WSL permanecem para execução fora do sandbox Windows (`Wsl/E_ACCESSDENIED` no sandbox).
