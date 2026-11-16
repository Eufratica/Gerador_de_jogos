# SESSION_STATE.md — Memória Operacional da PlayForge Factory

> **Regra de Continuidade:** Todo agente novo deve ler este arquivo na abertura da sessão para retomar o trabalho do estado verificado em disco e Git, sem depender de histórico de chat.

---

## 1. Snapshot Atual do Estado

- **Versão (`VERSION`):** `1.0.0`
- **Fases & Incrementos Concluídos:** **Fases 0–11 e Incrementos `P1`–`P5` (`OpenSpec 007`–`021`) concluídos e arquivados** sob `ADR-010`.
- **Jogo-Âncora:** `Zaikor: Zenkai Infinite` (`v0.4.0-playable-slice`), preservado integralmente na raiz (`ADR-006`); `git diff --stat -- project.godot src/ config/ tests/ .gitignore` vazio.
- **Ferramentas Locais Reais Detectadas no Host Windows 11 (`11.74 GB RAM`, `8 threads`, GPU integrada `Intel Iris Xe`):**
  - `Godot 4.4.stable.official.4c311cbee`: `tools/godot/Godot_v4.4-stable_win64_console.exe`
  - `Blender 5.3`: `C:/Program Files/Blender Foundation/Blender 5.3/blender.exe`
  - `FFmpeg 9.0.2`: instalado via `winget` (`Gyan.FFmpeg`)
  - `Ollama 0.40.16`: instalado via `winget` (`%LOCALAPPDATA%/Programs/Ollama/ollama.exe`)
  - `Unity` e `Unreal Engine 5`: **não instalados** neste host (adaptadores *Ports & Adapters* geram scaffold + validação estrutural e falham fechado com `EngineToolchainUnavailableError` quando execução/compilação é solicitada sem editor).

## 2. Capacidades Implementadas (`017`–`021`)

| Incremento / Fase | OpenSpec | Módulos Principais | Suíte Dedicada |
| :--- | :--- | :--- | :--- |
| **P1 (`Engine Orchestrator`)** | `017` | `factory/playforge/engine_orchestrator/`, `spec_engine/` v2 | `test_engine_orchestrator.py` (10 testes) |
| **P2 (`Tool & 3D Assets`)** | `018` | `factory/playforge/asset_pipeline/` (`glTF/GLB/OBJ/FBX/JPEG/MP3/PBR`) | `test_tool_and_3d_assets.py` (10 testes) |
| **P3 / Fase 10 (`Build Manager`)** | `019` | `factory/playforge/build_system/` (`SHA-256`, `verify_build`, `approve_release`) | `test_build_system.py` (7 testes) |
| **P4 (`Gameplay & Seção 10`)** | `020` | `factory/playforge/gameplay_systems/`, `ai/agents.py` (13 papéis) | `test_gameplay_and_agents.py` (5 testes) |
| **P5 / Fase 11 (`Evolution`)** | `021` | `factory/playforge/evolution/` (`LocalRagMemory`, `OptimizationAdvisor`, `FactoryDashboard`) | `test_evolution_phase11.py` (4 testes) |

## 3. Evidências Executáveis

- `factory/tests/`: **136 testes Python** (`test_factory_core` 19 + `test_spec_engine` 28 + `test_template_registry` 15 + `test_game_generator` 7 + `test_ai_mcp` 10 + `test_asset_audio_pipeline` 6 + `test_qa_balance_engine` 9 + `test_automation` 6 + `test_engine_orchestrator` 10 + `test_tool_and_3d_assets` 10 + `test_build_system` 7 + `test_gameplay_and_agents` 5 + `test_evolution_phase11` 4).
- `.\infrastructure\scripts\playforge.ps1 test-win`: `229 assertions | Failed: 0`, `Action Balance Verifier` `PASSED` (0 soft-locks), `Engine Boot Gate` `14 assertions | Failed: 0`.
- Restrições preservadas: política `FREE_TIER_POLICY.md` (`paid_services_enabled: false`), portas do operador intactas, sem inicialização indevida de `data/` na raiz e zero alterações no jogo-âncora.

## 4. Próximas Ações Opcionais (Dependem de Decisão/Hardware Externo)

1. Commit/tag no Git pelo operador após revisar o *working tree*.
2. Caso o operador instale `Unity Editor`, `Unreal Engine 5` (workstation `>= 32 GB RAM` + GPU dedicado DX12), `Android SDK` ou modelos `Ollama` (`ollama pull ...`), executar `engine-probe`, `build-toolchains` e `ai-health` para ativar execução local adicional.
3. `Sprint 4C` do jogo-âncora (`src/adapters/` & export `.aab` comercial) mediante decisão humana.
