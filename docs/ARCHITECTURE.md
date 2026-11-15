# ARCHITECTURE.md — Arquitetura Macro da PlayForge Factory

> Para a arquitetura detalhada já implementada no **jogo-âncora (`Zaikor` / núcleo Idle-DDTank)**, consulte [ARQUITETURA.md](ARQUITETURA.md).  
> Este documento define a arquitetura-alvo modular da **PlayForge Factory**, os seus limites de isolamento e a estratégia segura de coexistência com o repositório atual.

---

## 1. Visão Arquitetural Dual

```text
+-------------------------------------------------------------------------+
|                       PLAYFORGE FACTORY (FASES 2-11)                    |
|                                                                         |
|  [n8n Community] <---> [FastAPI / Factory Core] <---> [PostgreSQL]      |
|   (Orquestracao           |            |              [+ pgvector]      |
|    & Aprovacoes)          v            v              [+ Valkey  ]      |
|                    [LangGraph]    [Project Manager]                     |
|                     (Agentes)      |      |                             |
|                        |           |      +--> [Template Registry]      |
|                        v           |      +--> [Spec Engine]            |
|                 [Model Router]     v      +--> [Game Generator]         |
|                   (Ollama)     [MCP Servers (Escopo por project_id)]    |
+------------------------------------+------------------------------------+
                                     | Gera / Valida / Testa em Sandbox
                                     v
+-------------------------------------------------------------------------+
|              JOGOS ISOLADOS (PROJETOS INDEPENDENTES)                    |
|                                                                         |
|  [Jogo-Ancora Atual (raiz -> futuro games/zaikor/)]                     |
|    project.godot | config/*.json | src/core/ | src/engine/ | tests/     |
|                                                                         |
|  [Game Project 002 (futuro games/game-002/)]                            |
|    Workspace isolado derivado de Template + Game Specification aprovada |
+-------------------------------------------------------------------------+
```

---

## 2. Arquitetura Hexagonal (*Ports & Adapters*)

Aplicada nos dois níveis sem abstrações ociosas:

1. **Nos Jogos Produzidos:**
   - **Domínio Puro (`core/`):** regras determinísticas, matemática `BigNum`, balística, máquina de estados, economia e validadores de schema sem imports de cena, I/O ou rede.
   - **Borda (`engine/` e `adapters/`):** renderização Godot, áudio, entrada, SDKs de terceiros, saves e telemetria local SQLite via interfaces explícitas.
2. **Na Fábrica (`factory/` / `apps/api/` nas Fases 2+):**
   - **Domínio:** `Project`, `GameSpecification`, `Template`, `Approval`, `ValidationReport`, `BuildArtifact`.
   - **Adaptadores:** `Ollama` (`ModelRouter`), `PostgreSQL/pgvector`, `Godot CLI Runner`, `n8n` webhooks, ferramentas `MCP` confinadas por projeto.

---

## 3. Estratégia de Transição Incremental (Preservação)

Estado real no commit `cab6ee8`:
- `Zaikor` está na **raiz** (`project.godot`, `src/`, `config/`, `tests/`).
- `src/factory/` contém **dois verificadores GDScript** (`balance_verifier.gd` e `action_balance_verifier.gd`), não a plataforma multi-projeto da fábrica.
- Nenhum módulo Python, FastAPI, Docker Compose, LangGraph, Ollama, MCP ou n8n existe ainda no repositório.

**Regra de Migração (`PEND-002` & `PEND-004`):**
1. Na **Fase 0** e **Fase 1**, nada do jogo-âncora é movido para preservar 100% dos caminhos `res://` e dos testes existentes.
2. Na **Fase 2**, quando `factory/` e `games/` forem introduzidos sob ADR aprovado, a migração opcional do `Zaikor` para `games/zaikor/` só poderá ocorrer com validação integral de referências `res://` e aprovação nos mesmos gates (`229` unitários + `ActionBalanceVerifier` + `verify_engine_boot`).

---

## 4. Documentos Relacionados

- Fábrica & Módulos: [GAME_FACTORY.md](GAME_FACTORY.md)
- Templates & Reúso do Âncora: [GAME_TEMPLATES.md](GAME_TEMPLATES.md)
- Banco de Dados & Memória: [DATABASE.md](DATABASE.md)
- Infraestrutura & Ambiente: [INFRASTRUCTURE.md](INFRASTRUCTURE.md)
- Automação & Agentes: [AUTOMATION.md](AUTOMATION.md) | [AGENT_CONTRACTS.md](AGENT_CONTRACTS.md) | [MODEL_ROUTER.md](MODEL_ROUTER.md) | [MCP.md](MCP.md)
