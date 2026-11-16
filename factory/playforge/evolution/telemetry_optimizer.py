"""Telemetria local e consultor de otimizacao assistida com aprovacao humana (Fase 11)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from factory.playforge.models import FactoryError
from factory.playforge.registry import ProjectManager, _atomic_write_json

OPTIMIZATION_REPORT_SCHEMA_VERSION = 1


class OptimizationAdvisor:
    """Coleta metricas reais do workspace e propoe otimizacoes (nunca altera codigo/balanceamento)."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    def analyze_project(self, project_id: str) -> dict[str, Any]:
        project = self.manager.require_mutable_project(project_id)
        ws = self.manager.resolve_game_path(project_id, ".")

        spec_path = ws / "specs" / "game_specification.json"
        spec: dict[str, Any] = {}
        if spec_path.is_file():
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                spec = {}

        tech = spec.get("technical_requirements", {}) if isinstance(spec.get("technical_requirements"), dict) else {}
        ram_budget_mb = int(tech.get("max_ram_mb", 256) or 256)
        target_fps = int(tech.get("target_fps", 60) or 60)

        reg_path = ws / "assets" / "asset_registry.json"
        assets: list[dict[str, Any]] = []
        if reg_path.is_file():
            try:
                reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
                assets = list(reg_data.get("assets", {}).values())
            except json.JSONDecodeError:
                assets = []

        total_asset_bytes = sum(int(a.get("byte_size", 0) or 0) for a in assets)
        script_files = [
            p
            for p in ws.rglob("*")
            if p.is_file() and p.suffix.lower() in (".gd", ".cs", ".cpp", ".h")
        ]
        qa_path = ws / "qa" / "qa_report.json"
        qa_passed: bool | None = None
        if qa_path.is_file():
            try:
                qa_passed = bool(json.loads(qa_path.read_text(encoding="utf-8")).get("passed"))
            except json.JSONDecodeError:
                qa_passed = False

        recommendations: list[dict[str, Any]] = []
        for asset in assets:
            fmt = str(asset.get("format", "")).lower()
            bsize = int(asset.get("byte_size", 0) or 0)
            if fmt == "wav" and bsize > 512_000 and str(asset.get("asset_type")) == "bgm":
                recommendations.append(
                    {
                        "id": f"opt-audio-stream-{asset['asset_id']}",
                        "category": "audio_compression",
                        "severity": "medium",
                        "recommendation": f"Converter BGM '{asset['asset_id']}' ({bsize} bytes WAV) para OGG streaming.",
                        "requires_human_approval": True,
                    }
                )
            if fmt in ("gltf", "glb", "obj") and int(asset.get("lod_level", 0) or 0) == 0 and bsize > 256_000:
                recommendations.append(
                    {
                        "id": f"opt-lod-{asset['asset_id']}",
                        "category": "mesh_lod",
                        "severity": "medium",
                        "recommendation": f"Gerar LOD1/LOD2 para malha 3D '{asset['asset_id']}' em cenas extensas.",
                        "requires_human_approval": True,
                    }
                )

        if target_fps >= 60 and len(script_files) >= 50:
            recommendations.append(
                {
                    "id": "opt-object-pooling",
                    "category": "runtime_cpu",
                    "severity": "low",
                    "recommendation": "Avaliar Object Pooling para projeteis/inimigos visando estabilidade a 60 FPS.",
                    "requires_human_approval": True,
                }
            )
        if qa_passed is not True:
            recommendations.append(
                {
                    "id": "opt-run-qa-baseline",
                    "category": "quality_baseline",
                    "severity": "high",
                    "recommendation": "Executar 'qa-run <project_id> --strict' para estabelecer linha de base de frames e orfaos.",
                    "requires_human_approval": True,
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "id": "opt-baseline-healthy",
                    "category": "baseline_ok",
                    "severity": "info",
                    "recommendation": "Telemetria dentro do orcamento configurado; manter monitoramento apos proximas mudancas.",
                    "requires_human_approval": False,
                }
            )

        report: dict[str, Any] = {
            "optimization_schema_version": OPTIMIZATION_REPORT_SCHEMA_VERSION,
            "project_id": project_id,
            "engine": project.get("engine"),
            "analyzed_at": self.manager.now_timestamp(),
            "auto_applied": False,
            "requires_human_approval_for_changes": True,
            "telemetry": {
                "target_fps": target_fps,
                "max_ram_mb": ram_budget_mb,
                "asset_count": len(assets),
                "total_asset_bytes": total_asset_bytes,
                "script_file_count": len(script_files),
                "qa_passed": qa_passed,
            },
            "recommendations": recommendations,
        }
        _atomic_write_json(ws / "qa" / "optimization_recommendations.json", report)
        self.manager.log_event(
            "INFO",
            "OPTIMIZATION_REPORT_GENERATED",
            project_id=project_id,
            recommendation_count=len(recommendations),
        )
        return report
