# BUILD_AND_RELEASE.md — Build Engine, Versionamento & Publicação

## 1. Estado Real Atual (Fase 0)

- **Editor / Runtime Local:** `Godot 4.4.stable` (executáveis desktop Windows presentes localmente em `tools/godot/`).
- **Lacunas Reais:** Não há ainda `export_presets.cfg`, Android SDK/NDK/JDK provisionados no projeto, keystores locais externos, scripts Fastlane ou módulo Python `Build Engine`. Apenas a execução local via `--path .` e testes `--headless` operam hoje.

---

## 2. Política de Versionamento (SemVer `MAJOR.MINOR.PATCH`)

Cada componente possui versionamento independente:
- **PlayForge Factory** (`0.x.y` na construção da plataforma);
- **Templates** (ex.: `godot-2d-action-rpg@1.0.0`);
- **Game Specifications & Schemas** (compatibilidade explícita de schema);
- **Jogos Produzidos** (ex.: `Zaikor` atualmente no marco documental `v0.4.0-playable-slice`);
- **Builds / Artefatos** (hash SHA-256 + commit + spec + resultado dos testes).

---

## 3. Fluxo Alvo de Build & Release (Fase 10)

1. Selecionar `project_id`, versão e plataforma-alvo (priorizando **builds locais reproduzíveis em Windows/Linux/Android de teste** antes de lojas externas — ver [FREE_TIER_POLICY.md](../FREE_TIER_POLICY.md));
2. Rodar **todos** os Quality Gates aplicáveis (`Static + Unit + Integration + Balance + Engine Boot + Asset/License Check`);
3. Exportar via Godot CLI `--headless` em workspace isolado;
4. Registrar manifesto da build (versão, commit, template, hash, logs, cobertura);
5. **Gate Humano Obrigatório:** Nenhuma publicação ou distribuição externa avança sem revisão e aprovação explícita do operador. Keystores e tokens **jamais** entram no repositório Git.
