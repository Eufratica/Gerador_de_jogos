"""Handlers e subcomandos CLI para AI Engine, Multiagentes e Servidores MCP (Fase 6)."""
from __future__ import annotations

import argparse
import json
from typing import Any

from factory.playforge.ai.agents import AgentRegistry, get_engineering_role_catalog
from factory.playforge.ai.model_router import ModelRouter, OllamaClient
from factory.playforge.ai.orchestrator import build_mvp_generation_orchestrator
from factory.playforge.ai.schemas import DEFAULT_OLLAMA_BASE_URL
from factory.playforge.mcp.schemas import MCPToolValidationError
from factory.playforge.mcp.servers import AVAILABLE_MCP_SERVERS, create_mcp_server
from factory.playforge.registry import ProjectManager


def register_ai_mcp_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra subcomandos ai-*, agent-*, workflow-* e mcp-* na CLI da PlayForge."""
    p_health = sub.add_parser(
        "ai-health",
        help="Audita hardware local, politica Zero Cost e disponibilidade real do Ollama.",
    )
    p_health.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"Endpoint local do Ollama (padrao: {DEFAULT_OLLAMA_BASE_URL}).",
    )

    p_agents = sub.add_parser("agent-list", help="Lista contratos formais dos 14 agentes da fabrica.")
    p_agents.add_argument("--agent-id", default=None, help="Filtra um unico agent_id.")

    sub.add_parser("agent-roles", help="Lista os 13 papeis da Secao 10 mapeados aos contratos de agentes.")

    p_wf_run = sub.add_parser(
        "workflow-run",
        help="Executa workflow checkpointed em SQLite com pausa em gate humano.",
    )
    p_wf_run.add_argument("project_id", help="Slug do projeto alvo.")
    p_wf_run.add_argument(
        "--workflow",
        default="mvp-generation",
        choices=["mvp-generation"],
        help="Nome do grafo de workflow.",
    )
    p_wf_run.add_argument("--max-iterations", type=int, default=12, help="Limite anti-loop de nos.")
    p_wf_run.add_argument("--prefer-template", default=None, help="Template preferencial.")
    p_wf_run.add_argument("--skip-godot-tests", action="store_true", help="Nao executa Godot headless no no final.")
    p_wf_run.add_argument("--verify-template-tests", action="store_true", help="Re-executa suite do demo do template.")
    p_wf_run.add_argument("--skip-package", action="store_true", help="Nao gera ZIP preview em builds/.")
    p_wf_run.add_argument("--run-id", default=None, help="Identificador explicito da execucao.")

    p_wf_res = sub.add_parser("workflow-resume", help="Retoma workflow pausado a partir do checkpoint SQLite.")
    p_wf_res.add_argument("run_id", help="ID da execucao persistida.")
    p_wf_res.add_argument("--max-iterations", type=int, default=None, help="Novo teto de iteracoes se informado.")
    p_wf_res.add_argument("--skip-godot-tests", action="store_true", help="Forca skip dos testes Godot na retomada.")

    p_mcp_list = sub.add_parser("mcp-list-tools", help="Lista ferramentas registradas nos servidores MCP.")
    p_mcp_list.add_argument(
        "--server",
        default="all",
        choices=["all", *AVAILABLE_MCP_SERVERS],
        help="Servidor alvo ou 'all'.",
    )

    p_mcp_call = sub.add_parser("mcp-call", help="Invoca uma ferramenta MCP confinada com auditoria.")
    p_mcp_call.add_argument("server", choices=list(AVAILABLE_MCP_SERVERS), help="Nome do servidor MCP.")
    p_mcp_call.add_argument("tool", help="Nome da ferramenta MCP.")
    p_mcp_call.add_argument("--args-json", default="{}", help="Objeto JSON com argumentos da ferramenta.")
    p_mcp_call.add_argument("--agent-id", default=None, help="Agent ID para checagem de minimo privilegio.")


def handle_ai_mcp_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos da Fase 6 sobre o workspace raiz do manager."""
    if args.command == "ai-health":
        client = OllamaClient(base_url=args.ollama_url)
        router = ModelRouter(repo_root=manager.repo_root, client=client)
        return router.health_report()

    if args.command == "agent-list":
        registry = AgentRegistry()
        if args.agent_id:
            return registry.get_agent(args.agent_id).to_dict()
        agents = registry.list_agents()
        return {"count": len(agents), "agents": agents}

    if args.command == "agent-roles":
        roles = get_engineering_role_catalog(AgentRegistry())
        return {"count": len(roles), "roles": roles}

    if args.command == "workflow-run":
        orch = build_mvp_generation_orchestrator(
            manager,
            run_godot_tests=not args.skip_godot_tests,
            verify_template_tests=args.verify_template_tests,
            package_preview_build=not args.skip_package,
        )
        initial_state: dict[str, Any] = {
            "run_godot_tests": not args.skip_godot_tests,
            "package_preview_build": not args.skip_package,
        }
        if args.prefer_template:
            initial_state["prefer_template_id"] = args.prefer_template
        return orch.run(
            workflow_name=args.workflow,
            project_id=args.project_id,
            entry_node="spec_design",
            initial_state=initial_state,
            run_id=args.run_id,
            max_iterations=args.max_iterations,
        )

    if args.command == "workflow-resume":
        orch = build_mvp_generation_orchestrator(
            manager,
            run_godot_tests=not args.skip_godot_tests,
        )
        patch = {"run_godot_tests": False} if args.skip_godot_tests else None
        return orch.resume(
            args.run_id,
            max_iterations=args.max_iterations,
            state_patch=patch,
        )

    if args.command == "mcp-list-tools":
        targets = AVAILABLE_MCP_SERVERS if args.server == "all" else (args.server,)
        servers_out: dict[str, Any] = {}
        for name in targets:
            srv = create_mcp_server(name, manager)
            servers_out[name] = srv.list_tools()
        return {"servers": servers_out}

    if args.command == "mcp-call":
        try:
            parsed_args = json.loads(args.args_json)
        except json.JSONDecodeError as exc:
            raise MCPToolValidationError(f"--args-json invalido: {exc}") from exc
        if not isinstance(parsed_args, dict):
            raise MCPToolValidationError("--args-json deve ser um objeto JSON.")
        srv = create_mcp_server(args.server, manager)
        return srv.call_tool(args.tool, parsed_args, agent_id=args.agent_id)

    raise ValueError(f"Comando AI/MCP nao suportado: {args.command}")
