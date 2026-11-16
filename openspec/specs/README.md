# Índice Oficial de Capabilities (`openspec/specs/`)

Este diretório contém a **fonte oficial de verdade** por capability, mantendo preservado o histórico de mudanças em `openspec/changes/` (`001`–`021`) e `openspec/archive/` (`002`–`021`).

## Capabilities Ativas

| Capability | Arquivo | Fase / Incremento | Estado Real |
| :--- | :--- | :--- | :--- |
| `game-factory` | [spec.md](game-factory/spec.md) | Fases 0–5 | Implementada (`009`, `012`) |
| `game-projects` | [spec.md](game-projects/spec.md) | Fase 2 | Implementada (`009`, isolamento multi-projeto e guarda do âncora) |
| `game-specification` | [spec.md](game-specification/spec.md) | Fase 3 + P1 | Implementada (`010` v1 + `017` v2 multi-engine retrocompatível) |
| `game-templates` | [spec.md](game-templates/spec.md) | Fase 4 | Implementada (`011`: `godot-2d-action-rpg@1.0.0`) |
| `infrastructure` | [spec.md](infrastructure/spec.md) | Fase 1 | Ativa e verificada (`008`: Docker Compose, DevContainer, CLI Linux+Win) |
| `security` | [spec.md](security/spec.md) | Transversal | Políticas ativas (`.gitignore`, *fail-closed*, isolamento, `FREE_TIER_POLICY.md`) |
| `ai-agents` | [spec.md](ai-agents/spec.md) | Fase 6 + P4 | Implementada (`013`: Model Router Ollama local, 14 contratos, MCP; `020`: 13 papéis Seção 10) |
| `asset-audio` | [spec.md](asset-audio/spec.md) | Fase 7 | Implementada (`014`: AssetRegistry, PNG/WAV/OGG, Godot headless, MCPs) |
| `game-testing` | [spec.md](game-testing/spec.md) | Fase 8 | Implementada (`015`: QA Engine 4 pilares, StaticAnalyzer, 11 gêneros, profiling Godot) |
| `automation` | [spec.md](automation/spec.md) | Fase 9 | Implementada (`016`: catálogo `WF-001`..`WF-020`, `AutomationEngine` + webhook loopback) |
| `engine-orchestration` | [spec.md](engine-orchestration/spec.md) | P1 (`017`) | Implementada (`EngineSelector` 14 critérios + `GodotAdapter`/`UnityAdapter`/`UnrealAdapter`) |
| `tool-orchestration` | [spec.md](tool-orchestration/spec.md) | P2 (`018`) | Implementada (3D `glTF`/`GLB`/`OBJ`/`FBX`, `JPEG`/`MP3`, PBR e auditoria `has_rig`/`has_materials`) |
| `build-distribution` | [spec.md](build-distribution/spec.md) | Fase 10 / P3 (`019`) | Implementada (`BuildManager` SHA-256, smoke test, `verify_build`, `approve_release`) |
| `gameplay-systems` | [spec.md](gameplay-systems/spec.md) | P4 (`020`) | Implementada (8 sistemas modulares sob demanda Godot/Unity/Unreal + 13 papéis Seção 10) |
| `telemetry-evolution` | [spec.md](telemetry-evolution/spec.md) | Fase 11 / P5 (`021`) | Implementada (`LocalRagMemory` TF-IDF local, `OptimizationAdvisor` e `FactoryDashboard`) |
