# OpenSpec Archive 006: Sprint 4B — Cena Jogável 2D Dark Fantasy (`Zaikor: Zenkai Infinite`)

- **ID:** `006-gow-2d-dark-fantasy-godot-scene`
- **Status:** `ARCHIVED` (`v0.4.0-playable-slice` — Promovido após aprovação do operador nas decisões A1–A4 e conclusão dos gates da Etapa 3)
- **Versão Arquivada:** `v0.4.0-playable-slice`
- **Dependências:**
  - [004-gow-2d-action-magic-game.md](../changes/004-gow-2d-action-magic-game.md) (`APPROVED_IN_EXECUTION`)
  - [005-action-world-combat-core.md](005-action-world-combat-core.md) (`ARCHIVED` — `v0.3.0-core-action`)

---

## 1. Resumo da Entrega (`src/engine/` & `src/core/` & `project.godot`)

Cliente jogável 2D lateral em Godot `4.4` (`1920x1080` lógico, override janela `1280x720`, orientação paisagem):
1. **[main.tscn](../../src/engine/main.tscn) & [main.gd](../../src/engine/main.gd) & [local_checkpoint_store.gd](../../src/engine/services/local_checkpoint_store.gd):**
   - Tela Título Dark Fantasy (**"ZAIKOR: ZENKAI INFINITE"**) com **"CONTINUAR DO ALTAR"** / **"NOVO JOGO"** e persistência local *fail-closed* via `LocalCheckpointStore` (caminho padrão `user://checkpoint_v1.json`, parametrizável por `save_path` para testes herméticos).
2. **[battle_arena.tscn](../../src/engine/scenes/battle_arena.tscn) & [battle_arena.gd](../../src/engine/scenes/battle_arena.gd):**
   - Controlador de arena e câmera (`Camera2D` com acompanhamento suave, hitstop e tremor por trauma), carregando `config/balance_v1.json` + `config/action_world_v1.json` em modo *fail-closed*, conectando entrada PC + Touch diretamente ao `ActionCombatCore` sem duplicar regras de negócio.
   - Preservação de timestamp offline (`saved_utc_ms`) na restauração em [action_combat_core.gd](../../src/core/action_combat_core.gd) (`restore_from_checkpoint`) para cálculo do Baú do Dragão.
3. **Renderização Dark Fantasy & Zero GC:**
   - [world_backdrop.gd](../../src/engine/world/world_backdrop.gd): paralaxe por mundo (`world_1_ashen_citadel` vs. `world_2_crimson_foundry`), plataformas, baús, Altares de Salvamento pulsantes e portais travados/liberados.
   - [silhouette_warrior.gd](../../src/engine/actors/silhouette_warrior.gd) & [silhouette_enemy.gd](../../src/engine/actors/silhouette_enemy.gd): silhuetas 2D de alto contraste, cachecol fluido, pós-imagens em *dash* / Fúria, telégrafos de `WINDUP` e status elementais.
   - [vfx_pool.gd](../../src/engine/vfx/vfx_pool.gd) & [procedural_sfx.gd](../../src/engine/audio/procedural_sfx.gd): pools pré-alocados para VFX das 4 magias + textos de dano via `BigNum.format`, e 16 SFX sintéticos `AudioStreamWAV` pré-gerados no `_ready()`.
4. **HUD & Modais ([game_hud.gd](../../src/engine/ui/game_hud.gd) & [altar_forge_modal.gd](../../src/engine/ui/altar_forge_modal.gd)):**
   - Barras de HP/Mana/Fúria, barra dupla de Chefe (**HP + Postura**), 4 magias com cooldown, botão contextual de Altar/Baú/Portal, controles Touch + dicas de teclado com toggle `Touch: ON/OFF`, QTE Finisher, derrota *fail-closed* (`Sprint 4C` bloqueado até integrar AdMob/Billing) e Modal de Forja/Gacha/Baú Offline.

---

## 2. Verificação da Etapa 3 (Evidências Reais Pós-Edição Final)

| Gate | Comando / Script | Resultado Observado |
| :--- | :--- | :--- |
| Isolamento `src/core/` | `Select-String` em `src/core/*.gd` | Passou — apenas ocorrências em comentários (`#`/`##`), zero acoplamento de engine/rede/env |
| Fronteira `src/engine/` & Segredos | Audit `src/engine/**/*.gd` & scan `src/`, `config/` | Passou — chamadas em `src/engine/` apenas delegam a `IdleEconomy`; 0 segredos encontrados |
| Unitários Puros (`< 1s`) | `res://tests/unit/run_unit_tests.gd` | `229 assertions | Failed: 0 | Elapsed: 750.23 ms` (`QUALITY GATE PASSED`) |
| Verificador Ação 20Hz | `res://tests/integration/run_action_verifier.gd` | `Elapsed: 1011.11 ms` — `F2P_PURE` (`64.2s`) & `F2P_REWARDED` (`66.6s`), `worlds=2, rooms=8, altars=2, 0 soft-locks` (`ACTION BALANCE GATE PASSED`) |
| Boot & Wiring Engine | `res://tests/integration/verify_engine_boot.gd` | `Assertions: 14 | Failed: 0`, log `--log-file` limpo sem `SCRIPT ERROR` (`ENGINE BOOT GATE PASSED`) |

---

## 3. Critérios de Aceitação Concluídos

- [x] **Zero lógica de negócio na Engine:** fórmulas de combate, economia exponencial, gacha e offline residem integralmente em `src/core/`.
- [x] **Verificação Headless de Cenas & Scripts (Godot 4.4 CLI):** instanciação de `main.tscn` e `battle_arena.tscn`, cast de magia, Forja, save/restore local e offline timestamp validados com `0` falhas (`14` assertions) + `229` unitários (`0` falhas) + `ActionBalanceVerifier` (`0` soft-locks).
- [x] **Controles PC + Touch e Cena `16:9` configurados e conectados:** `project.godot`, `BattleArena`, `GameHud` e `AltarForgeModal` estruturados e ligados para execução direta em janela desktop (`Godot_v4.4-stable_win64.exe --path C:\Jogo_Android`) e posterior empacotamento Android no Sprint 4C.
