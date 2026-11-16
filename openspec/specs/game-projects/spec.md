# Capability Specification: `game-projects`

- **Capability ID:** `game-projects`
- **Status:** `IMPLEMENTED_PHASE_2` *(Jogo-âncora protegido em raiz e gerenciador multi-projeto com isolamento em `games/<project_id>/` implementado em `factory/playforge/`)*
- **Referência Técnica:** [docs/ARQUITETURA.md](../../docs/ARQUITETURA.md) | [DECISIONS.md](../../DECISIONS.md) (`PEND-001`, `PEND-002`)

## Requisitos de Isolamento Multi-Projeto

1. **Identidade Própria:** Todo projeto administrado possui `project_id`, nome, gênero, engine/versão, estado, `GameSpecification`, GDD, código, assets, testes, builds e métricas isolados.
2. **Isolamento de Workspace:** Alterar arquivos ou configs do jogo A não pode alterar arquivos do jogo B; agentes e ferramentas MCP atuam apenas no `project_id` designado.
3. **Preservação do Jogo-Âncora (`Zaikor: Zenkai Infinite`):**
   - Localização atual preservada: raiz (`project.godot`, `config/`, `src/`, `tests/`).
   - Histórico preservado: `openspec/changes/001`–`006` e `openspec/archive/002,003,005,006`.
   - Migração para `games/zaikor/` só ocorrerá mediante ADR aprovado na Fase 2+.

## Cenários Verificáveis

- **Cenário `GP-01` (Preservação da Linha de Base):** No estado da Fase 0, os testes existentes do jogo-âncora continuam executando diretamente a partir da raiz `res://` com exit code `0`.
- **Cenário `GP-02` (Isolamento Futuro Multi-Projeto):** Ao criar `game-002` na Fase 2+, todos os artefatos de `game-002` residem em workspace próprio e nenhuma execução em `game-002` grava ou apaga arquivos de `Zaikor`.
