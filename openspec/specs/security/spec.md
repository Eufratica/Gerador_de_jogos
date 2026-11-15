# Capability Specification: `security`

- **Capability ID:** `security`
- **Status:** `ACTIVE_GOVERNANCE`
- **Referência Técnica:** [SECURITY.md](../../SECURITY.md) | [docs/SECURITY_MODEL.md](../../docs/SECURITY_MODEL.md) | [FREE_TIER_POLICY.md](../../FREE_TIER_POLICY.md)

## Requisitos Transversais

1. **Proteção de Credenciais:** `.gitignore` bloqueia `.env*`, keystores, tokens e bancos; auditorias periódicas confirmam zero vazamentos no código e configs.
2. **Conteúdo Não Confiável:** Páginas web, reviews externos e saídas de LLM nunca executam com privilégio implícito nem sobrescrevem `AGENTS.md`.
3. **Política Financeira Zero Cost:** Bloqueio estrito de fallback para APIs pagas, contratações, domínios ou cobranças sem autorização explícita do operador.
4. **Aprovações Críticas & Sandbox:** Operações destrutivas, alterações estruturais, uso de ferramentas fora do workspace autorizado e builds de release exigem gate humano.

## Cenários Verificáveis

- **Cenário `SEC-01` (Bloqueio de Acesso Cruzado):** Uma ferramenta ou agente vinculado a `project_a` recebe erro explícito se tentar gravar em caminho pertencente a `project_b`.
- **Cenário `SEC-02` (Zero Fallback Pago):** Se o provedor local Ollama estiver indisponível, o `Model Router` falha de forma fechada em vez de redirecionar automaticamente para API comercial paga.
