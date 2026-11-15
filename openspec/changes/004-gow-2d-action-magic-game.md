# OpenSpec Change 004: Jogo 1 — Ação Dark Fantasy 2D Lateral (Estilo God of War com Mundos Interconectados, Poderes Mágicos & Altares)

- **ID:** `004-gow-2d-action-magic-game`
- **Status:** `APPROVED_IN_EXECUTION` *(Decisões A1, A2, A3 e A4 aprovadas pelo operador em 2026-11-15; executando via Sprints `005` [4A] ➔ `006` [4B] ➔ `007` [4C])*
- **Versão Alvo:** `v0.3.0-gow-slice`
- **Dependências Preservadas (Bloco 1 — 100% Reaproveitadas):**
  - [002-bignum-and-ddtank-ballistics.md](../archive/002-bignum-and-ddtank-ballistics.md) (`ARCHIVED`)
  - [003-economy-fsm-and-balance-verifier.md](../archive/003-economy-fsm-and-balance-verifier.md) (`ARCHIVED`)

---

## 1. Decisões Aprovadas pelo Operador (Base Imutável do Jogo 1)

1. **A1 — Movimentação & Câmera:** **2D Lateral Puro** (*estilo Dead Cells / God of War: Betrayal*), com corrida esquerda/direita, pulo/plataformas e esquiva direcional com *i-frames*.
2. **A2 — Direção Visual (Bloco 4B):** **Silhueta Dark Fantasy de alto contraste + armas, runas e magias brilhantes** (*estilo Shadow of Death*), construída nativamente no Godot 4.4 com polígonos/rigs 2D + shaders neon e partículas sem bloqueio por arte externa.
3. **A3 — Progressão & Mundo:** **Mundos interconectados estilo God of War**, compostos por salas/áreas de exploração e combate, **Altares de Salvamento** (checkpoints que curam HP/Mana, salvam progresso local/Supabase e abrem Forja/Runas/Upgrades) e **Chefes Titânicos** ao final de cada mundo.
4. **A4 — Ordem de Entrega (Sprints):**
   - **Sprint 4A (`OpenSpec 005`):** Núcleo puro 2D + Mundos/Salas/Altares + Combos/Magias/Postura/QTE + `ActionBalanceVerifier` headless;
   - **Sprint 4B (`OpenSpec 006`):** Cena visual Dark Fantasy jogável no Godot 4.4 (`1920x1080` PC + Touch Mobile), câmera, hitstop, shaders/VFX, UI de Forja/Altar/Baú;
   - **Sprint 4C (`OpenSpec 007`):** Ports & Adapters (*AdMob + UMP*, *Google Play Billing v6+ `no_ads_pass` + Restore*, *Supabase Cloud Save anti-tamper*, *SQLite Telemetry*) + exportação Android `.aab`.

---

## 2. Escopo Geral e Invariantes

- Toda matemática de escala (`BigNum`), progressão de atributos/forja/Gacha/offline 8h (`IdleEconomy`) e PRNG determinístico (`SeededRng`) do Bloco 1 são reutilizados diretamente pelo núcleo de ação.
- **`src/core/` permanece 100% livre** de `Node`, `SceneTree`, `FileAccess`, rede ou env global, rodando testes unitários offline em `< 1.000 ms`.
- Toda nomenclatura, herói, mundos, inimigos e magias são **originais de Dark Fantasy mitológica** para conformidade integral com políticas da Google Play Store.
