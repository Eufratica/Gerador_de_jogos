# OpenSpec Change 010: Fase 3 — Game Specification Engine

- **ID:** `010-phase3-game-specification-engine`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 3 — Game Specification Engine`
- **Capabilities Alvo:** `game-specification` (`GS-01`, `GS-02`), `game-projects` (`GP-02`)

---

## 1. Explore & Propose

Na Fase 2 entregamos o Factory Core e o Project Manager em `factory/playforge/`.  
A Fase 3 implementou o **Game Specification Engine** em `factory/playforge/spec_engine/` usando apenas biblioteca padrão Python (offline, determinístico e *fail-closed*):
1. Schemas versionados (`SPEC_SCHEMA_VERSION = 1`, `GDD_SCHEMA_VERSION = 1`) para `GameSpecification` (34 campos contratuais cobrindo as 31 dimensões do Prompt Mestre v2.0) e `GameDesignDocument` (25 seções obrigatórias).
2. Validador *fail-closed* (`SpecificationValidator`): rejeição de campos ausentes, tipos errados (incluindo guarda explícita contra coerção `bool` ➔ `int`), enums desconhecidos, campos extras não autorizados (`additionalProperties: false`), formato SemVer, inconsistências semânticas (`gacha_rates` != 1.0, `total_rooms` divergente, referências de salas inexistentes) e checagem de compatibilidade (`check_compatibility`).
3. Gerador e fluxo de aprovação (`SpecificationGenerator`): geração e gravação atômica de `specs/game_specification.json`, `gdd/gdd.json` e `gdd/gdd.md` com vínculo explícito `linked_spec_id`/`linked_spec_version`, proteção do jogo-âncora `zaikor`, isolamento estrito de `game_id` e aprovação humana criptograficamente verificável via SHA-256 (`specs/spec_approval.json`, `approve_specification`, `verify_spec_approved`).
4. CLI estendida (`spec-validate`, `spec-generate`, `gdd-generate`, `spec-approve`).

---

## 2. Design Técnico (`factory/playforge/spec_engine/`)

- `schemas.py`: `SPEC_SCHEMA_VERSION`, `GDD_SCHEMA_VERSION`, `SEMVER_RE`, enums suportados, `SPEC_REQUIRED_FIELDS`, `GDD_SECTIONS`, `GDD_REQUIRED_FIELDS`, `GDD_ALLOWED_FIELDS`.
- `validator.py`: `SpecificationValidator`, `ValidationError`, `SchemaCompatibilityError`, `compute_spec_digest`, `parse_semver`.
- `generator.py`: `SpecificationGenerator` com `build_default_spec`, `generate_and_save_spec`, `build_default_gdd`, `generate_and_save_gdd`, `approve_specification` e `verify_spec_approved`.
- `cli.py`: subcomandos `spec-validate` (arquivo ou `--project`), `spec-generate`, `gdd-generate` e `spec-approve`.
- `factory/tests/test_spec_engine.py`: 28 testes unitários cobrindo todos os cenários positivos, negativos e de CLI.

---

## 3. Critérios de Aceitação (`Verify`) — Evidências

- [x] Validador aceita especificação válida completa e rejeita campos ausentes, tipos inválidos (incluindo `bool` como `int`), enums desconhecidos e campos desconhecidos.
- [x] Validador rejeita semântica inconsistente (soma de `gacha_rates != 1.0`, `total_rooms` divergente, salas com conexões inexistentes, engine/versão incompatível).
- [x] Validador aceita e valida GDD estruturado com as 25 seções obrigatórias e rejeita seções desconhecidas ou vazias.
- [x] Gerador produz `specs/game_specification.json`, `gdd/gdd.json` e `gdd/gdd.md` atomicamente dentro de `games/<project_id>/`, bloqueando escrita no jogo-âncora `zaikor` e desvios entre projetos.
- [x] Fluxo de aprovação grava `specs/spec_approval.json` com SHA-256 canônico e falha *fail-closed* caso a especificação seja alterada após a aprovação.
- [x] CLI `spec-validate`, `spec-generate`, `gdd-generate` e `spec-approve` operam com exit codes e JSON padronizados.
- [x] Suíte Python completa (`factory/tests/`) passa 100% (`47` testes em `1.285 s`, 0 falhas, 0 erros) e testes do jogo-âncora `Zaikor` seguem íntegros (`229` unitários em `331.27 ms` + Action Balance `397.90 ms` + Engine Boot `14` assertions).
