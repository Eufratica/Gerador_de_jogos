"""Handlers CLI do Build Manager (Fase 10)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.registry import ProjectManager

from .builder import BuildManager
from .schemas import SUPPORTED_BUILD_TARGETS


def register_build_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    sub.add_parser("build-toolchains", help="Detecta toolchains reais de export/build no host.")

    p_pkg = sub.add_parser("build-package", help="Gera pacote auditavel (hashes + manifesto) para um alvo.")
    p_pkg.add_argument("project_id")
    p_pkg.add_argument("--target", required=True, choices=SUPPORTED_BUILD_TARGETS)
    p_pkg.add_argument("--version", default=None)
    p_pkg.add_argument("--require-native", action="store_true", help="Falha se nao houver export nativo (bloqueia bundle estrutural).")

    p_ver = sub.add_parser("build-verify", help="Reverifica hashes do artefato contra o manifesto.")
    p_ver.add_argument("project_id")
    p_ver.add_argument("--target", required=True, choices=SUPPORTED_BUILD_TARGETS)
    p_ver.add_argument("--version", required=True)

    p_app = sub.add_parser("build-approve-release", help="Registra aprovacao humana de release (sem publicar).")
    p_app.add_argument("project_id")
    p_app.add_argument("--target", required=True, choices=SUPPORTED_BUILD_TARGETS)
    p_app.add_argument("--version", required=True)
    p_app.add_argument("--approver", required=True)
    p_app.add_argument("--notes", required=True)


def handle_build_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    bm = BuildManager(manager)
    if args.command == "build-toolchains":
        return bm.probe_build_toolchains()
    if args.command == "build-package":
        return bm.build_target(
            args.project_id, args.target, version=args.version, allow_structural_bundle=not args.require_native
        )
    if args.command == "build-verify":
        return bm.verify_build(args.project_id, args.version, args.target)
    if args.command == "build-approve-release":
        return bm.approve_release(
            args.project_id, args.version, args.target, approver=args.approver, notes=args.notes
        )
    raise ValueError(f"Comando build nao suportado: {args.command}")
