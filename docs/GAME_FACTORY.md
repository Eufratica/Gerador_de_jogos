# GAME_FACTORY.md — Auditoria Real & Arquitetura dos Módulos da Fábrica

## 1. Auditoria Real dos 18 Domínios da Fábrica (Estado na Fase 0)

Classificação honesta baseada estritamente no estado observado do repositório (`cab6ee8`):

| Módulo / Capacidade | Status Real Hoje | Evidência / Lacuna Observada | Fase Prevista |
| :--- | :--- | :--- | :--- |
| **Balance Engine** | **Implementado parcialmente** | Existem `src/factory/balance_verifier.gd` (72h Idle/DDTank) e `action_balance_verifier.gd` (20Hz Zaikor) em GDScript para o jogo-âncora; falta abstração por gênero multi-projeto. | Fase 8 *(evolução)* |
| **QA Engine** | **Implementado parcialmente** | Existem runners Godot headless (`run_unit_tests.gd`, `run_action_verifier.gd`, `verify_engine_boot.gd`) no jogo-âncora; falta camada genérica para outros projetos. | Fase 8 |
| **Build Engine** | **Apenas documentado** | Existe menção a build `.aab` + Fastlane em `AGENTS.md`/`001`, mas nenhum preset de exportação Android, Gradle ou script de build no repo. | Fase 10 |
| **Publishing Engine** | **Apenas documentado** | Planejado em `AGENTS.md`/`001`; nenhum adapter nem workflow ativo. | Fase 10 |
| **Factory Core** | **Ausente** | Nenhuma CLI/API/orquestração Python implementada ainda. | Fase 2 |
| **Project Manager** | **Ausente** | Apenas 1 projeto implícito na raiz (`Zaikor`). | Fase 2 |
| **Game Specification** | **Apenas documentado** | Existem configs específicos do Jogo 1 (`balance_v1.json`, `action_world_v1.json`), ainda sem schema genérico multi-jogo da fábrica. | Fase 3 |
| **Game Design Engine** | **Ausente** | Sem motor estruturado de geração/versionamento de GDD. | Fase 3 |
| **Template Registry** | **Ausente** | Componentes candidatos existem dentro de `src/core/` e `src/engine/`, ainda não extraídos nem registrados como template. | Fase 4 |
| **Game Generator** | **Ausente** | Sem gerador de workspaces isolados a partir de spec + template. | Fase 5 (**MVP**) |
| **Asset Pipeline** | **Ausente** | Jogo-âncora usa geometria `_draw()` sem assets externos; falta pipeline de importação/validação/licenças. | Fase 7 |
| **Agent Orchestrator / LangGraph** | **Ausente** | Sem grafo LangGraph nem definição Python de agentes. | Fase 6 |
| **Ollama / Model Router** | **Ausente** | `ollama` não encontrado no PATH; roteador inexistente. | Fase 6 |
| **n8n Automation** | **Ausente** | Sem Docker Compose nem workflows exportados em `automation/`. | Fase 9 |
| **MCP Servers** | **Ausente** | Sem servidores MCP em `mcp-servers/`. | Fase 6 |
| **Memory Engine (`pgvector`)** | **Apenas documentado** | `data/` possui apenas `.gitkeep`; `src/adapters/` possui apenas `.gitkeep`. | Fase 6 / 11 |
| **Analytics / Telemetry** | **Apenas documentado** | Previsto no SDD `001`; `TelemetryPort` ainda não implementado. | Fase 11 *(ou 4C)* |

---

## 2. Ciclo de Vida Padrão de Um Jogo na Fábrica (21 Etapas)

```text
IDEIA ➔ RESEARCH ➔ GDD ➔ GAME SPECIFICATION ➔ ARQUITETURA ➔ APROVACAO HUMANA
  ➔ SELECAO DE TEMPLATE ➔ GERACAO DO PROJETO ➔ PRODUCAO DE ASSETS
  ➔ IMPLEMENTACAO ➔ INTEGRACAO ➔ TESTES ➔ BALANCEAMENTO ➔ AUDITORIA
  ➔ PREVIEW ➔ APROVACAO HUMANA ➔ BUILD ➔ DISTRIBUICAO ➔ MONITORAMENTO ➔ OTIMIZACAO
```

Cada transição exige persistência de estado (`project_id`, responsável/agente, entradas, saídas, timestamp e evidência) para suportar retomada após falha ou pausa de aprovação.

---

## 3. Meta do Primeiro MVP Funcional (Fase 5)

Sem simular agentes ou builds falsas, o MVP da fábrica estará pronto quando:
1. Criar um **novo `project_id`** isolado;
2. Gerar e validar uma **`GameSpecification`** JSON versionada + **`GDD`** aprovado pelo operador;
3. Selecionar um **template real extraído do jogo-âncora** no `Template Registry`;
4. Gerar o novo projeto Godot em diretório isolado (`games/<novo-jogo>/`);
5. Rodar testes headless Godot CLI reais no novo projeto e produzir um **preview funcional + artefato de build local validado**.
