# Capability: `telemetry-evolution`

Origem: OpenSpec `021` (Fase 11 / `P5`). Código: `factory/playforge/evolution/`. Testes: `factory/tests/test_evolution_phase11.py`.

## Requisitos
- **EVO-01 — Memória RAG Local Zero Cost:** `LocalRagMemory` indexa metadados, `GameSpecification`, relatórios de seleção de engine, `AssetRegistry`, relatórios QA e `BuildManifest` usando vetorização TF-IDF + cosseno em `stdlib` (`data/rag/knowledge_index.json`), com bloqueio anti-*prompt-injection* (`scan_prompt_injection`) e zero chamadas pagas.
- **EVO-02 — Telemetria & Otimização Assistida:** `OptimizationAdvisor` coleta métricas reais observadas no workspace (FPS/RAM alvo, tamanho e formato de assets, scripts, status QA) e grava `qa/optimization_recommendations.json` com `auto_applied: false` e `requires_human_approval_for_changes: true`, protegendo `zaikor`.
- **EVO-03 — Painel Executivo Multi-Projeto:** `FactoryDashboard.summarize()` consolida visão multi-projeto (`stage`, `engine`, `spec_present`, `asset_count`, `qa_passed`, `build_targets`) com leitura segura do jogo-âncora.

## CLI
`evolution-index`, `evolution-search`, `evolution-optimize`, `evolution-dashboard`.
