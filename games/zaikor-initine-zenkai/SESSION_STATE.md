# SESSION_STATE.md — Memória Operacional de Zaikor: Initine Zenkai

## 1. Snapshot Atual

- **Versão (`VERSION`):** `0.1.0-etapa1`
- **Etapa Concluída:** **Etapa 1 — Projeto Godot Funcional (`gl_compatibility`, `1280×720`, perfis gráficos e cena raiz 3D)**
- **Estágio na PlayForge Factory (`projects.json`):** `GERACAO_DO_PROJETO` (gates de especificação e arquitetura aprovados pelo operador sob Opção A: `Godot 4.7.2 Stable`)
- **Próxima Etapa Planejada:** **Etapa 2 — Personagem e Câmera em Terceira Pessoa (`SpringArm3D` com anticolisão)**

---

## 2. Ambiente e Toolchain Verificados (`2026-11-16`)

- **Godot do Projeto (`Zaikor: Initine Zenkai`):** `4.7.2.stable.official.ed1daf0bf` em `../../tools/godot-4.7.2/` (SHA-512 validado)
- **Godot da Fábrica / Âncora 2D (`Zaikor` na raiz):** `4.4.stable.official.4c311cbee` em `../../tools/godot/` (preservado)
- **Hardware Host:** `11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz` (`4c/8t`), `Intel(R) Iris(R) Xe Graphics`, `11.74 GB` RAM (`DIMM A 8 GB + DIMM B 4 GB @ 2133 MT/s` flex-mode), `132.56 GB` livres em `C:`
- **Ferramentas Auxiliares:** `Blender 5.3.0`, `FFmpeg 9.0.2`, `Ollama 0.40.16` (`qwen2.5-coder:3b`)

---

## 3. Evidências Executáveis da Etapa 1

- **Testes Unitários Headless (`tests/unit/run_unit_tests.gd` em `Godot 4.7.2 Stable`):** `16` assertions, `0` falhas, tempo `3.28 ms` (lógica pura `ZizGraphicsConfig` e `ZizGameBootstrap`).
- **Teste de Integração de Boot (`tests/integration/verify_main_boot.gd` em `Godot 4.7.2 Stable`):** `boot_valid: true`, `rendering_method: gl_compatibility`, `13` ações `InputMap` verificadas, alternância de perfil `medium`/`low` e bloqueio de perfil inválido aprovados, `orphan_nodes_after_free: 0`, `orphan_nodes_delta: 0`, `boot_ms: 75.75`, `static_memory_mb: 26.07`.
- **Execução Real em GPU (`Godot_v4.7.2-stable_win64_console.exe -- --benchmark-frames=60`):**
  - `video_adapter`: `Intel(R) Iris(R) Xe Graphics` (`Intel`), `rendering_method`: `gl_compatibility`, `profile_id`: `low`
  - `fps` (reportado pelo Engine após warmup): `31.0 FPS` (`32.26 ms`, cap `30 FPS` + VSync)
  - `wall_avg_fps` (incluindo primeiro boot/warmup frio de shaders no `_ready()`): `6.2 FPS` (`9654.59 ms` nos 60 quadros totais)
  - `static_memory_mb`: `35.74 MB`, `active_nodes`: `11`, `orphan_nodes`: `0`
- **Jogo-Âncora (`Zaikor` 2D na raiz):** preservado intacto com `229` unit assertions + `ActionBalanceVerifier` + `EngineBootGate` passando.
