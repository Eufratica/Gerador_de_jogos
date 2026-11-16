# Capability Specification: `asset-audio`

- **Capability ID:** `asset-audio`
- **Status:** `IMPLEMENTED_PHASE_7` *(AssetRegistry isolado por projeto, validacao binaria PNG/WAV/OGG, governanca comercial/licencas fail-closed, sintese procedural Zero Cost, `asset-mcp` & `audio-mcp` e auditoria Godot 4.4 headless)*
- **Referências Técnicas:** [docs/ASSET_PIPELINE.md](../../docs/ASSET_PIPELINE.md) | [docs/AUDIO_PIPELINE.md](../../docs/AUDIO_PIPELINE.md) | [docs/LICENSE_COMPLIANCE.md](../../docs/LICENSE_COMPLIANCE.md) | [ai-agents](../ai-agents/spec.md)

## Contratos Ativos

1. **Registro e Proveniência Obrigatória (`AST-01`):**
   - Todo asset registrado em `games/<project_id>/assets/asset_registry.json` contém integralmente os 20 campos do contrato (`asset_id`, `name`, `asset_type`, `project_id`, `game_id`, `version`, `file_path`, `format`, `dimensions`, `resolution`, `byte_size`, `origin`, `author_or_provider`, `tool_used`, `model_used`, `prompt_or_seed`, `license`, `restrictions`, `sha256_hash`, `validation_status`).
   - Escrita restrita exclusivamente a `assets/` ou `audio/` de projetos mutáveis (`zaikor` protegido com `ProtectedProject`; escapes/segredos bloqueados com `AssetValidationError`).
2. **Licenças Comerciais e Proveniência IA (`AST-02`):**
   - Licenças ausentes, proprietárias, `-NC` (não comerciais), `-ND` ou `UNKNOWN` falham fechado (`AssetLicenseError`).
   - Licenças que requerem atribuição (`CC-BY-4.0`, `OFL-1.1`) exigem registro explícito em `restrictions`.
   - Ativos de IA (`local_ai_verified`) exigem `model_used`, `prompt_or_seed` e licença comercial compatível explicitamente documentados.
3. **Inspeção Técnica, Anti-Órfão e Decodificação Godot (`AUD-01`):**
   - `inspect_png` valida assinatura, chunk `IHDR`+CRC32 e `IEND`; `inspect_wav` valida PCM16, sample rate e zera/rejeita clipping (`clipped_samples > 0`).
   - `audit_project_assets` reprova arquivos órfãos ou temporários (`.tmp`, `.bak`) não registrados e executa verificação opcional em **Godot 4.4 headless** (`Image.load_from_file` e `AudioStreamWAV.load_from_file`).
