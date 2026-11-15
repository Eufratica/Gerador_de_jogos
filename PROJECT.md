# PROJECT.md — PlayForge Factory (`Gerador_de_jogos`)

## 1. Identidade do Projeto

- **Nome do Repositório / Plataforma:** `Gerador_de_jogos` (**PlayForge Factory**)
- **Natureza:** Fábrica modular data-driven para concepção, especificação, geração, validação, build e evolução de jogos 2D/2.5D em **Godot 4.x + GDScript**.
- **Projeto-Âncora Existente:** `Zaikor: Zenkai Infinite` *(Godot `4.4.stable` — Sprint 4B concluído em `cab6ee8`)*.
- **Orçamento / Política de Infraestrutura:** **Zero Cost / Free First** (execução local-first no Windows 11 + WSL2 + Docker + Ollama + ferramentas open source/gratuitas).

---

## 2. Escopo Duplo (Separação Obrigatória)

### 2.1 A Fábrica (`PlayForge Factory`)
Responsável por administrar múltiplos jogos de forma independente:
- Pesquisa de gêneros/mercado (tratando fontes externas como dados não confiáveis);
- Geração e validação de **Game Design Documents** e **Game Specifications** tipadas/versionadas;
- Registro e reutilização de **Templates** validados (extraídos incrementalmente do jogo-âncora e evoluções);
- Geração controlada e isolada de projetos Godot em diretórios separados;
- Orquestração multiagentes com **LangGraph**, modelos locais via **Ollama** (`Model Router`), memória **PostgreSQL + pgvector**, servidores **MCP** e automação **n8n Community Edition** com aprovações humanas (*Human-in-the-Loop*);
- **QA Engine**, **Balance Engine**, **Asset/Audio Pipeline**, **Build Engine** e telemetria.

### 2.2 Os Jogos Produzidos (`Zaikor` + Novos Projetos)
Cada jogo terá identidade, GDD, especificação, código, assets, testes, saves, builds e métricas próprios.  
**Regra crítica:** o jogo-âncora é referência de engenharia e fonte inicial de componentes reutilizáveis, mas a lógica da fábrica não pertence ao jogo, e alterações no jogo A não podem impactar o jogo B.

---

## 3. Divergências de Identidade Registradas (Ver [DECISIONS.md](DECISIONS.md))

A inspeção da Fase 0 encontrou duas referências nominais distintas no repositório anterior:
1. `AGENTS.md`, `docs/ARQUITETURA.md` e `openspec/changes/001` nomeiam o título âncora como **`TITAN SAIYAN: IDLE CLASH`** (Idle RPG + Dragon Ball Ki + God of War + balística DDTank).
2. `openspec/changes/004`, `archive/005`, `archive/006` e `project.godot` pivôtaram o Jogo 1 entregue como **`Zaikor: Zenkai Infinite`** (2D lateral Dark Fantasy estilo God of War, reaproveitando `BigNum`, `IdleEconomy` e `SeededRng`).

Ambas as trilhas de código (`ddtank_ballistics.gd`, `combat_fsm.gd`, `terrain_heightmap.gd` e `action_combat_core.gd`) coexistem funcionalmente em `src/core/`. A consolidação oficial de nomes e roadmap entre a conclusão mobile do `Zaikor` (`Sprint 4C`) e a construção da `PlayForge Factory` (`Fases 1–11`) está registrada como decisão pendente (`PEND-001` e `PEND-002`) em [DECISIONS.md](DECISIONS.md).

---

## 4. Critério do Primeiro MVP Real da Fábrica (Alvo Futuro — Fase 5+)

A fábrica atingirá seu primeiro MVP funcional quando for capaz de executar ponta a ponta (sem simulação falsa de agentes/builds):
1. Receber ideia e inicializar um segundo projeto isolado;
2. Pesquisar referências, gerar GDD, arquitetura e **Game Specification** validada por schema;
3. Obter aprovação humana da especificação;
4. Selecionar template validado no **Template Registry** e gerar workspace Godot isolado;
5. Integrar mecânicas, UI e assets validados;
6. Executar QA headless, checagem de balanceamento e auditoria automatizada;
7. Gerar preview e build validada após aprovação humana.
