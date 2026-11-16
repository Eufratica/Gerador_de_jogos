# Proposal — 002: Etapa 1 — Projeto Godot Funcional em Compatibility Renderer

## Necessidade
Criar a fundação executável em **Godot 4.7.2 Stable** (`Compatibility Renderer`, `1280×720`, perfil gráfico `Baixo` padrão) para validar boot limpo, perfis gráficos, mapa inicial de entrada e medição baseline no hardware real antes de implementar personagem 3D e câmera na Etapa 2.

## Escopo
- Instalar `Godot 4.7.2 Stable` lado a lado em `../../tools/godot-4.7.2/` conforme aprovação `ZIZ-GATE-01` (opção A).
- Configurar `project.godot` com `Compatibility Renderer`, `1280×720` e ações base do `InputMap`.
- Implementar `scripts/core/graphics_config.gd`, `scripts/core/game_bootstrap.gd` e `scenes/main/main.tscn` + `main.gd`.
- Implementar suíte unitária (`tests/unit/`) e teste de integração de boot + zero nós órfãos (`tests/integration/`).
