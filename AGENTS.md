# AGENTS.md — Contrato Central de Governança da PlayForge Factory

**Repositório:** `Gerador_de_jogos`  
**Fábrica:** `PlayForge Factory` *(nome de trabalho)*  
**Jogo-Âncora Atual:** `Zaikor: Zenkai Infinite` *(identidade histórica anterior: `TITAN SAIYAN: IDLE CLASH` — ver [DECISIONS.md](DECISIONS.md))*  
**Metodologia:** SDLC + SDD (`OpenSpec`) + Documentation as Code  
**Política Financeira:** **ZERO COST / FREE FIRST** (ver [FREE_TIER_POLICY.md](FREE_TIER_POLICY.md))

---

## 1. Papel do Repositório e Separação Obrigatória

Este repositório abriga dois produtos conceitualmente distintos que **não podem ser acoplados**:

1. **PlayForge Factory (Fábrica de Jogos):** infraestrutura modular para pesquisar mercados, gerar especificações (`Game Specification` + `GDD`), gerenciar múltiplos projetos isolados, selecionar templates validados, gerar projetos Godot, orquestrar agentes (`LangGraph` + `Ollama` + `MCP` + `n8n Community`), validar QA/balanceamento e preparar builds.
2. **Jogos Produzidos pela Fábrica (`Zaikor` como projeto-âncora):** projetos independentes com identidade, código, configurações, assets, saves, testes e versões próprias.

> **Regra de Preservação em Transição (Fase 0):** Os módulos funcionais do jogo-âncora estão atualmente na raiz (`project.godot`, `config/`, `src/core/`, `src/engine/`, `src/factory/`, `tests/`). **É proibido mover, apagar ou quebrar esses caminhos** sem plano de migração e ADR aprovados.

---

## 2. Princípios Invioláveis

1. **Preservação e Histórico:** Nunca apagar ou reescrever código funcional apenas para adequar nomes ou pastas sem especificação e aprovação.
2. **Zero Inventividade / Fatos vs. Hipóteses:** Nunca transformar suposições em requisitos; investigar repositório/ambiente e solicitar validação humana em decisões críticas.
3. **Nenhuma Alteração Estrutural Sem ADR + Aprovação:** Trocar engine, banco, orquestrador de agentes, motor de automação, contratos MCP, política de segurança, isolamento entre jogos ou introduzir serviços pagos exige `Discovery ➔ Proposta/SDD ➔ Análise de Impacto ➔ ADR ➔ Aprovação Humana`.
4. **Separação Pura no Código Godot (`src/core/` vs `src/engine/` & `src/adapters/`):**
   - `src/core/` deve permanecer **100% puro, determinístico (PRNG seedável, relógio injetável) e offline**, sem depender de `Node`, `SceneTree`, `FileAccess`, rede ou env global, rodando testes CLI headless em `< 1s`.
   - `src/engine/` e `src/adapters/` encapsulam cena, áudio, entrada, SDKs e I/O atrás de interfaces explícitas (*Ports & Adapters*).
5. **Qualidade Baseada em Evidências (`Fail-Closed`):** Nenhum gate ou teste é declarado aprovado sem execução observada pós-edição e zero fallbacks permissivos em verificações críticas de integridade, schema, balanço ou consentimento.
6. **Zero Cost (`Free First`):** Proibido acionar APIs pagas (mesmo como fallback), contratar VPS/domínios ou inserir cobrança. Ver [FREE_TIER_POLICY.md](FREE_TIER_POLICY.md).
7. **Segurança e Hermetismo:** Código gerado por IA e dados externos (web, reviews, repos) são **conteúdo não confiável** até validação. Segredos, `.env` real, keystores e tokens são proibidos no Git. Ver [SECURITY.md](SECURITY.md).
8. **Sem Complexidade Prematura:** Não criar microserviços, bancos duplicados ou diretórios vazios sem uso real na fase corrente.

---

## 3. Matriz de Permissões dos Agentes

| Categoria | Ações |
| :--- | :--- |
| **Permitido sem aprovação individual** | Ler arquivos, auditar código/Git, criar documentação, criar e executar testes locais, gerar relatórios, executar tarefas previamente aprovadas em escopo delimitado. |
| **Exige aprovação explícita** | Alterar arquitetura central, contratos/ADRs, migrar pastas do jogo-âncora, instalar/mudar dependências estruturais, executar migrações críticas, excluir projetos/histórico, alterar balanceamento de produção, ativar serviços externos ou preparar publicação em lojas. |
| **Proibido sem autorização explícita** | Contratar serviços, ativar cobranças, comprar domínios, usar APIs pagas, inserir cartão, expor credenciais, desabilitar proteções ou publicar versões. |

---

## 4. Ciclo Obrigatório de Sessão e Desenvolvimento

### Início de Sessão
Antes de editar código ou infraestrutura, todo agente deve ler:
1. [AGENTS.md](AGENTS.md)
2. [PROJECT.md](PROJECT.md)
3. [docs/SESSION_STATE.md](docs/SESSION_STATE.md)
4. [ROADMAP.md](ROADMAP.md) e [TASKS.md](TASKS.md)
5. [openspec/config.yaml](openspec/config.yaml) e mudanças ativas em `openspec/changes/`
6. Estado real do Git (`git status`, `git log -n 5`)

### Fluxo de Mudanças (SDD / OpenSpec + 4 Mentores)
- Mudanças históricas `001`–`006` seguem o ciclo `ENTENDER (SDD) ➔ IMPLEMENTAR ➔ REVISAR & AUDITAR TESTES ➔ PROMOVER & ARQUIVAR`.
- Mudanças da fábrica seguem o ciclo SDLC + OpenSpec em `openspec/`: `Explore ➔ Propose ➔ Specs ➔ Design ➔ Tasks ➔ Apply ➔ Verify ➔ Sync ➔ Archive` *(atualmente operado em Markdown manual; CLI `openspec` não instalado — ver `openspec/config.yaml`)*.

### Finalização de Sessão
1. Atualizar [docs/SESSION_STATE.md](docs/SESSION_STATE.md), [TASKS.md](TASKS.md) e documentação afetada.
2. Registrar evidências reais dos comandos executados (comandos, contagens, tempos e limitações).
3. Não avançar de fase sem aprovação humana quando houver gate de fase.
