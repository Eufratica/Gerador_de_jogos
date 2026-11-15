# MODEL_ROUTER.md — Roteamento Local-First & Política de IA (Fase 6)

> **Estado Atual (Fase 0):** `ollama` e modelos locais ainda **não foram detectados** no ambiente Windows inspecionado (`NOT_FOUND`). Este documento define o contrato obrigatório para quando o módulo for implantado na Fase 6.

---

## 1. Princípios do `Model Router`

1. **Ollama Local Prioritário (Zero Cost):** Nenhuma API paga de terceiros pode ser configurada como fallback automático.
2. **Privacidade & Segurança:** Arquivos sensíveis (`.env`, segredos, credenciais) jamais podem ser enviados a provedores externos.
3. **Validação Estruturada:** Toda resposta de modelo é tratada como entrada não confiável e precisa passar por parser estrito + schema JSON antes de produzir efeito na fábrica.
4. **Rastreabilidade Completa:** Toda chamada registra `request_id`, `project_id`, `agent_id`, `model_id`, `model_version`, `prompt_version`, ferramentas usadas, latência e resultado.

---

## 2. Roteamento por Complexidade de Tarefa

| Tier de Tarefa | Uso Previsto | Estratégia de Seleção |
| :--- | :--- | :--- |
| **Tier S (Rápido / Leve)** | Classificação, resumo, validação textual simples, extração estruturada curta | Modelos compactos compatíveis com a RAM/VRAM real do host |
| **Tier M (Padrão)** | Geração de GDD estruturado, `GameSpecification`, diálogo/conteúdo, scripts delimitados | Modelos de porte médio balanceando contexto e latência local |
| **Tier L (Raciocínio / Arquitetura)** | Design arquitetural, depuração complexa, auditoria | Selecionado somente se o hardware disponível suportar com segurança; caso contrário exige particionamento da tarefa ou intervenção humana |

---

## 3. Regra de Hardware Real (Anti-Alucinação de Capacidade)

Antes de baixar ou declarar suporte a qualquer modelo Ollama na Fase 1/6:
- Auditar RAM, VRAM da GPU e espaço em disco livres fora do sandbox;
- Verificar licença individual de cada modelo para compatibilidade comercial (ex.: Apache-2.0 vs restrições específicas);
- Não baixar múltiplos modelos pesados sem necessidade prática comprovada.
