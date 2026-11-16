"""Handlers e subcomandos CLI do Game Template Registry (Fase 4)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager
from factory.playforge.template_registry.registry import TemplateRegistry


def register_template_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra os subcomandos template-* no parser principal da CLI."""
    p_list = sub.add_parser("template-list", help="Lista ou filtra templates validados.")
    p_list.add_argument("--include-deprecated", action="store_true", help="Inclui versoes deprecated.")
    p_list.add_argument("--genre", default=None, help="Filtra por genero suportado.")
    p_list.add_argument("--engine", default=None, help="Filtra por engine suportada.")
    p_list.add_argument("--platform", default=None, help="Filtra por plataforma suportada.")

    p_show = sub.add_parser("template-show", help="Exibe detalhes validados de um template.")
    p_show.add_argument("template_id", help="Slug do template (ex.: godot-2d-action-rpg).")
    p_show.add_argument("--version", default=None, help="Versao SemVer especifica (default: mais recente).")

    p_val = sub.add_parser("template-validate", help="Valida integridade e opcionalmente executa testes Godot.")
    p_val.add_argument("template_id", help="Slug do template.")
    p_val.add_argument("--version", default=None, help="Versao SemVer especifica.")
    p_val.add_argument("--run-godot-tests", action="store_true", help="Executa runner headless Godot no demo.")

    p_sel = sub.add_parser("template-select", help="Seleciona o melhor template compativel para um projeto.")
    p_sel.add_argument("project_id", help="Slug do projeto alvo.")
    p_sel.add_argument("--prefer", default=None, help="Template preferencial em caso de compatibilidade.")
    p_sel.add_argument(
        "--allow-unapproved",
        action="store_true",
        help="Permite selecao exploratoria sem aprovacao previa da GameSpecification.",
    )
    p_sel.add_argument(
        "--run-godot-tests",
        action="store_true",
        help="Exige aprovacao em tempo real da suite headless Godot do template.",
    )

    p_cmp = sub.add_parser("template-compare", help="Compara dois templates ou duas versoes.")
    p_cmp.add_argument("left_id", help="Template esquerdo.")
    p_cmp.add_argument("right_id", help="Template direito.")
    p_cmp.add_argument("--left-version", default=None, help="Versao do template esquerdo.")
    p_cmp.add_argument("--right-version", default=None, help="Versao do template direito.")

    p_dep = sub.add_parser("template-deprecate", help="Marca uma versao especifica como DEPRECATED.")
    p_dep.add_argument("template_id", help="Slug do template.")
    p_dep.add_argument("--version", required=True, help="Versao SemVer alvo.")
    p_dep.add_argument("--reason", required=True, help="Justificativa da depreciacao.")
    p_dep.add_argument("--by", default="operator", help="Responsavel pela acao.")


def handle_template_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos template-* sobre o workspace raiz do manager."""
    reg = TemplateRegistry(repo_root=manager.repo_root)

    if args.command == "template-list":
        items = reg.search_templates(
            genre=args.genre,
            engine=args.engine,
            platform=args.platform,
            include_deprecated=args.include_deprecated,
        )
        return {"count": len(items), "templates": items}

    if args.command == "template-show":
        return reg.get_template(args.template_id, version=args.version, include_deprecated=True)

    if args.command == "template-validate":
        return reg.validate_template(
            args.template_id,
            version=args.version,
            run_godot_tests=args.run_godot_tests,
        )

    if args.command == "template-select":
        return reg.select_template_for_project(
            manager,
            args.project_id,
            require_approved_spec=not args.allow_unapproved,
            prefer_template_id=args.prefer,
            run_godot_tests=args.run_godot_tests,
        )

    if args.command == "template-compare":
        return reg.compare_templates(
            args.left_id,
            args.left_version,
            args.right_id,
            args.right_version,
        )

    if args.command == "template-deprecate":
        return reg.deprecate_template(
            args.template_id,
            args.version,
            args.reason,
            deprecated_by=args.by,
        )

    raise ValueError(f"Comando de template nao suportado: {args.command}")
