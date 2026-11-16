# TESTING.md — Guia Oficial de Testes, Quality Gates e Validações (PlayForge Factory)

> Consolida os comandos executáveis reais, gates *fail-closed* e o histórico de estratégia técnica de [TESTING_STRATEGY.md](TESTING_STRATEGY.md) e [QA_STRATEGY.md](QA_STRATEGY.md).

---

## 1. Regra Inviolável (*Fail-Closed*)

Nenhum módulo, template, spec, asset, build ou jogo é declarado aprovado com base apenas na geração de arquivos. Exige-se **execução observada pós-edição** sem erros, falhas ou regressões silenciosas.

---

## 2. Suítes Executáveis Atuais (`VERSION 1.0.0`)

### 2.1 Fábrica Python (`factory/tests/` — Stdlib `unittest`)
Executa todas as 13 suítes (`136` testes totais cobrindo Fases 2–11 e Incrementos `P1`–`P5`):
- `test_factory_core.py` (`19`), `test_spec_engine.py` (`28`), `test_template_registry.py` (`15`), `test_game_generator.py` (`7`), `test_ai_mcp.py` (`10`), `test_asset_audio_pipeline.py` (`6`), `test_qa_balance_engine.py` (`9`), `test_automation.py` (`6`), `test_engine_orchestrator.py` (`10`), `test_tool_and_3d_assets.py` (`10`), `test_build_system.py` (`7`), `test_gameplay_and_agents.py` (`5`), `test_evolution_phase11.py` (`4`).

```powershell
# Local / Host Windows:
python -m unittest discover -s factory/tests -v

# Dentro do container factory-runner (Linux):
.\infrastructure\scripts\playforge.ps1 test-factory
```

### 2.2 Jogo-Âncora `Zaikor: Zenkai Infinite` (`Godot 4.4` Headless)

```powershell
# Suíte completa Windows (Unit 229 assertions < 1s + Action Balance + Engine Boot 14 assertions):
.\infrastructure\scripts\playforge.ps1 test-win

# Suíte completa Linux no container factory-runner:
.\infrastructure\scripts\playforge.ps1 test-linux
```

### 2.3 CLI Operacional (Multi-Engine, Assets, QA, Build, Automação & Evolução)
```powershell
python -m factory.playforge.cli engine-matrix
python -m factory.playforge.cli tool-status
python -m factory.playforge.cli ai-health
python -m factory.playforge.cli agent-roles
python -m factory.playforge.cli gameplay-catalog
python -m factory.playforge.cli build-toolchains
python -m factory.playforge.cli qa-run zaikor --frames 3 --strict
python -m factory.playforge.cli automation-validate --strict
python -m factory.playforge.cli evolution-dashboard
```
