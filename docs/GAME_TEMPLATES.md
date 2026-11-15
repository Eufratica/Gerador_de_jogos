# GAME_TEMPLATES.md — Auditoria de Reúso do Jogo-Âncora & Template Registry (Fase 4)

## 1. Auditoria Real de Reusabilidade do Jogo-Âncora (`Zaikor` + Núcleo DDTank/Idle)

Inspeção módulo a módulo dos arquivos em `src/` e `tests/` no commit `cab6ee8`:

| Arquivo Atual | Classificação de Reúso | Ação Prevista na Fase 4 (Template Extraction) |
| :--- | :--- | :--- |
| `src/core/big_num.gd` | **100% Genérico** | Extrair para biblioteca base de matemática (`core-idle-math`) de templates Idle/RPG/Simulação. |
| `src/core/seeded_rng.gd` | **100% Genérico** | Extrair para biblioteca determinística universal de templates Godot. |
| `src/core/idle_economy.gd` | **Alta Reusabilidade (Parametrizável)** | Extrair núcleo de curvas exponenciais, Gacha c/ pity, Prestígio e Offline 8h anti-tamper; desacoplar chaves fixas (`ki_transformations`) via config. |
| `src/core/balance_config.gd` | **Template Específico (`Idle + DDTank`)** | Generalizar validador em módulos componíveis (economia, gacha, balística, mundo). |
| `src/core/terrain_heightmap.gd` | **Alta Reusabilidade (`Balística 2D`)** | Base pronta para futuro template de artilharia/destruição de terreno (`DDTank-like`). |
| `src/core/ddtank_ballistics.gd` | **Alta Reusabilidade (`Balística 2D`)** | Base pronta para futuro template de balística parabólica + vento + guia preditivo. |
| `src/core/combat_fsm.gd` | **Template Específico (`Idle + DDTank`)** | Preservar para o futuro template *Action Idle Ballistics*; não utilizado na cena atual do `Zaikor`. |
| `src/core/action_world_config.gd` | **Alta Reusabilidade (`Ação 2D Lateral`)** | Generalizar schema de mundos/salas/portais/altares para template *2D Action Side-Scroller*. |
| `src/core/action_combat_core.gd` | **Reutilizável c/ Parametrização** | Extrair sistema de plataformas, dash/i-frames, combos e postura/QTE; parametrizar lista de magias em vez de assumir 4 slots fixos de Zaikor. |
| `src/engine/vfx/vfx_pool.gd` | **Reutilizável (Núcleo de Pooling)** | Separar pool de textos flutuantes/sparks (genérico) dos 4 efeitos elementais específicos de `Zaikor`. |
| `src/engine/audio/procedural_sfx.gd` | **Reutilizável** | Generalizar sintetizador WAV em memória por receita JSON (sem nomes fixos de gameplay). |
| `src/engine/services/local_checkpoint_store.gd` | **Reutilizável** | Evoluir para camada genérica de save local validado/versionado por `game_id`. |
| `src/engine/actors/*`, `world_backdrop.gd`, `game_hud.gd`, `altar_forge_modal.gd` | **Específico do Jogo-Âncora (`Zaikor`)** | Manter no projeto `Zaikor`; usar apenas padrões de HUD Touch/PC e câmera como referência de template. |
| `tests/unit/test_harness.gd` | **100% Genérico** | Padronizar como harness base de testes GDScript em templates gerados. |
| `src/factory/balance_verifier.gd` & `action_balance_verifier.gd` | **Verificadores de Gênero** | Servirão de base para os plugins por gênero no `Balance Engine` (Fase 8). |

---

## 2. Contrato de Template (Fase 4)

Todo template registrado no **Game Template Registry** deverá definir:
- `template_id`, `name`, `template_version` (`SemVer`), `engine` (`godot`), `engine_version` (`4.4.stable`), `genre`, `supported_platforms`;
- `file_structure`, `available_systems`, `reusable_components`, `asset_slots`, `dependencies`, `config_schema_version`, `allowed_extensions`, `tests`, `license`, `documentation` e projeto demo validado.

**Regra de Isolamento:** Atualizar um template para `2.0.0` **nunca** altera projetos já gerados na versão `1.x`; migrações são explícitas e versionadas.

---

## 3. Ordem Recomendada de Templates Iniciais

Não tentar criar 11 gêneros de uma vez:
1. **`godot-2d-action-rpg` (Template 1 — Fase 4):** derivado diretamente do `ActionCombatCore` + `IdleEconomy` + `BigNum` + `SeededRng` + `LocalCheckpointStore` + `VfxPool`/`ProceduralSfx` validados no `Zaikor`.
2. **`godot-2d-idle-ballistics` (Template 2 — Posterior):** derivado de `CombatFsm` + `DDTankBallistics` + `TerrainHeightmap` + `IdleEconomy`.
