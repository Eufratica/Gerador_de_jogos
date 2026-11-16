# OpenSpec Governance — Zaikor: Initine Zenkai

**Modo Atual:** Documentação SDD/OpenSpec em Markdown manual *(ferramenta CLI `openspec` não instalada no ambiente; nunca simular execução do binário).*

---

## Ciclo Obrigatório de Mudança (Seção 12)

Toda funcionalidade ou alteração estrutural deve abrir uma pasta em `openspec/changes/<id>-<nome>/` com `proposal.md`, `design.md` e `tasks.md` seguindo os 12 passos:

1. Identificar necessidade e problema a resolver.
2. Criar proposta (`proposal.md`).
3. Analisar impacto nos módulos existentes.
4. Atualizar especificações em `openspec/specs/`.
5. Criar plano técnico (`design.md` com RF, RNF, critérios de aceitação e plano de testes).
6. Dividir em tarefas pequenas (`tasks.md`).
7. Implementar incrementalmente.
8. Executar testes unitários/integração/gameplay/benchmark reais.
9. Revisar alterações e manter 0 arquivos órfãos/temporários.
10. Atualizar documentação (`SESSION_STATE.md`, `HANDOFF.md`, `TASKS.md`, `CHANGELOG.md`).
11. Registrar aprovação da mudança.
12. Arquivar mudança concluída em `openspec/archive/`.
