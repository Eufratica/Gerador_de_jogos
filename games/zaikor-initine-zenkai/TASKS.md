# TASKS.md — Backlog Rastreável de Zaikor: Initine Zenkai

## Fase 0 / Etapa 0 — Análise do Ambiente, Governança e Preparação (`CONCLUÍDA`)

- [x] **ZIZ-001:** Provisionar projeto isolado `zaikor-initine-zenkai` via PlayForge CLI preservando `100%` do jogo-âncora 2D na raiz e garantindo `games/.gdignore`.
- [x] **ZIZ-002:** Inspecionar hardware real do host (`i5-1135G7`, `Intel Iris Xe`, `DIMM A 8 GB + DIMM B 4 GB @ 2133 MT/s = 11.74 GB flex-mode`, `132.56 GB` livres em `C:`) e ferramentas instaladas (`Godot 4.4.stable`, `Blender 5.3.0`, `FFmpeg 9.0.2`, `Ollama 0.40.16` + `qwen2.5-coder:3b`) -> [ENVIRONMENT_AUDIT.md](docs/performance/ENVIRONMENT_AUDIT.md).
- [x] **ZIZ-003:** Validar versão oficial estável do Godot (`4.7.2 Stable` lançada em 18/08/2026 vs `4.8 beta 3` em desenvolvimento — Seção 6.1 veta beta) e registrar decisão pendente `ADR-ZIZ-002` em [DECISIONS.md](DECISIONS.md).
- [x] **ZIZ-004:** Criar governança e memória contínua (`AGENTS.md`, `PROJECT.md`, `README.md`, `VERSION`, `ROADMAP.md`, `TASKS.md`, `DECISIONS.md`, `CHANGELOG.md`, `SESSION_STATE.md`, `HANDOFF.md`).
- [x] **ZIZ-005:** Criar documentação técnica/narrativa inicial ([ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md), [LORE_AND_NARRATIVE.md](docs/narrative/LORE_AND_NARRATIVE.md), [ART_CREDITS.md](docs/art/ART_CREDITS.md)).
- [x] **ZIZ-006:** Criar estrutura SDD/OpenSpec ([openspec/AGENTS.md](openspec/AGENTS.md), [openspec/specs/architecture/spec.md](openspec/specs/architecture/spec.md), change `001-phase0-environment-and-foundation`).
- [x] **ZIZ-007:** Gerar e validar *fail-closed* `gdd/gdd.json` (`25` seções), `gdd/gdd.md`, `specs/engine_selection_report.json` (`godot`, `89.23/100`) e `specs/game_specification.json` (`v2`, `spec-validate` aprovado).

---

## Gate Humano Fase 0 ➔ Etapa 1 (`APROVADO`)

- [x] **ZIZ-GATE-01:** Operador aprovou **Opção A (`Godot 4.7.2 Stable`)**, instalada paralelamente com SHA-512 validado em `../../tools/godot-4.7.2/` (preservando `tools/godot/` `4.4.stable`).

---

## Etapa 1 — Projeto Godot Funcional (`CONCLUÍDA — 0.1.0-etapa1`)

- [x] **ZIZ-101:** Change OpenSpec `002-godot-project-compatibility-base` criada e arquivada (com arquivamento da `001`).
- [x] **ZIZ-102:** `project.godot` configurado para **Compatibility Renderer (`gl_compatibility`)**, `1280×720`, `features=["4.7", "GL Compatibility"]` e `13` ações iniciais no `InputMap`.
- [x] **ZIZ-103:** Implementados `scripts/core/graphics_config.gd` (`low`/`medium`/`high` com bloqueio fail-closed de `Lumen`/`Nanite`/`RayTracing`/`forward_plus`), `scripts/core/game_bootstrap.gd`, cena `scenes/main/main.tscn` + `main.gd` (HUD e alternância `F1`/`F2`/`F3` + `--benchmark-frames`).
- [x] **ZIZ-104:** Executados testes headless (`16` assertions `3.28 ms`, boot `0` nós órfãos) e primeira execução real em GPU `Intel(R) Iris(R) Xe Graphics` (`31.0 FPS` reportados ao fim de 60 quadros; warmup inicial frio total `9.65 s` incluído na janela de bootstrap).

---

## Etapas 2 a 15 — Backlog Planejado da Vertical Slice (`PENDENTE`)

- [ ] **Etapa 2:** Câmera 3P suave com `SpringArm3D` (anticolisão, ajuste combate, sensibilidade/inversão) + corpo inicial articulado de Zaikor.
- [ ] **Etapa 3:** Movimentação 3D completa (caminhar, correr, rotação gradual, pular, esquiva, recuperação).
- [ ] **Etapa 4:** Sistema modular de combate (rápido, carregado, combo, buffer de entrada, guarda/parry, stagger, target-lock).
- [ ] **Etapa 5:** Inimigos e FSM de 8 estados (`Vulto do Eco`, variação ágil/resistente, `Sentinela de Cinza`).
- [ ] **Etapa 6:** Sistema `Initine`, estado `Zenkai` e árvore inicial de progressão modular.
- [ ] **Etapa 7:** Cenário modular *O Vale do Primeiro Eco* com LOD/culling e narrativa ambiental.
- [ ] **Etapa 8:** Interações (santuários, baús, colecionáveis) e puzzle de ressonância *Initine*.
- [ ] **Etapa 9:** Chefe *Arconte da Ruptura* com apresentação, fases, sinais claros e recompensa.
- [ ] **Etapa 10:** Menu inicial, HUD enxuto, menus internos (Pausa/Habilidades/Diário/Configurações/Acessibilidade) e tela de conclusão.
- [ ] **Etapa 11:** Salvamento versionado validado + checkpoint no santuário.
- [ ] **Etapa 12:** Camadas adaptativas de áudio e SFX originais (`FFmpeg` / síntese) + VFX controlados.
- [ ] **Etapa 13:** Cena de benchmark progressivo (passos 1–9 da Seção 7.4) e ajuste de otimização real.
- [ ] **Etapa 14:** Testes completos (unitários, integração, gameplay, save e regressão).
- [ ] **Etapa 15:** Validação final contra todos os critérios da Seção 22 e build Windows verificável.
