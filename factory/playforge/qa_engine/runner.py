"""Orquestrador multi-projeto do QA Engine (4 pilares + profiling real Godot) (Fase 8)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.asset_pipeline.schemas import AssetError
from factory.playforge.asset_pipeline.synthesizer import resolve_factory_godot_bin
from factory.playforge.models import ANCHOR_PROJECT_ID
from factory.playforge.registry import ProjectManager, _atomic_write_json, validate_project_id

from .balance_verifier import BalanceVerifierEngine
from .schemas import QA_REPORT_SCHEMA_VERSION, QAValidationError
from .static_analyzer import (
    StaticAnalyzer,
    collect_project_files,
    ensure_auditable_project,
    safe_log_qa_event,
    stage_isolated_godot_project,
)

_MAIN_SCENE_RE = re.compile(r'^\s*run/main_scene\s*=\s*"(res://[^"]+)"', re.MULTILINE)
_PROFILE_MARKER = "PLAYFORGE_QA_PROFILE:"


def _isolated_godot_env(user_home: Path) -> dict[str, str]:
    user_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["APPDATA"] = str(user_home)
    env["LOCALAPPDATA"] = str(user_home)
    env["USERPROFILE"] = str(user_home)
    env["HOME"] = str(user_home)
    return env


def _build_headless_probe_gd(main_scene_res: str, frames: int) -> str:
    safe_frames = max(1, min(120, int(frames)))
    return f'''extends SceneTree

func _initialize() -> void:
\tvar orphan_before: int = int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
\tvar t_boot0: int = Time.get_ticks_usec()
\tvar scene_res := ResourceLoader.load("{main_scene_res}")
\tif scene_res == null or not (scene_res is PackedScene):
\t\tprinterr("QA_PROBE_FAIL: cannot load main_scene: {main_scene_res}")
\t\tquit(1)
\t\treturn
\tvar inst: Node = (scene_res as PackedScene).instantiate()
\tif inst == null:
\t\tprinterr("QA_PROBE_FAIL: main_scene returned null instance")
\t\tquit(1)
\t\treturn
\troot.add_child(inst)
\tawait process_frame
\tvar boot_ms: float = float(Time.get_ticks_usec() - t_boot0) / 1000.0

\tvar t_frames0: int = Time.get_ticks_usec()
\tfor _i in range({safe_frames}):
\t\tawait process_frame
\tvar frames_total_ms: float = float(Time.get_ticks_usec() - t_frames0) / 1000.0
\tvar frame_ms_avg: float = frames_total_ms / float({safe_frames})

\tvar static_mem_bytes: float = float(Performance.get_monitor(Performance.MEMORY_STATIC))
\tvar active_nodes: int = int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))
\tvar fps: float = float(Performance.get_monitor(Performance.TIME_FPS))

\tinst.queue_free()
\tawait process_frame
\tawait process_frame
\tvar orphan_after: int = int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
\tvar orphan_delta: int = maxi(0, orphan_after - orphan_before)

\tvar payload := {{
\t\t"main_scene": "{main_scene_res}",
\t\t"frames_stepped": {safe_frames},
\t\t"boot_ms": snappedf(boot_ms, 0.01),
\t\t"frame_ms_avg": snappedf(frame_ms_avg, 0.01),
\t\t"static_memory_bytes": int(static_mem_bytes),
\t\t"active_node_count": active_nodes,
\t\t"orphan_nodes_after_free": orphan_after,
\t\t"orphan_nodes_delta": orphan_delta,
\t\t"fps": snappedf(fps, 0.01)
\t}}
\tprint("{_PROFILE_MARKER}" + JSON.stringify(payload))
\tquit(0 if orphan_delta == 0 and orphan_after == 0 else 1)
'''


class QAEngine:
    """Executor integrado dos 4 pilares de QA da PlayForge Factory (Fase 8)."""

    def __init__(
        self,
        manager: ProjectManager,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.manager = manager
        self._clock = clock
        self.static_analyzer = StaticAnalyzer(manager)
        self.balance_engine = BalanceVerifierEngine(manager, clock=clock)
        self.asset_registry = AssetRegistry(manager, clock=clock)

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _resolve_godot_or_fail(self, godot_bin: Path | None) -> Path:
        resolved = godot_bin if godot_bin is not None else resolve_factory_godot_bin(self.manager.repo_root)
        if resolved is None or not Path(resolved).is_file():
            raise QAValidationError(
                "Binario Godot CLI nao encontrado para execucao headless (GT-02)."
            )
        return Path(resolved)

    def _discover_godot_test_runners(
        self,
        project_id: str,
        project_files: list[tuple[str, Path]],
    ) -> list[tuple[str, list[str]]]:
        if project_id == ANCHOR_PROJECT_ID:
            return [
                ("res://tests/unit/run_unit_tests.gd", []),
                ("res://tests/integration/run_action_verifier.gd", []),
                ("res://tests/integration/verify_engine_boot.gd", ["--save-path={SAVE_PATH}"]),
            ]

        runners: list[tuple[str, list[str]]] = []
        for rel, path in project_files:
            if not (rel.startswith("tests/") and path.suffix.lower() == ".gd"):
                continue
            head = path.read_text(encoding="utf-8", errors="replace")[:400]
            if re.search(r"^\s*extends\s+SceneTree\b", head, re.MULTILINE):
                runners.append((f"res://{rel}", []))
        return runners

    def _run_godot_script(
        self,
        *,
        godot_bin: Path,
        proj_dir: Path,
        user_home: Path,
        script_target: str,
        extra_user_args: list[str] | None = None,
        timeout_s: float = 30.0,
    ) -> tuple[int, str]:
        cmd = [
            str(godot_bin),
            "--headless",
            "--no-header",
            "--path",
            str(proj_dir),
            "--script",
            script_target,
        ]
        if extra_user_args:
            cmd.extend(["--", *extra_user_args])
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=_isolated_godot_env(user_home),
            check=False,
        )
        combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
        return proc.returncode, combined

    def run_godot_suites(
        self,
        project_id: str,
        *,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Executa suites GDScript SceneTree do projeto em copia isolada headless."""
        validate_project_id(project_id)
        _, project_files = collect_project_files(self.manager, project_id)
        runners = self._discover_godot_test_runners(project_id, project_files)
        if not runners:
            return {
                "passed": False,
                "suites": [],
                "reason": f"Nenhum script runner (extends SceneTree) encontrado em tests/ para '{project_id}'.",
            }

        resolved_bin = self._resolve_godot_or_fail(godot_bin)
        suite_results: list[dict[str, Any]] = []
        all_ok = True

        with tempfile.TemporaryDirectory(prefix="playforge_qa_suites_") as tmp:
            tmp_root = Path(tmp)
            proj_dir = stage_isolated_godot_project(self.manager, project_id, tmp_root / "project")
            user_home = tmp_root / "user_home"
            save_path = (tmp_root / "boot_save.json").as_posix()

            for script_res, raw_args in runners:
                resolved_args = [arg.replace("{SAVE_PATH}", save_path) for arg in raw_args]
                code, output = self._run_godot_script(
                    godot_bin=resolved_bin,
                    proj_dir=proj_dir,
                    user_home=user_home,
                    script_target=script_res,
                    extra_user_args=resolved_args,
                )
                failed_nonzero = bool(re.search(r"Failed:\s*[1-9]\d*", output))
                script_err = "SCRIPT ERROR:" in output
                passed = (code == 0) and not failed_nonzero and not script_err
                if not passed:
                    all_ok = False
                suite_results.append(
                    {
                        "script": script_res,
                        "passed": passed,
                        "returncode": code,
                        "output": output,
                    }
                )

        return {"passed": all_ok, "suites": suite_results}

    def profile_project_godot(
        self,
        project_id: str,
        *,
        frames: int = 10,
        godot_bin: Path | None = None,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Executa probe real de MainScene + Performance no Godot 4.4 headless (GT-02)."""
        validate_project_id(project_id)
        _, project_files = collect_project_files(self.manager, project_id)
        file_map = {rel: path for rel, path in project_files}
        pg_path = file_map.get("project.godot")
        if pg_path is None:
            raise QAValidationError(f"project.godot ausente para '{project_id}'.")

        match = _MAIN_SCENE_RE.search(pg_path.read_text(encoding="utf-8", errors="replace"))
        if not match:
            raise QAValidationError(f"run/main_scene nao definido em project.godot de '{project_id}'.")
        main_scene_res = match.group(1)

        resolved_bin = self._resolve_godot_or_fail(godot_bin)
        with tempfile.TemporaryDirectory(prefix="playforge_qa_prof_") as tmp:
            tmp_root = Path(tmp)
            proj_dir = stage_isolated_godot_project(self.manager, project_id, tmp_root / "project")
            probe_path = proj_dir / "__playforge_qa_probe.gd"
            probe_path.write_text(_build_headless_probe_gd(main_scene_res, frames), encoding="utf-8")

            code, output = self._run_godot_script(
                godot_bin=resolved_bin,
                proj_dir=proj_dir,
                user_home=tmp_root / "user_home",
                script_target="res://__playforge_qa_probe.gd",
            )

        metrics: dict[str, Any] = {}
        for line in output.splitlines():
            if line.startswith(_PROFILE_MARKER):
                raw_json = line[len(_PROFILE_MARKER) :].strip()
                metrics = json.loads(raw_json)
                break

        has_script_err = "SCRIPT ERROR:" in output
        passed = (
            code == 0
            and not has_script_err
            and bool(metrics)
            and int(metrics.get("orphan_nodes_after_free", 1)) == 0
            and int(metrics.get("orphan_nodes_delta", 1)) == 0
        )
        result = {
            "passed": passed,
            "project_id": project_id,
            "returncode": code,
            "godot_bin": str(resolved_bin),
            "metrics": metrics,
            "script_errors_detected": has_script_err,
            "raw_output": output if not passed else "",
        }
        if strict and not passed:
            raise QAValidationError(
                f"Profiling Godot headless falhou em '{project_id}' (code={code}): {output}"
            )
        return result

    def run_qa_pipeline(
        self,
        project_id: str,
        *,
        with_godot: bool = True,
        with_assets: bool = True,
        require_assets: bool = False,
        genre: str | None = None,
        seed: int = 2026,
        frames: int = 10,
        godot_bin: Path | None = None,
        save_report: bool = True,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Executa os 4 pilares do QA Engine sobre project_id e consolida specs/qa_report.json."""
        ensure_auditable_project(self.manager, project_id)

        static_res = self.static_analyzer.audit_project(project_id)
        balance_res = self.balance_engine.verify_project_balance(
            project_id,
            genre=genre,
            seed=seed,
            run_godot=(with_godot and project_id == ANCHOR_PROJECT_ID),
            save_report=save_report,
            strict=False,
        )

        godot_suites_res: dict[str, Any]
        profile_res: dict[str, Any]
        if with_godot:
            try:
                godot_suites_res = self.run_godot_suites(project_id, godot_bin=godot_bin)
            except QAValidationError as exc:
                godot_suites_res = {"passed": False, "suites": [], "error": str(exc)}
            try:
                profile_res = self.profile_project_godot(
                    project_id,
                    frames=frames,
                    godot_bin=godot_bin,
                    strict=False,
                )
            except QAValidationError as exc:
                profile_res = {"passed": False, "error": str(exc), "metrics": {}}
        else:
            godot_suites_res = {"status": "SKIPPED_BY_OPTION", "passed": True, "suites": []}
            profile_res = {"status": "SKIPPED_BY_OPTION", "passed": True, "metrics": {}}

        assets_res = self._audit_assets_pillar(
            project_id,
            with_assets=with_assets,
            require_assets=require_assets,
            verify_godot=with_godot,
            godot_bin=godot_bin,
        )

        gate_failures: list[str] = []
        if not static_res["passed"]:
            gate_failures.append(f"static ({len(static_res['violations'])} violacoes)")
        if not balance_res["passed"]:
            gate_failures.append(f"balance ({len(balance_res['findings'])} achados)")
        if with_godot and not godot_suites_res["passed"]:
            gate_failures.append("godot_suites")
        if with_godot and not profile_res["passed"]:
            gate_failures.append("godot_profile")
        if not assets_res["passed"]:
            gate_failures.append("assets")

        overall_passed = len(gate_failures) == 0
        report = {
            "qa_schema_version": QA_REPORT_SCHEMA_VERSION,
            "project_id": project_id,
            "verified_at": self._now_timestamp(),
            "passed": overall_passed,
            "failed_pillars": gate_failures,
            "pillars": {
                "static": static_res,
                "balance": balance_res,
                "godot_suites": godot_suites_res,
                "godot_profile": profile_res,
                "assets": assets_res,
            },
        }

        if save_report and project_id != ANCHOR_PROJECT_ID:
            report_path = self.manager.resolve_game_path(project_id, "specs/qa_report.json")
            _atomic_write_json(report_path, report)

        safe_log_qa_event(
            self.manager,
            "INFO" if overall_passed else "ERROR",
            "QA_PIPELINE",
            project_id=project_id,
            passed=overall_passed,
            failed_pillars=gate_failures,
        )

        if strict and not overall_passed:
            raise QAValidationError(
                f"QA Engine reprovou '{project_id}' nos pilares: {', '.join(gate_failures)}."
            )
        return report

    def _audit_assets_pillar(
        self,
        project_id: str,
        *,
        with_assets: bool,
        require_assets: bool,
        verify_godot: bool,
        godot_bin: Path | None,
    ) -> dict[str, Any]:
        if not with_assets:
            return {"status": "SKIPPED_BY_OPTION", "passed": True}

        ws_base = (
            self.manager.repo_root
            if project_id == ANCHOR_PROJECT_ID
            else self.manager.resolve_game_path(project_id, ".")
        )
        has_reg = (ws_base / "assets" / "asset_registry.json").is_file()
        has_media_files = any(
            item.is_file() and item.name not in (".gdignore", "asset_registry.json") and item.suffix.lower() != ".import"
            for folder in ("assets", "audio")
            if (ws_base / folder).is_dir()
            for item in (ws_base / folder).rglob("*")
        )

        if not has_reg and not has_media_files:
            if require_assets:
                return {
                    "status": "FAILED_MISSING_ASSET_REGISTRY",
                    "passed": False,
                    "error": "assets/asset_registry.json ausente e require_assets=True.",
                }
            return {"status": "SKIPPED_NO_ASSET_REGISTRY", "passed": True}

        try:
            return self.asset_registry.audit_project_assets(
                project_id,
                verify_godot=verify_godot,
                godot_bin=godot_bin,
            )
        except AssetError as exc:
            return {
                "status": "FAILED",
                "passed": False,
                "error": str(exc),
            }
