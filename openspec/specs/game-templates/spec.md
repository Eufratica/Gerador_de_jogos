# Capability Specification: `game-templates`

- **Capability ID:** `game-templates`
- **Status:** `AUDITED_PHASE_0` *(Candidatos reutilizáveis auditados no jogo-âncora; Registry planejado para Fase 4)*
- **Referência Técnica:** [docs/GAME_TEMPLATES.md](../../docs/GAME_TEMPLATES.md)

## Requisitos Contratuais

1. **Contrato Declarativo de Template:** Cada template registra `template_id`, versão `SemVer`, engine/versão compatível, gênero, plataformas, árvore de arquivos, sistemas incluídos, slots de assets, dependências, testes e licença.
2. **Extração Controlada do Âncora:** Apenas módulos comprovadamente genéricos ou parametrizáveis (`big_num.gd`, `seeded_rng.gd`, `idle_economy.gd`, `action_world_config.gd`, `ddtank_ballistics.gd`, `terrain_heightmap.gd`, `local_checkpoint_store.gd`, `test_harness.gd`) devem compor os templates iniciais (`godot-2d-action-rpg` e futuro `godot-2d-idle-ballistics`).
3. **Imutabilidade para Projetos Gerados:** Atualizar um template nunca modifica automaticamente jogos já gerados a partir de versões anteriores.

## Cenários Verificáveis

- **Cenário `TPL-01` (Validação Pré-Uso):** Nenhum template sem testes validados, versão da engine compatível e licença declarada pode ser selecionado pelo `Game Generator`.
