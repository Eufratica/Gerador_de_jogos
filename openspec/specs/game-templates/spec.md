# Capability Specification: `game-templates`

- **Capability ID:** `game-templates`
- **Status:** `IMPLEMENTED_PHASE_4` *(Template inicial `godot-2d-action-rpg` `1.0.0` extraído e validado com Registry fail-closed em `factory/playforge/template_registry/`)*
- **Referência Técnica:** [docs/GAME_TEMPLATES.md](../../docs/GAME_TEMPLATES.md)

## Requisitos Contratuais

1. **Contrato Declarativo de Template:** Cada template registra `template_id`, versão `SemVer`, engine/versão compatível, gênero, plataformas, árvore de arquivos, sistemas incluídos, slots de assets, dependências, testes e licença.
2. **Extração Controlada do Âncora:** Apenas módulos comprovadamente genéricos ou parametrizáveis (`big_num.gd`, `seeded_rng.gd`, `idle_economy.gd`, `action_world_config.gd`, `ddtank_ballistics.gd`, `terrain_heightmap.gd`, `local_checkpoint_store.gd`, `test_harness.gd`) devem compor os templates iniciais (`godot-2d-action-rpg` `1.0.0` entregue na Fase 4 e futuro `godot-2d-idle-ballistics`).
3. **Imutabilidade para Projetos Gerados:** Atualizar ou depreciar (`DEPRECATED`) uma versão de template nunca remove arquivos nem modifica jogos já gerados a partir de versões anteriores.
4. **Isolamento Engine & Integridade:** `templates/.gdignore` isola templates da varredura `res://` do jogo-âncora `Zaikor`; `TemplateValidator` verifica extensões permitidas, anti-path-traversal, digest `SHA-256` do `skeleton/` e aprovação de testes Godot headless.

## Cenários Verificáveis

- **Cenário `TPL-01` (Validação Pré-Uso):** Nenhum template sem testes validados, versão da engine compatível e licença declarada pode ser selecionado pelo `Game Generator`.
