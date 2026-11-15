# Capability Specification: `game-testing`

- **Capability ID:** `game-testing`
- **Status:** `PARTIAL_ACTIVE` *(Gates do jogo-âncora operacionais em GDScript; camada multi-projeto planejada para Fase 8)*
- **Referência Técnica:** [docs/QA_STRATEGY.md](../../docs/QA_STRATEGY.md) | [docs/TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md)

## Contratos de Verificação

1. **Execução Real Obrigatória:** Nenhum teste é dado como aprovado sem execução observada pós-edição final e registro de comando, commit, exit code, contagens e data.
2. **Gates Ativos do Jogo-Âncora (`Godot 4.4.stable --headless`):**
   - `tests/unit/run_unit_tests.gd`: suíte pura (`src/core/`) determinística e `< 1s` (`229 assertions, 0 failed`).
   - `tests/integration/run_action_verifier.gd`: campanha 20Hz (`Mundo 1 -> Mundo 2`, `0 soft-locks`).
   - `tests/integration/verify_engine_boot.gd`: smoke test SceneTree real (`14 assertions, 0 failed`).
   - `tests/integration/run_balance_verifier.gd`: simulação 72h sobre `CombatFsm`/`BalanceVerifier`.
3. **Evolução na Fase 8 (Fábrica):** QA Engine genérico multi-projeto integrando validação estática, unitários Python/Godot, headless scene/gameplay checks, asset/license checks, profiling medido e simuladores de balanceamento por gênero.

## Cenários Verificáveis

- **Cenário `GT-01` (Fail-Closed em Violação de Core):** Se qualquer script em `src/core/` importar `Node`, `SceneTree`, `FileAccess`, rede ou env global, a auditoria estática reprova a validação.
- **Cenário `GT-02` (Evidência de Desempenho):** Nenhuma métrica de FPS ou alocação GC é afirmada sem coleta objetiva de profiler no hardware-alvo.
