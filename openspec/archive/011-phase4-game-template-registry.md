# OpenSpec Change 011: Fase 4 — Game Template Registry

- **ID:** `011-phase4-game-template-registry`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 4 — Game Template Registry`
- **Capabilities Alvo:** `game-templates` (`TPL-01`), `game-factory` (`GF-01`), `game-projects` (`GP-01`)

---

## 1. Explore & Propose

Na Fase 3 entregamos o Game Specification Engine (`factory/playforge/spec_engine/`).  
A Fase 4 entregou o **Game Template Registry** completo, com o primeiro template validado extraído dos módulos reutilizáveis do jogo-âncora `Zaikor: Zenkai Infinite` (`docs/GAME_TEMPLATES.md`), preservando intacta toda a raiz `res://` (`ADR-006`):
1. Diretório `templates/` isolado do `Zaikor` via `templates/.gdignore`.
2. Template versionado `templates/godot-2d-action-rpg/1.0.0/` (`template_manifest.json`, `README.md` MIT, `skeleton/` e `demo/` executável em Godot `4.4-stable` headless com 10 arquivos Godot/GDScript/JSON).
3. Pacote `factory/playforge/template_registry/` (apenas stdlib Python): contratos tipados, `TemplateValidator` *fail-closed*, cálculo `SHA-256` do esqueleto, runner Godot isolado em diretório temporário (`run_demo_tests`), catálogo SemVer `TemplateRegistry` (busca, compatibilidade com `GameSpecification`, seleção vinculada a spec aprovada gravando `specs/template_selection.json`, comparação e depreciação versionada preservando projetos/versões antigas).
4. Subcomandos CLI `template-*` integrados em `factory/playforge/cli.py` e suíte dedicada `factory/tests/test_template_registry.py`.

---

## 2. Design Técnico

- `templates/.gdignore` + `templates/godot-2d-action-rpg/1.0.0/` (`template_manifest.json`, `README.md`, `skeleton/`, `demo/`):
  - `src/core/big_num.gd`, `src/core/seeded_rng.gd`, `src/core/game_loop_core.gd` (100% puro e determinístico).
  - `src/engine/local_checkpoint_store.gd`, `src/engine/main.gd`, `src/engine/main.tscn`, `config/template_defaults.json`, `project.godot`.
  - `tests/unit/test_harness.gd`, `tests/unit/run_template_tests.gd` (10 assertions headless < 1s).
- `factory/playforge/template_registry/`:
  - `schemas.py`: `TEMPLATE_MANIFEST_SCHEMA_VERSION = 1`, `TEMPLATE_ID_RE`, `TEMPLATE_REQUIRED_FIELDS`, `TEMPLATE_OPTIONAL_FIELDS`, `TEMPLATE_ALL_ALLOWED_FIELDS`, `APPROVED_OPEN_SOURCE_LICENSES`, `ALLOWED_TEST_RUNNERS`.
  - `validator.py`: `TemplateValidator`, `TemplateError`, `TemplateValidationError`, `TemplateNotFoundError`, `TemplateCompatibilityError`.
  - `registry.py`: `TemplateRegistry` com `list_templates`, `search_templates`, `get_template`, `validate_template`, `check_spec_compatibility`, `select_best_template`, `select_template_for_project`, `compare_templates`, `deprecate_template`.
  - `cli_handlers.py`: registro e despacho de `template-list`, `template-show`, `template-validate`, `template-select`, `template-compare`, `template-deprecate`.

---

## 3. Critérios de Aceitação (`Verify`) — Evidências

- [x] `templates/.gdignore` isola o catálogo; `playforge.ps1 test-win` do jogo-âncora `Zaikor` passa sem conflitos de `class_name` e com `git diff --stat -- project.godot src/ config/ tests/ .gitignore` vazio.
- [x] Template `godot-2d-action-rpg` `1.0.0` possui `template_manifest.json` válido, licença `MIT`, `skeleton/` íntegro (10 arquivos, checksum `SHA-256`) e `demo/` validado em Godot 4.4 headless com exit code `0` (`10 assertions | Failed: 0`).
- [x] `TemplateValidator` rejeita *fail-closed* campos desconhecidos, campos obrigatórios ausentes, coerção `bool`➔`int`, licenças não aprovadas, arquivos ausentes ou não declarados, extensões proibidas e tentativas de *path traversal*.
- [x] `TemplateRegistry` ordena por SemVer, bloqueia seleção se `GameSpecification` não estiver aprovada (`ApprovalRequired`) ou em `zaikor` (`ProtectedProject`), compara diferenças entre versões e deprecia (`DEPRECATED`) sem apagar arquivos ou afetar versões ativas (`Cenário TPL-01`).
- [x] Suíte Python completa (`factory/tests/`) passa 100% (`62` testes em `4.602 s`: `19` core + `28` spec + `15` template registry incluindo execução real do Godot headless no template demo).
