# Spec: Base Arquitetural, Hardware & Governança — Zaikor: Initine Zenkai

## 1. Problema que Resolve
Garantir que o desenvolvimento do jogo 3D *Zaikor: Initine Zenkai* ocorra de forma modular, reproduzível, isolada do projeto-âncora 2D da raiz e rigorosamente dimensionada para o notebook alvo (`i5-1135G7` + `Intel Iris Xe` integrada + RAM flex-mode `@ 2133 MT/s`).

## 2. Requisitos Funcionais (RF)
- **RF-01:** Operar em workspace isolado `games/zaikor-initine-zenkai/` registrado no `ProjectManager` sem alterar a raiz `../../project.godot`.
- **RF-02:** Executar nativamente no Windows 11 sem dependência de Docker, Linux ou serviços pagos em runtime.
- **RF-03:** Manter GDD (`25` seções) e `GameSpecification v2` validados *fail-closed* antes da Etapa 1.
- **RF-04:** Implementar base Godot `4.x Stable` usando **Compatibility Renderer**, viewport base `1280×720`, perfis gráficos (`Baixo`, `Médio`, `Alto` experimental) e separação `scripts/core/` puro vs nós 3D.

## 3. Requisitos Não Funcionais (RNF)
- **RNF-01 (Desempenho Alvo):** Referência `1280 × 720`, meta `30 FPS` no perfil **Baixo**, sujeita a medição real na Etapa 13.
- **RNF-02 (Proibições Técnicas):** Vedados por padrão Ray Tracing, Lumen, Nanite, Virtual Shadow Maps, volumetria pesada e versões Beta do Godot (incluindo `4.8 beta`).
- **RNF-03 (Testabilidade):** Toda regra pura de `scripts/core/` deve rodar em Godot `--headless` em `< 1s`.
- **RNF-04 (Originalidade & Zero Cost):** IP 100% original e ferramentas gratuitas (`Blender 5.3.0`, `FFmpeg 9.0.2`, `Godot`).

## 4. Sistemas Afetados
PlayForge Factory registry (`data/registry/projects.json`), `specs/`, `gdd/`, `docs/`, `openspec/` e futura árvore Godot na Etapa 1.

## 5. Critérios de Aceitação
- [x] Ambiente real auditado (CPU, iGPU, RAM flex-mode, disco, ferramentas, versão Godot web).
- [x] `GameSpecification v2` aprovada por `spec-validate --project` e GDD validado em `25` seções.
- [x] Todos os documentos de governança e continuidade criados sem diretórios vazios ociosos.
- [ ] Gate `ZIZ-GATE-01`: decisão humana sobre `Godot 4.7.2 Stable` vs `4.4.stable` antes da criação de `project.godot` (Etapa 1).
