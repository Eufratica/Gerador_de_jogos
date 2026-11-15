# ASSET_PIPELINE.md — Pipeline de Assets & Provenance

## 1. Estado Real Atual (Fase 0)

No jogo-âncora atual (`Zaikor: Zenkai Infinite`), **não existem assets binários externos** (spritesheets PNG, fontes customizadas ou modelos 3D). Todo o visual atual é renderizado via desenho vetorial `_draw()` em GDScript (`silhouette_warrior.gd`, `silhouette_enemy.gd`, `world_backdrop.gd`, `vfx_pool.gd`).

O pipeline completo de assets será implementado na **Fase 7**, com especificação e registro de procedência obrigatórios.

---

## 2. Fluxo Alvo de Produção de Assets (Fase 7)

```text
REQUISITO ➔ ASSET SPECIFICATION ➔ PRODUCAO (Local/Gratuita) ➔ VALIDACAO TECNICA
  ➔ VERIFICACAO DE LICENCA ➔ OTIMIZACAO ➔ IMPORTACAO GODOT ➔ INTEGRACAO EM CENA
  ➔ TESTE HEADLESS ➔ VERSIONAMENTO NO ASSET REGISTRY
```

---

## 3. Contrato do `Asset Registry`

Todo recurso importado ou gerado deverá registrar:
- `asset_id`, `name`, `asset_type`, `project_id`, `game_id`, `version`, `file_path`, `format`, `dimensions`, `resolution`, `byte_size`;
- **Proveniência:** `origin`, `author_or_provider`, `tool_used`, `model_used` *(se IA)*, `prompt_or_seed` *(se IA)*, `license`, `restrictions`, `sha256_hash`, `validation_status`.

---

## 4. Regras Rígidas de Assets e Licenças

1. Proibido incluir assets sem procedência e licença documentadas.
2. Não assumir automaticamente uso comercial livre para imagens geradas por modelos — validar licença do modelo e ferramenta (ver [LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md)).
3. Ferramentas gratuitas prioritárias: Blender, Krita, GIMP, LibreSprite, Pixelorama, FFmpeg.
4. Builds finais não podem empacotar arquivos temporários ou assets órfãos sem referência válida.
