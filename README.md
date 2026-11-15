# PlayForge Factory (`Gerador_de_jogos`)

Plataforma orientada a especificações (**SDLC + SDD / OpenSpec**) para conceber, especificar, gerar, testar, balancear, compilar e evoluir múltiplos jogos 2D/2.5D em **Godot 4.x + GDScript**, utilizando ferramentas locais e gratuitas (**Zero Cost / Free First**).

> **Estado Atual:** **Fase 0 — Governança e Diagnóstico** *(documentação e governança da fábrica em validação humana; nenhum código da fábrica multi-projeto implementado ainda além dos verificadores `BalanceVerifier` e `ActionBalanceVerifier` do jogo-âncora).*

---

## Componentes do Repositório Hoje

1. **Fundação & Governança da Fábrica (Fase 0):**
   - Contratos e estado operacional em [AGENTS.md](AGENTS.md), [PROJECT.md](PROJECT.md), [ROADMAP.md](ROADMAP.md), [TASKS.md](TASKS.md), [DECISIONS.md](DECISIONS.md) e [docs/SESSION_STATE.md](docs/SESSION_STATE.md).
   - Especificações OpenSpec em [openspec/config.yaml](openspec/config.yaml), `openspec/specs/` e `openspec/changes/`.
2. **Jogo-Âncora Existente (`Zaikor: Zenkai Infinite`):**
   - Cliente 2D lateral Dark Fantasy em **Godot `4.4.stable` (`1920x1080`)** na raiz atual ([project.godot](project.godot)).
   - Núcleo puro headless em `src/core/` (`BigNum`, `SeededRng`, `BalanceConfig`, `IdleEconomy`, `CombatFsm`, `TerrainHeightmap`, `DDTankBallistics`, `ActionWorldConfig`, `ActionCombatCore`).
   - Cliente visual Godot em `src/engine/` (Tela Título, arena, silhuetas, VFX pool, SFX WAV procedural, HUD Touch/PC, Forja/Gacha/Baú Offline, checkpoint local).
   - Verificadores headless em `src/factory/` (`BalanceVerifier`, `ActionBalanceVerifier`).
   - *(Módulos do ciclo original de monetização em `src/adapters/` ainda contêm apenas `.gitkeep`.)*

---

## Como Executar os Testes Existentes (Godot `4.4.stable` Local)

Com o binário local provisionado em `tools/godot/Godot_v4.4-stable_win64_console.exe` *(ignorado pelo `.gitignore`)*:

```powershell
# 1. Testes unitários puros (< 1s, 229 assertions offline)
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/unit/run_unit_tests.gd

# 2. Verificador de progressão 20Hz do jogo-âncora (Mundo 1 -> Mundo 2)
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/integration/run_action_verifier.gd

# 3. Smoke test headless de boot das cenas e UI (passe --save-path em ambiente restrito se necessário)
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/integration/verify_engine_boot.gd
```

Para abrir o jogo-âncora em janela no Windows:

```powershell
.\tools\godot\Godot_v4.4-stable_win64.exe --path .
```

---

## Mapa Rápido da Documentação

- **Visão, Roadmap & Estado:** [PROJECT.md](PROJECT.md) | [ROADMAP.md](ROADMAP.md) | [TASKS.md](TASKS.md) | [CHANGELOG.md](CHANGELOG.md) | [docs/SESSION_STATE.md](docs/SESSION_STATE.md)
- **Governança, Segurança & Custo Zero:** [AGENTS.md](AGENTS.md) | [DECISIONS.md](DECISIONS.md) | [SECURITY.md](SECURITY.md) | [FREE_TIER_POLICY.md](FREE_TIER_POLICY.md) | [CONTRIBUTING.md](CONTRIBUTING.md)
- **Arquitetura & Fábrica (`docs/`):** [ARCHITECTURE.md](docs/ARCHITECTURE.md) | [ARQUITETURA.md](docs/ARQUITETURA.md) *(jogo-âncora histórico)* | [GAME_FACTORY.md](docs/GAME_FACTORY.md) | [GAME_TEMPLATES.md](docs/GAME_TEMPLATES.md) | [INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
