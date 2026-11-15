# GAME_SPECIFICATION_SCHEMA.md — Especificação Estruturada de Jogos (Fase 3)

## 1. Papel da `GameSpecification`

Nenhum projeto novo pode ser gerado pelo `Game Generator` apenas a partir de texto livre de um LLM.  
Toda ideia aprovada passa primeiro por conversão para uma **`GameSpecification`** estruturada (JSON Schema tipado + versionamento `MAJOR.MINOR.PATCH`).

---

## 2. Campos Obrigatórios Previstos

- **Identificação:** `spec_id`, `game_id`, `name`, `spec_version`, `schema_version`, `genre`, `subgenre`, `target_platforms`, `engine` (`godot`), `engine_version` (`4.4.stable` inicial).
- **Produto:** `target_audience`, `product_goals`, `value_proposition`, `general_references`, `acceptance_criteria`.
- **Gameplay & Conteúdo:** `core_gameplay`, `core_loop`, `controls`, `mechanics`, `characters`, `enemies`, `worlds`, `levels`, `progression`, `difficulty`, `economy`, `narrative`.
- **Apresentação & Som:** `ui_spec`, `accessibility`, `audio_spec`, `art_direction`, `asset_requirements`.
- **Engenharia & Operação:** `persistence_spec`, `technical_requirements`, `security_constraints`, `monetization_spec` *(opcional/desativada por padrão quando não solicitada)*.

---

## 3. Regras de Validação (*Fail-Closed*)

O validador da Fase 3 deverá garantir:
1. Rejeição de campos obrigatórios ausentes, tipos errados ou enums inválidos;
2. Bloqueio de campos desconhecidos nos contratos estritos (`additionalProperties: false` onde aplicável);
3. Verificação semântica de consistência entre sistemas (ex.: economia de upgrades referenciada pelo núcleo, soma de probabilidades Gacha `== 1.0`, portais válidos entre salas, limites físicos coerentes);
4. Compatibilidade explícita entre `spec_version` e a versão exigida pelo template selecionado;
5. Mudanças incompatíveis de contrato exigem bump `MAJOR` ou script explícito de migração.

---

## 4. Relação com os Configs Existentes do Jogo-Âncora

O repositório já possui dois contratos JSON validados por parsers *fail-closed* em GDScript que servirão de base empírica para desenhar o schema da Fase 3:
- `config/balance_v1.json` + `src/core/balance_config.gd` (`schema_version: "1.0.0"`)
- `config/action_world_v1.json` + `src/core/action_world_config.gd` (`schema_version: "1.0.0"`)
