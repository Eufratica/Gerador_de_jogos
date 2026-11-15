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

- Nenhuma pendência aberta na passagem da Fase 0 para a Fase 1. *(Novas pendências estruturais da Fase 1+ serão registradas aqui antes de execução.)*
