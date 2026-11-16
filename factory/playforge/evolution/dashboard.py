"""Dashboard executivo consolidado multi-projeto da PlayForge Factory (Fase 11)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from factory.playforge.registry import ProjectManager


class FactoryDashboard:
    """Consolida telemetria, status de spec/assets/QA/build de todos os projetos registrados."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    def summarize(self) -> dict[str, Any]:
        projects = self.manager.list_projects()
        rows: list[dict[str, Any]] = []

        for p in projects:
            pid = p["project_id"]
            ws = self.manager.repo_root if p.get("protected") else self.manager.resolve_game_path(pid, ".")
            spec_present = (ws / "specs" / "game_specification.json").is_file()

            asset_count = 0
            reg_file = ws / "assets" / "asset_registry.json"
            if reg_file.is_file():
                try:
                    asset_count = len(json.loads(reg_file.read_text(encoding="utf-8")).get("assets", {}))
                except json.JSONDecodeError:
                    asset_count = 0

            qa_passed: bool | None = None
            qa_file = ws / "qa" / "qa_report.json"
            if qa_file.is_file():
                try:
                    qa_passed = bool(json.loads(qa_file.read_text(encoding="utf-8")).get("passed"))
                except json.JSONDecodeError:
                    qa_passed = False

            build_targets: list[str] = []
            builds_dir = ws / "builds"
            if builds_dir.is_dir():
                for mf in sorted(builds_dir.rglob("build_manifest.json")):
                    try:
                        tgt = json.loads(mf.read_text(encoding="utf-8")).get("target")
                        if tgt and tgt not in build_targets:
                            build_targets.append(str(tgt))
                    except json.JSONDecodeError:
                        continue

            rows.append(
                {
                    "project_id": pid,
                    "name": p.get("name"),
                    "kind": p.get("kind"),
                    "protected": bool(p.get("protected", False)),
                    "engine": p.get("engine"),
                    "stage": p.get("stage"),
                    "version": p.get("version"),
                    "spec_present": spec_present,
                    "asset_count": asset_count,
                    "qa_passed": qa_passed,
                    "build_targets": build_targets,
                }
            )

        return {
            "dashboard_schema_version": 1,
            "generated_at": self.manager.now_timestamp(),
            "project_count": len(rows),
            "projects": rows,
            "paid_services_enabled": False,
        }
