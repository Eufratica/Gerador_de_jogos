# Capability: `gameplay-systems`

Origem: OpenSpec `020` (`P4`). Código: `factory/playforge/gameplay_systems/` + `factory/playforge/ai/agents.py`. Testes: `factory/tests/test_gameplay_and_agents.py`.

## Requisitos
- **GMP-01 — Catálogo Modular Multi-Engine:** 8 sistemas (`locomotion`, `combat_action`, `enemy_ai`, `progression_skills`, `inventory_crafting`, `quests_dialogue`, `world_environment_cycle`, `save_system_versioned`) com geração pura desacoplada para `godot`, `unity` e `unreal`.
- **GMP-02 — Injeção Sob Demanda (Seção 8):** `GameplaySystemInjector.inject_systems()` gera apenas os `system_id`s explicitamente solicitados, protege o jogo-âncora `zaikor`, falha fechado em ID/engine inválido e registra `config/gameplay_systems.json`.
- **GMP-03 — Alinhamento dos 13 Papéis da Seção 10:** `SPECIALIZED_ENGINEERING_ROLE_MAP` e `get_engineering_role_catalog()` vinculam os 13 papéis especializados do Master Engineering Prompt aos 14 contratos existentes de `build_default_agent_contracts()` sem quebrar privilégios mínimos.

## CLI
`gameplay-catalog`, `gameplay-inject`, `agent-roles`.
