# Spec: Base Godot, Renderizador Compatibility & Perfis Gráficos — Zaikor: Initine Zenkai

## 1. Problema que Resolve
Estabelecer o projeto Godot executável inicial isolado com o renderizador `gl_compatibility`, resolução de referência `1280×720`, perfis gráficos validados *fail-closed* para a `Intel Iris Xe` e suíte automatizada de testes de inicialização.

## 2. Comportamento Esperado
- O projeto abre diretamente na cena `res://scenes/main/main.tscn` em janela `1280×720` com `gl_compatibility`.
- Por padrão inicia no perfil **Baixo** (`fps_cap = 30`, sombras simples, sem `glow`/`fog` pesado), permitindo alternância via `F1`/`F2`/`F3` (`Baixo`/`Médio`/`Alto` experimental).
- Perfis inválidos ou tentativas de habilitar recursos vedados (`lumen`, `nanite`, `ray_tracing`, `virtual_shadow_maps`, `heavy_volumetrics`) são rejeitados *fail-closed* por `ZizGraphicsConfig.validate_profile`.

## 3. Requisitos & Critérios de Aceitação
- [x] `project.godot` fixado em `rendering/renderer/rendering_method="gl_compatibility"`, `1280×720` e `InputMap` básico mapeado (`13` ações).
- [x] `scripts/core/graphics_config.gd` e `game_bootstrap.gd` 100% puros (`RefCounted`, zero dependências de cena/arquivo) testados via `tests/unit/run_unit_tests.gd` em `< 1s` (`16` assertions, `3.28 ms`).
- [x] Cena base 3D (`scenes/main/main.tscn`) carrega sem erros, alterna perfis e encerra com `0` nós órfãos em `tests/integration/verify_main_boot.gd`.
- [x] Medição baseline inicial executada e registrada sem números fabricados (`Intel(R) Iris(R) Xe Graphics`, `35.74 MB`, `31.0 FPS` steady-state / warmup incluído no primeiro boot frio `9.65 s`).
