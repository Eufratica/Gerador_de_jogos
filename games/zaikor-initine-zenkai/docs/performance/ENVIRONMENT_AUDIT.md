# Auditoria Real do Ambiente — Zaikor: Initine Zenkai (`Fase 0`)

**Data da Inspeção:** `2026-11-16`
**Escopo:** Verificação real do hardware Windows 11, ferramentas instaladas, capacidade de disco/RAM e versão oficial da Godot Engine.

---

## 1. Hardware Verificado no Host

| Componente | Especificação Esperada (Prompt) | Valor Real Observado no Host | Observação Técnica |
| :--- | :--- | :--- | :--- |
| **Processador** | Intel Core i5-1135G7 (4c/8t) | `11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz` (`4` cores / `8` threads) | Aderente |
| **GPU** | Intel Iris Xe Graphics (integrada) | `Intel(R) Iris(R) Xe Graphics` (sem GPU dedicada) | Exige `Compatibility Renderer` e controle rígido de *draw calls* / shaders / texturas |
| **Memória RAM Total** | `10 GB` @ `2133 MT/s` | `11.74 GB` utilizáveis (`DIMM A`: `8 GB` @ `3200 MT/s` + `DIMM B`: `4 GB` @ `2667 MT/s`; clock ativo: **`2133 MT/s`**) | Configuração **assimétrica (flex-mode)**: os primeiros 8 GB operam em dual-channel e os 4 GB restantes em single-channel; iGPU compartilha esta banda |
| **Armazenamento** | SSD | Drive `C:` com **`132.56 GB` livres** de **`475.69 GB` totais** | Espaço amplo para projeto, Blender e exports |

> **Conclusão de Memória & Canal:** A dúvida sobre dual-channel da Seção 7 foi esclarecida via WMI/CIM (`Win32_PhysicalMemory`): há 2 pentes heterogêneos (`8 GB` + `4 GB`) limitados a `2133 MT/s`, portanto deve-se assumir banda reduzida e limite conservador de consumo pelo jogo (`<= 4 GB`, idealmente `< 1.5–2 GB` na Vertical Slice).

---

## 2. Ferramentas Locais Auditadas

| Ferramenta | Status no Host | Caminho / Versão Verificada | Uso no Projeto |
| :--- | :--- | :--- | :--- |
| **Godot Engine (Atual)** | Instalada | `Godot_v4.4-stable_win64.exe` (`4.4.stable.official.4c311cbee`) em `../../tools/godot/` | Execução imediata e testes headless já operacionais |
| **Godot 4.7.2 Stable** | **Instalada (Aprovada `ZIZ-GATE-01`)** | `4.7.2.stable.official.ed1daf0bf` em `../../tools/godot-4.7.2/` (SHA-512 validado) | Engine principal oficial de `Zaikor: Initine Zenkai` |
| **Godot 4.8** | Não instalada / **Vetada** | Confirmada na web em fase **Beta** (`4.8 beta 3`, nov/2026) | Proibida pela regra *"Não utilize versões beta, nightly ou experimentais"* |
| **Blender** | Instalado | `Blender 5.3.0` (`C:/Program Files/Blender Foundation/Blender 5.3/blender.exe`) | Modelagem low-poly, rig, animação e export `GLB/GLTF` |
| **FFmpeg** | Instalado | `9.0.2` (`Gyan.FFmpeg` via `winget`) | Processamento/conversão de áudio `.wav`/`.ogg` gratuitos |
| **Ollama (IA Local)** | Instalado & Ativo | `0.40.16` (`127.0.0.1:11434`), modelo `qwen2.5-coder:3b` | Apoio local gratuito via PlayForge Factory |
| **Docker / Linux** | Presentes no host para a fábrica | Não exigidos pelo jogo | Execução do jogo será **100% nativa no Windows** (Seção 24) |

---

## 3. Riscos e Mitigações Identificadas na Fase 0

1. **Banda da Intel Iris Xe + RAM 2133 MT/s:** Mitigada com `Compatibility Renderer`, resolução `1280 × 720`, baixa contagem de polígonos, materiais PBR econômicos/compartilhados, ausência de volumetria/Lumen/VSM e benchmark progressivo a cada bloco na Etapa 13.
2. **Divergência de versão Godot (`4.4.stable` instalada vs `4.7.2 Stable` especificada):** Mitigada via gate explícito `ZIZ-GATE-01` antes de criar o `project.godot` na Etapa 1.
