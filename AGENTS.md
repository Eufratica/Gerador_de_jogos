# AGENTS.md: CONTRATO CENTRAL DE ENGENHARIA, FÁBRICA DATA-DRIVEN & GAME DESIGN

**Projeto:** `PLAYFORGE / TITAN SAIYAN: IDLE CLASH`  
**Escopo:** Fábrica autônoma data-driven para jogos mobile 2D/2.5D de alta retenção na **Google Play Store** + Título Âncora *Action Idle RPG* com balística tátil estilo DDTank, escala cósmica Dragon Ball e brutalidade God of War.

Este repositório é governado por um contrato industrial estrito. Nenhuma linha de código de produção pode ser escrita sem especificação aprovada (`SDD`), testes unitários puros offline, Quality Gate ativo (*fail-closed*) e protocolo **OpenSpec + Git**.

---

## 🏛️ 1. REGRAS FUNDAMENTAIS (INVIOLÁVEIS)

1. **Proibido Codificar Sem Planejamento Aprovado (`SDD` + Alinhamento)**
   - Nenhuma alteração de arquitetura, economia, balística, schema ou SDK mobile pode ser iniciada sem diagnóstico, **SDD (Software Design Document)** em `openspec/changes/` e validação prévia das decisões com o operador.
2. **Separação Estrita: Lógica Pura (`src/core/`) vs. Efeitos de Engine & SDKs (`src/engine/` & `src/adapters/`)**
   - **Camada Pura (`src/core/` — Zero dependência de Engine/UI/Rede/Env Global):**
     - Fórmulas de balística parabólica (`x(t)`, `y(t)`, vento dinâmico, colisão contínua em hitbox de cabeça/corpo e deformação lógica de terreno);
     - Matemática `BigNumber` (dano cósmico, custo exponencial, armadura/penetração, multiplicadores de Prestígio/Ascensão e ganho offline por delta de timestamp);
     - Máquinas de estado de combate (`IDLE_AUTO`, `RAGE_BERSERK`, `DDTANK_AIM`, `DDTANK_FLIGHT`, `BOSS_QTE`, `DEFEAT_REVIVE_OFFER`, `PRESTIGE_RESET`) e validação de contratos de economia/Gacha.
     - **Regra de Ouro:** Toda a camada `src/core/` deve rodar e ser testada em **< 1 segundo via CLI/headless**, totalmente offline, determinística (PRNG seedável e relógio injetável), sem abrir editor gráfico, sem rede e sem ler variáveis de ambiente globais.
   - **Camada de Borda (`src/engine/` e `src/adapters/`):**
     - `src/engine/`: Nós da cena (Godot 4.3+ recomendado pelo APK enxuto), shaders neon/aura, partículas, áudio/SFX, touch input e renderização desacoplada da regra de negócio;
     - `src/adapters/`: Ports & Adapters explícitos para **AdMediationPort** (AdMob / AppLovin MAX + Consentimento UMP LGPD/GDPR), **BillingPort** (Google Play Billing v6+ para `No-Ads Pass`), **CloudSavePort** (Supabase/Firebase com assinatura anti-tamper), **TelemetryPort** (SQLite), **RAGMemoryPort** (Qdrant + fallback SQLite embutido) e **AutomationBridgePort** (MCP/n8n).
3. **Princípio `Fail-Closed` nos Quality Gates (Zero Fallbacks Permissivos)**
   - Se um verificador de integridade, assinatura de build, balanço de economia (`BalanceVerifier`), consentimento UMP, validação de probabilidades de Gacha ou auditoria de política da Play Store falhar ou estiver indisponível, o gate **BLOQUEIA** o avanço ou release.
   - Nunca degradar uma checagem crítica para "aprovar tudo" em fallback (ex.: nunca conceder recompensa de anúncio sem callback validado do SDK ou entitlement verificado de `No-Ads Pass`; nunca pular consentimento UMP).
4. **Hermetismo de Config, Segurança & `.gitignore`**
   - Proibido hardcodar chaves, tokens JWT, keystores Android (`.jks`/`.keystore`), arquivos `google-services.json`, senhas de exportação ou credenciais MCP no repositório.
   - Configurações de jogo e fábrica são tipadas via Schema JSON validado e testadas com instâncias isoladas (sem depender do ambiente da máquina).
5. **OpenSpec Change & Memória Persistente no Git**
   - Nenhuma feature entra sem `openspec/changes/00X-nome-da-feature.md` (contratos de dados, invariantes, casos de borda e critérios de aceitação).
   - Memória de chat é efêmera; arquitetura viva, lições aprendidas e changelogs ficam versionados em `docs/ARQUITETURA.md`.

---

## 🔄 2. AS 4 ETAPAS OBRIGATÓRIAS DE DESENVOLVIMENTO (OS 4 MENTORES)

Toda tarefa, mecânica, pacote de conteúdo ou correção percorre obrigatoriamente o pipeline:

`[1. ENTENDER (SDD)] ➔ [2. IMPLEMENTAR (Cirúrgico)] ➔ [3. REVISAR & AUDITAR TESTES] ➔ [4. PROMOVER & ARQUIVAR (OpenSpec)]`

### Etapa 1 — `ENTENDER` (Mentor de Planejamento & SDD)
- Consulta o histórico no `docs/ARQUITETURA.md` e na memória RAG (`src/factory/`) para não repetir erros ou mecânicas saturadas.
- Produz `openspec/changes/00X-<nome>.md` + SDD com schemas declarativos (JSON/DTOs), máquinas de estado, critérios de aceitação e **3 a 5 perguntas de alinhamento** para aprovação do operador.

### Etapa 2 — `IMPLEMENTAR` (Mentor de Execução Cirúrgica)
- Implementa de forma atômica seguindo estritamente o SDD aprovado, mantendo mecânicas, fases, chefes e curvas **data-driven** (em configs/schemas validados, jamais hardcoded na cena).
- Garante **`Zero GC Alloc`** nos loops de combate em 60/120 FPS (object pooling, arrays/structs pré-alocados) e isola efeitos da engine atrás de interfaces claras (`Ports`).

### Etapa 3 — `REVISAR & AUDITAR TESTES` (Mentor de Testes & Auditoria Semântica)
- Audita o `git diff` buscando acoplamento indevido entre `core/` e `engine/`, segredos vazados, mutações fora do escopo e fallbacks silenciosos.
- Executa **3 níveis obrigatórios de verificação**:
  1. **Unitários Puros (`tests/unit/`, offline, determinísticos):** provar que a balística acerta o alvo em 1.000+ combinações de vento/ângulo/força, zero overflow/`NaN` no `BigNumber`, monotonicidade do ganho offline e invariantes do gacha.
  2. **Playtest Headless & Balance Auditor (`BalanceVerifier`):** simular automaticamente milhares de segundos de progressão para detectar travamentos (*progress walls*), soft-locks ou economia quebrada *antes* do build `.aab`.
  3. **Auditoria de Build & Dispositivo:** validação de permissões Android (`AndroidManifest`), consentimento UMP, fluxos de `Rewarded Ads`, `No-Ads Pass` idempotente + `Restore Purchases`, Save/Load anti-tamper e roteiro de teste manual no aparelho.

### Etapa 4 — `PROMOVER & ARQUIVAR` (Mentor de Arquivo & OpenSpec)
- Move a especificação implementada de `openspec/changes/` para `openspec/archive/` e consolida contratos em `docs/ARQUITETURA.md`.
- Registra versão semântica, changelog e indexa decisões + resultados no SQLite/RAG da fábrica.

---

## 🧠 3. CICLO INTELIGENTE DE FÁBRICA (`src/factory/`)

1. **SQLite (`data/game_factory.db`) — Fatos & Telemetria:** catálogo de builds/jogos/temporadas, versões AAB, retenção (D1, D7, duração de sessão, ponto exato de abandono em fases/chefes), conversão de Rewarded Ads e IAP.
2. **Vector DB / Memória RAG (Qdrant + fallback SQLite embutido offline):**
   - `gdd_winning_patterns`: hooks de primeiros 60s, transformações, chefes e economias de maior retenção.
   - `playstore_player_reviews`: avaliações reais (1★ a 5★) de concorrentes (*Slayer Legend*, *Idle Slayer*, *DDTank*, etc.) para eliminar objeções antes do lançamento.
   - Anti-repetição de nomes, falas, skins e curvas geradas.
3. **Otimizador Neural (`BalanceRetentionNN` — PyTorch CLI/Server):** ajusta pesos recomendados da curva de XP/Ouro/HP e cadência de especiais (Remote Config JSON), sempre auditados por limites de segurança e aprovados pelo `BalanceVerifier` (*fail-closed*).
4. **Automação n8n + MCP + Fastlane + Sub-Pipeline de Vídeo 9:16:** orquestração para minerar reviews ➔ propor SDD de ajuste ➔ rodar bateria headless + `BalanceVerifier` ➔ gerar `.aab` assinado via Godot CLI + Fastlane (Faixa Interna) + trailers verticais 9:16 (FFmpeg/Remotion + narração neural limpa com `SentenceBoundary`).

---

## 🎮 4. ESCOPO DO JOGO ÂNCORA & MONETIZAÇÃO PLAY STORE

- **Fusão dos 5 Titãs:**
  1. *Slayer Legend & Idle Slayer:* auto-batalha 24/7, ganho offline com teto anti-exploit (8h), upgrades exponenciais, Gacha com *pity* garantido e Prestígio/Ascensão.
  2. *Dragon Ball:* 5 estágios de transformação visual de Ki (*Base ➔ Fúria Primitiva ➔ Super Saiyajin ➔ Divino ➔ Ultra Instinto*), feixes de energia e notação escalada (`K`, `M`, `B`, `T`, `Qa`, `Qi`, ...).
  3. *God of War:* lâminas com correntes e machados colossais, Chefes Titânicos com quebra de postura e QTE *Finishers*, Barra de Fúria Cósmica (*Berserk*).
  4. *DDTank:* **"DISPARO DE ESPECIAL / POW"** tátil por arraste de ÂNGULO e FORÇA com trajetória parabólica afetada por vento dinâmico, crateras/deformação no terreno e acerto perfeito na cabeça/núcleo (**"POW! CRÍTICO NUCLEAR 10x"**).
- **Monetização & Conformidade Obrigatória:**
  - **Zero Interstitials Forçados** no gameplay.
  - **5 Rewarded Ads Voluntários de Alto Valor:** *Baú do Dragão* (3x offline até 8h), *Fúria dos Deuses* (20 min 2x velocidade + 2x ouro/gemas), *Invocação Diária 10x Grátis* (até 3/dia), *Reviver Imediato no Boss* (HP cheio + Fúria/POW cheia), *Mira Laser Atômica DDTank* (guia preditivo compensando o vento).
  - **IAP `"No-Ads Pass"` (Play Billing v6+ + `Restore Purchases` obrigatório):** entrega todas as recompensas dos Rewarded Ads em 1 clique sem assistir vídeos.
  - **Conformidade Play Store:** Consentimento UMP (LGPD/GDPR), declaração transparente de probabilidades de Gacha, integridade de save e zero coleta abusiva de dados.
