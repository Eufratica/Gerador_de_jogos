"""Ponte de execucao da automacao n8n (WF-001..WF-020), servidor loopback e gates humanos (Fase 9)."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from factory.playforge.ai.model_router import inspect_environment
from factory.playforge.ai.orchestrator import GraphOrchestrator, SqliteCheckpointer
from factory.playforge.ai.schemas import AIError
from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.asset_pipeline.synthesizer import inspect_media_toolchain
from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.models import ANCHOR_PROJECT_ID, ApprovalRequired, FactoryError, WorkspaceEscape
from factory.playforge.qa_engine.balance_verifier import BalanceVerifierEngine
from factory.playforge.qa_engine.runner import QAEngine
from factory.playforge.qa_engine.static_analyzer import StaticAnalyzer
from factory.playforge.registry import ProjectManager, _atomic_write_json, validate_project_id
from factory.playforge.security_utils import append_jsonl_record, scan_prompt_injection, scrub_secrets
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.template_registry.registry import TemplateRegistry

from .schemas import (
    ALLOWED_LOOPBACK_HOSTS,
    AUTOMATION_SCHEMA_VERSION,
    HumanGateBlockedError,
    WorkflowValidationError,
    get_workflow_definition,
)
from .validator import validate_exports_directory

_MAX_WEBHOOK_BYTES = 1024 * 1024


def _scan_untrusted_payload(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            key_str = str(k)
            if ".." in key_str and "/" in key_str:
                raise WorkflowValidationError(f"Chave suspeita de travessia no payload ({path}.{key_str}).")
            _scan_untrusted_payload(v, f"{path}.{key_str}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_untrusted_payload(item, f"{path}[{idx}]")
    elif isinstance(value, str):
        hits = scan_prompt_injection(value)
        if hits:
            raise WorkflowValidationError(
                f"Conteudo suspeito/prompt injection bloqueado em '{path}': {', '.join(hits)}."
            )


class AutomationEngine:
    """Executor deterministico e fail-closed dos workflows WF-001..WF-020."""

    def __init__(
        self,
        manager: ProjectManager,
        *,
        exports_dir: Path | None = None,
        checkpoint_db: Path | None = None,
        audit_log_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.manager = manager
        self.exports_dir = exports_dir or (manager.repo_root / "automation" / "exports")
        self.checkpoint_db = checkpoint_db or (manager.repo_root / "data" / "checkpoints" / "orchestrator.sqlite3")
        self.audit_log_path = audit_log_path or (manager.repo_root / "data" / "logs" / "automation_audit.jsonl")
        self._clock = clock

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _checkpointer(self) -> SqliteCheckpointer:
        return SqliteCheckpointer(self.checkpoint_db)

    def _record_audit(self, record: dict[str, Any], *, read_only_hint: bool = False) -> None:
        if read_only_hint and not self.manager.registry_path.is_file():
            return
        append_jsonl_record(self.audit_log_path, {"ts": self._now_timestamp(), **record})

    def _require_project_id(self, payload: dict[str, Any], *, mutable: bool = True) -> str:
        raw_pid = payload.get("project_id")
        if not isinstance(raw_pid, str) or not raw_pid.strip():
            raise WorkflowValidationError("Campo 'project_id' obrigatorio no payload do workflow.")
        pid = validate_project_id(raw_pid.strip())
        if mutable:
            self.manager.require_mutable_project(pid)
        return pid

    def _create_human_gate_run(
        self,
        *,
        workflow_id: str,
        project_id: str,
        approval_stage: str,
        payload: dict[str, Any],
        run_id: str | None = None,
    ) -> dict[str, Any]:
        cp = self._checkpointer()
        effective_run_id = run_id or f"n8n-{workflow_id.lower()}-{uuid.uuid4().hex[:10]}"
        ts = self._now_timestamp()
        state = {
            "workflow_id": workflow_id,
            "project_id": project_id,
            "approval_stage": approval_stage,
            "payload": scrub_secrets(payload),
        }
        cp.create_run(
            run_id=effective_run_id,
            workflow_name=f"n8n:{workflow_id}",
            project_id=project_id,
            entry_node="human_gate",
            max_iterations=4,
            state=state,
            timestamp=ts,
        )
        cp.record_checkpoint(
            run_id=effective_run_id,
            step_index=0,
            node_id="human_gate",
            agent_id="orchestrator",
            node_status="PAUSED",
            run_status="WAITING_HUMAN_APPROVAL",
            next_node="release_or_continue",
            iteration_count=1,
            state=state,
            timestamp=ts,
            note=f"Aguardando aprovacao humana nominal em '{approval_stage}' ({workflow_id}).",
            pending_approval_stage=approval_stage,
            completed=False,
        )
        return {
            "status": "WAITING_HUMAN_APPROVAL",
            "gate_cleared": False,
            "workflow_id": workflow_id,
            "project_id": project_id,
            "run_id": effective_run_id,
            "pending_approval_stage": approval_stage,
        }

    def approve_human_gate(
        self,
        run_id: str,
        *,
        approver: str,
        approved: bool,
        notes: str,
    ) -> dict[str, Any]:
        """Registra decisao humana nominal para gate n8n/WF-014 pausado no checkpointer SQLite."""
        clean_approver = str(approver).strip()
        clean_notes = str(notes).strip()
        if not clean_approver or not clean_notes:
            raise WorkflowValidationError("Aprovador e justificativa nominal sao obrigatorios.")
        hits = scan_prompt_injection(clean_notes)
        if hits:
            raise WorkflowValidationError(f"Notas invalidas bloqueadas ({', '.join(hits)}).")

        cp = self._checkpointer()
        try:
            run_data = cp.load_run(run_id)
        except AIError as exc:
            raise WorkflowValidationError(str(exc)) from exc

        if run_data["status"] != "WAITING_HUMAN_APPROVAL":
            raise WorkflowValidationError(
                f"Run '{run_id}' nao aguarda aprovacao humana (status atual: {run_data['status']})."
            )

        project_id = run_data["project_id"]
        stage = run_data.get("pending_approval_stage") or "spec"
        ts = self._now_timestamp()
        state = dict(run_data["state"])
        state["human_decision"] = {
            "approver": clean_approver,
            "approved": bool(approved),
            "notes": clean_notes,
            "decided_at": ts,
        }

        if approved and project_id != ANCHOR_PROJECT_ID:
            if stage == "spec":
                SpecificationGenerator(self.manager).approve_specification(
                    project_id=project_id,
                    approver=clean_approver,
                    decision_notes=clean_notes,
                    require_gdd=self.manager.resolve_game_path(project_id, "gdd/gdd.json").is_file(),
                )
            elif stage == "architecture":
                self.manager.record_approval(
                    project_id=project_id,
                    approval_stage="APROVACAO_HUMANA_ARQUITETURA",
                    approver=clean_approver,
                    decision_notes=clean_notes,
                )
            elif stage == "release":
                self.manager.record_approval(
                    project_id=project_id,
                    approval_stage="APROVACAO_HUMANA_PREVIEW",
                    approver=clean_approver,
                    decision_notes=clean_notes,
                )

        final_status = "COMPLETED" if approved else "REJECTED"
        cp.record_checkpoint(
            run_id=run_id,
            step_index=1,
            node_id="human_gate",
            agent_id="orchestrator",
            node_status="COMPLETED" if approved else "REJECTED",
            run_status=final_status,
            next_node=None,
            iteration_count=int(run_data["iteration_count"]) + 1,
            state=state,
            timestamp=ts,
            note=f"Decisao humana de '{clean_approver}': {'APROVADO' if approved else 'REJEITADO'}.",
            pending_approval_stage=None,
            completed=True,
        )
        out = {
            "status": final_status,
            "gate_cleared": bool(approved),
            "run_id": run_id,
            "project_id": project_id,
            "approval_stage": stage,
            "approver": clean_approver,
        }
        self._record_audit({"event": "HUMAN_GATE_RESOLVED", **out})
        return out

    def trigger_workflow(
        self,
        workflow_id: str,
        payload: dict[str, Any] | None = None,
        *,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Executa a acao oficial correspondente a WF-001..WF-020 validando seguranca e gates."""
        defn = get_workflow_definition(workflow_id)
        data: dict[str, Any] = dict(payload or {})
        if not isinstance(data, dict):
            raise WorkflowValidationError("Payload do workflow deve ser objeto JSON (dict).")
        _scan_untrusted_payload(data)

        # Bloqueia explicitamente mutacao de zaikor em payloads externos antes mesmo de handlers especificos
        if defn.workflow_id not in ("WF-017", "WF-020") and data.get("project_id") == ANCHOR_PROJECT_ID:
            self.manager.require_mutable_project(ANCHOR_PROJECT_ID)

        dispatch: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "WF-001": self._wf_001_init,
            "WF-002": self._wf_002_research,
            "WF-003": self._wf_003_gdd,
            "WF-004": self._wf_004_architecture,
            "WF-005": self._wf_005_spec,
            "WF-006": self._wf_006_template_select,
            "WF-007": self._wf_007_project_generate,
            "WF-008": self._wf_008_asset_generate,
            "WF-009": self._wf_009_gameplay_check,
            "WF-010": self._wf_010_uiux_profile,
            "WF-011": self._wf_011_integration_verify,
            "WF-012": self._wf_012_game_qa,
            "WF-013": self._wf_013_balance_audit,
            "WF-014": self._wf_014_human_approval,
            "WF-015": self._wf_015_build_package,
            "WF-016": self._wf_016_publishing,
            "WF-017": self._wf_017_analytics,
            "WF-018": self._wf_018_optimization,
            "WF-019": self._wf_019_error_recovery,
            "WF-020": self._wf_020_monitoring,
        }
        handler = dispatch[defn.workflow_id]
        result = handler(data)
        result.setdefault("workflow_id", defn.workflow_id)
        result.setdefault("workflow_name", defn.name)
        result.setdefault("automation_schema_version", AUTOMATION_SCHEMA_VERSION)
        if "gate_cleared" not in result:
            result["gate_cleared"] = bool(result.get("passed", result.get("status") not in ("WAITING_HUMAN_APPROVAL", "BLOCKED", "FAILED")))

        read_only_wf = defn.workflow_id in ("WF-017", "WF-020")
        self._record_audit(
            {
                "event": "WORKFLOW_TRIGGER",
                "workflow_id": defn.workflow_id,
                "project_id": data.get("project_id"),
                "status": result.get("status"),
                "gate_cleared": result["gate_cleared"],
            },
            read_only_hint=read_only_wf,
        )

        if strict and not result["gate_cleared"]:
            if defn.requires_human_gate:
                raise HumanGateBlockedError(
                    f"Workflow '{defn.workflow_id}' pausado/bloqueado aguardando aprovacao humana."
                )
            raise WorkflowValidationError(f"Workflow '{defn.workflow_id}' nao obteve aprovacao no gate.")
        return result

    def _wf_001_init(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_pid = payload.get("project_id")
        pid = validate_project_id(raw_pid) if isinstance(raw_pid, str) else ""
        if not pid:
            raise WorkflowValidationError("WF-001 exige 'project_id' valido.")
        name = str(payload.get("name") or f"Projeto {pid}").strip()
        genre = str(payload.get("genre") or "action-rpg").strip()
        if not self.manager.registry_path.is_file():
            self.manager.init_registry()
        proj = self.manager.create_project(project_id=pid, name=name, genre=genre)
        return {"status": "INITIALIZED", "project": proj, "gate_cleared": True}

    def _wf_002_research(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        genre = str(payload.get("genre") or self.manager.get_project(pid)["genre"])
        refs = payload.get("references", [])
        if not isinstance(refs, list):
            raise WorkflowValidationError("Campo 'references' em WF-002 deve ser lista.")
        clean_refs = [str(r).strip() for r in refs if isinstance(r, str) and r.strip()]
        artifact = {
            "workflow_id": "WF-002",
            "project_id": pid,
            "genre": genre,
            "untrusted_sources_sanitized": True,
            "references_count": len(clean_refs),
            "facts": [f"Genero alvo declarado: {genre}."],
            "hypotheses": [f"Sessao curta e metas claras adequadas para {genre} (pendente validacao em testes)."],
            "references": clean_refs,
            "generated_at": self._now_timestamp(),
        }
        out_path = self.manager.resolve_game_path(pid, "specs/market_research.json")
        _atomic_write_json(out_path, artifact)
        return {"status": "COMPLETED", "output_path": "specs/market_research.json", "gate_cleared": True}

    def _wf_003_gdd(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        gdd = SpecificationGenerator(self.manager).generate_and_save_gdd(pid)
        return {"status": "GENERATED", "title": gdd["title"], "project_id": pid, "gate_cleared": True}

    def _wf_004_architecture(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        project = self.manager.get_project(pid)
        if not project.get("approvals", {}).get("APROVACAO_HUMANA_ARQUITETURA", {}).get("approved"):
            return self._create_human_gate_run(
                workflow_id="WF-004",
                project_id=pid,
                approval_stage="architecture",
                payload=payload,
                run_id=payload.get("run_id"),
            )
        return {"status": "ARCHITECTURE_APPROVED", "project_id": pid, "gate_cleared": True}

    def _wf_005_spec(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        spec_gen = SpecificationGenerator(self.manager)
        spec = spec_gen.generate_and_save_spec(pid)
        return {"status": "GENERATED", "spec_id": spec["spec_id"], "project_id": pid, "gate_cleared": True}

    def _wf_006_template_select(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        reg = TemplateRegistry(repo_root=self.manager.repo_root)
        sel = reg.select_template_for_project(
            self.manager,
            pid,
            prefer_template_id=payload.get("prefer_template_id"),
            run_godot_tests=bool(payload.get("run_godot_tests", False)),
        )
        return {"status": "SELECTED", **sel, "gate_cleared": True}

    def _wf_007_project_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        res = GameGenerator(self.manager).generate_project(
            pid,
            prefer_template_id=payload.get("prefer_template_id"),
            run_godot_tests=bool(payload.get("run_godot_tests", True)),
            verify_template_tests=bool(payload.get("verify_template_tests", True)),
            package_preview_build=bool(payload.get("package_preview_build", False)),
            force=bool(payload.get("force", False)),
        )
        return {**res, "gate_cleared": True}

    def _wf_008_asset_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        reg = AssetRegistry(self.manager)
        pack = reg.generate_default_pack(pid)
        audit = reg.audit_project_assets(pid, verify_godot=bool(payload.get("verify_godot", False)))
        return {"status": "COMPLETED", "pack": pack, "audit": audit, "gate_cleared": bool(audit["passed"])}

    def _wf_009_gameplay_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        rep = StaticAnalyzer(self.manager).audit_project(pid)
        return {"status": "PASSED" if rep["passed"] else "FAILED", **rep, "gate_cleared": bool(rep["passed"])}

    def _wf_010_uiux_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        frames = int(payload.get("frames", 3))
        rep = QAEngine(self.manager).profile_project_godot(pid, frames=frames, strict=False)
        return {"status": "PASSED" if rep["passed"] else "FAILED", **rep, "gate_cleared": bool(rep["passed"])}

    def _wf_011_integration_verify(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        rep = GameGenerator(self.manager).verify_generated_project(pid)
        return {"status": "VERIFIED", **rep, "gate_cleared": bool(rep["passed"])}

    def _wf_012_game_qa(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        rep = QAEngine(self.manager).run_qa_pipeline(
            pid,
            with_godot=bool(payload.get("with_godot", True)),
            with_assets=bool(payload.get("with_assets", True)),
            frames=int(payload.get("frames", 5)),
            strict=False,
        )
        return {"status": "PASSED" if rep["passed"] else "FAILED", **rep, "gate_cleared": bool(rep["passed"])}

    def _wf_013_balance_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        rep = BalanceVerifierEngine(self.manager).verify_project_balance(
            pid,
            genre=payload.get("genre"),
            seed=int(payload.get("seed", 2026)),
            strict=False,
        )
        return {"status": "PASSED" if rep["passed"] else "FAILED", **rep, "gate_cleared": bool(rep["passed"])}

    def _wf_014_human_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        stage = str(payload.get("approval_stage") or "spec").strip()
        if stage not in ("architecture", "spec", "release"):
            raise WorkflowValidationError(f"approval_stage invalido para WF-014: '{stage}'.")
        return self._create_human_gate_run(
            workflow_id="WF-014",
            project_id=pid,
            approval_stage=stage,
            payload=payload,
            run_id=payload.get("run_id"),
        )

    def _wf_015_build_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        qa_rep = QAEngine(self.manager).run_qa_pipeline(
            pid,
            with_godot=bool(payload.get("with_godot", False)),
            with_assets=bool(payload.get("with_assets", True)),
            strict=False,
        )
        if not qa_rep["passed"]:
            return {
                "status": "BLOCKED_QA_FAILED",
                "gate_cleared": False,
                "failed_pillars": qa_rep["failed_pillars"],
            }
        pkg = GameGenerator(self.manager).package_preview_artifact(pid)
        return {"status": "PACKAGED", "package": pkg, "gate_cleared": True}

    def _wf_016_publishing(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        project = self.manager.get_project(pid)
        release_app = project.get("approvals", {}).get("APROVACAO_HUMANA_PREVIEW", {})
        if not release_app.get("approved"):
            raise ApprovalRequired(
                f"Publicacao (WF-016) bloqueada: aprovacao humana 'release' ausente em '{pid}'."
            )
        manifest = {
            "workflow_id": "WF-016",
            "project_id": pid,
            "release_approver": release_app.get("approver"),
            "approved_at": release_app.get("approved_at"),
            "distribution_mode": "LOCAL_OFFLINE_MANIFEST_ONLY",
            "store_upload_executed": False,
            "generated_at": self._now_timestamp(),
        }
        out_path = self.manager.resolve_game_path(pid, "builds/release_manifest.json")
        _atomic_write_json(out_path, manifest)
        return {"status": "RELEASE_MANIFEST_READY", "manifest": manifest, "gate_cleared": True}

    def _wf_017_analytics(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_pid = payload.get("project_id")
        target_pid = validate_project_id(raw_pid) if isinstance(raw_pid, str) and raw_pid.strip() else ANCHOR_PROJECT_ID
        reports_present: list[str] = []
        if target_pid != ANCHOR_PROJECT_ID:
            for rel in ("specs/qa_report.json", "specs/balance_report.json", "specs/verification_report.json"):
                if self.manager.resolve_game_path(target_pid, rel).is_file():
                    reports_present.append(rel)
        return {
            "status": "COLLECTED",
            "project_id": target_pid,
            "pii_collected": False,
            "reports_indexed": reports_present,
            "gate_cleared": True,
        }

    def _wf_018_optimization(self, payload: dict[str, Any]) -> dict[str, Any]:
        pid = self._require_project_id(payload, mutable=True)
        proposal = {
            "workflow_id": "WF-018",
            "project_id": pid,
            "auto_applied": False,
            "requires_human_sdd_review": True,
            "recommendation": "Revisar curvas de progressao com base em specs/balance_report.json antes de nova aprovacao OpenSpec.",
            "created_at": self._now_timestamp(),
        }
        out_path = self.manager.resolve_game_path(pid, "specs/optimization_proposal.json")
        _atomic_write_json(out_path, proposal)
        return {
            "status": "PROPOSAL_CREATED_AWAITING_REVIEW",
            "proposal_path": "specs/optimization_proposal.json",
            "auto_applied": False,
            "gate_cleared": True,
        }

    def _wf_019_error_recovery(self, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise WorkflowValidationError("WF-019 exige 'run_id' para inspecao/recuperacao no SQLite.")
        cp = self._checkpointer()
        try:
            run_data = cp.load_run(run_id.strip())
        except AIError as exc:
            raise WorkflowValidationError(str(exc)) from exc
        checkpoints = cp.list_checkpoints(run_id.strip())
        return {
            "status": "RECOVERED_INSPECTION",
            "run_id": run_id.strip(),
            "run_status": run_data["status"],
            "project_id": run_data["project_id"],
            "checkpoints_count": len(checkpoints),
            "gate_cleared": True,
        }

    def _wf_020_monitoring(self, payload: dict[str, Any]) -> dict[str, Any]:
        exports_audit = validate_exports_directory(self.exports_dir, strict=False)
        env_info = inspect_environment()
        media_info = inspect_media_toolchain(repo_root=self.manager.repo_root)
        projects_count = (
            len(self.manager.list_projects()) if self.manager.registry_path.is_file() else 0
        )
        passed = bool(exports_audit["passed"]) and bool(media_info["godot_cli_available"])
        return {
            "status": "HEALTHY" if passed else "DEGRADED",
            "passed": passed,
            "gate_cleared": passed,
            "registry_initialized": self.manager.registry_path.is_file(),
            "projects_registered": projects_count,
            "exports_audit": {
                "passed": exports_audit["passed"],
                "validated_count": exports_audit["validated_count"],
                "expected_count": exports_audit["expected_count"],
            },
            "ai_environment": {
                "ollama_daemon_reachable": env_info.ollama_daemon_reachable,
                "supported_tiers": list(env_info.supported_tiers),
            },
            "godot_cli_available": media_info["godot_cli_available"],
            "zero_cost_policy": "ENFORCED_LOCAL_ONLY",
        }


class AutomationWebhookServer:
    """Servidor HTTP loopback (127.0.0.1) para webhooks do n8n Community."""

    def __init__(
        self,
        engine: AutomationEngine,
        *,
        host: str = "127.0.0.1",
        port: int = 8787,
    ) -> None:
        clean_host = host.strip().lower()
        if clean_host not in ALLOWED_LOOPBACK_HOSTS:
            raise WorkflowValidationError(
                f"Bind externo proibido por seguranca ({host}); use loopback 127.0.0.1/localhost."
            )
        self.engine = engine
        self.host = host
        self.port = int(port)
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._serving = False

    @property
    def server_port(self) -> int:
        if self._httpd is not None:
            return int(self._httpd.server_port)
        return self.port

    def start(self) -> int:
        engine = self.engine

        class _Handler(BaseHTTPRequestHandler):
            def _write_json(self, status_code: int, body: dict[str, Any]) -> None:
                raw = json.dumps(body, ensure_ascii=True, sort_keys=True).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                if self.path == "/health":
                    res = engine.trigger_workflow("WF-020", {})
                    self._write_json(200, res)
                    return
                self._write_json(404, {"error": "NotFound", "message": "Endpoint desconhecido."})

            def do_POST(self) -> None:
                if not self.path.startswith("/webhook/"):
                    self._write_json(404, {"error": "NotFound", "message": "Rota webhook invalida."})
                    return
                wf_id = self.path[len("/webhook/") :].strip("/")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self._write_json(400, {"error": "BadRequest", "message": "Content-Length invalido."})
                    return
                if length < 0 or length > _MAX_WEBHOOK_BYTES:
                    self._write_json(413, {"error": "PayloadTooLarge", "message": "Payload acima de 1MB."})
                    return

                raw_body = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(raw_body.decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    self._write_json(400, {"error": "InvalidJSON", "message": str(exc)})
                    return

                try:
                    out = engine.trigger_workflow(wf_id, payload)
                    code = 202 if out.get("status") == "WAITING_HUMAN_APPROVAL" else (200 if out.get("gate_cleared") else 422)
                    self._write_json(code, out)
                except ApprovalRequired as exc:
                    self._write_json(403, {"error": "ApprovalRequired", "message": str(exc)})
                except (FactoryError, WorkspaceEscape) as exc:
                    self._write_json(400, {"error": exc.__class__.__name__, "message": str(exc)})

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

        self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)
        return int(self._httpd.server_port)

    def serve_forever(self) -> None:
        if self._httpd is None:
            self.start()
        assert self._httpd is not None
        self._serving = True
        try:
            self._httpd.serve_forever(poll_interval=0.05)
        finally:
            self._serving = False

    def start_background(self) -> int:
        port = self.start()
        if self._thread is None or not self._thread.is_alive():
            ready = threading.Event()

            def _run() -> None:
                ready.set()
                self.serve_forever()

            self._thread = threading.Thread(
                target=_run,
                name="playforge-automation-webhook",
                daemon=True,
            )
            self._thread.start()
            ready.wait(timeout=2.0)
        return port

    def stop(self) -> None:
        httpd = self._httpd
        if httpd is not None:
            if self._serving:
                httpd.shutdown()
            httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> AutomationWebhookServer:
        self.start_background()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
