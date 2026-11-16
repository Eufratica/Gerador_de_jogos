# PROJECT.md — Zaikor: Initine Zenkai

## 1. Visão Geral

- **Título:** `Zaikor: Initine Zenkai`
- **Project ID na Fábrica:** `zaikor-initine-zenkai`
- **Gênero:** Ação e Aventura 3D em Fantasia Sombria (Single-Player, Terceira Pessoa)
- **Versão Atual:** `0.0.1-phase0` *(Pré-produção / Fase 0)*
- **Meta Vertical Slice:** Trecho completo de ~10–15 min ambientado na **Área 1 — O Vale do Primeiro Eco**, com protagonista jogável, câmera em terceira pessoa, movimentação, combate modular, estado *Zenkai*, 3 perfis de inimigos, 1 quebra-cabeça *Initine*, 1 chefe com múltiplas fases, menu/HUD/configurações, áudio adaptativo básico e salvamento versionado.

---

## 2. Alinhamento Engine & Hardware

| Parâmetro | Diretriz do Prompt Mestre | Realidade Verificada no Host (`2026-11-16`) | Decisão Inicial |
| :--- | :--- | :--- | :--- |
| **CPU** | Intel Core i5-1135G7 (4c/8t) | `11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz` (4 núcleos / 8 threads) | Confirmado |
| **GPU** | Intel Iris Xe Graphics (integrada) | `Intel(R) Iris(R) Xe Graphics` (sem GPU dedicada) | `Compatibility Renderer` fixado |
| **RAM** | 10 GB @ 2133 MT/s *(canal a verificar)* | `11.74 GB` totais (`DIMM A 8 GB` + `DIMM B 4 GB` @ `2133 MT/s` — dual-channel assimétrico *flex-mode*) | Orçamento conservador (`<= 4 GB` processo jogo; memória compartilhada c/ SO + iGPU) |
| **Disco** | SSD | Drive `C:` com `132.56 GB` livres de `475.69 GB` totais | Suficiente |
| **Engine** | Godot `4.7.2 Stable` (sem beta) | Instalada localmente: `Godot 4.4.stable`; na web (`godotengine.org`): `4.7.2 Stable` é atual e `4.8` está em **Beta (`4.8 beta 3`)** | `4.8` descartado (beta). Aguardando aprovação humana para baixar `4.7.2 Stable` ou manter `4.4.stable` |
| **Resolução / Meta FPS** | `1280 × 720` / `30 FPS` (perfil Baixo referência) | Ainda sem cena 3D medida *(benchmark real na Etapa 1–13)* | Meta de engenharia sujeita a medição real |

---

## 3. Ferramentas Gratuitas Locais Confirmadas

- **Godot Console / Editor (atual no repo):** `../../tools/godot/Godot_v4.4-stable_win64.exe` (`4.4.stable.official.4c311cbee`)
- **Modelagem / Animação 3D (`GLB/GLTF`):** `Blender 5.3.0` (`C:/Program Files/Blender Foundation/Blender 5.3/blender.exe`)
- **Áudio:** `FFmpeg 9.0.2` (instalado via `winget`)
- **IA Local (apoio conceitual / fábrica):** `Ollama 0.40.16` + `qwen2.5-coder:3b` (`127.0.0.1:11434`, custo zero)

---

## 4. Limitações e Restrições de Desempenho (Seção 7.2)

Proibidos por padrão neste projeto: Ray Tracing, Lumen, Nanite, Virtual Shadow Maps, volumetria pesada, pós-processamento excessivo, reflexos em tempo real em grandes superfícies, excesso de luzes dinâmicas e carregamento simultâneo de regiões inteiras. Prioridade absoluta para LOD, Frustum/Occlusion Culling, instancing, texturas comprimidas, geometria enxuta e perfil gráfico **Baixo** em `1280 × 720`.
