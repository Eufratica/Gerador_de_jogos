# Arquitetura Técnica — Zaikor: Initine Zenkai

## 1. Princípios Arquiteturais

1. **Godot 4.x Stable + Compatibility Renderer:** Obrigatório para estabilidade e desempenho na `Intel Iris Xe` (GPU integrada com RAM compartilhada a `2133 MT/s`).
2. **Separação Estrita `scripts/core/` vs Camada de Cena (`scenes/` e demais `scripts/`):**
   - `scripts/core/`: regras puras determinísticas de combate, escalonamento de dano, FSM de inimigos, recursos *Initine/Zenkai*, árvores de habilidades, validação de puzzles e serialização/checksum de saves — **sem dependências de `Node`, `SceneTree`, câmera ou I/O direto**, executáveis por testes CLI `--headless` em `< 1s`.
   - `scenes/` e scripts de cena (`scripts/player/`, `scripts/camera/`, `scripts/enemies/`, `scripts/bosses/`, `scripts/ui/`, etc.): orquestração de nós 3D, `CharacterBody3D`, `SpringArm3D`, áudio, animações e controles, delegando cálculos críticos aos módulos puros.
3. **Criação Sob Demanda de Pastas:** Nenhuma subpasta de `scenes/`, `scripts/`, `assets/`, `resources/` ou `tests/` é criada vazia antes da etapa em que receberá arquivos reais funcionais.

---

## 2. Estrutura Modular Planejada por Etapas

- `scripts/core/`: modelos matemáticos, contratos de entrada/buffer, máquinas de estado puras, esquemas de save v1 e configurações gráficas (`Baixo`/`Médio`/`Alto`).
- `scripts/camera/` + `scenes/player/`: câmera terceira pessoa sobre o ombro com `SpringArm3D`, suavização angular, ajuste de distância/FOV em combate, bloqueio anti-corte de parede e configuração de sensibilidade/inversão.
- `scripts/player/`: movimentação `CharacterBody3D` (andar, correr, rotação interpolada para direção, pulo, esquiva, recuperação, escalada/travessia controlada e interação).
- `scripts/combat/`: orquestração modular de ataques rápidos, carregados, combos com buffer e janelas de cancelamento, guarda/contra-ação, stagger, alvo travado e ativação *Zenkai*.
- `scripts/enemies/` & `scripts/bosses/`: FSM de 8 estados (`IDLE`, `PATROL`, `ALERT`, `APPROACH`, `ATTACK`, `COOLDOWN`, `STAGGER`, `DEFEATED`) e encontros multifase para o chefe *Arconte da Ruptura*.
- `scripts/interaction/` & `scripts/progression/`: quebra-cabeças de ressonância *Initine*, portas/santuários/baús/colecionáveis e árvore de desbloqueio gradual.
- `scripts/save/`: persistência local versionada (`user://saves/`), escrita atômica e validação anti-corrupção por campos estáveis por string ID (nunca referências de instância).
- `scripts/ui/` & `scenes/ui/`: Menu inicial, HUD enxuto, Pausa, Habilidades, Diário, Configurações/Acessibilidade e Tela de Conclusão.

---

## 3. Perfis Gráficos & Limites na Iris Xe (Seções 7.1–7.5)

| Parâmetro | Perfil **Baixo** *(Padrão Alvo)* | Perfil **Médio** | Perfil **Alto** *(Experimental)* |
| :--- | :--- | :--- | :--- |
| Resolução Interna | `1280 × 720` (ou escala 0.85 se medido abaixo de 30 FPS) | `1280 × 720` | `1280 × 720` / nativo se validado |
| Meta de Quadros | `30 FPS` | `30 FPS` | Somente se estável em benchmark real |
| Sombras Dinâmicas | Seletivas / baixa resolução (`DirectionalLight3D` simples) | Moderadas | Condicionadas a medição real |
| Pós-processamento | Desligado ou mínimo (sem glow pesado/SSA0/SSR) | Moderado sem SSR/volumetria | Experimental |
| LOD / Culling | Agressivo + Frustum/Occlusion + instancing | Balanceado | Distância ampliada |

---

## 4. Protocolo de Benchmark Progressivo (Seção 7.4)

Na Etapa 13 será validada uma cena controlada medindo FPS médio, 1% low/quedas, tempo de quadro (`ms`), memória estática/RAM e tempo de carregamento nos 9 degraus: (1) cenário vazio, (2) iluminação, (3) protagonista, (4) animações, (5) 1 inimigo, (6) múltiplos inimigos, (7) VFX, (8) combate completo e (9) carregamento de nova região.
