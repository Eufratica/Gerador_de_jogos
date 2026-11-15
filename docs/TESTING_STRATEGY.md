# TESTING_STRATEGY.md — Estratégia & Comandos de Teste

## 1. Camadas de Teste por Escopo

| Camada | Escopo Atual (Jogo-Âncora `Zaikor`) | Evolução Prevista na Fábrica |
| :--- | :--- | :--- |
| **Static Validation** | `Select-String` isolamento `src/core/` + scan de segredos + check fronteira `src/engine/` | Suite Python unificada validando todos os `games/*`, specs e manifests |
| **Unit Tests** | `tests/unit/run_unit_tests.gd` (6 suítes, `229` assertions em `~243 ms`) | Suíte Python (`pytest`) para Fábrica/Generator/Schemas + suítes Godot por template/jogo |
| **Integration Tests** | `verify_engine_boot.gd` (`14` assertions de SceneTree, Forja, save/offline) | Testes de contrato entre API, LangGraph, Banco/pgvector, MCP e Godot CLI |
| **Balance Tests** | `run_action_verifier.gd` (`~581 ms`, 20Hz) & `run_balance_verifier.gd` (72h Idle/DDTank) | Runners configuráveis por gênero de jogo |
| **Build & Security Tests** | Scan estático atual; sem build `.aab`/`.exe` automatizado ainda | Validação de permissões, manifests, sandbox subprocess e assinatura |

---

## 2. Linha de Base Executada na Fase 0 (`cab6ee8`)

Executado via Godot `4.4.stable.official.4c311cbee` (`--headless`):

```powershell
# Unitários puros (< 1s): PASS — 229 assertions | Failed: 0 | Elapsed: 242.56 ms
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/unit/run_unit_tests.gd

# Verificador de ação 20Hz: PASS — Elapsed: 580.77 ms | F2P_PURE=64.2s, F2P_REWARDED=66.6s, 0 soft-locks
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/integration/run_action_verifier.gd

# Boot das cenas: PASS — Assertions: 14 | Failed: 0
.\tools\godot\Godot_v4.4-stable_win64_console.exe --headless --no-header --path . --script res://tests/integration/verify_engine_boot.gd -- --save-path=C:/caminho/gravavel/boot_save.json
```

**Limitações registradas hoje:**
- No sandbox atual, `user://` (`AppData/Roaming/Godot/app_userdata`) não tem permissão de escrita, exigindo `-- --save-path=<caminho_permitido>` em `verify_engine_boot.gd` quando rodado dentro de sandbox restrito.
- `run_balance_verifier.gd` (72h sobre `CombatFsm`/`BalanceVerifier`, ~8.5 min de duração histórica) não foi re-executado na inspeção rápida da Fase 0.
- Ainda **não existem** testes Python da fábrica nem testes em dispositivo Android físico.
