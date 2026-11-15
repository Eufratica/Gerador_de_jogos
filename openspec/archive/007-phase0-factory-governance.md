# OpenSpec Archive 007: Fase 0 — Governança, Diagnóstico Real e Fundação da PlayForge Factory

- **ID:** `007-phase0-factory-governance`
- **Status:** `ARCHIVED` *(Aprovado pelo operador em 2026-11-15 — ADRs `005` a `008` consolidados em [DECISIONS.md](../../DECISIONS.md))*
- **Fase SDLC:** `Discovery + Requirements Analysis + Specification + Architecture Design (Fase 0)`
- **Base Histórica Preservada:** `main @ cab6ee8` (`001`–`006`)

---

## Resumo da Entrega Arquivada

1. Auditoria completa de Git, ambiente e módulos do jogo-âncora (`Zaikor`) e fábrica (`BalanceVerifier`/`ActionBalanceVerifier`).
2. Preservação integral dos `58` arquivos funcionais de `cab6ee8`, com re-execução real de `229` unitários (`0` falhas em `517.30 ms`), `ActionBalanceVerifier` (`0` soft-locks em `580.77 ms`) e `verify_engine_boot.gd` (`14` assertions, `0` falhas).
3. Criação dos `10` documentos raiz (`AGENTS.md` atualizado + `9` novos), `20` documentos técnicos em `docs/` (`ARQUITETURA.md` preservado + `19` novos incluindo `SESSION_STATE.md`) e estrutura `openspec/` (`config.yaml` + `specs/*`).
4. Consolidação de `ADR-005` a `ADR-008` destravando a **Fase 1 (`OpenSpec 008`)**.
