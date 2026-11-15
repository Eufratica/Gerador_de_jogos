# CONTRIBUTING.md — Padrões de Desenvolvimento, Git, SDD & Qualidade

Este documento orienta desenvolvedores humanos e agentes autônomos atuando no repositório `Gerador_de_jogos`.

---

## 1. Fluxo Obrigatório de Trabalho (SDLC + OpenSpec)

1. **Inspeção inicial:** Leia [AGENTS.md](AGENTS.md), [PROJECT.md](PROJECT.md), [docs/SESSION_STATE.md](docs/SESSION_STATE.md), [ROADMAP.md](ROADMAP.md) e [TASKS.md](TASKS.md).
2. **Nenhuma mudança estrutural sem especificação:** Toda feature, ajuste de arquitetura, schema, template ou módulo da fábrica começa em `openspec/changes/`.
3. **Pequenas entregas verificáveis:** Implemente em incrementos atômicos, revisando diffs e mantendo compatibilidade com projetos existentes.
4. **Proibido código gerado solto:** Todo artefato gerado ou modificado precisa passar pelos gates aplicáveis antes de ser dado como concluído.
5. **Atualização contínua:** Mantenha `docs/SESSION_STATE.md`, `TASKS.md`, `CHANGELOG.md` e OpenSpec sincronizados ao fim de cada marco.

---

## 2. Convenções de Git e Commits

- **Branches:**
  - `main`: linha principal estável e auditada.
  - `develop` *(opcional quando houver integração paralela)*
  - `feature/<nome>`, `fix/<nome>`, `docs/<nome>`, `refactor/<nome>`
- **Formato de Commits (Conventional Commits):**
  - `feat(escopo): descrição`
  - `fix(escopo): descrição`
  - `docs(escopo): descrição`
  - `test(escopo): descrição`
  - `refactor(escopo): descrição`
  - `chore(escopo): descrição`

---

## 3. Padrões Técnicos por Camada

- **GDScript (`src/core/` e futuros jogos Godot):**
  - Zero dependências de cena/engine/SO/rede em `core/`.
  - Tipagem explícita sempre que possível, determinismo (`SeededRng`, relógio injetável) e validação *fail-closed* de JSON.
- **Python (Fábrica — Fases 2+):**
  - Schemas tipados e validados (`JSON Schema` / contratos explícitos), isolamento por projeto (`project_id`), timeouts e tratamento explícito de erros sem silenciamento.
- **Documentação & OpenSpec:**
  - Diferenciar sempre **implementado/testado** de **planejado/proposto**.
  - Nunca arquivar uma change OpenSpec incompleta nem apagar decisões anteriores em [DECISIONS.md](DECISIONS.md).
