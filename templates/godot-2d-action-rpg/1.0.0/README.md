# Template: `godot-2d-action-rpg` (`v1.0.0`)

Template base **Godot 4.4+ / GDScript** extraido dos componentes reutilizaveis do jogo-ancora `Zaikor: Zenkai Infinite` sob separacao estrita Ports & Adapters (`src/core/` puro vs. `src/engine/`).

## Sistemas Incluidos
- `BigNum` (`src/core/big_num.gd`): aritmetica deterministica de grande escala.
- `SeededRng` (`src/core/seeded_rng.gd`): PRNG XorShift32 seedavel.
- `GameLoopCore` (`src/core/game_loop_core.gd`): nucleo puro e data-driven de loop 2D (heroi, inimigos de sala, dash/ataque, economia e progresso entre salas).
- `LocalCheckpointStore` (`src/engine/local_checkpoint_store.gd`): persistencia local JSON *fail-closed* versionada.
- `Main` (`src/engine/main.tscn` + `src/engine/main.gd`): cena de boot enxuta conectando dados JSON, core puro e entrada/renderizacao 2D.
- `TestHarness` + `run_template_tests.gd`: suíte determinística headless `< 1s`.

## Licenca
- MIT (compatível com uso comercial e politica Zero Cost da PlayForge Factory).
