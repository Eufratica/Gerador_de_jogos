# AGENT_CONTRACTS.md — Contratos do Sistema Multiagentes (Fase 6)

> **Estado Atual (Fase 0):** Documentação normativa para implantação futura via **LangGraph** na Fase 6. Nenhum agente Python autônomo está em execução ainda no repositório.

---

## 1. Catálogo Oficial dos 14 Agentes Especializados

| ID | Agente | Responsabilidade Delimitada | Ferramentas / Escopo |
| :--- | :--- | :--- | :--- |
| `orchestrator` | Master Orchestrator | Plano de execução, grafo de dependências, aprovações humanas, consolidação | Lê estado; despacha subagentes; **não** executa tudo sozinho |
| `research` | Research Agent | Pesquisa de gêneros, referências, tendências com registro de fontes | Somente leitura + coleta tratada como dado não confiável |
| `game-design` | Game Design Agent | Conceito, GDD (25 seções), core loop, progressão, critérios | `game-design-mcp` / gera rascunhos para revisão |
| `architecture` | Game Architect Agent | Estrutura técnica, módulos, contratos, cenas, dependências | `game-project-mcp` / especificações |
| `gameplay` | Gameplay Agent | Mecânicas, combate, física, IA, máquinas de estado em `core/` & `engine/` | `gameplay-mcp`, `godot-mcp` (confinado ao `project_id`) |
| `ui-ux` | UI/UX Agent | HUD, menus, responsividade PC/Mobile, acessibilidade | `godot-mcp` (confinado a UI do projeto ativo) |
| `art-asset` | Art and Asset Agent | Direção visual, organização de assets, validação de resolução/formato | `asset-mcp` |
| `audio` | Audio Agent | SFX, ambiente, música original, otimização de áudio | `audio-mcp` |
| `content` | Content Agent | Narrativa, textos, missões, eventos, descrições de fases | Escopo textual do `project_id` |
| `balance` | Balance Agent | Economia, curvas, simulação de progressão e detecção de progress walls | `balance-mcp` |
| `qa` | QA Agent | Testes unitários, integração, headless Godot, regressão e evidências | `testing-mcp` |
| `auditor` | Auditor Agent | Code review, licenças, segurança, isolamento; **pode vetar releases** | Leitura + análise estática + gates |
| `build` | Build Agent | Preparação, exportação Godot CLI, manifestos e hashes | `build-mcp` |
| `analytics` | Analytics Agent | Análise de telemetria, abandono/retenção, propostas de melhoria | `analytics-mcp` |

---

## 2. Campos Obrigatórios de Cada Contrato

Todo agente registrado deverá declarar formalmente:
- `agent_id`, `name`, `responsibility`, `objective`, `input_schema`, `output_schema`;
- `allowed_tools`, `permissions`, `restrictions`, `model_tier`;
- **Limites Anti-Loop (Obrigatórios):** `max_context_tokens`, `max_iterations`, `timeout_seconds`, `max_retries`, `failure_policy`, `audit_log_enabled`, `success_criteria`.

**Regras:** Um agente não assume papel de outro sem justificativa nem executa fora do `project_id` autorizado. Saídas de modelos são sempre tratadas como não confiáveis até passar pelos validadores de schema e testes.
