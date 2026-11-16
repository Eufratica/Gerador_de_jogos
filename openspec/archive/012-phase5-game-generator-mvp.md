# OpenSpec Change 012: Fase 5 — Game Generator (MVP)

- **ID:** `012-phase5-game-generator-mvp`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 5 — Game Generator (MVP)`
- **Capabilities Alvo:** `game-factory` (`GF-01`, `GF-02`, `GF-03`), `game-projects` (`GP-02`), `game-specification` (`GS-01`), `game-templates` (`TPL-01`)

---

## 1. Explore & Propose

Concluímos o **MVP funcional da PlayForge Factory** em `factory/playforge/generator/`, conectando `ProjectManager` (Fase 2), `SpecificationGenerator` + `SpecificationValidator` (Fase 3) e `TemplateRegistry` + `TemplateValidator` (Fase 4) para gerar **projetos Godot 4.4 isolados e jogáveis** em `games/<project_id>/`, sem tocar no jogo-âncora `Zaikor`.

---

## 2. Design Técnico (`factory/playforge/generator/`)

- `schemas.py`: `GENERATION_MANIFEST_SCHEMA_VERSION = 1`, `PREVIEW_REPORT_SCHEMA_VERSION = 1`, `GeneratorError`, `GenerationConflictError`, `GenerationVerificationError`.
- `config_mapper.py`: funções determinísticas `render_project_godot`, `map_spec_to_runtime_config` (com normalização determinística anti-softlock de campanha e perfil de equilíbrio auditável) e `render_generated_verification_test` (`tests/unit/verify_generated_game.gd` com 18 assertions).
- `game_generator.py`: `GameGenerator` com `generate_project`, `verify_generated_project` e `package_preview_artifact`:
  - Criação automática de `games/.gdignore` para impedir colisão com `Zaikor`.
  - Bloqueio de `zaikor` (`ProtectedProject`), spec não aprovada/adulterada (`ApprovalRequired`), template `DEPRECATED`/incompatível (`TemplateCompatibilityError`) e ausência de Godot CLI (`GenerationVerificationError`).
  - Idempotência (`UP_TO_DATE`), detecção de conflito/adulteração pós-geração (`GenerationConflictError` sem `--force`), hashes `SHA-256` em `specs/generation_manifest.json`, validação headless em `specs/verification_report.json` e pacote ZIP determinístico + `.sha256` + JSON em `games/<project_id>/builds/`.
- `cli_handlers.py` + `cli.py`: subcomandos `game-generate`, `game-verify` e `game-package`.
- `factory/tests/test_game_generator.py`: 7 testes (incluindo geração real + execução Godot 4.4 headless + CLI end-to-end).

---

## 3. Critérios de Aceitação (`Verify`) — Evidências

- [x] Bloqueia `zaikor`, specs ausentes/não aprovadas/adulteradas, templates `DEPRECATED`/incompatíveis e ausência de Godot CLI.
- [x] Gera projeto Godot isolado com `games/.gdignore`, hashes `SHA-256` por arquivo, idempotência (`UP_TO_DATE`) e bloqueio de conflito sem `--force`.
- [x] Executa `Godot 4.4 --headless` real sobre o projeto gerado (`tests/unit/verify_generated_game.gd`, 18 assertions, exit code `0`, `< 1s`).
- [x] Produz pacote determinístico `.zip`, `.sha256` e `-preview-report.json` em `games/<project_id>/builds/`.
- [x] Suíte Python completa (`factory/tests/`) passa 100% (`69` testes em `20.266 s` — `ELAPSED_S: 20.824`) e jogo-âncora `Zaikor` permanece intacto.
