# OpenSpec Capability: `automation` (`n8n Community` + Ponte Local)

- **Status:** `IMPLEMENTED_PHASE_9` (`OpenSpec 016`)
- **Última Atualização:** `2026-11-15`
- **Responsabilidade:** Orquestração externa de workflows macro (`WF-001`..`WF-020`), gatilhos loopback (`127.0.0.1`), agendamentos e filas **Human-in-the-Loop**, sem acoplar regras internas de agentes (`LangGraph`/SQLite) nem mutar o jogo-âncora `Zaikor`.

---

## 1. Requisitos e Contratos (`AUT-01` .. `AUT-04`)

### `AUT-01` — Catálogo Oficial (`WF-001`..`WF-020`) & Exports n8n Determinísticos
- O catálogo `OFFICIAL_WORKFLOW_CATALOG` define os 20 workflows oficiais mapeados em [docs/AUTOMATION.md](../../docs/AUTOMATION.md), persistidos em `automation/exports/` (`WF-001_project_initialization.json` a `WF-020_factory_monitoring.json`).
- Todos os exports nascem com `active: false`, `meta.schemaVersion = 1` (`AUTOMATION_SCHEMA_VERSION`), nós padrão compatíveis com n8n Community (`n8n-nodes-base.webhook` ou `n8n-nodes-base.scheduleTrigger` para `WF-017`/`WF-020`, `n8n-nodes-base.httpRequest`, `n8n-nodes-base.if`, `n8n-nodes-base.respondToWebhook`/`noOp`) e URL de ponte exclusivamente em loopback (`http://127.0.0.1:8787/webhook/WF-xxx`).

### `AUT-02` — Validação *Fail-Closed* e Zero Credenciais/Segredos
- `validate_workflow_export` e `validate_exports_directory(..., strict=True)` rejeitam com `WorkflowValidationError`:
  - campo `credentials` não vazio em nós;
  - literais de tokens (`sk-`, `ghp_`, `AIza`, `Bearer`, chaves PEM) ou campos sensíveis preenchidos (`api_key`, `secret`, `password`, `access_token`, etc.);
  - domínios comerciais externos (`FORBIDDEN_COMMERCIAL_DOMAINS`) ou qualquer URL HTTP(S) fora de `ALLOWED_LOOPBACK_HOSTS` (`127.0.0.1`, `localhost`, `::1`);
  - `active: true`, arquivos órfãos, arquivos proibidos (`.env`, `.keystore`, `.pem`, `.key`) ou ausência de qualquer item do catálogo `WF-001`..`WF-020`.

### `AUT-03` — Proteção Anti-Injection, Confinamento `Zaikor` e Bind Loopback
- `AutomationEngine.trigger_workflow` sanitiza recursivamente payloads externos via `scan_prompt_injection` e bloqueia travessia de chaves antes de executar qualquer handler (`WorkflowValidationError`).
- Operações mutáveis contra o jogo-âncora `zaikor` são bloqueadas via `require_mutable_project` (`ProtectedProject`). Workflows estritamente *read-only* (`WF-017`, `WF-020`) não mutam projetos nem criam `data/` se o registro não estiver inicializado.
- `AutomationWebhookServer` proíbe *bind* fora de `ALLOWED_LOOPBACK_HOSTS`, limita payload HTTP a 1 MiB (`_MAX_WEBHOOK_BYTES`) e expõe `GET /health` + `POST /webhook/<workflow_id>`.

### `AUT-04` — Gates Humanos Obrigatórios (`Human-in-the-Loop`) & Integração Multi-Módulo
- `WF-004` (`architecture`), `WF-014` (`Human Approval` para estágios `architecture | spec | release`) e `WF-016` (`Publishing`) aplicam bloqueio humano explícito:
  - `WF-004` sem aprovação prévia (`APROVACAO_HUMANA_ARQUITETURA`) e `WF-014` criam checkpoint `WAITING_HUMAN_APPROVAL` no `SqliteCheckpointer` (falham em `--strict` com `HumanGateBlockedError` ou respondem HTTP `202` na ponte webhook).
  - `automation-approve` / `approve_human_gate` registra decisão nominal, persiste aprovação no registro (`APROVACAO_HUMANA_ARQUITETURA` / `APROVACAO_HUMANA_PREVIEW`) ou `specs/spec_approval.json` via `SpecificationGenerator.approve_specification`.
  - `WF-016` exige `APROVACAO_HUMANA_PREVIEW` aprovada (`ApprovalRequired` / HTTP `403` sem aprovação) e gera exclusivamente manifesto offline local (`store_upload_executed: false`).
  - `WF-015` executa gate de QA (`QAEngine`) antes do empacotamento; `WF-017` coleta apenas índices locais sem PII; `WF-018` gera proposta JSON (`auto_applied: false`); `WF-019` inspeciona checkpoints SQLite; `WF-020` audita exports, ambiente local de IA e Godot CLI.

---

## 2. Interfaces Entregues

- **Pacote Python:** `factory/playforge/automation/` (`__init__.py`, `schemas.py`, `exporter.py`, `validator.py`, `runner.py`, `cli_handlers.py`).
- **CLI PlayForge (`factory/playforge/cli.py`):** `automation-list`, `automation-export`, `automation-validate [--strict]`, `automation-trigger <WF-xxx> [--project] [--payload-json] [--strict]`, `automation-approve <run_id> --approver <nome> (--approve|--reject) --notes <texto>`, `automation-serve [--host 127.0.0.1] [--port 8787]`.
- **Infraestrutura Opcional (`docker-compose.yml`):** serviço `n8n` (`docker.n8n.io/n8nio/n8n:1.95.3`, `profiles: ["automation"]`) em `127.0.0.1:${PLAYFORGE_N8N_PORT:-5679}:5678` (evitando a porta `5678` já ocupada no host), telemetria desativada, mount somente leitura `./automation/exports:/workspace/automation/exports:ro` e comando `up-automation` em `playforge.sh` / `playforge.ps1`.
