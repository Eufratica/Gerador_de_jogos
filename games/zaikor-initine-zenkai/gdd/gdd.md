# Game Design Document — Zaikor: Initine Zenkai

- **Project ID:** `zaikor-initine-zenkai`
- **GDD Schema Version:** `1`
- **Linked Spec:** `spec-zaikor-initine-zenkai-v1` (`v0.1.0`)

---

## 1. Concept

Jogo 3D single-player de acao e aventura em fantasia sombria protagonizado por Zaikor em Aetheryn.

## 2. Vision

Experiencia cinematografica em terceira pessoa com combate pesado e responsivo, exploracao narrativa e quebra-cabecas de energia Initine.

## 3. Genre

Acao e aventura 3D / Fantasia sombria (Vertical Slice no Vale do Primeiro Eco).

## 4. Target Audience

Jogadores de PC Windows apreciadores de acao-aventura narrativa e combate tatico.

## 5. Differentials

Sincronizacao Zenkai que modifica propriedades das habilidades em vez de mero buff numerico, otimizada nativamente para GPU integrada Intel Iris Xe.

## 6. References

Linguagem cinematografica geral estilo God of War, com IP, lore, personagens, modelos e audio 100% originais.

## 7. Core Loop

Explorar regioes de Aetheryn -> Resolver quebra-cabecas Initine -> Combater criaturas e chefes -> Ativar Zenkai -> Salvar em santuarios e evoluir habilidades.

## 8. Gameplay Loop

Camera 3P proxima, ataque rapido/carregado, combo com input buffer, esquiva, guarda/contra-acao, habilidades Initine e finalizacao nao grafica.

## 9. Mechanics

Combate modular 3D, estado Zenkai com ativacao cinematografica curta, travamento de alvo, puzzle de ressonancia de obeliscos e arvore modular de habilidades.

## 10. Controls

Teclado/Mouse e suporte opcional a controle com inversao de eixos, sensibilidade e reducao de camera shake.

## 11. Characters

Zaikor (antigo guardiao ligado a Initine, personalidade firme e conflitos internos) e O Silencio Primordial (antagonista filosofico).

## 12. Enemies

Criaturas comuns (Vulto do Eco), ageis, resistentes, energeticas, suporte, elite (Sentinela de Cinza) e chefe Arconte da Ruptura com FSM de 8 estados.

## 13. Environments

Ruinas monumentais antigas, florestas misteriosas e templos em modulos 3D reutilizaveis sob iluminacao artistica economica.

## 14. Levels And Worlds

Estrutura em 7 capitulos planejados; Vertical Slice focada na Area 1 (O Vale do Primeiro Eco: Santuario, Trilha, Mirante do Puzzle e Anfiteatro do Chefe).

## 15. Progression

Arvore progressiva em 7 categorias: ofensiva, defensiva, mobilidade, controle Initine, Zenkai, recursos e passivas.

## 16. Economy

Vestigios de Initine e Fragmentos de Eco obtidos exclusivamente via combate, exploracao, baus e puzzles (Zero monetizacao predatoria).

## 17. Difficulty

Curva gradual com ataques de chefe claramente sinalizados e janelas justas de vulnerabilidade.

## 18. Ui Ux

Menu inicial completo + HUD enxuto (Vida, Energia/Recurso, Indicador Zenkai, interacao contextual e barra de chefe) + menus de Pausa/Habilidades/Diario/Config.

## 19. Audio

Camadas adaptativas (ambiente, exploracao, combate, chefe) e SFX originais via FFmpeg/sintese sem trilhas comerciais.

## 20. Visual Direction

Estilizacao semi-realista dark fantasy, silhuetas marcantes e brilho ciano Initine contrastando com pedra envelhecida.

## 21. Accessibility

Legendas escalaveis, modo daltonico, inversao de eixos, reducao de tremor de camera e remapeamento.

## 22. Monetization

Nenhuma (Free / Sem microtransacoes ou APIs pagas).

## 23. Technical Requirements

Godot 4.x estavel (4.7.2 Stable recomendada; 4.4.stable no host atual), Compatibility Renderer, 1280x720, meta 30 FPS para i5-1135G7 / Intel Iris Xe / 11.74 GB RAM flex-mode.

## 24. Mvp Scope

Vertical Slice jogavel de 10-15 min no Vale do Primeiro Eco com Zaikor, 3 tipos de inimigos, 1 puzzle, 1 chefe, UI, audio e checkpoint versionado.

## 25. Acceptance Criteria

Abertura limpa em Compatibility Renderer, movimentacao/camera/combate/Zenkai/puzzle/chefe/save funcionais e benchmark real registrado.
