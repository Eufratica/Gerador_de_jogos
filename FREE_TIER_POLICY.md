# FREE_TIER_POLICY.md — Política Financeira Zero Cost (`Free First`)

## 1. Regra Central

Todo o desenvolvimento e operação da **PlayForge Factory** e dos jogos iniciais seguem a política **FREE FIRST / ZERO COST**:
- **Proibido** contratar VPS, comprar domínios, ativar planos pagos, inserir cartão de crédito, fazer deploy pago ou usar APIs comerciais/pagas (inclusive como fallback automático).
- Antes de adotar qualquer ferramenta, biblioteca ou modelo de IA, deve-se verificar **licença**, **custo real** e **existência de alternativa local gratuita**.

---

## 2. Stack Base Gratuita / Local-First Prevista

| Camada | Tecnologia Prevista | Política / Custo | Status Atual no Repo |
| :--- | :--- | :--- | :--- |
| **Game Engine** | Godot Engine 4.x (`4.4.stable` atual) | MIT (100% gratuito/local) | Instalado em `tools/godot/` |
| **IA Local** | Ollama + modelos compatíveis c/ hardware | Execução local (checar licença por modelo!) | Não instalado (`NOT_FOUND`) |
| **Orquestração Agentes** | Python + LangGraph + FastAPI | MIT / open source local | Planejado (Fases 1–6) |
| **Banco & Vetor** | PostgreSQL + pgvector + SQLite + Valkey | Open source / container local | Planejado (Fases 1–2) |
| **Automação** | n8n Community Edition | Uso interno gratuito *(checar Sustainable Use License — ver [LICENSE_COMPLIANCE.md](docs/LICENSE_COMPLIANCE.md))* | Planejado (Fase 9) |
| **Assets & Áudio** | Blender, Krita, GIMP, Audacity, FFmpeg, síntese procedural | Open source / local gratuito | Síntese procedural GDScript ativa no `Zaikor` |
| **Infraestrutura** | WSL2 Ubuntu + Docker Compose + Git/GitHub Free | Local / conta gratuita | Git ativo; Docker/WSL pendentes de inspeção F1 |

---

## 3. Custos Reais Fora do Escopo Automático

Não prometer "custo zero absoluto" para recursos físicos ou externos que dependem de terceiros:
- Hardware local, energia elétrica e armazenamento da máquina do operador;
- Taxas externas de publicação caso o operador decida publicar em lojas comerciais no futuro (ex.: taxa de cadastro na Google Play Console — **bloqueada até aprovação humana explícita**).
- Serviços em nuvem de terceiros com limite de free tier (ex.: Supabase/AdMob no futuro `Sprint 4C` — **nenhum ativado nesta fase**).

Se em alguma etapa futura não houver alternativa gratuita viável, o agente deve **documentar a limitação, apresentar alternativas e aguardar decisão humana**.
