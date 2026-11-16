"""Engine Selection and Orchestration System (14 criterios + relatorio justificativo) (P1)."""
from __future__ import annotations

from typing import Any

from factory.playforge.ai.model_router import inspect_environment
from factory.playforge.asset_pipeline.synthesizer import inspect_media_toolchain

from .adapter import EngineAdapterRegistry
from .schemas import (
    ENGINE_SELECTION_SCHEMA_VERSION,
    SELECTION_CRITERIA,
    EngineProfileRequest,
    EngineSelectionError,
)


class EngineSelector:
    """Analisa os 14 criterios sem escolha por conveniencia e gera relatorio justificativo."""

    def __init__(self, registry: EngineAdapterRegistry) -> None:
        self.registry = registry

    def evaluate(
        self,
        request: EngineProfileRequest,
        *,
        hardware_profile: dict[str, Any] | None = None,
        media_toolchain: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request.validate()
        adapters = self.registry.list_adapters()
        if not adapters:
            raise EngineSelectionError("Nenhum EngineAdapter registrado para avaliacao.")

        hw = dict(hardware_profile) if hardware_profile is not None else inspect_environment().to_dict()
        media = dict(media_toolchain) if media_toolchain is not None else inspect_media_toolchain()

        total_weight = sum(w for _, w, _ in SELECTION_CRITERIA)
        evaluations: list[dict[str, Any]] = []

        for adapter in adapters:
            probe = adapter.probe_toolchain()
            raw_scores, reasons = adapter.score_profile(request, hw, probe)

            weighted_sum = 0.0
            criteria_details: list[dict[str, Any]] = []
            for cid, weight, label in SELECTION_CRITERIA:
                val = round(float(raw_scores.get(cid, 0.0)), 2)
                weighted_sum += val * weight
                criteria_details.append(
                    {
                        "criterion_id": cid,
                        "label": label,
                        "weight": weight,
                        "score": val,
                        "rationale": reasons.get(cid, ""),
                    }
                )

            normalized_score = round((weighted_sum / (total_weight * 10.0)) * 100.0, 2)
            host_ram = float(hw.get("total_ram_gb") or 0.0)
            host_gpu = bool(hw.get("has_dedicated_gpu", False))
            hw_compatible = host_ram >= probe.recommended_min_ram_gb and (
                not probe.requires_dedicated_gpu or host_gpu
            )
            warnings: list[str] = []
            if not probe.available:
                warnings.append(f"Toolchain '{adapter.engine_id}' nao instalada no host atual.")
            if not hw_compatible:
                warnings.append(
                    f"Hardware local ({host_ram:.2f} GB RAM, GPU dedicada={host_gpu}) abaixo do "
                    f"recomendado para '{adapter.engine_id}' ({probe.recommended_min_ram_gb:.0f} GB RAM, "
                    f"GPU dedicada={probe.requires_dedicated_gpu})."
                )

            evaluations.append(
                {
                    "engine_id": adapter.engine_id,
                    "display_name": adapter.display_name,
                    "overall_score_100": normalized_score,
                    "toolchain_installed": probe.available,
                    "hardware_compatible": hw_compatible,
                    "executable_locally_now": bool(probe.available and hw_compatible),
                    "license_summary": adapter.license_summary,
                    "supported_technologies": list(adapter.supported_technologies),
                    "probe": probe.to_dict(),
                    "warnings": warnings,
                    "criteria_breakdown": criteria_details,
                }
            )

        evaluations.sort(key=lambda item: item["overall_score_100"], reverse=True)
        top_fit = evaluations[0]
        local_candidates = [item for item in evaluations if item["executable_locally_now"]]
        executable_now = local_candidates[0]["engine_id"] if local_candidates else None

        recommended_tools = _recommend_complementary_tools(request, media)
        report: dict[str, Any] = {
            "selection_schema_version": ENGINE_SELECTION_SCHEMA_VERSION,
            "selection_policy": "WEIGHTED_14_CRITERIA_NO_BLIND_DEFAULT",
            "recommended_engine": top_fit["engine_id"],
            "recommended_engine_score": top_fit["overall_score_100"],
            "executable_locally_now": executable_now,
            "requires_external_install": not top_fit["toolchain_installed"],
            "hardware_feasible_locally": top_fit["hardware_compatible"],
            "justification_summary": (
                f"Engine selecionada por merito tecnico nos 14 criterios: '{top_fit['display_name']}' "
                f"({top_fit['overall_score_100']}/100). "
                + (
                    f"Executavel imediatamente no host local: '{executable_now}'."
                    if executable_now
                    else "Nenhuma engine ranqueada esta instalada e compativel para execucao imediata neste host."
                )
            ),
            "host_environment": {
                "total_ram_gb": hw.get("total_ram_gb"),
                "cpu_threads": hw.get("cpu_threads"),
                "has_dedicated_gpu": hw.get("has_dedicated_gpu"),
            },
            "recommended_tools": recommended_tools,
            "request_profile": request.to_dict(),
            "rankings": evaluations,
        }
        report["report_markdown"] = format_selection_report_markdown(report)
        return report

    def evaluate_from_spec(
        self,
        spec: dict[str, Any],
        *,
        hardware_profile: dict[str, Any] | None = None,
        media_toolchain: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Infere EngineProfileRequest a partir de uma GameSpecification estruturada e avalia."""
        gameplay = spec.get("core_gameplay", {}) if isinstance(spec.get("core_gameplay"), dict) else {}
        perspective = str(gameplay.get("perspective", "2D")).lower()
        camera_raw = str(gameplay.get("camera", "side-scroller")).lower()
        dim = "2d" if "2d" in perspective and "2.5" not in perspective else ("2.5d" if "2.5" in perspective else "3d-indie")
        cam = (
            "third-person-cinematic"
            if "third" in camera_raw
            else ("first-person" if "first" in camera_raw else ("isometric" if "iso" in camera_raw else ("top-down" if "top" in camera_raw else "side-scroller")))
        )
        chars = spec.get("characters", [])
        char_count = max(len(chars) if isinstance(chars, list) else 1, 1)
        platforms = tuple(str(p) for p in spec.get("target_platforms", ["windows"]))
        req = EngineProfileRequest(
            genre=str(spec.get("genre", "action-rpg")),
            world_dimension=dim,
            camera_type=cam,
            character_count=char_count,
            animation_complexity="basic-2d" if dim == "2d" else "standard-3d",
            physics_needs="deterministic-2d" if dim == "2d" else "rigidbody-3d",
            graphic_quality="pixel-vector-2d" if dim == "2d" else "stylized-3d",
            target_platforms=platforms,
            expected_performance="mobile-60fps-low-spec" if "android" in platforms else "desktop-60fps",
            development_complexity="medium",
        )
        return self.evaluate(req, hardware_profile=hardware_profile, media_toolchain=media_toolchain)


def _recommend_complementary_tools(
    request: EngineProfileRequest,
    media: dict[str, Any],
) -> list[dict[str, Any]]:
    ext = media.get("external_cli_tools", {})
    tools: list[dict[str, Any]] = []
    if request.world_dimension in ("3d-indie", "3d-aaa-large") or request.animation_complexity in ("standard-3d", "advanced-mocap-cinematic"):
        tools.append(
            {
                "tool": "blender",
                "role": "Modelagem 3D, escultura, UV, retopologia, rigging e PBR (GPL gratuito)",
                "installed": bool(ext.get("blender")),
                "path": ext.get("blender"),
            }
        )
    tools.append(
        {
            "tool": "ffmpeg",
            "role": "Processamento e conversao de audio WAV/OGG/MP3 (LGPL/GPL gratuito)",
            "installed": bool(ext.get("ffmpeg")),
            "path": ext.get("ffmpeg"),
        }
    )
    tools.append(
        {
            "tool": "native-audio-or-fmod-optional",
            "role": "Audio nativo da engine (padrao zero-cost; FMOD/Wwise apenas opcionais)",
            "installed": True,
            "path": "builtin",
        }
    )
    return tools


def format_selection_report_markdown(report: dict[str, Any]) -> str:
    """Formata o relatorio justificativo de selecao em Markdown legivel para humanos e OpenSpec."""
    lines = [
        "# Relatorio de Selecao de Engine (`Engine Selection System`)",
        "",
        f"- **Engine Recomendada (Merito Tecnico):** `{report['recommended_engine']}` ({report['recommended_engine_score']}/100)",
        f"- **Executavel Localmente Agora:** `{report['executable_locally_now'] or 'NENHUMA'}`",
        f"- **Host:** `{report['host_environment'].get('total_ram_gb')} GB RAM` | `{report['host_environment'].get('cpu_threads')} threads` | GPU dedicada=`{report['host_environment'].get('has_dedicated_gpu')}`",
        f"- **Justificativa:** {report['justification_summary']}",
        "",
        "## Ranking Multi-Engine",
        "",
        "| Engine | Score (/100) | Instalada no Host | Compativel com Hardware | Executavel Localmente |",
        "| :--- | ---: | :--- | :--- | :--- |",
    ]
    for item in report["rankings"]:
        lines.append(
            f"| `{item['engine_id']}` | {item['overall_score_100']:.2f} | {item['toolchain_installed']} | {item['hardware_compatible']} | {item['executable_locally_now']} |"
        )
    lines.append("")
    lines.append("## Detalhamento dos 14 Criterios (Engine #1)")
    lines.append("")
    top = report["rankings"][0]
    for crit in top["criteria_breakdown"]:
        lines.append(
            f"- **{crit['label']}** (peso `{crit['weight']}`): `{crit['score']}/10` — {crit['rationale']}"
        )
    if top["warnings"]:
        lines.append("")
        lines.append("## Alertas / Bloqueios")
        for warn in top["warnings"]:
            lines.append(f"- {warn}")
    return "\n".join(lines) + "\n"
