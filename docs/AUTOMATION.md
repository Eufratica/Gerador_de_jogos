# AUTOMATION.md — LangGraph vs. n8n Community Edition & Workflows

> **Estado Atual (Fase 0):** Nenhum serviço `LangGraph` ou `n8n` está implantado ainda. Serão introduzidos progressivamente nas Fases 6 e 9.

---

## 1. Separação Clara de Responsabilidades

Não duplicar lógicas equivalentes nem criar workflows gigantes:
- **LangGraph (Fase 6):** controla o **estado interno inteligente** entre os 14 agentes (passagem de contexto, revisões iterativas, loops com limite, checkpoints e retomada de grafos multiagentes).
- **n8n Community Edition (Fase 9):** controla **automações externas/de negócio**, webhooks, agendamentos, notificações, filas de **Human-in-the-Loop** e disparo dos pipelines macro entre módulos da fábrica.

> **Conformidade de Licença (n8n):** utilizar apenas internamente conforme permissões da *Sustainable Use License* vigente; nunca expor o editor administrativo aos usuários finais nem revender n8n como produto próprio. Ver [LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md).

---

## 2. Catálogo Progressivo de Workflows (`WF-001` a `WF-020`)

| ID | Nome | Trigger / Responsabilidade | Gate / Aprovação |
| :--- | :--- | :--- | :--- |
| `WF-001` | Project Initialization | Criar projeto isolado e registro inicial | Automático (auditado) |
| `WF-002` | Market Research | Coleta/síntese de referências do gênero | Sanitização anti-injection |
| `WF-003` | Game Design Document | Geração versionada do GDD (25 itens) | Revisão humana recomendada |
| `WF-004` | Game Architecture | Definição técnica dos módulos | Revisão arquitetural |
| `WF-005` | Game Specification | Conversão e validação de schema JSON | Gate schema *fail-closed* |
| `WF-006` | Template Selection | Seleção e compatibilidade no Registry | Gate compatibilidade |
| `WF-007` | Project Generation | Instanciar workspace isolado + código | Diff & sandbox guard |
| `WF-008` | Asset Generation | Especificação, produção e licenciamento | Gate licença + formato |
| `WF-009` | Gameplay Development | Coordenação de mecânicas no escopo | Unit + headless tests |
| `WF-010` | UI/UX Generation | Integração HUD/menus no projeto ativo | Engine boot test |
| `WF-011` | Integration | Ligação de cenas/sistemas/saves | Integration tests |
| `WF-012` | Game QA | Execução completa da suíte headless | QA Gate *fail-closed* |
| `WF-013` | Balance Audit | Simulação por gênero e soft-lock check | Balance Gate |
| `WF-014` | **Human Approval** | Pausa estado e aguarda decisão nominal | **Bloqueio humano explícito** |
| `WF-015` | Build Generation | Exportação, hashes e relatório | Pré-requisito QA+Balance |
| `WF-016` | Publishing | Preparação/envio após autorização | **Aprovação humana obrigatória** |
| `WF-017` | Analytics Collection | Ingestão local/telemetria agregada | Privacy check |
| `WF-018` | Game Optimization | Sugestão de ajustes orientados por dados | Proposta OpenSpec (`SDD`) |
| `WF-019` | Error Recovery | Retry limitado, checkpoint e rollback | Anti-corrupção |
| `WF-020` | Factory Monitoring | Saúde dos serviços, execuções e logs | Observabilidade contínua |

Todo export em `automation/exports/` (a ser criado na Fase 9) deverá ser importável, versionado e **100% livre de credenciais reais**.
