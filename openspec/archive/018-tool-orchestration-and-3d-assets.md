# OpenSpec 018 (arquivado): Orquestração de Ferramentas, Assets 3D e PBR (`P2`)

- **Status:** `[DONE]` — TOOL-01..TOOL-03 implementados.
- **Evidência:** `python -m unittest discover -s factory/tests -v` → `Ran 120 tests in 130.232s`, `OK` (inclui `test_tool_and_3d_assets.py` + `test_asset_audio_pipeline.py`).
- **Ferramentas reais no host:** `Gyan.FFmpeg 9.0.2` e `Ollama 0.40.16` instalados via `winget`; descoberta Windows adicionada em `synthesizer.py` e `model_router.py`.
- **Spec resultante:** [tool-orchestration](../specs/tool-orchestration/spec.md)
