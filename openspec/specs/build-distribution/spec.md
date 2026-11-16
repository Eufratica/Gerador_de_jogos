# Capability: `build-distribution`

Origem: OpenSpec `019` (Fase 10 / `P3`). Código: `factory/playforge/build_system/`. Testes: `factory/tests/test_build_system.py`.

## Requisitos
- **BLD-01 — Inspeção real de toolchains:** `BuildManager.probe_build_toolchains()` verifica disponibilidade real de `godot`, `java`, `keytool`, `adb`, `android_sdk`, export templates Godot, `Unity`, `Unreal` sem simular capacidade ausente (`paid_services_enabled: false`).
- **BLD-02 — Empacotamento auditável & gates fail-closed:** `BuildManager.build_target()` bloqueia `zaikor`, valida `game_specification.json` e alvo em `target_platforms`, bloqueia segredos (`.env`, `.keystore`, etc.) e arquivos temporários, valida `AssetRegistry` quando presente, empacota ZIP determinístico em `games/<id>/builds/<ver>/<target>/`, registra `artifact_kind: "structural-source-bundle"` + hashes SHA-256 + smoke test Godot real.
- **BLD-03 — Modo nativo estrito:** `--require-native` (`allow_structural_bundle=False`) falha fechado com `BuildTargetUnavailableError` quando export nativo não estiver automatizado/instalado.
- **BLD-04 — Integridade e aprovação humana:** `verify_build()` revalida SHA-256 de ZIP e entradas internas (`BuildIntegrityError` em adulterações); `approve_release()` exige verificação aprovada e aprovação humana explícita (`RELEASE_APPROVED`, `published_externally: false`).

## CLI
`build-toolchains`, `build-package`, `build-verify`, `build-approve-release`.
