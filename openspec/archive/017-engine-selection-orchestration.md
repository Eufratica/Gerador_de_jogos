# OpenSpec 017 (arquivado): Engine Selection and Orchestration System (`P1`)

- **Status:** `[DONE]` — ENG-01..ENG-04 implementados.
- **Evidência:** `python -m unittest discover -s factory/tests -v` → `Ran 110 tests in 37.792s`, `OK` (inclui 10 testes novos em `test_engine_orchestrator.py` e os 28 de `test_spec_engine.py`).
- **Limitações:** Unity e Unreal não estão instalados neste host (11.74 GB RAM, sem GPU dedicada); apenas scaffold/validação estrutural foi exercitado para elas. Execução real de testes só para Godot 4.4.
- **Spec resultante:** [engine-orchestration](../specs/engine-orchestration/spec.md)
