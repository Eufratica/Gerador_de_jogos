#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

ENV_FILE="${REPO_ROOT}/.env"
ENV_EXAMPLE="${REPO_ROOT}/.env.example"

load_env_defaults() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
  POSTGRES_DB="${POSTGRES_DB:-playforge}"
  POSTGRES_USER="${POSTGRES_USER:-playforge}"
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-playforge_local_dev}"
  PLAYFORGE_PG_PORT="${PLAYFORGE_PG_PORT:-5434}"
  PLAYFORGE_VALKEY_PORT="${PLAYFORGE_VALKEY_PORT:-6381}"
  PLAYFORGE_N8N_PORT="${PLAYFORGE_N8N_PORT:-5679}"
  PLAYFORGE_AUTOMATION_BRIDGE_PORT="${PLAYFORGE_AUTOMATION_BRIDGE_PORT:-8787}"
  GODOT_VERSION="${GODOT_VERSION:-4.4-stable}"
}

compose_cmd() {
  docker compose -f "${REPO_ROOT}/docker-compose.yml" "$@"
}

usage() {
  cat <<'EOF'
Uso: ./infrastructure/scripts/playforge.sh <comando> [opcoes]

Comandos:
  env-init                         Cria .env a partir de .env.example se ainda nao existir
  config                           Valida o docker-compose.yml
  build-runner | build             Constroi a imagem factory-runner (Python 3.12 + Godot 4.4)
  up                               Sobe o banco PostgreSQL + pgvector em background
  up-cache                         Sobe PostgreSQL + pgvector e Valkey (profile cache)
  up-automation                    Sobe n8n Community opcional (profile automation, 127.0.0.1:5679)
  down                             Para os servicos do PlayForge sem apagar volumes
  restart                          Reinicia os servicos do PlayForge
  status                           Mostra status dos containers PlayForge
  logs [servico]                   Exibe ultimas 100 linhas de log
  health | db-check                Verifica saude do PostgreSQL e extensao pgvector
  test-linux                       Executa testes Godot headless dentro do container Linux
  test-factory                     Executa testes Python do Factory Core dentro do container Linux
  backup-db [arquivo.sql]          Gera dump SQL local em build/backups/ (ignorado no Git)
  restore-db <arquivo> --confirm-restore
                                   Restaura dump SQL (exige confirmacao explicita)
EOF
}

cmd="${1:-}"
if [[ -z "${cmd}" ]]; then
  usage
  exit 1
fi
shift

load_env_defaults

case "${cmd}" in
  env-init)
    if [[ -f "${ENV_FILE}" ]]; then
      echo "[playforge] .env ja existe em ${ENV_FILE} (preservado)."
    else
      cp "${ENV_EXAMPLE}" "${ENV_FILE}"
      echo "[playforge] .env criado a partir de .env.example (nao rastreado no Git)."
    fi
    ;;

  config)
    compose_cmd --profile cache --profile tools --profile automation config >/dev/null
    echo "[playforge] docker-compose.yml valido (profiles default, cache, tools, automation)."
    ;;

  build-runner|build)
    compose_cmd --profile tools build factory-runner
    ;;

  up)
    compose_cmd up -d db
    ;;

  up-cache)
    compose_cmd --profile cache up -d db valkey
    ;;

  up-automation)
    compose_cmd --profile automation up -d n8n
    ;;

  down)
    compose_cmd --profile cache --profile tools --profile automation down
    ;;

  restart)
    compose_cmd restart
    ;;

  status)
    compose_cmd --profile cache --profile tools --profile automation ps
    ;;

  logs)
    compose_cmd logs --tail=100 "$@"
    ;;

  health|db-check)
    compose_cmd exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
    compose_cmd exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT current_database() AS db, extname, extversion FROM pg_extension WHERE extname = 'vector';"
    ;;

  test-linux)
    compose_cmd --profile tools run --rm --no-deps factory-runner bash -euo pipefail -c '
      echo "=== Tool Versions ==="
      python3 --version
      godot --headless --version
      echo "=== Unit Tests (Linux Headless) ==="
      godot --headless --no-header --path /workspace --script res://tests/unit/run_unit_tests.gd
      echo "=== Action Balance Verifier (Linux Headless) ==="
      godot --headless --no-header --path /workspace --script res://tests/integration/run_action_verifier.gd
      echo "=== Engine Boot Gate (Linux Headless) ==="
      godot --headless --no-header --path /workspace --script res://tests/integration/verify_engine_boot.gd -- --save-path=/tmp/playforge_boot_verify.json
    '
    ;;

  test-factory)
    compose_cmd --profile tools run --rm --no-deps factory-runner python3 -m unittest discover -s /workspace/factory/tests -v
    ;;

  backup-db)
    mkdir -p "${REPO_ROOT}/build/backups"
    ts="$(date +%Y%m%d_%H%M%S)"
    out_file="${1:-build/backups/playforge_${ts}.sql}"
    if [[ "${out_file}" != /* ]]; then
      out_file="${REPO_ROOT}/${out_file}"
    fi
    mkdir -p "$(dirname -- "${out_file}")"
    compose_cmd exec -T db pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists > "${out_file}"
    echo "[playforge] Backup gerado em ${out_file}"
    ;;

  restore-db)
    backup_file="${1:-}"
    confirm_flag="${2:-}"
    if [[ -z "${backup_file}" ]]; then
      echo "[playforge] ERRO: informe o arquivo de backup." >&2
      exit 2
    fi
    if [[ "${confirm_flag}" != "--confirm-restore" ]]; then
      echo "[playforge] BLOQUEADO (fail-closed): restore-db sobrescreve dados. Repita com --confirm-restore." >&2
      exit 2
    fi
    if [[ "${backup_file}" != /* ]]; then
      backup_file="${REPO_ROOT}/${backup_file}"
    fi
    if [[ ! -f "${backup_file}" ]]; then
      echo "[playforge] ERRO: arquivo nao encontrado: ${backup_file}" >&2
      exit 2
    fi
    compose_cmd exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 < "${backup_file}"
    echo "[playforge] Restore concluido a partir de ${backup_file}"
    ;;

  *)
    echo "[playforge] Comando desconhecido: ${cmd}" >&2
    usage
    exit 1
    ;;
esac
