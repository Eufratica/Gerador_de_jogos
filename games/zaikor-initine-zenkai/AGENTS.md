# AGENTS.md — Governança do Projeto Zaikor: Initine Zenkai

**Projeto:** `Zaikor: Initine Zenkai` (`project_id: zaikor-initine-zenkai`)
**Natureza:** Jogo 3D single-player de ação e aventura em fantasia sombria
**Engine Alvo:** `Godot Engine 4.x Stable` (`4.7.2-stable` recomendada; `4.4.stable` disponível atualmente no host) — **Compatibility Renderer**
**Localização Isolada:** `C:\Jogo_Android\games\zaikor-initine-zenkai\` (gerenciado pela PlayForge Factory, 100% isolado do jogo-âncora 2D na raiz do repositório)

---

## 1. Regras Invioláveis de Arquitetura e Preservação

1. **Isolamento Absoluto do Jogo-Âncora (`ADR-006` da Fábrica):** Nunca editar, mover ou quebrar arquivos da raiz (`../../project.godot`, `../../src/`, `../../config/`, `../../tests/`) ou de outros jogos em `../../games/`. Todo arquivo de `Zaikor: Initine Zenkai` reside estritamente dentro de `games/zaikor-initine-zenkai/`.
2. **Proibição Total de Plágio:** Referências de linguagem cinematográfica (*God of War* como nível de câmera, peso de combate e ritmo) não autorizam copiar personagens, mitologias, nomes, modelos 3D, texturas, animações, cenários, UI, trilhas ou efeitos sonoros existentes.
3. **Nativo Windows + Hardware Real:** Executar e validar nativamente no Windows sem exigir Docker, Linux, GPU dedicada ou APIs/ferramentas pagas.
4. **Renderizador Fixado (`Compatibility Renderer`):** Nunca migrar para `Forward+` ou `Mobile` sem justificativa técnica, medição real na Intel Iris Xe e ADR aprovado. Versões beta/nightly (incluindo `Godot 4.8 beta`) são proibidas como base principal.
5. **Desenvolvimento Incremental por Etapas:** Proibido tentar construir todas as regiões, chefes e sistemas de uma vez. Sempre manter o projeto funcional e validado ao fim de cada etapa.

---

## 2. Papéis Multidisciplinares (Seção 15)

| Papel | Responsabilidade Principal |
| :--- | :--- |
| **Diretor Técnico** | Arquitetura modular, orçamento de frame/RAM, aprovação de renderizador e estabilidade |
| **Game Designer** | Mecânicas de combate/Zenkai, quebra-cabeças Initine, progressão e equilíbrio |
| **Programador de Gameplay** | Câmera 3P, movimentação, combate modular, FSM de inimigos, chefe e salvamento |
| **Artista Técnico** | Integração Blender `GLB/GLTF`, materiais econômicos, LOD, culling e iluminação |
| **Level Designer** | Fluxo espacial e narrativa ambiental (*O Vale do Primeiro Eco* e áreas futuras) |
| **Roteirista** | Universo *Aetheryn*, *Zaikor*, energia *Initine*, estado *Zenkai* e *O Silêncio Primordial* |
| **Engenheiro de QA** | Testes unitários (`scripts/core/`), integração, gameplay, benchmark e regressão |
| **Revisor** | Auditoria contra especificações SDD, OpenSpec, licenças e integridade de cenas |

---

## 3. Regras Obrigatórias de Implementação (Seção 16)

1. Trabalhar em tarefas pequenas e verificáveis via SDD + OpenSpec (`openspec/changes/`).
2. Separar estritamente lógica pura testável em headless (`scripts/core/`) da camada de cenas/nós 3D (`scenes/`, `scripts/player/`, etc.); nunca concentrar UI, combate, câmera e IA em um único script gigante.
3. Usar tipagem explícita em GDScript sempre que possível, funções pequenas e tratamento de erros explícito.
4. Nunca usar pseudocódigo, funções vazias simulando entrega final, dados de benchmark inventados, caminhos absolutos dependentes de máquina ou referências quebradas.
5. Nunca criar pastas vazias sem uso real na etapa corrente.
6. Todo asset externo ou gerado passa por verificação de licença e registro em `docs/art/ASSET_CREDITS.md`.
7. Segredos, tokens e credenciais são estritamente proibidos no projeto.

---

## 4. Ciclo Obrigatório de Sessão (Seção 14)

**Ao iniciar qualquer sessão:** ler `AGENTS.md`, `PROJECT.md`, `SESSION_STATE.md`, `HANDOFF.md`, `TASKS.md`, `DECISIONS.md` e checar `git status` + estado no registro PlayForge.
**Ao finalizar qualquer sessão:** atualizar `SESSION_STATE.md`, `HANDOFF.md`, `TASKS.md`, `DECISIONS.md` (se aplicável), `CHANGELOG.md` e registrar somente arquivos reais, testes executados e medições observadas.
