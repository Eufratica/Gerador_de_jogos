# Capability: `engine-orchestration`

Origem: OpenSpec `017` (`P1`, ADR-010). Código: `factory/playforge/engine_orchestrator/`. Testes: `factory/tests/test_engine_orchestrator.py`.

## Requisitos
- **ENG-01 — Seleção justificada:** `EngineSelector` pontua cada `EngineAdapter` registrado nos 14 critérios (`SELECTION_CRITERIA`) e gera relatório JSON + Markdown; hardware real do host e toolchain detectada entram no relatório (avisos explícitos quando insuficientes).
- **ENG-02 — Expansibilidade:** `EngineAdapterRegistry.register()` adiciona novas engines sem alterar o núcleo.
- **ENG-03 — Toolchain real e fail-closed:** `UnityEngineAdapter`/`UnrealEngineAdapter` geram scaffold estrutural e validam arquivos, mas `run_tests` levanta `EngineToolchainUnavailableError` se o editor não estiver instalado. `GodotEngineAdapter` executa teste headless real.
- **ENG-04 — Retrocompatibilidade:** `spec_schema_version=1` aceita apenas `godot` e rejeita campos desconhecidos; `spec_schema_version=2` aceita `godot|unity|unreal` e campos opcionais (`tools_required`, `camera_spec`, `physics_spec`, `inventory_spec`, `quests_spec`, `engine_selection_report`).

## CLI
`engine-matrix`, `engine-probe`, `engine-select`, `engine-scaffold`, `engine-verify`.
