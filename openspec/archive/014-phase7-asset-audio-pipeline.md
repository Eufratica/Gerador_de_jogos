# OpenSpec Change 014: Fase 7 — Asset & Audio Pipeline

- **ID:** `014-phase7-asset-audio-pipeline`
- **Status:** `[ARCHIVED]` *(Concluído e validado em 2026-11-15)*
- **Fase SDLC:** `Fase 7 — Asset & Audio Pipeline`
- **Capabilities Alvo:** `asset-audio` (`AST-01`, `AST-02`, `AUD-01`), `ai-agents`, `security` (`SEC-01`, `SEC-02`)

---

## 1. Resumo da Auditoria e Implementação

1. **Auditoria de Ferramentas (`asset-toolchain`):** confirmada ausência de `ffmpeg`, `blender`, `krita`, `gimp`, `magick` e `sox` no host, disponibilidade de `Godot_v4.4-stable_win64_console.exe` (`Image.load_from_file=true`, `AudioStreamWAV.load_from_file=true`) e política Zero Cost (`paid_services_enabled: false`).
2. **`factory/playforge/asset_pipeline/`:**
   - `schemas.py`: contratos de `AssetRegistry` (20 campos obrigatórios de `docs/ASSET_PIPELINE.md`), lista fechada de licenças comerciais aprovadas, bloqueio de marcadores não comerciais/desconhecidos e exceções `AssetValidationError` / `AssetLicenseError` / `AssetNotFoundError`.
   - `validator.py`: validadores binários puros `inspect_png` (magic + `IHDR` CRC32 + `IEND`), `inspect_wav` (PCM16, taxa, duracao, dBFS e bloqueio de clipping) e `inspect_ogg`, além de `validate_license_and_provenance` (exigindo atribuição em `CC-BY-4.0`/`OFL-1.1` e `model_used`/`prompt_or_seed` em IA local).
   - `synthesizer.py`: sintetizadores locais Zero Cost em stdlib (`synthesize_png_sprite` com 5 padrões RGBA e `synthesize_wav_audio` com 6 presets PCM16 sem clipping) + `resolve_factory_godot_bin`.
   - `registry.py`: `AssetRegistry` isolado em `games/<project_id>/assets/asset_registry.json`, geração de pack inicial (`generate_default_pack` com 7 assets), `audit_project_assets` contra adulteração de hash, arquivos órfãos/temporários e validação real em **Godot 4.4 headless**.
   - `cli_handlers.py` + `cli.py`: subcomandos `asset-toolchain`, `asset-generate-pack`, `asset-register`, `asset-list`, `asset-audit` e `audio-inspect`.
3. **MCP & Contratos de Agentes:** adicionados `asset-mcp` (4 tools) e `audio-mcp` (3 tools) em `factory/playforge/mcp/servers.py` e permissões mínimas explícitas em `art-asset`, `audio`, `qa` e `auditor` (`factory/playforge/ai/agents.py`).
4. **Testes:** 6 novos testes unitários e E2E em `factory/tests/test_asset_audio_pipeline.py` (85 testes Python totais aprovados).

---

## 2. Critérios de Aceitação (`Verify`) — Evidências

- [x] `asset-toolchain` relata fielmente ausência de CLIs externos e presença de sintetizadores locais + Godot 4.4.
- [x] PNGs corrompidos/CRC inválidos e WAVs com clipping falham fechado (`AssetValidationError`).
- [x] Licenças `UNKNOWN`/`CC-BY-NC-4.0`/`ALL_RIGHTS_RESERVED`, `CC-BY-4.0` sem atribuição e IA local sem modelo/seed falham fechado (`AssetLicenseError`).
- [x] `zaikor`, caminhos fora de `assets/`/`audio/`, arquivos órfãos e `.tmp` são bloqueados.
- [x] `audit_project_assets(verify_godot=True)` executa `Godot 4.4 --headless` real decodificando PNGs e WAVs gerados (`AssetsVerified:7 | Failed: 0`).
- [x] Suíte Python completa (`85` testes em `factory/tests/`) e jogo-âncora `Zaikor` (`playforge.ps1 test-win`) passam 100% após a última edição sem modificar `Zaikor`.
