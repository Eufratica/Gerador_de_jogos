# OpenSpec Change 009: Fase 2 — Core da Fábrica & Multi-Projeto (`Factory Core` + `Project Manager`)

- **ID:** `009-phase2-factory-core-multiproject`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15 com aprovação do operador)*
- **Fase SDLC:** `Fase 2 — Core da Fábrica & Multi-Projeto`
- **Capabilities Alvo:** `game-factory` (`GF-01`, `GF-02`), `game-projects` (`GP-01`, `GP-02`)

---

## 1. Explore & Propose

Na Fase 1 entregamos o ambiente reproduzível (`Docker Compose`, `factory-runner` com Python `3.12` + Godot `4.4-stable`, scripts `playforge.sh` / `playforge.ps1`).  
Esta mudança introduziu o núcleo mínimo e *fail-closed* em `factory/playforge/` usando apenas a biblioteca padrão do Python (offline, determinístico com relógio injetável, sem dependências externas prematuras), capaz de:
1. Registrar explicitamente o jogo-âncora (`zaikor`, protegido contra alteração/exclusão) e múltiplos jogos novos isolados em `games/<project_id>/`.
2. Garantir isolamento estrito de workspace (*anti-path-traversal*, recusa de duplicados e separação física de artefatos por projeto com 7 subpastas: `specs`, `gdd`, `src`, `assets`, `tests`, `builds`, `logs`).
3. Gerenciar o ciclo de vida das 20 etapas da fábrica (`IDEIA` ➔ `OTIMIZACAO`) com exigência obrigatória de evidência e bloqueio *fail-closed* nas etapas de aprovação humana (`APROVACAO_HUMANA_ARQUITETURA` e `APROVACAO_HUMANA_PREVIEW`).
4. Registrar eventos auditáveis em JSONL estruturado (`data/logs/factory.jsonl`) e expor uma CLI (`python -m factory.playforge.cli`).

---

## 2. Design Técnico (`factory/playforge/`)

- `models.py`: constantes (`SCHEMA_VERSION`, `PROJECT_ID_RE`, `STAGES`, `APPROVAL_STAGES`, `ANCHOR_PROJECT_ID`) e hierarquia de exceções *fail-closed* (`FactoryError`).
- `logging_utils.py`: `StructuredLogger` gravando JSON Lines ordenados com relógio injetável.
- `registry.py`: `ProjectManager` com persistência atômica (temp file + `os.replace`) em `data/registry/projects.json`, manifest isolado por projeto (`games/<project_id>/project_manifest.json`), validação de IDs e confinamento de paths.
- `cli.py`: CLI `argparse` com subcomandos `init`, `list`, `show`, `create`, `approve`, `advance`.
- `factory/tests/test_factory_core.py`: suíte `unittest` cobrindo isolamento, proteções do âncora, persistência, corrupção, logs e gates de aprovação humana.

---

## 3. Critérios de Aceitação (`Verify`) — Evidências

- [x] Registro inicializa e protege o jogo-âncora `zaikor` (`ProtectedProject` em tentativas de sobrescrita/exclusão).
- [x] Novos projetos em `games/<project_id>/` respeitam validação de ID, anti-path-traversal (`WorkspaceEscape`), unicidade e isolamento total (`Cenário GP-02` / `GF-01`).
- [x] Máquina de estados bloqueia transição sem evidência (`EvidenceRequired`), bloqueia pulo de etapa (`InvalidTransition`) e bloqueia avanço em etapas humanas sem aprovação (`ApprovalRequired` — `Cenário GF-02`).
- [x] Registro corrompido falha explicitamente com `RegistryCorrupt`.
- [x] Suíte `unittest` passa 100% (19 testes em 0.692s com 0 falhas e 0 erros).
- [x] Testes do jogo-âncora `Zaikor` permanecem intactos (`229` unitários em 237.89 ms + Action Balance em 352.48 ms + Engine Boot em 14 assertions).

### Log de Execução dos Testes Python
```text
test_cli_create_and_show_project (test_factory_core.TestFactoryCli.test_cli_create_and_show_project) ... ok
test_cli_error_returns_json_and_code_1 (test_factory_core.TestFactoryCli.test_cli_error_returns_json_and_code_1) ... ok
test_cli_list_contains_anchor (test_factory_core.TestFactoryCli.test_cli_list_contains_anchor) ... ok
test_structured_logger_writes_json_lines (test_factory_core.TestFactoryCoreModelsAndLogging.test_structured_logger_writes_json_lines) ... ok
test_validate_project_id_invalid_slugs (test_factory_core.TestFactoryCoreModelsAndLogging.test_validate_project_id_invalid_slugs) ... ok
test_validate_project_id_valid_slugs (test_factory_core.TestFactoryCoreModelsAndLogging.test_validate_project_id_valid_slugs) ... ok
test_anchor_project_is_immutable_and_cannot_be_deleted (test_factory_core.TestProjectManager.test_anchor_project_is_immutable_and_cannot_be_deleted) ... ok
test_corrupted_registry_raises_registry_corrupt (test_factory_core.TestProjectManager.test_corrupted_registry_raises_registry_corrupt) ... ok
test_create_duplicate_project_fails (test_factory_core.TestProjectManager.test_create_duplicate_project_fails) ... ok
test_create_project_cannot_overwrite_anchor (test_factory_core.TestProjectManager.test_create_project_cannot_overwrite_anchor) ... ok
test_create_project_isolated_structure (test_factory_core.TestProjectManager.test_create_project_isolated_structure) ... ok
test_create_project_rejects_existing_workspace (test_factory_core.TestProjectManager.test_create_project_rejects_existing_workspace) ... ok
test_delete_mutable_project_requires_confirmation (test_factory_core.TestProjectManager.test_delete_mutable_project_requires_confirmation) ... ok
test_human_approval_gate_architecture (test_factory_core.TestProjectManager.test_human_approval_gate_architecture) ... ok
test_init_registry_creates_protected_anchor (test_factory_core.TestProjectManager.test_init_registry_creates_protected_anchor) ... ok
test_resolve_game_path_confinement_and_anti_traversal (test_factory_core.TestProjectManager.test_resolve_game_path_confinement_and_anti_traversal) ... ok
test_state_machine_rejects_stage_skip (test_factory_core.TestProjectManager.test_state_machine_rejects_stage_skip) ... ok
test_state_machine_rejects_without_evidence (test_factory_core.TestProjectManager.test_state_machine_rejects_without_evidence) ... ok
test_state_machine_sequential_advance (test_factory_core.TestProjectManager.test_state_machine_sequential_advance) ... ok

----------------------------------------------------------------------
Ran 19 tests in 0.692s

OK
TOTAL TESTS: 19
FAILURES: 0
ERRORS: 0
```
