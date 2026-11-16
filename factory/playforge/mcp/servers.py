"""Servidores MCP confinados da PlayForge Factory (game-project, game-design, godot, testing)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from factory.playforge.ai.agents import AgentRegistry
from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.asset_pipeline.validator import inspect_wav
from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.models import ANCHOR_PROJECT_ID, WorkspaceEscape
from factory.playforge.qa_engine.balance_verifier import BalanceVerifierEngine
from factory.playforge.qa_engine.runner import QAEngine
from factory.playforge.qa_engine.static_analyzer import StaticAnalyzer
from factory.playforge.registry import ProjectManager, _atomic_write_text, validate_project_id
from factory.playforge.security_utils import is_forbidden_secret_relpath
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.validator import SpecificationValidator
from factory.playforge.template_registry.registry import TemplateRegistry

from .base_server import MCPServer
from .schemas import MCPAccessDenied, MCPToolError, ToolSpec

_MAX_TEXT_READ_BYTES = 512 * 1024
_MAX_TEXT_WRITE_BYTES = 512 * 1024


def _default_audit_path(manager: ProjectManager) -> Path:
    return manager.repo_root / "data" / "logs" / "mcp_audit.jsonl"


def _resolve_scoped_file(manager: ProjectManager, project_id: str, rel_path: str) -> Path:
    """Resolve e valida caminho relativo estritamente dentro do workspace de project_id."""
    validate_project_id(project_id)
    cleaned = rel_path.replace("\\", "/").strip()
    if not cleaned or cleaned.startswith("/") or (len(cleaned) >= 2 and cleaned[1] == ":"):
        raise MCPAccessDenied(f"Caminho absoluto nao permitido: '{rel_path}'.")
    if is_forbidden_secret_relpath(cleaned):
        raise MCPAccessDenied(
            f"Caminho bloqueado por politica de segredos ou travessia (SEC-01): '{rel_path}'."
        )

    ws_root = manager.resolve_game_path(project_id, ".").resolve()
    target = manager.resolve_game_path(project_id, cleaned)
    resolved_target = target.resolve()
    try:
        resolved_target.relative_to(ws_root)
    except ValueError as exc:
        raise WorkspaceEscape(
            f"Caminho '{rel_path}' resolve para fora do workspace '{project_id}'."
        ) from exc
    return target


def create_game_project_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'game-project-mcp' para manipulacao isolada por project_id."""
    server = MCPServer(
        "game-project-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )

    def handle_list(_args: dict[str, Any]) -> dict[str, Any]:
        projects = manager.list_projects()
        return {"count": len(projects), "projects": projects}

    def handle_get(args: dict[str, Any]) -> dict[str, Any]:
        return manager.get_project(args["project_id"])

    def handle_read_file(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        rel_path = args["rel_path"]
        target = _resolve_scoped_file(manager, pid, rel_path)
        if not target.is_file():
            raise MCPToolError(f"Arquivo nao encontrado no projeto '{pid}': '{rel_path}'.")
        raw = target.read_bytes()
        if len(raw) > _MAX_TEXT_READ_BYTES:
            raise MCPToolError(f"Arquivo excede o limite de {_MAX_TEXT_READ_BYTES} bytes.")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MCPToolError(f"Arquivo '{rel_path}' nao e texto UTF-8 valido.") from exc
        return {
            "project_id": pid,
            "rel_path": rel_path,
            "size_bytes": len(raw),
            "content": content,
            "files_touched": [],
        }

    def handle_write_file(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        rel_path = args["rel_path"]
        content = args["content"]
        if "\x00" in content:
            raise MCPAccessDenied("Conteudo binario com byte nulo recusado em escrita textual MCP.")
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_TEXT_WRITE_BYTES:
            raise MCPToolError(f"Conteudo excede o limite de {_MAX_TEXT_WRITE_BYTES} bytes.")
        manager.require_mutable_project(pid)
        target = _resolve_scoped_file(manager, pid, rel_path)
        _atomic_write_text(target, content)
        return {
            "status": "WRITTEN",
            "project_id": pid,
            "rel_path": rel_path,
            "bytes_written": len(encoded),
            "files_touched": [rel_path],
        }

    server.register_tool(
        ToolSpec(
            name="project_list",
            description="Lista projetos registrados na PlayForge Factory.",
            input_schema={"type": "object", "required": [], "properties": {}, "additionalProperties": False},
            handler=handle_list,
            requires_project_id=False,
        )
    )
    server.register_tool(
        ToolSpec(
            name="project_get",
            description="Retorna metadados de um projeto registrado por project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_get,
        )
    )
    server.register_tool(
        ToolSpec(
            name="project_read_file",
            description="Le arquivo textual UTF-8 confinado ao workspace de project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id", "rel_path"],
                "properties": {
                    "project_id": {"type": "string"},
                    "rel_path": {"type": "string"},
                },
                "additionalProperties": False,
            },
            handler=handle_read_file,
        )
    )
    server.register_tool(
        ToolSpec(
            name="project_write_file",
            description="Escreve arquivo textual UTF-8 exclusivamente em projeto mutavel confinado (bloqueia zaikor e segredos).",
            input_schema={
                "type": "object",
                "required": ["project_id", "rel_path", "content"],
                "properties": {
                    "project_id": {"type": "string"},
                    "rel_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "additionalProperties": False,
            },
            handler=handle_write_file,
        )
    )
    return server


def create_game_design_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'game-design-mcp' para GameSpecification e GDD."""
    server = MCPServer(
        "game-design-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )
    spec_gen = SpecificationGenerator(manager)
    validator = SpecificationValidator()

    def handle_spec_generate(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        spec = spec_gen.generate_and_save_spec(pid)
        return {
            "status": "GENERATED",
            "project_id": pid,
            "spec_id": spec["spec_id"],
            "files_touched": ["specs/game_specification.json"],
        }

    def handle_spec_validate(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        spec_path = manager.resolve_game_path(pid, "specs/game_specification.json")
        if not spec_path.is_file():
            raise MCPToolError(f"GameSpecification ausente para '{pid}'.")
        try:
            raw = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPToolError(f"GameSpecification JSON invalido para '{pid}': {exc}") from exc
        validated = validator.validate_spec(raw)
        return {
            "status": "VALID",
            "project_id": pid,
            "spec_id": validated["spec_id"],
            "game_id": validated["game_id"],
            "files_touched": [],
        }

    def handle_gdd_generate(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        gdd = spec_gen.generate_and_save_gdd(pid)
        return {
            "status": "GENERATED",
            "project_id": pid,
            "title": gdd["title"],
            "files_touched": ["gdd/gdd.json", "gdd/gdd.md"],
        }

    for name, desc, fn in (
        ("spec_generate", "Gera specs/game_specification.json validado para project_id.", handle_spec_generate),
        ("spec_validate", "Valida specs/game_specification.json existente de project_id.", handle_spec_validate),
        ("gdd_generate", "Gera specs/gdd.json e specs/gdd.md a partir da spec de project_id.", handle_gdd_generate),
    ):
        server.register_tool(
            ToolSpec(
                name=name,
                description=desc,
                input_schema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {"project_id": {"type": "string"}},
                    "additionalProperties": False,
                },
                handler=fn,
            )
        )
    return server


def create_godot_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'godot-mcp' para templates e geracao/verificacao Godot isolada."""
    server = MCPServer(
        "godot-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )
    tpl_reg = TemplateRegistry(repo_root=manager.repo_root)
    game_gen = GameGenerator(manager, template_registry=tpl_reg)

    def handle_validate_template(args: dict[str, Any]) -> dict[str, Any]:
        return tpl_reg.validate_template(
            args["template_id"],
            version=args.get("version"),
            run_godot_tests=bool(args.get("run_godot_tests", False)),
        )

    def handle_generate_project(args: dict[str, Any]) -> dict[str, Any]:
        res = game_gen.generate_project(
            args["project_id"],
            prefer_template_id=args.get("prefer_template_id"),
            run_godot_tests=bool(args.get("run_godot_tests", True)),
            verify_template_tests=bool(args.get("verify_template_tests", True)),
            package_preview_build=bool(args.get("package_preview_build", True)),
            force=bool(args.get("force", False)),
        )
        res["files_touched"] = ["specs/generation_manifest.json"]
        return res

    def handle_verify_project(args: dict[str, Any]) -> dict[str, Any]:
        report = game_gen.verify_generated_project(args["project_id"])
        report["files_touched"] = ["specs/verification_report.json"]
        return report

    server.register_tool(
        ToolSpec(
            name="godot_validate_template",
            description="Valida manifesto, hashes e opcionalmente demo headless de um template.",
            input_schema={
                "type": "object",
                "required": ["template_id"],
                "properties": {
                    "template_id": {"type": "string"},
                    "version": {"type": "string"},
                    "run_godot_tests": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            handler=handle_validate_template,
            requires_project_id=False,
        )
    )
    server.register_tool(
        ToolSpec(
            name="godot_generate_project",
            description="Gera e verifica projeto Godot isolado para project_id com spec aprovada.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "prefer_template_id": {"type": "string"},
                    "run_godot_tests": {"type": "boolean"},
                    "verify_template_tests": {"type": "boolean"},
                    "package_preview_build": {"type": "boolean"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            handler=handle_generate_project,
        )
    )
    server.register_tool(
        ToolSpec(
            name="godot_verify_project",
            description="Executa verificacao de integridade e testes Godot headless em project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_verify_project,
        )
    )
    return server


def create_testing_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'testing-mcp' para execucao e leitura de suites verificadoras."""
    server = MCPServer(
        "testing-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )
    game_gen = GameGenerator(manager)
    static_analyzer = StaticAnalyzer(manager)
    balance_engine = BalanceVerifierEngine(manager)
    qa_engine = QAEngine(manager)

    def handle_run_suite(args: dict[str, Any]) -> dict[str, Any]:
        report = game_gen.verify_generated_project(args["project_id"])
        report["files_touched"] = ["specs/verification_report.json"]
        return report

    def handle_read_report(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        report_path = manager.resolve_game_path(pid, "specs/verification_report.json")
        if not report_path.is_file():
            raise MCPToolError(f"Relatorio de verificacao ausente para '{pid}'.")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPToolError(f"verification_report.json invalido para '{pid}': {exc}") from exc
        report["files_touched"] = []
        return report

    def handle_static_audit(args: dict[str, Any]) -> dict[str, Any]:
        report = static_analyzer.audit_project(args["project_id"])
        report["files_touched"] = []
        return report

    def handle_balance_audit(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        report = balance_engine.verify_project_balance(
            pid,
            genre=args.get("genre"),
            seed=int(args.get("seed", 2026)),
            run_godot=bool(args.get("run_godot", False)),
            save_report=True,
            strict=False,
        )
        report["files_touched"] = [] if pid == ANCHOR_PROJECT_ID else ["specs/balance_report.json"]
        return report

    def handle_qa_pipeline(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        report = qa_engine.run_qa_pipeline(
            pid,
            with_godot=bool(args.get("with_godot", True)),
            with_assets=bool(args.get("with_assets", True)),
            genre=args.get("genre"),
            seed=int(args.get("seed", 2026)),
            frames=int(args.get("frames", 10)),
            save_report=True,
            strict=False,
        )
        report["files_touched"] = [] if pid == ANCHOR_PROJECT_ID else ["specs/balance_report.json", "specs/qa_report.json"]
        return report

    def handle_read_qa_report(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        report_path = manager.resolve_game_path(pid, "specs/qa_report.json")
        if not report_path.is_file():
            raise MCPToolError(f"Relatorio QA ausente para '{pid}'.")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPToolError(f"qa_report.json invalido para '{pid}': {exc}") from exc
        report["files_touched"] = []
        return report

    server.register_tool(
        ToolSpec(
            name="testing_run_project_suite",
            description="Executa suite de integridade e Godot headless para project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_run_suite,
        )
    )
    server.register_tool(
        ToolSpec(
            name="testing_read_verification_report",
            description="Le specs/verification_report.json de project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_read_report,
        )
    )
    server.register_tool(
        ToolSpec(
            name="qa_run_static_audit",
            description="Audita referencias res://, segredos e pureza src/core/ em project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_static_audit,
        )
    )
    server.register_tool(
        ToolSpec(
            name="qa_run_balance_audit",
            description="Simula balanceamento deterministico multi-genero para project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "genre": {"type": "string"},
                    "seed": {"type": "integer"},
                    "run_godot": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            handler=handle_balance_audit,
        )
    )
    server.register_tool(
        ToolSpec(
            name="qa_run_full_pipeline",
            description="Executa pipeline completo de 4 pilares do QA Engine sobre project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "with_godot": {"type": "boolean"},
                    "with_assets": {"type": "boolean"},
                    "genre": {"type": "string"},
                    "seed": {"type": "integer"},
                    "frames": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            handler=handle_qa_pipeline,
        )
    )
    server.register_tool(
        ToolSpec(
            name="qa_read_report",
            description="Le specs/qa_report.json de project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=handle_read_qa_report,
        )
    )
    return server


def create_asset_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'asset-mcp' para sintese procedural, registro e auditoria de assets."""
    server = MCPServer(
        "asset-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )
    asset_reg = AssetRegistry(manager)

    def handle_generate_sprite(args: dict[str, Any]) -> dict[str, Any]:
        entry = asset_reg.generate_procedural_image_asset(
            project_id=args["project_id"],
            asset_id=args["asset_id"],
            name=args["name"],
            asset_type=args.get("asset_type", "sprite_2d"),
            rel_path=args["rel_path"],
            width=int(args.get("width", 64)),
            height=int(args.get("height", 64)),
            pattern=args.get("pattern", "hero_silhouette"),
            seed=int(args.get("seed", 2026)),
        )
        return {"status": "GENERATED", "asset": entry, "files_touched": [entry["file_path"], "assets/asset_registry.json"]}

    def handle_register(args: dict[str, Any]) -> dict[str, Any]:
        entry = asset_reg.register_existing_asset(
            project_id=args["project_id"],
            asset_id=args["asset_id"],
            name=args["name"],
            asset_type=args["asset_type"],
            rel_path=args["rel_path"],
            license_name=args["license"],
            origin=args.get("origin", "created_in_house"),
            author_or_provider=args.get("author_or_provider", "PlayForge Studio"),
            tool_used=args.get("tool_used", "manual-import"),
            model_used=args.get("model_used", "n/a"),
            prompt_or_seed=args.get("prompt_or_seed", "n/a"),
            restrictions=args.get("restrictions", "Uso comercial interno liberado"),
        )
        return {"status": "REGISTERED", "asset": entry, "files_touched": ["assets/asset_registry.json"]}

    def handle_list(args: dict[str, Any]) -> dict[str, Any]:
        items = asset_reg.list_assets(args["project_id"], asset_type=args.get("asset_type"))
        return {"count": len(items), "assets": items, "files_touched": []}

    def handle_audit(args: dict[str, Any]) -> dict[str, Any]:
        report = asset_reg.audit_project_assets(
            args["project_id"],
            verify_godot=bool(args.get("verify_godot", False)),
        )
        report["files_touched"] = []
        return report

    server.register_tool(
        ToolSpec(
            name="asset_generate_sprite",
            description="Sintetiza PNG RGBA local gratuito e registra proveniencia em AssetRegistry.",
            input_schema={
                "type": "object",
                "required": ["project_id", "asset_id", "name", "rel_path"],
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "name": {"type": "string"},
                    "rel_path": {"type": "string"},
                    "asset_type": {"type": "string"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "pattern": {"type": "string"},
                    "seed": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            handler=handle_generate_sprite,
        )
    )
    server.register_tool(
        ToolSpec(
            name="asset_register",
            description="Valida formato, SHA-256, licenca e proveniencia de asset existente no projeto.",
            input_schema={
                "type": "object",
                "required": ["project_id", "asset_id", "name", "asset_type", "rel_path", "license"],
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "name": {"type": "string"},
                    "asset_type": {"type": "string"},
                    "rel_path": {"type": "string"},
                    "license": {"type": "string"},
                    "origin": {"type": "string"},
                    "author_or_provider": {"type": "string"},
                    "tool_used": {"type": "string"},
                    "model_used": {"type": "string"},
                    "prompt_or_seed": {"type": "string"},
                    "restrictions": {"type": "string"},
                },
                "additionalProperties": False,
            },
            handler=handle_register,
        )
    )
    server.register_tool(
        ToolSpec(
            name="asset_list",
            description="Lista assets registrados em AssetRegistry de project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_type": {"type": "string"},
                },
                "additionalProperties": False,
            },
            handler=handle_list,
        )
    )
    server.register_tool(
        ToolSpec(
            name="asset_audit",
            description="Audita hashes, licencas, ausencia de orfaos/temporarios e opcionalmente Godot headless.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "verify_godot": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            handler=handle_audit,
        )
    )
    return server


def create_audio_mcp(
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Cria servidor 'audio-mcp' para sintese DSP gratuita sem clipping e inspecao WAV."""
    server = MCPServer(
        "audio-mcp",
        agent_registry=agent_registry,
        audit_log_path=audit_log_path or _default_audit_path(manager),
    )
    asset_reg = AssetRegistry(manager)

    def handle_generate_sfx(args: dict[str, Any]) -> dict[str, Any]:
        entry = asset_reg.generate_procedural_audio_asset(
            project_id=args["project_id"],
            asset_id=args["asset_id"],
            name=args["name"],
            asset_type="sfx",
            rel_path=args["rel_path"],
            preset=args.get("preset", "slash"),
            seed=int(args.get("seed", 2026)),
        )
        return {"status": "GENERATED", "asset": entry, "files_touched": [entry["file_path"], "assets/asset_registry.json"]}

    def handle_generate_bgm(args: dict[str, Any]) -> dict[str, Any]:
        entry = asset_reg.generate_procedural_audio_asset(
            project_id=args["project_id"],
            asset_id=args["asset_id"],
            name=args["name"],
            asset_type="bgm",
            rel_path=args["rel_path"],
            preset=args.get("preset", "dark_ambient_loop"),
            duration_s=float(args.get("duration_s", 1.2)),
            seed=int(args.get("seed", 2026)),
        )
        return {"status": "GENERATED", "asset": entry, "files_touched": [entry["file_path"], "assets/asset_registry.json"]}

    def handle_inspect_wav(args: dict[str, Any]) -> dict[str, Any]:
        pid = args["project_id"]
        rel_path = args["rel_path"]
        target = _resolve_scoped_file(manager, pid, rel_path)
        if not target.is_file():
            raise MCPToolError(f"Arquivo WAV ausente em '{pid}': '{rel_path}'.")
        metrics = inspect_wav(target.read_bytes(), reject_clipping=False)
        metrics["project_id"] = pid
        metrics["rel_path"] = rel_path
        metrics["files_touched"] = []
        return metrics

    server.register_tool(
        ToolSpec(
            name="audio_generate_sfx",
            description="Sintetiza SFX WAV PCM16 local sem clipping e registra em AssetRegistry.",
            input_schema={
                "type": "object",
                "required": ["project_id", "asset_id", "name", "rel_path"],
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "name": {"type": "string"},
                    "rel_path": {"type": "string"},
                    "preset": {"type": "string"},
                    "seed": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            handler=handle_generate_sfx,
        )
    )
    server.register_tool(
        ToolSpec(
            name="audio_generate_bgm",
            description="Sintetiza BGM loop WAV PCM16 local sem clipping e registra em AssetRegistry.",
            input_schema={
                "type": "object",
                "required": ["project_id", "asset_id", "name", "rel_path"],
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "name": {"type": "string"},
                    "rel_path": {"type": "string"},
                    "preset": {"type": "string"},
                    "duration_s": {"type": "number"},
                    "seed": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            handler=handle_generate_bgm,
        )
    )
    server.register_tool(
        ToolSpec(
            name="audio_inspect_wav",
            description="Mede sample_rate, duracao, dBFS e clipped_samples de arquivo WAV em project_id.",
            input_schema={
                "type": "object",
                "required": ["project_id", "rel_path"],
                "properties": {
                    "project_id": {"type": "string"},
                    "rel_path": {"type": "string"},
                },
                "additionalProperties": False,
            },
            handler=handle_inspect_wav,
        )
    )
    return server


_SERVER_FACTORIES: dict[str, Callable[..., MCPServer]] = {
    "asset-mcp": create_asset_mcp,
    "audio-mcp": create_audio_mcp,
    "game-project-mcp": create_game_project_mcp,
    "game-design-mcp": create_game_design_mcp,
    "godot-mcp": create_godot_mcp,
    "testing-mcp": create_testing_mcp,
}

AVAILABLE_MCP_SERVERS: tuple[str, ...] = tuple(sorted(_SERVER_FACTORIES))


def create_mcp_server(
    server_name: str,
    manager: ProjectManager,
    *,
    agent_registry: AgentRegistry | None = None,
    audit_log_path: Path | None = None,
) -> MCPServer:
    """Instancia qualquer servidor MCP oficial da Fase 6 pelo nome."""
    builder = _SERVER_FACTORIES.get(server_name)
    if builder is None:
        raise MCPToolError(
            f"Servidor MCP desconhecido '{server_name}'. Disponiveis: {AVAILABLE_MCP_SERVERS}."
        )
    return builder(
        manager,
        agent_registry=agent_registry,
        audit_log_path=audit_log_path,
    )
