# OpenSpec Change 003: Passo 2B — Economia Idle, SeededRNG, CombatFSM e BalanceVerifier Headless

- **ID:** `003-economy-fsm-and-balance-verifier`
- **Status:** `ARCHIVED` *(Etapas 1, 2, 3 e 4 concluídas; promovido para `openspec/archive/` em 2026-11-15)*
- **Versão Semântica:** `v0.2.0-core-b` *(Fecha o Bloco 1 — Núcleo Puro & Fábrica Headless)*
- **Dependências:**
  - [001-core-architecture-and-ballistics.md](../changes/001-core-architecture-and-ballistics.md) (`APPROVED`)
  - [002-bignum-and-ddtank-ballistics.md](002-bignum-and-ddtank-ballistics.md) (`ARCHIVED`)

---

## 1. Escopo Entregue (Passo 2B)

1. **`src/core/seeded_rng.gd` (`class_name SeededRng`):**
   - Gerador determinístico XorShift32 mascarado em `0xFFFFFFFF` (`reseed` normaliza `0` para `0x6D2B79F5` + 4 rodadas de warm-up), portátil entre plataformas e 100% isolado de entropia do SO.
2. **`src/core/idle_economy.gd` (`class_name IdleEconomy`):**
   - Compras exponenciais `O(1)` em lote (`buy_upgrade` via `BigNum.geometric_series_sum`), overflow de `crit_rate > 1.0` para `crit_damage`, cap `attack_speed = 4.0`, mitigação de armadura por penetração, 5 estágios de Ki (`BASE` ➔ `ULTRA_INSTINCT`), multiplicadores de Gacha/equipamentos.
   - **Ganho Offline anti-tamper:** rejeição *fail-closed* para recuo de relógio (`now_utc_ms < last_seen_utc_ms`), mínimo `60s`, teto rígido `28.800s` (8h) e multiplicador `3.0x` do *Baú do Dragão* exigindo `reward_verified` ou `has_no_ads_pass`.
   - **Gacha transparente + Hard Pity (`50`):** puxadas `1x`/`10x`, garantia `MYTHIC` na 50ª puxada, cap diário de `3` puxadas `10x` por anúncio (reset por dia UTC) e bloqueio *fail-closed* sem verificação.
   - **Prestígio seguro:** exige `max_stage_reached >= 50`, concede `Soul Orbs`, preserva `best_stage_lifetime`, `gems`, multiplicadores de Gacha/`No-Ads Pass` e reinicia ouro, níveis, Ki, `current_stage = 1` e `max_stage_reached = 1` (eliminando *exploit* de prestígios infinitos em estágio `1`).
3. **`src/core/combat_fsm.gd` (`class_name CombatFsm`):**
   - Estados completos (`IDLE_AUTO`, `RAGE_BERSERK`, `DDTANK_AIM`, `DDTANK_FLIGHT`, `BOSS_QTE`, `DEFEAT_REVIVE_OFFER`, `PRESTIGE_RESET`) desacoplados da cena.
   - Decisões aprovadas implementadas: recusa/timeout de revive retorna para farmar waves normais no **mesmo estágio** (`farming_same_stage_waves`); `DDTANK_AIM` abre automaticamente em **Chefes Titânicos** (a cada `5` estágios) e sob demanda em qualquer Boss com POW cheio; janela `BOSS_QTE` de `2500 ms`.
4. **`src/factory/balance_verifier.gd` (`class_name BalanceVerifier`):**
   - Auditor headless *fail-closed* simulando `72h` (`259.200s`, `SIM_DT = 2.0s`) nos 3 perfis (`F2P_PURE`, `F2P_REWARDED`, `NO_ADS_PASS`) sobre `TerrainHeightmap` + `DDTankBallistics`.
   - Reprova automaticamente `BigNum` inválido, *stall* de run `> 600.0s`, falha em atingir Prestígio `>= 50`, recuperação pós-Prestígio `> 900.0s` ou regressão de monotonicidade `F2P_REWARDED < F2P_PURE`.
5. **Testes & Runners CLI (`tests/unit/` e `tests/integration/`):**
   - `tests/unit/test_idle_economy.gd`, `tests/unit/test_combat_fsm.gd`, `tests/unit/run_unit_tests.gd` e `tests/integration/run_balance_verifier.gd`.

---

## 2. Decisões Aprovadas & Lições Auditadas (Etapa 3)

- **Decisão 1A:** Recusa de `DEFEAT_REVIVE_OFFER` mantém jogador farmando waves no mesmo estágio com botão para desafiar o Boss.
- **Decisão 2A:** `DDTANK_AIM` automático em Chefes Titânicos (`% 5 == 0`) + manual via "POW!" com barra cheia.
- **Decisão 3A & Auditoria Real da Etapa 3:**
  - A primeira simulação do `BalanceVerifier` expôs um *exploit* crítico: `execute_prestige` não zerava `max_stage_reached`, permitindo prestígios repetidos a cada `~90s` após o 1º Prestígio (`2.861` prestígios falsos), além de `BalanceVerifier` medir *stall* apenas contra o recorde global em vez de `run_best_stage`.
  - Ambos foram corrigidos em `src/core/idle_economy.gd`, `src/factory/balance_verifier.gd` e cobertos por testes de regressão em `tests/unit/test_idle_economy.gd`. Sem afrouxar nenhuma regra do `BalanceVerifier`, `config/balance_v1.json` passou com 0 travamentos.

---

## 3. Critérios de Aceitação & Evidência Verificada

- [x] **Isolamento estático (`src/core/*.gd`):** `Select-String` confirmou `0` usos funcionais de `Node`, `SceneTree`, `FileAccess`, `HTTP`, `get_environment`, `get_unix_time`, `AdMob`, `Billing`, `DirAccess`, `OS.`, `Time.` ou `ProjectSettings` (apenas ocorrências em comentários `##` de cabeçalho).
- [x] **Unitários puros `< 1s` (`run_unit_tests.gd`):** Exit code **`0`** em **`203.94 ms`** — **`191` assertions, `0` falhas** (`BigNum`: 34, `BalanceConfig`: 15, `DDTankBallistics`: 26, `IdleEconomy`: 95, `CombatFsm`: 21).
- [x] **Simulador Headless 72h (`run_balance_verifier.gd` com `config/balance_v1.json`):** Exit code **`0`** (`Elapsed: 512306.33 ms`, `0` falhas):
  - `F2P_PURE [PASS]`: `best_stage=274 | prestiges=89 | max_stall=88.0s | max_wave=14.0s | max_recovery=480.0s | gold=10.26Sx | orbs=8.65K`
  - `F2P_REWARDED [PASS]`: `best_stage=289 | prestiges=81 | max_stall=88.0s | max_wave=72.0s | max_recovery=472.0s | gold=208.39Sx | orbs=8.09K`
  - `NO_ADS_PASS [PASS]`: `best_stage=288 | prestiges=80 | max_stall=88.0s | max_wave=68.0s | max_recovery=472.0s | gold=43.09Sx | orbs=8.01K`
