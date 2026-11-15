# OpenSpec Change 002: Passo 2A — BigNumber, Schema Config e Balística DDTank em GDScript Puro

- **ID:** `002-bignum-and-ddtank-ballistics`
- **Status:** `ARCHIVED` *(Etapas 1, 2, 3 e 4 concluídas; promovido para `openspec/archive/` em 2026-11-15)*
- **Dependência:** [001-core-architecture-and-ballistics.md](../changes/001-core-architecture-and-ballistics.md)
- **Runtime Alvo:** `Godot 4.4+ Standard (GDScript)` — execução headless CLI em `< 1s` (`tools/godot/Godot_v4.4-stable_win64_console.exe --headless`).

---

## 1. Escopo Entregue (Passo 2A)

1. **`src/core/big_num.gd` (`class_name BigNum`):**
   - Aritmética cósmica canônica `(mantissa: float, exponent: int)` com zero canônico `(0.0, 0)` e $1.0 \le m < 10.0$.
   - Proteção explícita *fail-closed* contra `NaN`, `Inf`, entrada negativa, divisão por zero e subtração negativa (`sub_clamped`).
   - Cálculo fechado $O(1)$ de soma geométrica (`geometric_series_sum`) validado até escalas extremas (`> 1e250`) e formatador visual com sufixos (`K`, `M`, `B`, `T`, `Qa`, `Qi`, ..., `Dc` + notação científica + *carry-over* de arredondamento).
2. **`src/core/balance_config.gd` (`class_name BalanceConfig`) + `config/balance_v1.json`:**
   - Parser/validador estrito de JSON (`parse_and_validate(json_text: String)`) totalmente hermético (sem ler arquivos ou variáveis de ambiente dentro do núcleo).
   - Valida 100% das invariantes da SDD `001` e falha fechado em erro de sintaxe, chave ausente, Gacha `!= 1.0`, cap offline `> 8h` ou multiplicador crítico incorreto.
3. **`src/core/terrain_heightmap.gd` (`class_name TerrainHeightmap`):**
   - Array pré-alocado `PackedFloat64Array` (`256` amostras) cobrindo a arena `16:9` (`1920.0 px`, `Zero GC Alloc`).
   - Interpolação linear `sample_height(x)`, rastreamento de `max_height` para *broadphase* e escavação de cratera `carve_crater(...)` limitada por `bedrock_y`.
4. **`src/core/ddtank_ballistics.gd` (`class_name DDTankBallistics`):**
   - Física cartesiana ($+x$ direita, $+y$ para cima) com aceleração de vento $a_x = w \cdot \kappa_w$, passo fixo $\Delta t = 1/120\,\text{s}$, *broadphase* AABB exato e interseção contínua segmento-círculo (`segment_circle_intersect`) sem *tunneling*.
   - Zonas de acerto: `HEAD_CORE` (**"POW! CRÍTICO NUCLEAR 10x"**) ➔ `BODY` (`1.0x`) ➔ `LIMB_GLANCING` (`0.5x`) ➔ `TERRAIN` (escava cratera lógica).
   - `compute_laser_guide_into(...)` gravando em buffers `PackedFloat64Array` pré-alocados (**Zero GC Alloc**).
   - `solve_aim_for_head(...)` com resolução analítica compensada pelo vento para `1.320` cenários.
5. **`tests/unit/` (Suíte Offline `< 1s`):**
   - `test_harness.gd`, `test_big_num.gd`, `test_balance_config.gd`, `test_ddtank_ballistics.gd` e runner *fail-closed* `run_unit_tests.gd`.

---

## 2. Critérios de Aceitação & Evidência de Verificação (Etapa 3)

- [x] Nenhum arquivo em `src/core/` referencia `Node`, `SceneTree`, rede, `FileAccess`, áudio, UI ou variáveis de ambiente globais (verificado por busca estática em `src/core/*.gd`).
- [x] `Godot_v4.4-stable_win64_console.exe --headless --path C:\Jogo_Android --script res://tests/unit/run_unit_tests.gd` executado offline com **exit code `0`** em **`226.58 ms`** (`< 1.000 ms`).
- [x] **`1.320` / `1.320` cenários determinísticos** (`11` ventos `[-100..+100]` x `10` distâncias `[1320..1580]` x `4` elevações x `3` perfis de terreno incluindo crateras) atingiram `HEAD_CORE` (`10.0x POW!`).
- [x] Total verificado: **`75` assertions (`BigNum`: 34, `BalanceConfig`: 15, `DDTankBallistics`: 26), `0 failed`**.
