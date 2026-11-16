"""Orquestrador multiagente stateful com checkpoint SQLite e gates humanos (Fase 6)."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.models import APPROVAL_STAGES, ApprovalRequired, FactoryError
from factory.playforge.registry import ProjectManager, validate_project_id
from factory.playforge.security_utils import scrub_secrets
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.template_registry.registry import TemplateRegistry

from .agents import AgentRegistry
from .schemas import AIError, LoopLimitExceededError


class ApprovalPauseSignal(FactoryError):
    """Sinal interno indicando pausa controlada aguardando aprovacao humana."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(message)


class SqliteCheckpointer:
    """Persistencia checkpointed em SQLite local (compativel com retomada tipo LangGraph)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_runs (
                        run_id TEXT PRIMARY KEY,
                        workflow_name TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        current_node TEXT,
                        iteration_count INTEGER NOT NULL DEFAULT 0,
                        max_iterations INTEGER NOT NULL DEFAULT 12,
                        started_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        completed_at TEXT,
                        pending_approval_stage TEXT,
                        state_json TEXT NOT NULL,
                        error_json TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        node_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        state_json TEXT NOT NULL,
                        note TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
        finally:
            conn.close()

    def create_run(
        self,
        *,
        run_id: str,
        workflow_name: str,
        project_id: str,
        entry_node: str,
        max_iterations: int,
        state: dict[str, Any],
        timestamp: str,
    ) -> None:
        clean_state = json.dumps(scrub_secrets(state), sort_keys=True, ensure_ascii=True)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO workflow_runs (
                        run_id, workflow_name, project_id, status, current_node,
                        iteration_count, max_iterations, started_at, updated_at,
                        completed_at, pending_approval_stage, state_json, error_json
                    ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, NULL, NULL, ?, NULL)
                    """,
                    (
                        run_id,
                        workflow_name,
                        project_id,
                        "RUNNING",
                        entry_node,
                        max_iterations,
                        timestamp,
                        timestamp,
                        clean_state,
                    ),
                )
        finally:
            conn.close()

    def record_checkpoint(
        self,
        *,
        run_id: str,
        step_index: int,
        node_id: str,
        agent_id: str,
        node_status: str,
        run_status: str,
        next_node: str | None,
        iteration_count: int,
        state: dict[str, Any],
        timestamp: str,
        note: str | None = None,
        pending_approval_stage: str | None = None,
        error_payload: dict[str, Any] | None = None,
        completed: bool = False,
    ) -> None:
        clean_state = json.dumps(scrub_secrets(state), sort_keys=True, ensure_ascii=True)
        clean_err = (
            json.dumps(scrub_secrets(error_payload), sort_keys=True, ensure_ascii=True)
            if error_payload
            else None
        )
        completed_at = timestamp if completed else None
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO workflow_checkpoints (
                        run_id, step_index, node_id, agent_id, status, state_json, note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, step_index, node_id, agent_id, node_status, clean_state, note, timestamp),
                )
                conn.execute(
                    """
                    UPDATE workflow_runs
                    SET status = ?, current_node = ?, iteration_count = ?, updated_at = ?,
                        completed_at = COALESCE(?, completed_at),
                        pending_approval_stage = ?, state_json = ?, error_json = ?
                    WHERE run_id = ?
                    """,
                    (
                        run_status,
                        next_node,
                        iteration_count,
                        timestamp,
                        completed_at,
                        pending_approval_stage,
                        clean_state,
                        clean_err,
                        run_id,
                    ),
                )
        finally:
            conn.close()

    def load_run(self, run_id: str) -> dict[str, Any]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                raise AIError(f"Execucao de workflow '{run_id}' nao encontrada no checkpointer.")
            data = dict(row)
            data["state"] = json.loads(data.pop("state_json"))
            err_raw = data.pop("error_json")
            data["error"] = json.loads(err_raw) if err_raw else None
            return data
        finally:
            conn.close()

    def list_checkpoints(self, run_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM workflow_checkpoints WHERE run_id = ? ORDER BY seq ASC",
                (run_id,),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["state"] = json.loads(item.pop("state_json"))
                out.append(item)
            return out
        finally:
            conn.close()


@dataclass(frozen=True)
class GraphNode:
    """No tipado do grafo de orquestracao associado a um AgentContract."""

    node_id: str
    agent_id: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    required_tool: str | None = None
    next_node: str | None = None
    max_retries_override: int | None = None


class GraphOrchestrator:
    """Maquina de estados DAG com checkpoint SQLite, limites anti-loop e pausa em gates humanos."""

    def __init__(
        self,
        *,
        checkpointer: SqliteCheckpointer,
        agent_registry: AgentRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self.checkpointer = checkpointer
        self.agent_registry = agent_registry or AgentRegistry()
        self._clock = clock
        self._monotonic = monotonic_clock or time.monotonic
        self._nodes: dict[str, GraphNode] = {}

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def add_node(self, node: GraphNode) -> None:
        self.agent_registry.get_agent(node.agent_id)
        if node.required_tool:
            self.agent_registry.authorize_tool(node.agent_id, node.required_tool)
        self._nodes[node.node_id] = node

    def _execute_node_with_retry(self, node: GraphNode, state: dict[str, Any]) -> dict[str, Any]:
        contract = self.agent_registry.get_agent(node.agent_id)
        if node.required_tool:
            self.agent_registry.authorize_tool(node.agent_id, node.required_tool)
        max_retries = (
            node.max_retries_override if node.max_retries_override is not None else contract.max_retries
        )
        attempts = 0
        last_exc: Exception | None = None
        while attempts <= max_retries:
            attempts += 1
            try:
                return node.handler(dict(state))
            except (ApprovalPauseSignal, ApprovalRequired, LoopLimitExceededError):
                raise
            except Exception as exc:
                last_exc = exc
                if attempts > max_retries:
                    break
        raise AIError(
            f"No '{node.node_id}' (agente '{node.agent_id}') falhou apos {attempts} tentativa(s): {last_exc}"
        ) from last_exc

    def _drive_from(
        self,
        *,
        run_id: str,
        workflow_name: str,
        project_id: str,
        current_node: str | None,
        state: dict[str, Any],
        iteration_count: int,
        max_iterations: int,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        started_mono = self._monotonic()
        step_index = len(self.checkpointer.list_checkpoints(run_id))

        while current_node is not None:
            elapsed = self._monotonic() - started_mono
            if elapsed > timeout_seconds:
                msg = (
                    f"Timeout global de {timeout_seconds:.2f}s excedido no workflow '{workflow_name}' "
                    f"(no '{current_node}')."
                )
                self.checkpointer.record_checkpoint(
                    run_id=run_id,
                    step_index=step_index,
                    node_id=current_node,
                    agent_id=self._nodes.get(current_node, GraphNode(current_node, "orchestrator", lambda s: s)).agent_id,
                    node_status="TIMEOUT",
                    run_status="FAILED",
                    next_node=current_node,
                    iteration_count=iteration_count,
                    state=state,
                    timestamp=self._now_timestamp(),
                    note=msg,
                    error_payload={"error": "LoopLimitExceededError", "message": msg},
                    completed=True,
                )
                raise LoopLimitExceededError(msg)

            if iteration_count >= max_iterations:
                msg = (
                    f"Limite anti-loop de max_iterations={max_iterations} atingido no workflow '{workflow_name}' "
                    f"(proximo no '{current_node}')."
                )
                self.checkpointer.record_checkpoint(
                    run_id=run_id,
                    step_index=step_index,
                    node_id=current_node,
                    agent_id=self._nodes.get(current_node, GraphNode(current_node, "orchestrator", lambda s: s)).agent_id,
                    node_status="LOOP_LIMIT",
                    run_status="FAILED",
                    next_node=current_node,
                    iteration_count=iteration_count,
                    state=state,
                    timestamp=self._now_timestamp(),
                    note=msg,
                    error_payload={"error": "LoopLimitExceededError", "message": msg},
                    completed=True,
                )
                raise LoopLimitExceededError(msg)

            node = self._nodes.get(current_node)
            if node is None:
                raise AIError(f"No '{current_node}' nao registrado no grafo '{workflow_name}'.")

            iteration_count += 1
            step_index += 1

            try:
                patch = self._execute_node_with_retry(node, state)
            except ApprovalPauseSignal as pause:
                self.checkpointer.record_checkpoint(
                    run_id=run_id,
                    step_index=step_index,
                    node_id=node.node_id,
                    agent_id=node.agent_id,
                    node_status="AWAITING_APPROVAL",
                    run_status="AWAITING_APPROVAL",
                    next_node=node.node_id,
                    iteration_count=iteration_count,
                    state=state,
                    timestamp=self._now_timestamp(),
                    note=str(pause),
                    pending_approval_stage=pause.stage,
                )
                return self.get_status(run_id)
            except ApprovalRequired as exc:
                stage = APPROVAL_STAGES[0] if APPROVAL_STAGES else "APROVACAO_HUMANA_SPEC"
                self.checkpointer.record_checkpoint(
                    run_id=run_id,
                    step_index=step_index,
                    node_id=node.node_id,
                    agent_id=node.agent_id,
                    node_status="AWAITING_APPROVAL",
                    run_status="AWAITING_APPROVAL",
                    next_node=node.node_id,
                    iteration_count=iteration_count,
                    state=state,
                    timestamp=self._now_timestamp(),
                    note=str(exc),
                    pending_approval_stage=stage,
                )
                return self.get_status(run_id)
            except Exception as exc:
                self.checkpointer.record_checkpoint(
                    run_id=run_id,
                    step_index=step_index,
                    node_id=node.node_id,
                    agent_id=node.agent_id,
                    node_status="FAILED",
                    run_status="FAILED",
                    next_node=node.node_id,
                    iteration_count=iteration_count,
                    state=state,
                    timestamp=self._now_timestamp(),
                    note=str(exc),
                    error_payload={"error": exc.__class__.__name__, "message": str(exc)},
                    completed=True,
                )
                raise

            if not isinstance(patch, dict):
                raise AIError(f"No '{node.node_id}' deve retornar dict de estado.")

            override_next = patch.pop("_next", node.next_node)
            state.update(patch)
            next_node = override_next
            finished = next_node is None

            self.checkpointer.record_checkpoint(
                run_id=run_id,
                step_index=step_index,
                node_id=node.node_id,
                agent_id=node.agent_id,
                node_status="COMPLETED",
                run_status="COMPLETED" if finished else "RUNNING",
                next_node=next_node,
                iteration_count=iteration_count,
                state=state,
                timestamp=self._now_timestamp(),
                note=f"No '{node.node_id}' concluido",
                completed=finished,
            )
            current_node = next_node

        return self.get_status(run_id)

    def run(
        self,
        *,
        workflow_name: str,
        project_id: str,
        entry_node: str,
        initial_state: dict[str, Any] | None = None,
        run_id: str | None = None,
        max_iterations: int = 12,
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        """Inicia um novo workflow checkpointed para um projeto isolado."""
        validate_project_id(project_id)
        if max_iterations <= 0:
            raise LoopLimitExceededError("max_iterations deve ser > 0.")
        if entry_node not in self._nodes:
            raise AIError(f"entry_node '{entry_node}' nao registrado.")

        effective_run_id = run_id or f"wf-{project_id}-{uuid.uuid4().hex[:8]}"
        state: dict[str, Any] = dict(initial_state or {})
        state["project_id"] = project_id
        state["workflow_name"] = workflow_name

        self.checkpointer.create_run(
            run_id=effective_run_id,
            workflow_name=workflow_name,
            project_id=project_id,
            entry_node=entry_node,
            max_iterations=max_iterations,
            state=state,
            timestamp=self._now_timestamp(),
        )
        return self._drive_from(
            run_id=effective_run_id,
            workflow_name=workflow_name,
            project_id=project_id,
            current_node=entry_node,
            state=state,
            iteration_count=0,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )

    def resume(
        self,
        run_id: str,
        *,
        max_iterations: int | None = None,
        timeout_seconds: float = 120.0,
        state_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retoma uma execucao pausada ou interrompida exatamente do ultimo checkpoint."""
        saved = self.checkpointer.load_run(run_id)
        if saved["status"] == "COMPLETED":
            return self.get_status(run_id)
        if saved["status"] == "FAILED":
            raise AIError(f"Execucao '{run_id}' esta em estado FAILED e nao pode ser retomada sem novo run.")
        if not saved["current_node"]:
            raise AIError(f"Execucao '{run_id}' sem current_node definido para retomada.")

        merged_state = dict(saved["state"])
        if state_patch:
            merged_state.update(state_patch)

        limit = max_iterations if max_iterations is not None else int(saved["max_iterations"])
        return self._drive_from(
            run_id=run_id,
            workflow_name=saved["workflow_name"],
            project_id=saved["project_id"],
            current_node=saved["current_node"],
            state=merged_state,
            iteration_count=int(saved["iteration_count"]),
            max_iterations=limit,
            timeout_seconds=timeout_seconds,
        )

    def get_status(self, run_id: str) -> dict[str, Any]:
        run_data = self.checkpointer.load_run(run_id)
        run_data["checkpoints"] = self.checkpointer.list_checkpoints(run_id)
        return run_data


def build_mvp_generation_orchestrator(
    manager: ProjectManager,
    *,
    db_path: Path | None = None,
    agent_registry: AgentRegistry | None = None,
    run_godot_tests: bool = True,
    verify_template_tests: bool = False,
    package_preview_build: bool = True,
    clock: Callable[[], datetime] | None = None,
) -> GraphOrchestrator:
    """Constroi o grafo padrao MVP (Spec -> GDD -> Gate Humano -> Template -> GameGenerator)."""
    spec_gen = SpecificationGenerator(manager)
    tpl_reg = TemplateRegistry(repo_root=manager.repo_root)
    game_gen = GameGenerator(manager, template_registry=tpl_reg)

    checkpoint_file = db_path or (manager.repo_root / "data" / "checkpoints" / "orchestrator.sqlite3")
    orchestrator = GraphOrchestrator(
        checkpointer=SqliteCheckpointer(checkpoint_file),
        agent_registry=agent_registry or AgentRegistry(),
        clock=clock,
    )

    def node_spec_design(state: dict[str, Any]) -> dict[str, Any]:
        pid = state["project_id"]
        manager.require_mutable_project(pid)
        spec = spec_gen.generate_and_save_spec(pid)
        gdd = spec_gen.generate_and_save_gdd(pid)
        return {
            "spec_id": spec["spec_id"],
            "gdd_title": gdd["title"],
        }

    def node_human_spec_gate(state: dict[str, Any]) -> dict[str, Any]:
        pid = state["project_id"]
        try:
            approval = spec_gen.verify_spec_approved(pid)
        except ApprovalRequired as exc:
            raise ApprovalPauseSignal(
                "APROVACAO_HUMANA_SPEC",
                f"Aguardando aprovacao humana da GameSpecification para '{pid}': {exc}",
            ) from exc
        return {"spec_sha256": approval["spec_sha256"], "spec_approved": True}

    def node_template_selection(state: dict[str, Any]) -> dict[str, Any]:
        pid = state["project_id"]
        sel = tpl_reg.select_template_for_project(
            manager,
            pid,
            require_approved_spec=True,
            prefer_template_id=state.get("prefer_template_id"),
            run_godot_tests=verify_template_tests,
        )
        return {
            "template_id": sel["template_id"],
            "template_version": sel["template_version"],
            "skeleton_sha256": sel["skeleton_sha256"],
        }

    def node_game_generation(state: dict[str, Any]) -> dict[str, Any]:
        pid = state["project_id"]
        eff_godot = bool(state.get("run_godot_tests", run_godot_tests))
        eff_pkg = bool(state.get("package_preview_build", package_preview_build))
        res = game_gen.generate_project(
            pid,
            prefer_template_id=state.get("template_id"),
            verify_template_tests=verify_template_tests,
            run_godot_tests=eff_godot,
            package_preview_build=eff_pkg,
            force=bool(state.get("force", False)),
        )
        return {
            "generation_status": res["status"],
            "workspace": res["workspace"],
            "file_count": res["file_count"],
            "verification": res["verification"],
            "preview_package": res["preview_package"],
        }

    orchestrator.add_node(
        GraphNode(
            node_id="spec_design",
            agent_id="game-design",
            required_tool="spec_generate",
            handler=node_spec_design,
            next_node="human_spec_gate",
        )
    )
    orchestrator.add_node(
        GraphNode(
            node_id="human_spec_gate",
            agent_id="orchestrator",
            required_tool="spec_validate",
            handler=node_human_spec_gate,
            next_node="template_selection",
        )
    )
    orchestrator.add_node(
        GraphNode(
            node_id="template_selection",
            agent_id="architecture",
            required_tool="godot_validate_template",
            handler=node_template_selection,
            next_node="game_generation",
        )
    )
    orchestrator.add_node(
        GraphNode(
            node_id="game_generation",
            agent_id="gameplay",
            required_tool="godot_generate_project",
            handler=node_game_generation,
            next_node=None,
        )
    )
    return orchestrator
