# Capability: `tool-orchestration`

Origem: OpenSpec `018` (`P2`). Código: `factory/playforge/asset_pipeline/`. Testes: `factory/tests/test_tool_and_3d_assets.py`.

## Requisitos
- **TOOL-01 — Orquestração multi-domínio Zero Cost:** `inspect_media_toolchain()` reporta `tool_orchestration` por domínio (`modeling_sculpting`, `animation`, `audio`, `texturing_pbr`, `environments_terrain`), descobrindo binários reais (`ffmpeg`, `blender`, `krita`, etc.) e marcando `fmod`/`wwise`/`substance_painter` com `mandatory: false` (`paid_services_enabled: false`).
- **TOOL-02 — Formatos 3D, Áudio, Textura & PBR:** Suporte a `glTF 2.0`, `GLB 2.0`, `OBJ`, `FBX` (assinatura), `JPEG`, `MP3`, `PNG`, `WAV`, `OGG` com inspetores *fail-closed* e sintetizadores determinísticos *stdlib* (`synthesize_gltf_mesh`, `synthesize_glb_mesh`, `synthesize_obj_mesh`, `synthesize_pbr_texture_set`).
- **TOOL-03 — Auditoria de Integridade & Rig/Material:** `AssetRegistry.audit_project_assets()` verifica SHA-256, licenças comerciais aprovadas, anti-órfãos, `duplicate_hashes`, `models_missing_materials` e `animations_missing_rig`, reprovando se faltar material em malha 3D ou rig em animação 3D.

## CLI
`asset-generate-3d-pack`, `tool-status`, `asset-toolchain`, `asset-audit`.
