# Proposal — 001: Fase 0 — Análise do Ambiente e Fundação de Zaikor: Initine Zenkai

## Necessidade
Estruturar o novo jogo 3D *Zaikor: Initine Zenkai* isolado dentro da PlayForge Factory (`games/zaikor-initine-zenkai/`) seguindo estritamente SDD/OpenSpec, auditoria real do hardware alvo e preservação do projeto-âncora 2D na raiz.

## Escopo Desta Mudança (Fase 0)
- Registrar projeto isolado `zaikor-initine-zenkai` no `ProjectManager`.
- Auditar hardware real (CPU, GPU integrada, módulos de RAM e canal, SSD) e ferramentas instaladas.
- Verificar na fonte oficial (`godotengine.org`) o status estável de `Godot 4.7.2 Stable` vs `4.8 beta`.
- Entregar documentação completa de governança, narrativa, arquitetura, OpenSpec, GDD (`25` seções) e `GameSpecification v2`.
- Pausar formalmente no gate `APROVACAO_HUMANA_ARQUITETURA` (`ZIZ-GATE-01`) para decisão de instalação do `Godot 4.7.2 Stable` antes da Etapa 1.
