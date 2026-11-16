# HANDOFF.md — Guia de Retomada para a Próxima Sessão

## 1. Situação Atual

A **Etapa 1 — Projeto Godot Funcional (`0.1.0-etapa1`)** está concluída e validada em **`Godot 4.7.2.stable.official.ed1daf0bf`** usando **`Compatibility Renderer`** em `1280×720`, com testes unitários (`16` assertions, `3.28 ms`), boot de cena com `0` nós órfãos e execução real na `Intel(R) Iris(R) Xe Graphics`.

---

## 2. Comando de Execução Manual no Windows

```powershell
.\tools\godot-4.7.2\Godot_v4.7.2-stable_win64.exe --path C:\Jogo_Android\games\zaikor-initine-zenkai
```
*(Na janela aberta, pressione `F1` = Baixo, `F2` = Médio, `F3` = Alto experimental.)*

---

## 3. Próxima Entrega Planejada (`Etapa 2 — Personagem e Câmera`)

1. Abrir change OpenSpec `003-character-and-third-person-camera`.
2. Especificar em `openspec/specs/` e `scripts/core/` o modelo matemático puro de câmera terceira pessoa (`orbit`, limites de `pitch`, sensibilidade, inversão de eixos, distância padrão vs distância de combate).
3. Criar a cena inicial do protagonista **Zaikor** (`scenes/player/zaikor.tscn` com `CharacterBody3D`, colisor cápsula e silhueta provisória proporcional de `~1.8m` com indicação de frente e módulo inicial antes do rig Blender definitivo) + `SpringArm3D` com anticolisão contra geometria do cenário.
4. Criar testes unitários puros da câmera + teste de integração de colisão do `SpringArm3D` em `Godot 4.7.2` e atualizar `SESSION_STATE.md`, `TASKS.md`, `CHANGELOG.md` e `HANDOFF.md`.
