# Capability Specification: `infrastructure`

- **Capability ID:** `infrastructure`
- **Status:** `ACTIVE_VERIFIED` (`OpenSpec 008`, arquivada)
- **Referência Técnica:** [docs/INFRASTRUCTURE.md](../../docs/INFRASTRUCTURE.md)

## Requisitos de Infraestrutura Reproduzível

1. **Workspace Único (Sem Cópias Divergentes):** O repositório atual (`C:\Jogo_Android` / `/mnt/c/Jogo_Android` no WSL2) é montado diretamente nos containers e DevContainer sem clonar uma cópia independente.
2. **Paridade de Versão Godot (`4.4-stable`):** Editor/CLI Windows nativo (`tools/godot/`) e runner Linux headless (`infrastructure/docker/factory.Dockerfile`) devem executar exatamente `4.4-stable`.
3. **Orquestração Incremental & Sem Conflito de Portas:**
   - Respeitar portas já ocupadas detectadas no host (`8000`, `5678`, `6333/6334`, `1880`).
   - Fixar tags explícitas de imagem em `docker-compose.yml` (nunca `:latest` solto).
   - Aplicar limites explícitos de memória (`mem_limit`) compatíveis com `5.7Gi` de RAM disponíveis no WSL2.
   - Subir serviços futuros apenas sob profiles opcionais ou em fases posteriores (não subir `n8n` ou `ollama` na Fase 1).
4. **Zero Segredos:** `.env.example` traz apenas defaults locais não sensíveis; `.env` fica ignorado pelo `.gitignore`.

## Cenários Verificáveis

- **Cenário `INF-01` (Compose Config & Health):** `docker compose config` valida sem erros e `docker compose up -d db` deixa `db` (`pgvector/pgvector:pg16`) em estado `healthy`, permitindo criar a extensão `vector` sem conflitar com portas do host.
- **Cenário `INF-02` (Godot CLI em Container Linux):** `docker compose run --rm factory-runner` executa `godot --headless --version` (`4.4.stable`) e roda `tests/unit/run_unit_tests.gd` com `229 assertions | Failed: 0`.
- **Cenário `INF-03` (Segurança Destrutiva):** Comandos de reset/restore de banco exigem confirmação explícita antes de sobrescrever volumes ou dados.
