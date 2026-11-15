# GAME_DESIGN_STANDARDS.md — Padrões de Game Design & Propriedade Intelectual

## 1. Estrutura Obrigatória de Game Design Document (25 Itens)

Todo jogo concebido pela PlayForge Factory cujo escopo exigir GDD completo deverá documentar explicitamente:
1. Conceito | 2. Visão | 3. Gênero | 4. Público-Alvo | 5. Diferenciais | 6. Referências Gerais *(sem cópia de IP)* | 7. Core Loop | 8. Gameplay Loop | 9. Mecânicas | 10. Controles | 11. Personagens | 12. Inimigos | 13. Ambientes | 14. Níveis/Mundos | 15. Progressão | 16. Economia | 17. Dificuldade | 18. Interface (UI/UX) | 19. Áudio | 20. Direção Visual | 21. Acessibilidade | 22. Monetização *(se aplicável)* | 23. Requisitos Técnicos | 24. Escopo do MVP | 25. Critérios de Aceitação.

**Regra de Ouro:** O GDD descreve experiência, ritmo e regras de produto; a **`GameSpecification`** formaliza contratos verificáveis por schema e testes. Nunca confundir os dois artefatos.

---

## 2. Política de Propriedade Intelectual Original

- É **proibido** copiar personagens, marcas registradas, nomes protegidos, visuais, trilhas, mapas, diálogos ou código proprietário de terceiros.
- Inspirações de gênero/ritmo (ex.: *loop de progressão idle*, *trajetória parabólica com vento*, *combate 2D lateral com quebra de postura*) devem resultar em universo, estética, nomenclatura e código 100% originais.
- Nota histórica auditada no jogo-âncora: na evolução de `001` (`TITAN SAIYAN`) para `004`/`006` (`Zaikor: Zenkai Infinite`), os nomes de mundos, chefes (`titan_warden_w1`, `abyss_colossus_w2`) e magias (`chaos_flames`, `glacial_tempest`, `sky_lightning`, `titan_aegis`) foram criados em fantasia sombria mitológica original. Recomenda-se revisar na decisão `PEND-001` o uso ou remoção definitiva do termo legado `"Saiyan"` em arquivos históricos não comerciais.

---

## 3. Síntese do Jogo-Âncora Atual (`Zaikor: Zenkai Infinite`)

- **Gênero:** Action RPG 2D Lateral Dark Fantasy com progressão de atributos estilo Idle Forge.
- **Core Loop:** Explorar salas interconectadas ➔ lutar com combo de 3 golpes, pulo, dash c/ *i-frames* e 4 magias elementais ➔ acumular Fúria e quebrar postura de Chefes Titânicos com janela QTE ➔ usar Altares de Salvamento para curar, salvar checkpoint e investir ouro/gemas em upgrades, Gacha transparente e Baú Offline (teto 8h).
- **Resolução e Controles:** `1920x1080` Paisagem, suporte simultâneo PC (teclado + clique) e Mobile (botões Touch com toggle no HUD).
