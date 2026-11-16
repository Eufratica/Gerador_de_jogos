# Capability Specification: `game-factory`

- **Capability ID:** `game-factory`
- **Status:** `IMPLEMENTED_PHASE_5` *(Factory Core, Project Manager e Game Generator MVP operacionais em `factory/playforge/` com suíte Python + validação real Godot 4.4 headless sobre projetos gerados)*
- **Referência Técnica:** [docs/GAME_FACTORY.md](../../docs/GAME_FACTORY.md)

## Requisitos Funcionais e Estruturais

1. **Independência Fábrica vs. Jogos:** A fábrica administra ciclo de vida, templates, especificações, agentes, testes e builds sem acoplar seu código ao interior dos jogos gerados.
2. **Estado Persistente e Retomável:** Cada execução de jogo passa por etapas registradas (`IDEIA` ➔ `OTIMIZACAO`) com estado, responsável, entradas, saídas e evidências, permitindo pausa para aprovação humana e retomada após falha.
3. **Sem Simulação Falsa no MVP:** O primeiro MVP (Fase 5) só é válido quando gerar um 2º projeto Godot funcional real usando spec aprovada + template real + testes headless reais.

## Cenários Verificáveis

- **Cenário `GF-01` (Separação de Escopo):** Dado um repositório com múltiplos projetos sob gestão da fábrica, quando a fábrica atualiza suas dependências ou ferramentas internas, nenhuma cena, configuração ou código de jogo já gerado é modificado silenciosamente.
- **Cenário `GF-02` (Bloqueio por Falta de Aprovação):** Dado um pipeline em etapa crítica (arquitetura, spec para geração, build para distribuição), quando não existir aprovação humana registrada, a transição seguinte é bloqueada (*fail-closed*).
