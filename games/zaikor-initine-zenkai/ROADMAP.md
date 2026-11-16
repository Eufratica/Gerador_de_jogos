# ROADMAP.md — Zaikor: Initine Zenkai

Desenvolvimento incremental seguindo SDLC (Fases 1–8), SDD/OpenSpec e a ordem obrigatória de **16 etapas da Vertical Slice** (Seção 21 do Prompt Mestre).

---

## 1. Mapa das Etapas da Vertical Slice (`O Vale do Primeiro Eco`)

| **Etapa** | **Fase SDLC** | **Entrega** | **Status** | **Critério** |
| :--- | :--- | :--- | :--- | :--- |
| **0** | Fases 1–2 | Auditoria real, governança, GDD, Lore, Spec `v2` e OpenSpec | **CONCLUÍDA (`0.0.1-phase0`)** | Validado e arquivado (`001`) |
| **1** | Fase 3 | `Godot 4.7.2 Stable`, `project.godot` (`Compatibility`), `scripts/core/` e cena 3D base | **CONCLUÍDA (`0.1.0-etapa1`)** | `16` assertions headless (`3.28 ms`), `0` órfãos, boot na `Intel Iris Xe` validado (`31.0 FPS` steady-state) |
| **2** | Fase 3 | Personagem Zaikor (silhueta/articulado inicial) e câmera 3P (`SpringArm3D` anticolisão) | **PRÓXIMA** | SpringArm3D sem cortar paredes, limites de pitch e suavização |
| **3** | Fase 3 | Movimentação 3D completa (caminhar, correr, rotação gradual, pular, esquivar, recuperação) | Planejada | Testes headless + jogabilidade responsiva sem deslize descontrolado |
| **4** | Fase 3 | Sistema modular de combate (combo rápido, carregado, defesa/parry, buffer, stagger, alvo) | Planejada | Testes unitários em `scripts/core/` + validação em arena de teste |
| **5** | Fase 3 | Sistema de inimigos + FSM de 8 estados (`Vulto do Eco`, variação ágil/resistente, `Sentinela de Cinza`) | Planejada | Detecção, ataque, cooldown, stagger e derrota funcionais |
| **6** | Fase 3 | Árvore inicial de habilidades + energia `Initine` + sincronização `Zenkai` | Planejada | Ativação curta, custo equilibrado e alteração real de habilidades |
| **7** | Fase 3 | Cenário explorável modular: *Área 1 — O Vale do Primeiro Eco* (caminho principal + opcional) | Planejada | Modularidade + LOD + frustum culling respeitando orçamento da Iris Xe |
| **8** | Fase 3 | Sistema de interação (santuários/baús/colecionáveis) e puzzle de ressonância *Initine* | Planejada | Regra ensinada gradualmente, progressão destrava passagem bloqueada |
| **9** | Fase 3 | Chefe da Vertical Slice (*Arconte da Ruptura*) com apresentação, 2 fases, sinais e recompensa | Planejada | Confronto completo, janela de vulnerabilidade e conclusão |
| **10** | Fase 3 | Interface própria (Menu inicial, HUD enxuto, Pausa, Diário, Habilidades, Configurações/Acessibilidade, Tela Final) | Planejada | Todos os controles conectados e resolução/gráficos configuráveis |
| **11** | Fase 3 | Sistema de salvamento local versionado + checkpoint funcional | Planejada | Salva/carrega JSON validado com proteção contra corrupção |
| **12** | Fase 3 | Áudio original/FFmpeg (ambiente, exploração, combate, chefe, UI/SFX) e VFX econômicos | Planejada | Mixagem por barramentos e registro completo em `docs/art/ASSET_CREDITS.md` |
| **13** | Fases 6–7 (Otimização) | Cena de benchmark progressivo (passos 1–9 da Seção 7.4) e ajuste para meta 30 FPS @ 720p | Planejada | Medições reais documentadas na Iris Xe sem dados fabricados |
| **14** | Fases 5–6 (Testes) | Regressão completa (unitários, integração, gameplay, save e headless smoke) | Planejada | Zero erros críticos e todos os critérios da Seção 22 cumpridos |
| **15** | Fase 8 (Release Slice) | Vertical Slice finalizada, export Windows verificado e pacote de release | Planejada | Critérios da Seção 22 100% comprovados |

---

## 2. Fases Futuras (Pós-Vertical Slice)

- **Fase 4 (Produção Completa):** Capítulos 2–7 (*Ecos Perdidos* até *O Último Eco*), novos biomas, inimigos de energia/suporte, chefes adicionais, árvore expandida de habilidades e cinemáticas de história.
