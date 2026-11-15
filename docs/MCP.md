# MCP.md — Protocolo de Ferramentas Especializadas (Fase 6)

> **Estado Atual (Fase 0):** Nenhum servidor MCP foi implementado ainda no repositório. Este documento estabelece os contratos mínimos de segurança e escopo para a Fase 6+.

---

## 1. Servidores MCP Previstos (Ativação Progressiva)

| Servidor | Domínio |
| :--- | :--- |
| `game-project-mcp` | Criação/leitura isolada de projetos, registro de estado e arquivos permitidos |
| `game-design-mcp` | Manipulação estruturada e validação de GDDs e `GameSpecification` |
| `godot-mcp` | Execução headless controlada do Godot CLI, verificação de cenas e scripts no workspace autorizado |
| `testing-mcp` | Execução de suítes unitárias/integração e coleta estruturada de evidências |
| `balance-mcp` | Execução de simuladores de balanceamento por gênero |
| `asset-mcp` / `audio-mcp` | Catalogação, checagem de hash/licença/dimensão no `Asset Registry` |
| `build-mcp` / `analytics-mcp` / `publishing-mcp` | Geração de builds isoladas, leitura de telemetria agregada e preparo pré-aprovação |

---

## 2. Regras Obrigatórias de Contrato e Isolamento

1. **Menor Privilégio:** Proibido criar um servidor shell irrestrito. Cada tool exige nome, descrição, JSON Schema de entrada e saída, validação rígida e timeout.
2. **Confinamento por `project_id`:** Toda chamada MCP verifica o caminho resolvido para impedir *path traversal* ou acesso cruzado entre o Jogo A e o Jogo B.
3. **Auditoria:** Toda invocação registra `execution_id`, `agent_id`, `project_id`, `tool_name`, duração, status e arquivos tocados — nunca registrando tokens ou segredos.
