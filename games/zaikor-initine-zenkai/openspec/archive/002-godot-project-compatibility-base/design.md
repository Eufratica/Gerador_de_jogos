# Design — 002: Fundação Executável & Perfis Gráficos (Etapa 1)

## Arquitetura de Separação
- **`scripts/core/` (Puro):** `ZizGraphicsConfig` e `ZizGameBootstrap` não herdam `Node` nem acessam `SceneTree`/`FileAccess`, permitindo testes determinísticos rápidos.
- **`scenes/main/` (Borda Engine):** `MainRoot` (`Node3D`) recebe `WorldEnvironment`, `DirectionalLight3D`, plano 3D com `StaticBody3D`, marco visual Initine, `Camera3D` fixa de verificação e `OverlayHUD` exibindo telemetria real em tempo de execução.

## Riscos Mitigados
- Mantém `../../tools/godot/` (`4.4-stable`) preservado para o âncora e fábrica.
- Bloqueia por contrato (`ZizGraphicsConfig.validate_profile`) qualquer ativação acidental de `forward_plus`, `lumen`, `nanite` ou `ray_tracing`.
