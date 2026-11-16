"""Gerenciador multi-projeto e maquina de estados fail-closed da PlayForge Factory."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from .logging_utils import StructuredLogger, system_clock
from .models import (
    ANCHOR_NAME,
    ANCHOR_PROJECT_ID,
    APPROVAL_STAGES,
    ApprovalRequired,
    DEFAULT_ENGINE,
    DEFAULT_ENGINE_VERSION,
    EvidenceRequired,
    FactoryError,
    InvalidProjectId,
    InvalidTransition,
    KIND_ANCHOR,
    KIND_GAME,
    PROJECT_ID_RE,
    ProjectExists,
    ProjectNotFound,
    ProtectedProject,
    RegistryCorrupt,
    SCHEMA_VERSION,
    STAGES,
    WorkspaceEscape,
    WorkspaceExists,
)

PROJECT_SUBDIRS = ("specs", "gdd", "src", "assets", "tests", "builds", "logs")


def _atomic_write_text(path: Path, content: str) -> None:
    """Grava texto UTF-8 de forma atomica no mesmo diretorio do arquivo alvo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(str(tmp_path), str(path))
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Grava JSON de forma atomica no mesmo diretorio do arquivo alvo."""
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    _atomic_write_text(path, serialized)


def _ensure_within(base_dir: Path, target_path: Path) -> Path:
    """Garante que target_path resolve estritamente dentro de base_dir."""
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError as exc:
        raise WorkspaceEscape(
            f"Caminho fora do workspace permitido: '{target_path}' escapa de '{resolved_base}'."
        ) from exc
    if resolved_target == resolved_base:
        raise WorkspaceEscape(f"Caminho invalido: aponta para a raiz '{resolved_base}'.")
    return resolved_target


def _require_text(value: Any, error_cls: type[FactoryError], message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise error_cls(message)
    return value.strip()


def validate_project_id(project_id: str) -> str:
    """Valida slug de projeto evitando caracteres perigosos e path traversal."""
    if not isinstance(project_id, str) or not PROJECT_ID_RE.match(project_id):
        raise InvalidProjectId(
            f"project_id invalido: '{project_id}'. Use ^[a-z][a-z0-9-]{{2,39}}$."
        )
    return project_id


def _build_anchor_entry(timestamp: str) -> dict[str, Any]:
    return {
        "project_id": ANCHOR_PROJECT_ID,
        "name": ANCHOR_NAME,
        "genre": "2d-action-rpg-idle",
        "kind": KIND_ANCHOR,
        "protected": True,
        "engine": DEFAULT_ENGINE,
        "engine_version": DEFAULT_ENGINE_VERSION,
        "workspace": ".",
        "stage": "PREVIEW",
        "version": "0.4.0-playable-slice",
        "created_at": timestamp,
        "updated_at": timestamp,
        "approvals": {},
        "history": [],
    }


class ProjectManager:
    """Coordena registro de jogos, isolamento de diretorios e transicoes de ciclo de vida."""

    def __init__(
        self,
        repo_root: Path,
        registry_path: Optional[Path] = None,
        games_root: Optional[Path] = None,
        log_path: Optional[Path] = None,
        clock: Callable[[], str] = system_clock,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = (
            Path(registry_path).resolve()
            if registry_path is not None
            else self.repo_root / "data" / "registry" / "projects.json"
        )
        self.games_root = (
            Path(games_root).resolve()
            if games_root is not None
            else self.repo_root / "games"
        )
        effective_log = (
            Path(log_path).resolve()
            if log_path is not None
            else self.repo_root / "data" / "logs" / "factory.jsonl"
        )
        self._clock = clock
        self._logger = StructuredLogger(effective_log, clock=clock)

    def _validate_registry_payload(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise RegistryCorrupt("Registro deve ser um objeto JSON.")
        if data.get("schema_version") != SCHEMA_VERSION:
            raise RegistryCorrupt(
                f"schema_version invalida no registro: esperado {SCHEMA_VERSION}, encontrado {data.get('schema_version')!r}."
            )
        projects = data.get("projects")
        if not isinstance(projects, dict):
            raise RegistryCorrupt("Campo 'projects' ausente ou invalido no registro.")
        return data

    def load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            raise RegistryCorrupt(f"Registro nao inicializado em {self.registry_path}.")
        try:
            raw = self.registry_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryCorrupt(f"Falha ao ler registro JSON em {self.registry_path}: {exc}") from exc
        return self._validate_registry_payload(parsed)

    def _save_registry(self, data: dict[str, Any]) -> None:
        data["updated_at"] = self._clock()
        _atomic_write_json(self.registry_path, data)

    def _manifest_path(self, project: dict[str, Any]) -> Optional[Path]:
        if project.get("kind") != KIND_GAME:
            return None
        ws_dir = self._workspace_dir_for_project(project["project_id"])
        return ws_dir / "project_manifest.json"

    def _workspace_dir_for_project(self, project_id: str) -> Path:
        validate_project_id(project_id)
        return _ensure_within(self.games_root, self.games_root / project_id)

    def _sync_project(self, data: dict[str, Any], project: dict[str, Any]) -> None:
        manifest_path = self._manifest_path(project)
        if manifest_path is not None:
            _atomic_write_json(manifest_path, project)
        data["projects"][project["project_id"]] = project
        self._save_registry(data)

    def init_registry(self) -> dict[str, Any]:
        """Inicializa o registro e garante o cadastro protegido do jogo-ancora."""
        ts = self._clock()
        if self.registry_path.exists():
            data = self.load_registry()
            anchor = data["projects"].get(ANCHOR_PROJECT_ID)
            if anchor is None:
                data["projects"][ANCHOR_PROJECT_ID] = _build_anchor_entry(ts)
                self._save_registry(data)
                self._logger.log("INFO", "anchor_registered", project_id=ANCHOR_PROJECT_ID)
            return data

        data = {
            "schema_version": SCHEMA_VERSION,
            "created_at": ts,
            "updated_at": ts,
            "projects": {ANCHOR_PROJECT_ID: _build_anchor_entry(ts)},
        }
        self._save_registry(data)
        self._logger.log("INFO", "registry_initialized", registry_path=str(self.registry_path))
        return data

    def list_projects(self) -> list[dict[str, Any]]:
        data = self.load_registry()
        return [data["projects"][pid] for pid in sorted(data["projects"].keys())]

    def get_project(self, project_id: str) -> dict[str, Any]:
        validate_project_id(project_id)
        data = self.load_registry()
        project = data["projects"].get(project_id)
        if project is None:
            raise ProjectNotFound(f"Projeto nao encontrado: '{project_id}'.")
        return project

    def require_mutable_project(self, project_id: str) -> dict[str, Any]:
        """Retorna o projeto garantindo que existe e nao e protegido (jogo-ancora)."""
        data = self.load_registry()
        return self._ensure_mutable_project(data, project_id)

    def now_timestamp(self) -> str:
        """Retorna timestamp ISO UTC pelo relogio injetado do gerenciador."""
        return self._clock()

    def log_event(self, level: str, event: str, **fields: Any) -> None:
        """Grava evento estruturado no log oficial da fabrica."""
        self._logger.log(level, event, **fields)

    def resolve_game_path(self, project_id: str, subpath: str) -> Path:
        """Resolve um caminho relativo estritamente dentro do workspace do projeto."""
        project = self.get_project(project_id)
        if project.get("kind") == KIND_ANCHOR:
            base_dir = self.repo_root
        else:
            base_dir = self._workspace_dir_for_project(project_id)

        candidate = Path(subpath)
        if candidate.is_absolute():
            raise WorkspaceEscape(f"Caminho absoluto nao permitido dentro do projeto: '{subpath}'.")
        resolved_base = base_dir.resolve()
        resolved_target = (resolved_base / candidate).resolve()
        try:
            resolved_target.relative_to(resolved_base)
        except ValueError as exc:
            raise WorkspaceEscape(
                f"Tentativa de escape do workspace '{project_id}': '{subpath}'."
            ) from exc
        return resolved_target

    def create_project(
        self,
        project_id: str,
        name: str,
        genre: str,
        engine: str = DEFAULT_ENGINE,
        engine_version: str = DEFAULT_ENGINE_VERSION,
    ) -> dict[str, Any]:
        """Cria um projeto isolado em games/<project_id>/ sem afetar outros jogos."""
        validate_project_id(project_id)
        clean_name = _require_text(name, FactoryError, "Nome do projeto obrigatorio.")
        clean_genre = _require_text(genre, FactoryError, "Genero do projeto obrigatorio.")
        clean_engine = _require_text(engine, FactoryError, "Engine obrigatoria.")
        clean_version = _require_text(engine_version, FactoryError, "Versao da engine obrigatoria.")

        data = self.init_registry()
        existing = data["projects"].get(project_id)
        if existing is not None:
            if existing.get("protected"):
                raise ProtectedProject(
                    f"Projeto protegido '{project_id}' nao pode ser recriado ou sobrescrito."
                )
            raise ProjectExists(f"Projeto ja registrado: '{project_id}'.")

        ws_dir = self._workspace_dir_for_project(project_id)
        if ws_dir.exists():
            raise WorkspaceExists(f"Workspace ja existe no disco: '{ws_dir}'.")

        for subdir in PROJECT_SUBDIRS:
            (ws_dir / subdir).mkdir(parents=True, exist_ok=False)

        try:
            rel_ws = ws_dir.relative_to(self.repo_root).as_posix()
        except ValueError:
            rel_ws = str(ws_dir)

        ts = self._clock()
        project = {
            "project_id": project_id,
            "name": clean_name,
            "genre": clean_genre,
            "kind": KIND_GAME,
            "protected": False,
            "engine": clean_engine,
            "engine_version": clean_version,
            "workspace": rel_ws,
            "stage": STAGES[0],
            "version": "0.1.0",
            "created_at": ts,
            "updated_at": ts,
            "approvals": {},
            "history": [],
        }
        self._sync_project(data, project)
        self._logger.log("INFO", "project_created", project_id=project_id, workspace=rel_ws)
        return project

    def _ensure_mutable_project(self, data: dict[str, Any], project_id: str) -> dict[str, Any]:
        validate_project_id(project_id)
        project = data["projects"].get(project_id)
        if project is None:
            raise ProjectNotFound(f"Projeto nao encontrado: '{project_id}'.")
        if project.get("protected"):
            raise ProtectedProject(
                f"Projeto protegido '{project_id}' (jogo-ancora) nao pode ser modificado ou removido."
            )
        return project

    def record_approval(
        self,
        project_id: str,
        approval_stage: str,
        approver: str,
        decision_notes: str,
    ) -> dict[str, Any]:
        """Registra aprovacao humana obrigatoria para destravar gate de arquitetura ou preview."""
        if approval_stage not in APPROVAL_STAGES:
            raise InvalidTransition(
                f"Etapa de aprovacao invalida: '{approval_stage}'. Esperado: {APPROVAL_STAGES}."
            )
        clean_approver = _require_text(approver, ApprovalRequired, "Identificacao do aprovador obrigatoria.")
        clean_notes = _require_text(decision_notes, ApprovalRequired, "Notas da decisao obrigatorias.")

        data = self.load_registry()
        project = self._ensure_mutable_project(data, project_id)

        ts = self._clock()
        project["approvals"][approval_stage] = {
            "approved": True,
            "approver": clean_approver,
            "notes": clean_notes,
            "approved_at": ts,
        }
        project["updated_at"] = ts
        self._sync_project(data, project)
        self._logger.log(
            "INFO",
            "approval_recorded",
            project_id=project_id,
            approval_stage=approval_stage,
            approver=clean_approver,
        )
        return project

    def advance_stage(
        self,
        project_id: str,
        target_stage: str,
        actor: str,
        evidence: str,
        notes: str = "",
    ) -> dict[str, Any]:
        """Avanca uma etapa sequencialmente com gate fail-closed de evidencia e aprovacao humana."""
        if target_stage not in STAGES:
            raise InvalidTransition(f"Etapa desconhecida: '{target_stage}'.")
        clean_actor = _require_text(actor, FactoryError, "Ator responsavel pela transicao obrigatorio.")
        clean_evidence = _require_text(
            evidence, EvidenceRequired, "Evidencia obrigatoria para avancar de etapa."
        )

        data = self.load_registry()
        project = self._ensure_mutable_project(data, project_id)

        current_stage = project["stage"]
        cur_idx = STAGES.index(current_stage)
        target_idx = STAGES.index(target_stage)
        if target_idx != cur_idx + 1:
            raise InvalidTransition(
                f"Transicao invalida de '{current_stage}' para '{target_stage}'. "
                "Apenas avanco sequencial de 1 etapa e permitido."
            )

        if current_stage in APPROVAL_STAGES:
            approval_rec = project.get("approvals", {}).get(current_stage, {})
            if approval_rec.get("approved") is not True:
                self._logger.log(
                    "WARN",
                    "transition_blocked_approval_required",
                    project_id=project_id,
                    current_stage=current_stage,
                    target_stage=target_stage,
                )
                raise ApprovalRequired(
                    f"Aprovacao humana obrigatoria antes de sair de '{current_stage}' "
                    f"no projeto '{project_id}'."
                )

        ts = self._clock()
        project["stage"] = target_stage
        project["updated_at"] = ts
        project["history"].append(
            {
                "from": current_stage,
                "to": target_stage,
                "actor": clean_actor,
                "evidence": clean_evidence,
                "notes": notes.strip() if isinstance(notes, str) else "",
                "ts": ts,
            }
        )
        self._sync_project(data, project)
        self._logger.log(
            "INFO",
            "stage_advanced",
            project_id=project_id,
            from_stage=current_stage,
            to_stage=target_stage,
            actor=clean_actor,
        )
        return project

    def delete_project(self, project_id: str, confirm: bool = False) -> None:
        """Remove projeto nao protegido somente com confirmacao explicita."""
        data = self.load_registry()
        project = self._ensure_mutable_project(data, project_id)
        if not confirm:
            raise ApprovalRequired(
                f"Exclusao de '{project_id}' bloqueada (fail-closed): exige confirm=True."
            )
        ws_dir = self._workspace_dir_for_project(project_id)
        if ws_dir.exists():
            shutil.rmtree(str(ws_dir))
        del data["projects"][project_id]
        self._save_registry(data)
        self._logger.log("WARN", "project_deleted", project_id=project_id)
