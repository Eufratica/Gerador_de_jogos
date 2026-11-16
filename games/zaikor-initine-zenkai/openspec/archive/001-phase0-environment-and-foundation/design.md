# Design — 001: Arquitetura de Fundação e Gates de Fase 0

## Decisões Estruturais
1. **Isolamento via PlayForge (`ADR-ZIZ-001`):** Workspace em `games/zaikor-initine-zenkai/`, protegido por `games/.gdignore`, sem modificar `../../src/`, `../../tests/` ou `../../project.godot`.
2. **Engine Gate (`ADR-ZIZ-002`):** Registrar `4.7.2-stable` como versão recomendada na especificação (após verificar lançamento oficial de `4.7.2` e estado beta de `4.8 beta 3`), deixando instalação física pendente de aprovação explícita do operador (`ZIZ-GATE-01`) por exigir download externo e adição de ferramenta estrutural em `../../tools/`.
3. **Alinhamento Hardware (`ADR-ZIZ-004`):** Documentar RAM real como `11.74 GB` flex-mode (`8 GB + 4 GB @ 2133 MT/s`) e dimensionar `Compatibility Renderer` `1280×720` meta `30 FPS` com LOD/culling e zero volumetria/Lumen/Nanite.
4. **Estrutura Enxuta (Zero Pastas Vazias):** Não criar `scenes/`, `scripts/` ou `assets/` vazios antes da Etapa 1.

## Plano de Verificação da Fase 0
- `spec-validate zaikor-initine-zenkai --project` (`exit 0`, `status: VALID`)
- `SpecificationValidator.validate_gdd` (`25` seções)
- `engine-select --dimension 3d-indie ... --save-project zaikor-initine-zenkai`
- Verificação de zero diretórios vazios em `games/zaikor-initine-zenkai/` e zero regressão na suíte do âncora `Zaikor`.
