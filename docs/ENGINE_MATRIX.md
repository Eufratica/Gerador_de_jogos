# ENGINE_MATRIX.md — Seleção de Engines, Critérios & Compatibilidade (`Engine Selection System`)

> **Princípio Central:** *"A tecnologia deve se adaptar ao jogo. O jogo não deve ser limitado à tecnologia."* Nenhuma engine padrão é escolhida automaticamente apenas por conveniência; toda seleção gera relatório justificado auditável baseado nos **14 critérios** abaixo.

---

## 1. Matriz Comparativa das Engines Suportadas

| Engine | Melhor Adequação | Linguagens & Tecnologias | Licença / Política Free First | Estado Real no Host / Fábrica |
| :--- | :--- | :--- | :--- | :--- |
| **Godot Engine (`4.4+`)** | Jogos 2D, 3D independentes, RPGs 2D/isométricos, plataforma, estratégia, prototipagem rápida, baixo orçamento/hardware modesto, prioridade open source | `GDScript` *(C#/.NET opcional)*, Cenas/Nodes, Signals, Physics Engine, `AnimationTree`, Shaders | **MIT** (100% open source, `$0`, zero royalties, CLI `--headless`) | **Instalada e Executável Localmente** (`tools/godot/Godot_v4.4-stable_win64_console.exe` — `< 1s` headless) |
| **Unity** | Jogos 2D e 3D multiplataforma, projetos modulares com componentes/prefabs, times em C#, forte ecossistema de plugins | `C#`, GameObjects, Components, Prefabs, Animator, Physics, `URP`, `HDRP` | **Proprietária** (Unity Personal gratuita até limite de receita vigente; exige Unity Hub + conta + .NET) | **Adaptador Estrutural + Detecção de Host** *(não instalada no host atual; compilação bloqueada *fail-closed* até detecção real)* |
| **Unreal Engine (`5.x`)** | Ambientes 3D avançados, realismo gráfico, iluminação avançada, jogos cinematográficos, combate complexo 3ª pessoa, grandes mundos 3D | `C++`, Blueprints, Gameplay Framework, Enhanced Input, Animation Blueprints, `Niagara`, `Lumen`, `Nanite` | **Proprietária / EULA Epic** (`$0` inicial; `5%` royalty > US$ 1M em jogos; não open source) | **Adaptador Estrutural + Detecção de Host** *(ausente; recomendação Epic `32 GB RAM + 8 GB VRAM DX12` excede os `11.74 GB` / GPU integrada deste host)* |

---

## 2. Os 14 Critérios Oficiais de Seleção

Todo pedido avaliado pelo `Engine Selection and Orchestration System` pontua os critérios abaixo em `[0..10]` com pesos documentados:

1. **Gênero** (`action-rpg`, `platformer-2d`, `idle-rpg`, `roguelike`, `strategy`, `action-adventure-3d`, `open-world-3d`, etc.)
2. **Dimensão do mundo** (`2d`, `2.5d`, `3d-indie`, `3d-aaa-large`)
3. **Tipo de câmera** (`side-scroller`, `top-down`, `isometric`, `first-person`, `third-person-cinematic`)
4. **Quantidade de personagens** (contagem simultânea / elenco)
5. **Complexidade das animações** (procedural/2D, retargeting básico, motion capture / Animation Blueprints)
6. **Necessidade de física** (arcada 2D, balística determinística, corpos rígidos 3D / veículos / destruição)
7. **Qualidade gráfica desejada** (`stylized-2d`, `stylized-3d`, `pbr-standard`, `photorealistic-lumen-nanite`)
8. **Plataforma de destino** (`windows`, `linux`, `android`, `web`, `console`)
9. **Desempenho esperado** (`mobile-60fps-low-spec`, `desktop-60fps`, `high-end-gpu`)
10. **Complexidade de desenvolvimento** (tamanho de escopo e velocidade de iteração headless/CLI)
11. **Disponibilidade de ferramentas gratuitas** (sem depender de plugins/serviços pagos)
12. **Requisitos de hardware do ambiente/alvo** (consulta hardware real via `inspect_environment`: RAM, threads, GPU dedicada)
13. **Licenciamento** (preferência MIT/open source sob política `FREE FIRST` vs. EULA/royalties)
14. **Possibilidade de automação** (CLI headless determinístico, CI/CD e testes automatizados sem GUI manual)

---

## 3. Regra *Fail-Closed* por Adaptador

Cada engine opera via contrato explícito `EngineAdapter` (nunca acoplada ao núcleo de `ProjectManager` / `GameSpecification`):
- **Modo Seleção / Scaffolding:** gera projeto, configurações, scripts e manifestos no diretório isolado `games/<project_id>/`.
- **Modo Execução / Testes / Build:** verifica antes o binário real da engine (`probe_toolchain()`); se ausente ou incompatível com o alvo (ex.: Unreal sem `UE5` + VS/GPU ou Unity sem Unity Editor), **reprova de forma explícita (`EngineToolchainUnavailableError`)** sem simular sucesso.
