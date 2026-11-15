# OpenSpec Change 005: Sprint 4A — Núcleo Puro 2D, Mundos Interconectados, Altares, Combos/Magias e Verificador Headless

- **ID:** `005-action-world-combat-core`
- **Status:** `ARCHIVED` *(Etapas 1, 2, 3 e 4 concluídas; promovido para `openspec/archive/` em 2026-11-15)*
- **Versão Semântica:** `v0.3.0-core-action` *(Sprint 4A concluído)*
- **Dependências:**
  - [004-gow-2d-action-magic-game.md](../changes/004-gow-2d-action-magic-game.md) (`APPROVED_IN_EXECUTION`)
  - [002-bignum-and-ddtank-ballistics.md](002-bignum-and-ddtank-ballistics.md) (`ARCHIVED`)
  - [003-economy-fsm-and-balance-verifier.md](003-economy-fsm-and-balance-verifier.md) (`ARCHIVED`)

---

## 1. Escopo Entregue (Sprint 4A)

1. **`config/action_world_v1.json` + `src/core/action_world_config.gd` (`class_name ActionWorldConfig`):**
   - Schema JSON declarativo e validador *fail-closed* para:
     - Física 2D lateral (`move_speed = 460`, `jump_velocity = 980`, `gravity = 2100`, `dash_speed = 980`, `dash_iframe_s = 0.22s`), combos de 3 golpes (`slash_1`, `slash_2`, `chain_cleave_3`) e 4 poderes mágicos ativos (`chaos_flames` [BURN], `glacial_tempest` [FREEZE], `sky_lightning` [SHOCK], `titan_aegis` [SHIELD + STAGGER]).
     - 5 arquétipos (`shade_stalker`, `bone_sentinel`, `hex_acolyte`, `titan_warden_w1`, `abyss_colossus_w2`).
     - **2 Mundos interconectados (8 salas):** `world_1_ashen_citadel` (`w1_gate` ➔ `w1_catacombs` ➔ `w1_sanctuary` [Altar nº 1] ➔ `w1_boss_throne`) ligado por portal bidirecional a `world_2_crimson_foundry` (`w2_bridge` ➔ `w2_foundry` ➔ `w2_altar` [Altar nº 2] ➔ `w2_abyss_throne`).
2. **`src/core/action_combat_core.gd` (`class_name ActionCombatCore`):**
   - Motor determinístico 2D puro integrando plataformas unidirecionais, *dash* com *i-frames*, cancelamento, combo chain, 4 magias com mana/cooldown/status, IA inimiga com telégrafo (`WINDUP -> STRIKE -> RECOVERY`), quebra de postura ➔ **Boss QTE** (`2500 ms`), **Altares de Salvamento** (cura 100% + checkpoint snapshot `export_checkpoint_snapshot`/`restore_from_checkpoint`), Forja de upgrades (`IdleEconomy` + `BigNum`) e *revive* *fail-closed* (`resolve_defeat_revive`).
3. **`src/factory/action_balance_verifier.gd` + `tests/integration/run_action_verifier.gd`:**
   - Bot autônomo em `20 Hz` (`SIM_DT = 0.05s`) atravessando os 2 mundos, usando altares, comprando upgrades, esquivando ataques telegrafados, lançando as 4 magias e finalizando chefes no QTE.
4. **Testes Unitários Puros (`tests/unit/test_action_world_core.gd`):**
   - Suite incorporada em `tests/unit/run_unit_tests.gd` cobrindo validação *fail-closed*, plataforma `y >= 190px`, combo chain, cooldowns das 4 magias, *i-frames*, Altar de Salvamento, quebra de postura + QTE, tranca de portais, recusa de revive sem verificação e *round-trip* de snapshot.

---

## 2. Calibração & Achados da Etapa 3

- Na simulação física, ajustamos `jump_velocity` para `980.0` (`H_max ≈ 228.6 px`) para alcançar plataformas de `194 px` / `334 px`, centralizamos `HOMING_STRIKE` na altura vertical `y` do alvo elevado, ajustamos `vx = 0` em `ATTACK_RECOVERY` e calibrou-se `titan_warden_w1` (`hp = 2600`, `posture = 230`) e `abyss_colossus_w2` (`hp = 8200`, `posture = 340`) para garantir combate real com esquivas telegrafadas.

---

## 3. Critérios de Aceitação & Evidência Verificada (Etapa 3)

- [x] **Isolamento estático (`src/core/*.gd`):** `Select-String` confirmou **0** usos funcionais de `Node`, `SceneTree`, `FileAccess`, `HTTP`, `get_environment`, `get_unix_time`, `AdMob`, `Billing`, `DirAccess`, `OS`, `Time` ou `ProjectSettings`.
- [x] **Unitários puros `< 1s` (`run_unit_tests.gd`):** Exit code **`0`** em **`615.85 ms`** — **`229` assertions, `0` falhas** (`BigNum`: 34, `BalanceConfig`: 15, `DDTankBallistics`: 26, `IdleEconomy`: 95, `CombatFsm`: 21, `ActionWorldCore`: 38).
- [x] **`ActionBalanceVerifier` headless (`run_action_verifier.gd`):** Exit code **`0`** em **`741.30 ms`**:
  - `F2P_PURE [PASS]`: `clear_t=64.2s | worlds=2 | rooms=8 | altars=2 | magics=36 | qtes=10 | dodges=10 | deaths=0 | atk_lv=11 | gold=4.72K`
  - `F2P_REWARDED [PASS]`: `clear_t=66.6s | worlds=2 | rooms=8 | altars=2 | magics=37 | qtes=11 | dodges=11 | deaths=0 | atk_lv=11 | gold=4.72K`
