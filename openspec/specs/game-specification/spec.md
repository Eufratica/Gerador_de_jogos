# Capability Specification: `game-specification`

- **Capability ID:** `game-specification`
- **Status:** `PLANNED_PHASE_3` *(Schema e engine genérica planejados; inspiração empírica nos contratos do jogo-âncora)*
- **Referência Técnica:** [docs/GAME_SPECIFICATION_SCHEMA.md](../../docs/GAME_SPECIFICATION_SCHEMA.md)

## Requisitos Contratuais

1. **Spec Antes da Geração:** O `Game Generator` só aceita `GameSpecification` validada e aprovada pelo operador.
2. **Validação Estrita (*Fail-Closed*):** Verificar obrigatoriedade, tipos, enums, consistência semântica entre sistemas, campos desconhecidos quando exigido e compatibilidade de `schema_version`.
3. **Separação GDD vs. Spec:** GDD (visão/experiência em 25 itens) e `GameSpecification` (contrato estruturado executável) são vinculados por ID/versão, sem substituição mútua.

## Cenários Verificáveis

- **Cenário `GS-01` (Rejeição por Schema Inválido):** Uma especificação sem `core_loop`, com probabilidades de loot somando `!= 1.0`, ou com `schema_version` incompatível falha na validação emitindo mensagens claras de campo/erro.
- **Cenário `GS-02` (Compatibilidade Versionada):** Mudanças incompatíveis exigem nova versão `MAJOR` ou migrador explícito, sem quebrar projetos anteriores.
