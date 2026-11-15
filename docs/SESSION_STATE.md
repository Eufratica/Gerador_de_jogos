# SESSION_STATE.md — Memória Operacional da PlayForge Factory

> **Regra de Continuidade:** Todo agente novo deve ler este arquivo na abertura da sessão para retomar o trabalho do estado verificado em disco e Git, sem depender de histórico de chat.

---

## 1. Snapshot Atual do Estado

- **Fase Atual:** `FASE 1 — AMBIENTE REPRODUZÍVEL` **concluída e arquivada** (`008`). **Aguardando aprovação humana para iniciar a Fase 2** (Core da Fábrica & Multi-Projeto).
- **Jogo-Âncora:** `Zaikor: Zenkai Infinite` (`v0.4.0-playable-slice`), preservado na raiz (ADR-006); `git diff --stat -- project.godot src/ config/ tests/ .gitignore` vazio.
- **Base Git:** `main` @ `cab6ee8` (`origin/main`). Fases 0 e 1 estão no working tree; commit local feito ao final desta sessão (ver `git log`), sem `push`.
- **Decisões:** `ADR-001`–`ADR-008` em [DECISIONS.md](../DECISIONS.md); sem pendências abertas.

## 2. Evidências da Última Verificação (após a última edição de arquivos)

| Verificação | Resultado |
| :--- | :--- |
| `playforge.ps1 test-win` (Godot 4.4 Windows) | `229 assertions \| Failed: 0` (`477.25 ms`); Action Balance `PASSED` (`463.77 ms`); Engine Boot `14 assertions \| Failed: 0` |
| `playforge.sh test-linux` (container, Python 3.12.16 + Godot 4.4) | `229 assertions \| Failed: 0` (`276.09 ms`); Action Balance `PASSED` (`508.67 ms`); Engine Boot `14 assertions \| Failed: 0` |
| `playforge.sh health` | `accepting connections`; extensão `vector 0.8.7` |
| `playforge.sh status` | `playforge_db` healthy (`127.0.0.1:5434`); `playforge_valkey` healthy (`127.0.0.1:6381`) |
| `restore-db` sem `-ConfirmRestore` | Bloqueado (fail-closed); com a flag, restore OK (verificado antes das edições finais de docs) |
| Simulador 72h (`run_balance_verifier.gd`) | Não re-executado (~512 s; auditado na `003`) |

## 3. Ambiente e Restrições

- Detalhes de host/WSL2/portas e operação: [INFRASTRUCTURE.md](INFRASTRUCTURE.md).
- Containers do usuário (`8000`, `5678`, `1880`, `6333/6334`, `5433`, `6380`) não foram alterados.
- No sandbox do agente, `wsl`/Docker exigem execução fora do sandbox; `.env` foi criado via WSL (escrita pelo sandbox Windows é negada).
- Containers PlayForge (`playforge_db`, `playforge_valkey`) permanecem em execução.

## 4. Próxima Ação Exata

**Fase 2 — Core da Fábrica & Multi-Projeto** (diretório `factory/` em Python, Project Manager, isolamento de projetos, logs estruturados). **Não iniciar sem aprovação do operador.**
