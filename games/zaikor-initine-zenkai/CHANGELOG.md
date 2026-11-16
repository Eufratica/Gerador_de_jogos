# CHANGELOG.md — Zaikor: Initine Zenkai

## [0.1.0-etapa1] - 2026-11-16

### Added
- Instalação verificada por SHA-512 da `Godot 4.7.2 Stable` (`4.7.2.stable.official.ed1daf0bf`) em `../../tools/godot-4.7.2/` após aprovação da Opção A (`ZIZ-GATE-01`), preservando `tools/godot/` (`4.4-stable`).
- `project.godot` configurado em `gl_compatibility`, `1280×720`, `vsync_mode=1` e `13` ações iniciais no `InputMap`.
- Núcleo puro em `scripts/core/graphics_config.gd` (`ZizGraphicsConfig`) e `scripts/core/game_bootstrap.gd` (`ZizGameBootstrap`).
- Cena raiz 3D em `scenes/main/main.tscn` e `scenes/main/main.gd` com iluminação direcional econômica, céu procedural sombrio, plano de referência com colisão, marco Initine, HUD diagnóstico (`F1`/`F2`/`F3`) e suporte a `--benchmark-frames`.
- Suíte unitária headless (`tests/unit/`: `16` assertions, `0` falhas em `3.28 ms`) e teste de integração de boot (`tests/integration/verify_main_boot.gd`: `0` nós órfãos) mais baseline inicial na `Intel(R) Iris(R) Xe Graphics`.

## [0.0.1-phase0] - 2026-11-16

### Added
- Provisionamento isolado em `games/zaikor-initine-zenkai/` registrado no `ProjectManager` da PlayForge Factory (`ADR-ZIZ-001`), preservando integralmente o jogo-âncora na raiz.
- Auditoria real de hardware e ferramentas em `docs/performance/ENVIRONMENT_AUDIT.md` (`i5-1135G7`, `Intel Iris Xe`, `DIMM A 8 GB + DIMM B 4 GB @ 2133 MT/s` flex-mode, `132.56 GB` livres em `C:`, `Blender 5.3.0`, `FFmpeg 9.0.2`, `Ollama 0.40.16` + `qwen2.5-coder:3b`, `Godot 4.4.stable` instalado vs `4.7.2 Stable` disponível / `4.8 beta 3`).
- Documentos de governança e continuidade: `AGENTS.md`, `PROJECT.md`, `README.md`, `ROADMAP.md`, `TASKS.md`, `DECISIONS.md`, `VERSION`, `SESSION_STATE.md`, `HANDOFF.md`.
- Documentos de arquitetura, narrativa e registro de licenças: `docs/architecture/ARCHITECTURE.md`, `docs/narrative/LORE_AND_NARRATIVE.md`, `docs/art/ART_CREDITS.md`.
- Estrutura inicial SDD/OpenSpec em `openspec/` (`AGENTS.md`, `specs/architecture/spec.md`, `changes/001-phase0-environment-and-foundation/`).
- `GameSpecification` (`v2`, 3D Compatibility) validada em `specs/game_specification.json`, relatório de seleção de engine (14 critérios) em `specs/engine_selection_report.json`/`.md` e `GDD` completo (`25` seções) em `gdd/gdd.json`/`.md`.
