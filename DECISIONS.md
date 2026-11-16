# DECISIONS.md — Registro de Decisões Arquiteturais (ADRs) & Pendências

Nenhuma decisão arquitetural estrutural deve ser alterada silenciosamente. Decisões substituídas permanecem registradas com sua sucessora.

---

## 1. Decisões Arquiteturais Consolidadas (Preservadas do Repositório Atual)

### ADR-001 — Engine Principal: Godot 4.4+ com GDScript Headless
- **Estado:** `ACEITA` (evidenciada em `tools/godot/Godot_v4.4-stable_win64*.exe`, `project.godot` e `openspec/changes/001`).
- **Contexto:** Sem .NET SDK configurado para C# na época do bootstrap; Godot 4.4 GDScript oferece execução CLI `--headless` em `< 1s` para `src/core/` e exportação enxuta.
- **Consequência:** A fábrica deverá manter compatibilidade explícita de versão de engine por jogo e por template (`4.4.stable` atual para `Zaikor`).

### ADR-002 — Separação Estrita entre Lógica Pura (`src/core/`) e Bordas (`src/engine/`, `src/adapters/`) + *Fail-Closed*
- **Estado:** `ACEITA` (evidenciada em `src/core/*.gd` e `tests/unit/`).
- **Contexto:** Regras de combate, economia `BigNum`, balística e schema JSON não podem depender de `Node`, `SceneTree`, rede, relógio do SO ou variáveis globais.
- **Consequência:** Todos os templates de jogo derivados pela PlayForge Factory devem herdar este padrão de testabilidade determinística e *fail-closed*.

### ADR-003 — Pivô do Jogo-Âncora para Ação 2D Dark Fantasy (`Zaikor: Zenkai Infinite`)
- **Estado:** `ACEITA PARCIALMENTE — DIVERGÊNCIA NOMINAL EM ABERTO` (ver `openspec/changes/004` e `PEND-001`).
- **Contexto:** Em `004`–`006`, o Jogo 1 foi focado em um Action RPG 2D lateral Dark Fantasy (`Zaikor: Zenkai Infinite`), reaproveitando `BigNum`, `IdleEconomy` e `SeededRng`, enquanto os módulos `DDTankBallistics`, `TerrainHeightmap` e `CombatFsm` permaneceram no repositório sem uso direto na cena `battle_arena.tscn`.
- **Consequência:** Ambos os conjuntos estão preservados e podem servir de base para **dois templates distintos** na Fase 4 (`godot-2d-action-rpg` e `godot-idle-ballistics`).

### ADR-004 — Governança Dual PlayForge Factory 2.0 + Política Zero Cost
- **Estado:** `ACEITA COMO FUNDACIONAL NA FASE 0` (alinhada ao Prompt Mestre v2.0).
- **Contexto:** O repositório `Gerador_de_jogos` passa a governar formalmente a **fábrica** separada dos **jogos gerados**, com priorização absoluta por software livre/gratuito e execução local.
- **Consequência:** Infraestrutura real (`Docker`, `PostgreSQL+pgvector`, `Ollama`, `LangGraph`, `n8n Community`, `MCP`) será introduzida progressivamente apenas após validação da Fase 0 e inspeção real do ambiente na Fase 1.

---

## 2. Decisões Aprovadas na Conclusão da Fase 0 (2026-11-15)

Todas as pendências `PEND-001` a `PEND-005` foram aprovadas pelo operador (`"aprovo tudo"`), promovendo os ADRs abaixo:

### ADR-005 *(ex-PEND-001)* — Foco Imediato no MVP da PlayForge Factory & Nome do Jogo-Âncora
- **Estado:** `ACEITA`
- **Decisão:** Seguir a ordem `Fase 1 ➔ Fase 2 ➔ Fase 3 ➔ Fase 4 ➔ Fase 5` para construir a infraestrutura da fábrica e gerar o 2º projeto Godot isolado. O jogo-âncora preserva o nome oficial **`Zaikor: Zenkai Infinite`** na versão `v0.4.0-playable-slice` até eventual retomada do `Sprint 4C`.

### ADR-006 *(ex-PEND-002 & PEND-004)* — Preservação de Pastas até Migração Controlada na Fase 2
- **Estado:** `ACEITA`
- **Decisão:** Manter `project.godot`, `src/`, `config/` e `tests/` (incluindo `src/factory/*.gd`) na raiz durante as Fases 0 e 1 para não quebrar `res://`. A fábrica Python futura usará diretório próprio (`factory/` na Fase 2) e eventual migração do âncora para `games/zaikor/` só ocorrerá sob plano e validação integral dos testes.

### ADR-007 *(ex-PEND-003)* — Inspeção e Provisionamento Real de Ambiente na Fase 1
- **Estado:** `ACEITA`
- **Decisão:** Inspecionar host Windows, WSL2 (`Ubuntu-24.04`), Docker Engine/Compose, Python/Node/Ollama e hardware real antes de configurar containers e perfis leves compatíveis com os recursos da máquina.

### ADR-008 *(ex-PEND-005)* — Builds Locais Gratuitos Antes de Lojas Externas
- **Estado:** `ACEITA`
- **Decisão:** Priorizar execução e builds locais gratuitos (Windows / Linux headless / APK de teste quando aplicável) sob a política `FREE_TIER_POLICY.md`. Qualquer publicação em loja comercial ou serviço com possível cobrança exige autorização explícita futura.

---

## 3. Decisões Pendentes Atuais

- Nenhuma pendência estrutural não-documentada no início da Fase 6 *(novas pendências críticas futuras continuam sendo registradas aqui antes de execução)*.

### ADR-009 — Ponte Stdlib-First para Model Router (Ollama HTTP), Orquestração Checkpointed (SQLite) e Servidores MCP na Fase 6

- **Status:** `APROVADA` *(Fase 6 — `013-phase6-ai-engine-agents-mcp`)*
- **Contexto Observado:** Auditoria real do ambiente confirmou Python `3.13.18`, SQLite `3.53.1`, CPU Intel `i5-1135G7` (4 cores / 8 threads), `Intel Iris Xe` sem GPU dedicada, ~`12 GB` RAM no host (~`5.7Gi` RAM + `2.0Gi` swap no WSL2), ausência do binário `ollama` e ausência de pacotes pip externos (`langgraph`, `mcp`, `httpx`, `requests`, `pydantic`).
- **Decisão:** Implementar a Fase 6 em **Python puro (stdlib apenas: `urllib.request`, `sqlite3`, `json`)** seguindo os protocolos reais HTTP do Ollama (`127.0.0.1:11434`), semântica de grafo com estado persistente em SQLite e interrupção humana compatível com `LangGraph`, e protocolo `JSON-RPC 2.0` via `stdio` para `MCP`, mantendo interfaces explícitas (*Ports & Adapters*) para acoplar SDKs externos (`langgraph`, `mcp`) e daemon Ollama local quando instalados em etapa futura.
- **Regras Derivadas:** Roteamento por hardware libera apenas tiers `S`/`M` em CPU 12 GB (`Tier L` bloqueado); endpoints externos não-locais são proibidos (`PolicyViolationError`) e indisponibilidade do Ollama local falha fechado (`ProviderUnavailableError`) sem fallback pago (`SEC-02`).

### ADR-010 — Expansão Multi-Engine Incremental via `Ports & Adapters` Preservando Fases 0–9 (`OpenSpec 017+`)

- **Status:** `APROVADA` *(Autorização humana em `2026-11-15` para consolidar requisitos do Master Engineering Prompt e prosseguir incrementalmente)*
- **Contexto Observado:** Ao final da Fase 9 (`100` testes Python + suíte `Zaikor` `229` assertions passando), o núcleo da fábrica (`spec_engine`, `template_registry`, `generator`, `qa_engine`, `asset_pipeline`) operava acoplado a `Godot 4.x` e formatos 2D/áudio (`PNG`, `WAV`, `OGG`). A expansão multi-engine solicitada introduz: seleção inteligente ponderada por **14 critérios** (**Godot**, **Unity**, **Unreal Engine**), orquestração de ferramentas (`Blender`, `FFmpeg`, `FMOD`/`Wwise` opcionais), formatos 3D/mídia (`GLTF/GLB`, `FBX`, `OBJ`, `JPEG`, `MP3`), Build Manager independente de engine, módulos reutilizáveis de Gameplay e documentos ausentes (`VERSION`, `docs/HANDOFF.md`, `docs/ENGINE_MATRIX.md`, `docs/TESTING.md`).
- **Decisão:**
  1. Preservar **100%** dos módulos funcionais das Fases 0–9 e do jogo-âncora `Zaikor` (`ADR-006`) sem reescrita destrutiva.
  2. Evoluir por incrementos auditados via **Ports & Adapters**:
     - `P1`: `Engine Selection and Orchestration System` + `EngineAdapter` (`GodotAdapter` ativo + `UnityAdapter` / `UnrealAdapter` com geração estrutural e bloqueio *fail-closed* caso toolchain não esteja instalada no host) + evolução retrocompatível da `GameSpecification`.
     - `P2`: Orquestração de ferramentas (`Blender`, `FFmpeg`, `FMOD`/`Wwise` opcionais) e suporte a `GLTF/GLB`, `FBX`, `OBJ`, `JPEG`, `MP3` e materiais PBR.
     - `P3`: Build Manager multiplataforma independente de engine (antiga Fase 10).
     - `P4`: Aprofundamento Unity/Unreal + catálogo de sistemas de gameplay reutilizáveis (Action 3D, RPG, Open World sob demanda) + atualização de contratos dos 14 agentes.
     - `P5`: RAG (`pgvector`), telemetria e otimização contínua (antiga Fase 11).
  3. **Veracidade de Hardware e Licenças (`Free First`):** Como o host possui `11,74 GB` RAM e GPU integrada sem VRAM dedicada, e Unity Hub / Epic Games Launcher exigem conta/EULA/instalação massiva externa, ferramentas leves open-source (`Blender`, `FFmpeg`, `Ollama`) são instaláveis localmente via `winget`, enquanto `UnityAdapter` e `UnrealAdapter` nunca simulam compilação sem detectar a engine instalada localmente.
