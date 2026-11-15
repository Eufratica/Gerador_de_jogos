# DATABASE.md — Estratégia de Dados, Telemetria & Memória Semântica

> **Estado Atual (Fase 0):** A pasta `data/` contém apenas `.gitkeep`; ainda não há PostgreSQL, pgvector, Valkey ou banco SQLite gerado em disco. O único armazenamento em runtime hoje no jogo-âncora é o JSON local de checkpoint (`local_checkpoint_store.gd` em `user://checkpoint_v1.json`).

---

## 1. Estratégia Unificada (Sem Bancos Duplicados)

1. **PostgreSQL + extensão `pgvector` (Fonte Central de Verdade da Fábrica — Fases 2/6+):**
   - Dados transacionais e relacionais: `projects`, `games`, `game_specifications`, `gdds`, `templates`, `template_versions`, `components`, `assets`, `asset_metadata`, `agents`, `agent_runs`, `prompts`, `model_executions`, `workflow_executions`, `approvals`, `test_results`, `incidents`, `builds`, `releases`, `dependencies`, `licenses`, `analytics`, `audit_logs`.
   - Memória semântica (`pgvector`): evita manter um banco vetorial separado como `Qdrant` sem justificativa concreta, reconciliando a menção anterior ao Qdrant em `AGENTS.md` v1 / `001`.
2. **SQLite Local (Jogos Produzidos):**
   - Persistência/telemetria local embarcada nos jogos com ciclo de vida isolado por jogo.
3. **Valkey (Opcional quando houver fila/cache real):**
   - Introduzido apenas quando tarefas assíncronas ou cache distribuído justificarem.

---

## 2. Regras de RAG, Memória por Projeto & Migrations

- **Coleções Semânticas Previstas:** `game_design_patterns`, `gameplay_mechanics`, `asset_knowledge`, `balance_patterns`, `bug_history`, `generated_game_history`, `player_feedback`, `production_lessons`, `template_documentation`.
- **Isolamento por `project_id` / `game_id` / `version`:** conhecimento específico de um jogo é filtrado por projeto; apenas padrões gerais curados são compartilhados com a fábrica. Memória vetorial **nunca substitui** dados transacionais nem a fonte versionada no Git.
- **Migrations:** toda alteração estrutural usará migrations versionadas em `database/migrations/` (a ser criada na Fase 2).
