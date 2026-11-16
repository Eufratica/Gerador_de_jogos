# Capability Specification: `game-testing`

- **Capability ID:** `game-testing`
- **Status:** `IMPLEMENTED_PHASE_8` *(Gates GDScript do jogo-âncora + QA Engine e Balance Engine multi-projeto operacionalizados em `factory/playforge/qa_engine/`)*
- **Referência Técnica:** [docs/QA_STRATEGY.md](../../docs/QA_STRATEGY.md) | [docs/TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md) | [015-phase8-game-qa-balance-engine.md](../../openspec/archive/015-phase8-game-qa-balance-engine.md)

## Contratos de Verificação

1. **Execução Real Obrigatória:** Nenhum teste é dado como aprovado sem execução observada pós-edição final e registro de comando, ambiente, contagens, exit code e data.
2. **Gates Ativos do Jogo-Âncora (`Godot 4.4.stable --headless`):**
   - `tests/unit/run_unit_tests.gd`: suíte pura (`src/core/`) determinística e `< 1s` (`229 assertions, 0 failed`).
   - `tests/integration/run_action_verifier.gd`: campanha 20Hz (`Mundo 1 -> Mundo 2`, `0 soft-locks`).
   - `tests/integration/verify_engine_boot.gd`: smoke test SceneTree real (`14 assertions, 0 failed`).
   - `tests/integration/run_balance_verifier.gd`: simulação 72h sobre `CombatFsm`/`BalanceVerifier`.
3. **QA Engine & Balance Engine Multi-Projeto (`factory/playforge/qa_engine/`):**
   - **Pilar Estático (`StaticAnalyzer`):** escopo isolado por projeto (`zaikor` somente leitura), remoção de comentários `#` antes de validar pureza em `src/core/`, integridade `res://`, bloqueio de segredos/`.env`/keystores e conferência de `specs/generation_manifest.json`.
   - **Balanceamento Multi-Gênero (`BalanceVerifierEngine`):** 3 perfis determinísticos (`F2P_PURE`, `CASUAL_OPTIMAL`, `HARDCORE_STRESS`) com `seed` injetável cobrindo os 11 gêneros suportados (`action-rpg`, `idle-rpg`, `platformer-2d`, `roguelike`, `tower-defense`, `puzzle`, `arcade`, `strategy`, `adventure`, `simulation`, `ddtank-ballistics`), além de integração opcional com `run_action_verifier.gd` no `zaikor`.
   - **Godot Suites + Profiling Real (`QAEngine`):** execução em cópia temporária isolada de scripts `SceneTree` em `tests/`, medição objetiva via singleton `Performance` (`boot_ms`, `frame_ms_avg`, `static_memory_bytes`, `OBJECT_ORPHAN_NODE_COUNT == 0`) e auditoria do pilar de assets/licenças (`AssetRegistry`).
   - **CLI & MCP Confinado:** subcomandos `qa-static`, `qa-balance`, `qa-profile`, `qa-run` e tools `qa_run_static_audit`, `qa_run_balance_audit`, `qa_run_full_pipeline` e `qa_read_report` em `testing-mcp`.

## Cenários Verificáveis

- **Cenário `GT-01` (Fail-Closed em Violação de Core):** Comentários `#` não geram falso positivo, mas código real em `src/core/*.gd` importando/usando `Node`, `SceneTree`, `FileAccess`, rede ou env global reprova `qa-static` com arquivo e linha exatos.
- **Cenário `GT-02` (Evidência de Desempenho & Nós Órfãos):** Nenhuma métrica de FPS/memória/tempo é inventada; `qa-profile` mede em Godot 4.4 headless e falha fechado se `orphan_nodes_after_free > 0` ou houver `SCRIPT ERROR:`.
- **Cenário `GT-03` (Integridade `res://` & Higiene de Segredos):** Referências `res://` inexistentes em `project.godot`, `.tscn`/`.tres` ou `src/`, credenciais literais, arquivos proibidos ou adulteração contra `generation_manifest.json` reprovam a auditoria estática.
- **Cenário `GT-04` (Balanceamento Multi-Gênero Fail-Closed):** Todos os 11 gêneros suportados executam simulação determinística com `seed`; specs matematicamente invencíveis (`clear_rate == 0`) ou taxas de gacha inválidas (`!= 1.0`) reprovam `qa-balance` com `BalanceVerificationError` (`--strict`).
