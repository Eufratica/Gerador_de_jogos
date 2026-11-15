# Índice Oficial de Capabilities (`openspec/specs/`)

Este diretório contém a **fonte oficial de verdade** por capability, mantendo preservado o histórico de mudanças em `openspec/changes/` (`001`–`007`) e `openspec/archive/` (`002`, `003`, `005`, `006`).

> **Regra Anti-Bloat (Fase 0):** Apenas capabilities com escopo fundacional ativo ou auditoria imediata na Fase 0 possuem subdiretório concreto agora; as demais listadas abaixo serão instanciadas apenas na fase em que tiverem especificação e responsabilidade executável.

## Capabilities Especificadas na Fase 0

| Capability | Arquivo | Fase Alvo | Estado Real Hoje |
| :--- | :--- | :--- | :--- |
| `game-factory` | [spec.md](game-factory/spec.md) | Fases 0–11 | Governança definida; implementação pendente |
| `game-projects` | [spec.md](game-projects/spec.md) | Fase 2 | 1 jogo-âncora (`Zaikor`) na raiz; multi-projeto planejado |
| `game-specification` | [spec.md](game-specification/spec.md) | Fase 3 | Contratos JSON parciais no âncora; engine genérica planejada |
| `game-templates` | [spec.md](game-templates/spec.md) | Fase 4 | Inventário reutilizável auditado; Registry planejado |
| `game-testing` | [spec.md](game-testing/spec.md) | Fase 8 | Runners GDScript ativos no âncora (`229` + `Action` + `Boot`) |
| `infrastructure` | [spec.md](infrastructure/spec.md) | Fase 1 | Ativa e verificada (`008` arquivada: Docker Compose, DevContainer, CLI Linux+Win) |
| `security` | [spec.md](security/spec.md) | Transversal | Políticas ativas (`.gitignore`, *fail-closed*, isolamento) |

## Capabilities Mapeadas para Fases Futuras (Sem Diretórios Vazios)

`game-generator` (Fase 5) • `game-design` (Fase 3) • `gameplay-systems` (Fases 4–5) • `asset-pipeline` (Fase 7) • `audio-pipeline` (Fase 7) • `balance-engine` (Fase 8) • `build-engine` (Fase 10) • `publishing` (Fase 10) • `agents` (Fase 6) • `model-router` (Fase 6) • `rag-memory` (Fases 6/11) • `automation` (Fase 9) • `mcp` (Fase 6) • `analytics` (Fase 11).
