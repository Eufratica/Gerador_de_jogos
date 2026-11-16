# HANDOFF.md — Transferência Contínua de Sessão (`Gerador_de_jogos` / PlayForge Factory)

> **Princípio de Continuidade:** Todo contexto técnico, estado de verificação, bloqueios e próximos passos residem neste repositório — independentemente do agente, provedor de IA ou ambiente utilizado.

---

## 1. Estado Consolidado Atual (`VERSION: 1.0.0`)

- **Ramo Git:** `main` @ `b1be94b` com **Fases 0 a 11 e Incrementos `P1`–`P5` (`OpenSpec 007`–`021`)** implementados, testados e arquivados no *working tree* local.
- **Jogo-Âncora (`Zaikor: Zenkai Infinite`):** preservado integralmente na raiz ([project.godot](../project.godot), `src/core/`, `src/engine/`, `config/`, `tests/`), **sem modificações** (`ADR-006`).
- **Capacidades Entregues da Fábrica (`factory/playforge/`):**
  - **Fases 0–9 (`007`–`016`):** Governança OpenSpec, Compose (`pgvector`, `valkey`, `n8n` opcional), `ProjectManager` multi-projeto isolado, `SpecificationGenerator` (`v1` e `v2`) + `GDD` + aprovação SHA-256, `TemplateRegistry`, `GameGenerator`, `ModelRouter` Ollama local + `GraphOrchestrator` + `MCP`, `AssetRegistry` + Godot headless, `QAEngine` 4 pilares (11 gêneros) e ponte `n8n Community` (`WF-001`..`WF-020`).
  - **Multi-Engine & Ferramentas (`017`–`018` / `P1`–`P2`):** `EngineSelector` (14 critérios + relatório justificativo), `EngineAdapter` (`GodotEngineAdapter`, `UnityEngineAdapter`, `UnrealEngineAdapter`), suporte e auditoria 3D/PBR (`glTF`/`GLB`/`OBJ`/`FBX`/`JPEG`/`MP3`/PBR + `has_materials`/`has_rig`).
  - **Build, Gameplay Modular & Evolução (`019`–`021` / Fase 10, `P4`, Fase 11):** `BuildManager` com pacotes `structural-source-bundle` + SHA-256 + smoke test Godot + gate `RELEASE_APPROVED`, catálogo modular `GameplaySystemInjector` (8 sistemas sob demanda em Godot/Unity/Unreal), mapeamento dos 13 papéis da Seção 10, `LocalRagMemory` TF-IDF local, `OptimizationAdvisor` com aprovação humana e `FactoryDashboard`.

---

## 2. Ambiente e Ferramentas Reais Verificadas no Host

- **Hardware Local:** Windows 11 `AMD64`, `8` threads, `11.74 GB` RAM, GPU integrada `Intel Iris Xe` (sem GPU dedicada CUDA).
- **Instaladas e Detectadas pela Fábrica:** `Godot 4.4.stable`, `Blender 5.3`, `FFmpeg 9.0.2`, `Ollama 0.40.16`.
- **Não Instaladas / Limitações Honestas:** `Unity Editor` e `Unreal Engine 5` (UE5 requer `32 GB RAM + GPU DX12 >= 8 GB VRAM` e conta Epic), `Android SDK` e export templates Godot não estão presentes no host; para builds sem toolchain nativa, a fábrica gera `structural-source-bundle` verificável por SHA-256 e bloqueia modo `--require-native` / compilação C# ou C++ de forma *fail-closed*.
- **Portas Reservadas do Operador ([INFRASTRUCTURE.md](INFRASTRUCTURE.md)):** `8000`, `5678`, `1880`, `6333/6334`, `5433`, `6380` — preservadas.
- **Zero Cost (`FREE_TIER_POLICY.md`):** zero APIs pagas (inclusive fallback) e zero segredos no Git.
