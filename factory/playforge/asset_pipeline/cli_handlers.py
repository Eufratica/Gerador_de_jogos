"""Handlers e subcomandos CLI do Pipeline de Assets e Audio (Fase 7)."""
from __future__ import annotations

import argparse
from typing import Any

from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.asset_pipeline.schemas import ASSET_TYPES, ORIGIN_TYPES, AssetValidationError
from factory.playforge.asset_pipeline.synthesizer import inspect_media_toolchain
from factory.playforge.asset_pipeline.validator import inspect_wav
from factory.playforge.registry import ProjectManager
from factory.playforge.security_utils import is_forbidden_secret_relpath


def register_asset_audio_subcommands(sub: argparse._SubParsersAction[Any]) -> None:
    """Registra subcomandos asset-* e audio-* na CLI principal da PlayForge."""
    sub.add_parser(
        "asset-toolchain",
        help="Audita ferramentas gratuitas de midia e sintetizadores locais disponiveis.",
    )

    p_pack = sub.add_parser(
        "asset-generate-pack",
        help="Sintetiza e registra pack inicial de sprites PNG e SFX/BGM WAV sem custos.",
    )
    p_pack.add_argument("project_id", help="Slug do projeto alvo.")

    p_pack3d = sub.add_parser(
        "asset-generate-3d-pack",
        help="Sintetiza e registra pack 3D/PBR (glTF, GLB, OBJ, rig + mapas PBR) sem custos.",
    )
    p_pack3d.add_argument("project_id", help="Slug do projeto alvo.")

    sub.add_parser("tool-status", help="Status de ferramentas gratuitas e opcionais por dominio (Blender, FFmpeg...).")

    p_reg = sub.add_parser(
        "asset-register",
        help="Valida formato, SHA-256, proveniencia e licenca de um arquivo em assets/ ou audio/.",
    )
    p_reg.add_argument("project_id", help="Slug do projeto alvo.")
    p_reg.add_argument("--asset-id", required=True, help="Slug identificador do asset.")
    p_reg.add_argument("--name", required=True, help="Nome legivel do asset.")
    p_reg.add_argument("--type", dest="asset_type", required=True, choices=list(ASSET_TYPES), help="Tipo de asset.")
    p_reg.add_argument("--path", dest="rel_path", required=True, help="Caminho relativo (assets/... ou audio/...).")
    p_reg.add_argument("--license", dest="license_name", required=True, help="Licenca verificada (ex.: CC0-1.0, MIT).")
    p_reg.add_argument("--origin", default="created_in_house", choices=list(ORIGIN_TYPES), help="Origem do asset.")
    p_reg.add_argument("--author", default="PlayForge Studio", help="Autor ou provedor.")
    p_reg.add_argument("--tool", default="manual-import", help="Ferramenta gratuita utilizada.")
    p_reg.add_argument("--model", default="n/a", help="Modelo utilizado (obrigatorio se IA local).")
    p_reg.add_argument("--prompt-or-seed", default="n/a", help="Prompt/seed utilizado (obrigatorio se IA local).")
    p_reg.add_argument(
        "--restrictions",
        default="Comercial liberado mediante registro de proveniencia",
        help="Condicoes e atribuicoes da licenca.",
    )

    p_list = sub.add_parser("asset-list", help="Lista assets registrados no AssetRegistry de project_id.")
    p_list.add_argument("project_id", help="Slug do projeto alvo.")
    p_list.add_argument("--type", dest="asset_type", default=None, choices=list(ASSET_TYPES), help="Filtra por tipo.")

    p_audit = sub.add_parser(
        "asset-audit",
        help="Audita hashes, licencas, ausencia de orfaos/temporarios e opcionalmente Godot headless.",
    )
    p_audit.add_argument("project_id", help="Slug do projeto alvo.")
    p_audit.add_argument(
        "--verify-godot",
        action="store_true",
        help="Executa decodificacao real no Godot 4.4 headless (Image e AudioStreamWAV).",
    )

    p_wav = sub.add_parser("audio-inspect", help="Mede parametros tecnicos e clipping de um arquivo WAV.")
    p_wav.add_argument("project_id", help="Slug do projeto alvo.")
    p_wav.add_argument("rel_path", help="Caminho relativo dentro do projeto (audio/...).")
    p_wav.add_argument("--allow-clipping", action="store_true", help="Nao falha se houver clipping; apenas reporta.")


def handle_asset_audio_command(args: argparse.Namespace, manager: ProjectManager) -> dict[str, Any]:
    """Despacha subcomandos asset-* e audio-*."""
    if args.command == "asset-toolchain":
        return inspect_media_toolchain(repo_root=manager.repo_root)

    if args.command == "tool-status":
        tc = inspect_media_toolchain(repo_root=manager.repo_root)
        return {
            "tool_orchestration": tc["tool_orchestration"],
            "external_cli_tools": tc["external_cli_tools"],
            "paid_services_enabled": tc["paid_services_enabled"],
        }

    reg = AssetRegistry(manager)

    if args.command == "asset-generate-3d-pack":
        return reg.generate_3d_pbr_pack(args.project_id)

    if args.command == "asset-generate-pack":
        return reg.generate_default_pack(args.project_id)

    if args.command == "asset-register":
        return reg.register_existing_asset(
            project_id=args.project_id,
            asset_id=args.asset_id,
            name=args.name,
            asset_type=args.asset_type,
            rel_path=args.rel_path,
            license_name=args.license_name,
            origin=args.origin,
            author_or_provider=args.author,
            tool_used=args.tool,
            model_used=args.model,
            prompt_or_seed=args.prompt_or_seed,
            restrictions=args.restrictions,
        )

    if args.command == "asset-list":
        items = reg.list_assets(args.project_id, asset_type=args.asset_type)
        return {"project_id": args.project_id, "count": len(items), "assets": items}

    if args.command == "asset-audit":
        return reg.audit_project_assets(args.project_id, verify_godot=args.verify_godot)

    if args.command == "audio-inspect":
        if is_forbidden_secret_relpath(args.rel_path):
            raise AssetValidationError(f"Caminho proibido: '{args.rel_path}'.")
        target = manager.resolve_game_path(args.project_id, args.rel_path)
        if not target.is_file():
            raise AssetValidationError(f"Arquivo WAV nao encontrado em '{args.project_id}': '{args.rel_path}'.")
        metrics = inspect_wav(target.read_bytes(), reject_clipping=not args.allow_clipping)
        metrics["project_id"] = args.project_id
        metrics["rel_path"] = args.rel_path
        return metrics

    raise ValueError(f"Comando asset/audio nao suportado: {args.command}")
