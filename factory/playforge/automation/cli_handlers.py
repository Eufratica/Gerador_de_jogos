"""Handlers e subcomandos CLI da camada de automacao n8n Community (Fase 9)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from factory.playforge.registry import ProjectManager

from .exporter import generate_official_exports
from .runner import AutomationEngine, AutomationWebhookServer
from .schemas import OFFICIAL_WORKFLOW_CATALOG, WorkflowValidationError
from .validator import validate_exports_directory


def register_automation_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra subcomandos automation-* na CLI principal da PlayForge."""
    sub.add_parser("automation-list", help="Lista catalogo oficial WF-001..WF-020 (docs/AUTOMATION.md).")

    p_exp = sub.add_parser("automation-export", help="Gera/regenera exports JSON n8n livres de credenciais.")
    p_exp.add_argument("--exports-dir", default=None, help="Diretorio de destino (padrao: automation/exports).")

    p_val = sub.add_parser("automation-validate", help="Audita completude e seguranca dos exports n8n WF-001..WF-020.")
    p_val.add_argument("--exports-dir", default=None, help="Diretorio alvo (padrao: automation/exports).")
    p_val.add_argument("--strict", action="store_true", help="Retorna codigo 1 se houver qualquer violacao.")

    p_trig = sub.add_parser("automation-trigger", help="Executa ponte local de um workflow WF-001..WF-020.")
    p_trig.add_argument("workflow_id", help="Identificador WF-001..WF-020.")
    p_trig.add_argument("--project", dest="project_id", default=None, help="Slug do projeto alvo.")
    p_trig.add_argument("--payload-json", default="{}", help="Objeto JSON opcional de payload.")
    p_trig.add_argument("--strict", action="store_true", help="Falha fechado se gate humano/QA bloquear.")

    p_app = sub.add_parser("automation-approve", help="Resolve decisao humana de gate n8n/WF-014.")
    p_app.add_argument("run_id", help="ID da execucao pausada em WAITING_HUMAN_APPROVAL.")
    p_app.add_argument("--approver", required=True, help="Identificador nominal do operador humano.")
    decision = p_app.add_mutually_exclusive_group(required=True)
    decision.add_argument("--approve", action="store_true", help="Aprova o gate.")
    decision.add_argument("--reject", action="store_true", help="Rejeita o gate.")
    p_app.add_argument("--notes", required=True, help="Justificativa nominal.")

    p_srv = sub.add_parser("automation-serve", help="Inicia servidor HTTP loopback (127.0.0.1) para webhooks n8n.")
    p_srv.add_argument("--host", default="127.0.0.1", help="Endereco loopback (padrao: 127.0.0.1).")
    p_srv.add_argument("--port", type=int, default=8787, help="Porta TCP local (padrao: 8787).")


def handle_automation_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos automation-* da CLI PlayForge."""
    default_exports = manager.repo_root / "automation" / "exports"

    if args.command == "automation-list":
        return {
            "count": len(OFFICIAL_WORKFLOW_CATALOG),
            "workflows": [defn.to_dict() for defn in OFFICIAL_WORKFLOW_CATALOG],
        }

    if args.command == "automation-export":
        target_dir = Path(args.exports_dir) if args.exports_dir else default_exports
        written = generate_official_exports(target_dir, overwrite=True)
        return {"status": "EXPORTED", "exports_dir": str(target_dir), "count": len(written)}

    if args.command == "automation-validate":
        target_dir = Path(args.exports_dir) if args.exports_dir else default_exports
        return validate_exports_directory(target_dir, strict=args.strict)

    engine = AutomationEngine(manager, exports_dir=default_exports)
    if args.command == "automation-trigger":
        try:
            payload = json.loads(args.payload_json)
        except json.JSONDecodeError as exc:
            raise WorkflowValidationError(f"--payload-json invalido: {exc}") from exc
        if not isinstance(payload, dict):
            raise WorkflowValidationError("--payload-json deve ser um objeto JSON.")
        if args.project_id:
            payload["project_id"] = args.project_id
        return engine.trigger_workflow(args.workflow_id, payload, strict=args.strict)

    if args.command == "automation-approve":
        return engine.approve_human_gate(
            args.run_id,
            approver=args.approver,
            approved=bool(args.approve),
            notes=args.notes,
        )

    if args.command == "automation-serve":
        srv = AutomationWebhookServer(engine, host=args.host, port=args.port)
        srv.serve_forever()
        return {"status": "STOPPED"}

    raise ValueError(f"Comando automation nao suportado: {args.command}")
