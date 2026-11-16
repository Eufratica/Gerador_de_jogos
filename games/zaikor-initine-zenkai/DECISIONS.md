# DECISIONS.md — Registro de Decisões Arquiteturais (ADRs) — Zaikor: Initine Zenkai

Todas as decisões estruturais relevantes ficam registradas aqui antes de implementação irreversível.

---

### ADR-ZIZ-001 — Isolamento Estrito em `games/zaikor-initine-zenkai/`
- **Estado:** `ACEITA` (`2026-11-16`)
- **Contexto:** O repositório `C:\Jogo_Android` hospeda o jogo-âncora 2D (`Zaikor: Zenkai Infinite` na raiz, protegido pela `ADR-006` da PlayForge Factory) e os projetos independentes produzidos pela fábrica em `games/`.
- **Decisão:** Todo código, documentação, OpenSpec, assets, cenas e builds de `Zaikor: Initine Zenkai` residem exclusivamente em `games/zaikor-initine-zenkai/`, registrado no `ProjectManager` como `zaikor-initine-zenkai`, sob `games/.gdignore`.
- **Consequência:** Zero risco de conflito de `project.godot` ou `res://` com o jogo-âncora 2D na raiz.

---

### ADR-ZIZ-002 — Versão da Engine: `Godot 4.7.2 Stable` Aprovada (Opção A) vs `4.4.stable` Local vs `4.8` Beta
- **Estado:** `ACEITA (Opção A aprovada pelo operador em 2026-11-16)`
- **Contexto Verificado:**
  1. Pesquisa oficial em `godotengine.org` (`2026-11-16`) confirmou **`Godot 4.7.2 Stable`** (18/08/2026) como versão estável mais recente da série 4.7 e **`Godot 4.8` em Beta (`4.8 beta 3`)**, rejeitada pela Seção 6.1.
  2. Com aprovação explícita do operador (*"opção a"*), os binários oficiais foram baixados, validados por **SHA-512** (`83DECD58FDF67B9D657958A1AE6BF1929C20785315A81EFFE245874CDC57ACB709BF868E00778A96984338C1B29DAFDB453C6847747694621C6ECF5DA2259993`) e extraídos em `../../tools/godot-4.7.2/` (`4.7.2.stable.official.ed1daf0bf`), preservando `../../tools/godot/` (`4.4.stable`) para a fábrica e o jogo-âncora.
- **Consequência:** `project.godot` fixado com `config/features=PackedStringArray("4.7", "GL Compatibility")`.

---

### ADR-ZIZ-003 — Renderizador `Compatibility` + Orçamento Hardware `720p / 30 FPS`
- **Estado:** `ACEITA` (`2026-11-16`)
- **Decisão:** Fixar o renderizador do Godot em **Compatibility (`gl_compatibility`)**, resolução de referência **`1280 × 720`** e meta de engenharia **`30 FPS`** para perfil **Baixo** em `Intel Iris Xe` integrada. Proibir por padrão Ray Tracing, Lumen, Nanite, Virtual Shadow Maps, volumetria pesada e excesso de luzes/pós-processamento.
- **Consequência:** Alterar para `Forward+` ou `Mobile` exigirá nova análise, benchmark comparativo real na Iris Xe e aprovação explícita.

---

### ADR-ZIZ-004 — Memória Real do Host (`11.74 GB` Flex-Mode `8 GB + 4 GB @ 2133 MT/s`)
- **Estado:** `ACEITA` (`2026-11-16`)
- **Contexto Observado:** Consulta `Win32_PhysicalMemory` verificou dois módulos: `DIMM A` de `8 GB` (`3200 MT/s`) e `DIMM B` de `4 GB` (`2667 MT/s`) operando ambos a **`2133 MT/s`** (`11.74 GB` totais utilizáveis no Windows). Essa topologia assimétrica caracteriza **dual-channel parcial / flex-mode** (os primeiros 8 GB em canal duplo e o restante em canal simples).
- **Decisão:** Manter orçamento máximo de RAM do jogo conservador (`<= 4 GB` na especificação; perfil alvo enxuto com streaming/carregamento por regiões), considerando que a `Intel Iris Xe` compartilha largura de banda da RAM `2133 MT/s` com a CPU.

---

### ADR-ZIZ-005 — Execução Nativa Windows + Ferramentas Gratuitas Locais
- **Estado:** `ACEITA` (`2026-11-16`)
- **Decisão:** Toda execução e validação de runtime do jogo ocorre nativamente no Windows, sem exigir Docker, Linux, GPU dedicada ou APIs/ferramentas pagas. Blender `5.3.0` (`GLB/GLTF`) e FFmpeg `9.0.2` (áudio) já estão disponíveis localmente.

---

### ADR-ZIZ-006 — Política Anti-Plágio & Registro Obrigatório de Ativos
- **Estado:** `ACEITA` (`2026-11-16`)
- **Decisão:** Nomes, universo (*Aetheryn*, *Initine*, *Zaikor*, *Zenkai*, *O Silêncio Primordial*), cenários, modelos e áudio devem ser originais ou com licença aberta verificada registrada em `docs/art/ASSET_CREDITS.md`.
