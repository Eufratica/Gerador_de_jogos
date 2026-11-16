"""Testes do Engine Selection and Orchestration System e Spec Schema v2 (Incremento P1)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from factory.playforge.cli import main as playforge_cli_main
from factory.playforge.engine_orchestrator import (
    SELECTION_CRITERIA,
    EngineAdapter,
    EngineProfileRequest,
    EngineScaffoldResult,
    EngineSelectionError,
    EngineSelector,
    EngineTestResult,
    EngineToolchainUnavailableError,
    EngineValidationResult,
    GodotEngineAdapter,
    ToolchainProbeResult,
    UnityEngineAdapter,
    UnrealEngineAdapter,
    create_default_orchestrator,
)
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.validator import SpecificationValidator, ValidationError


class _DummyCustomAdapter(EngineAdapter):
    engine_id = "love2d-custom"
    display_name = "Love2D Custom Test Adapter"
    supported_dimensions = ("2d",)
    supported_technologies = ("Lua", "Custom 2D Loop")
    license_summary = "zlib (Open Source)"

    def probe_toolchain(self) -> ToolchainProbeResult:
        return ToolchainProbeResult(
            engine_id=self.engine_id,
            display_name=self.display_name,
            available=False,
            executable_path=None,
            version=None,
            license_type="zlib",
            recommended_min_ram_gb=1.0,
            requires_dedicated_gpu=False,
            headless_supported=False,
        )

    def scaffold_project(self, project_dir: Path, spec: dict[str, Any]) -> EngineScaffoldResult:
        return EngineScaffoldResult(
            engine_id=self.engine_id,
            project_dir=str(project_dir),
            files_written=(),
            executable_ready=False,
        )

    def validate_project(self, project_dir: Path) -> EngineValidationResult:
        return EngineValidationResult(
            engine_id=self.engine_id,
            passed=True,
            checked_files=(),
        )

    def run_tests(self, project_dir: Path) -> EngineTestResult:
        raise EngineToolchainUnavailableError("Custom adapter sem runtime.")

    def score_profile(self, request, hardware_profile, probe):
        scores = {cid: 5.0 for cid, _, _ in SELECTION_CRITERIA}
        reasons = {cid: "Pontuacao neutra customizada." for cid, _, _ in SELECTION_CRITERIA}
        return scores, reasons


class EngineOrchestratorTests(unittest.TestCase):
    def test_14_criteria_exact_definition(self) -> None:
        self.assertEqual(len(SELECTION_CRITERIA), 14)
        for cid, weight, label in SELECTION_CRITERIA:
            self.assertTrue(cid)
            self.assertGreater(weight, 0.0)
            self.assertTrue(label)

    def test_select_prefers_godot_for_2d_open_source_low_spec(self) -> None:
        orchestrator = create_default_orchestrator(repo_root=REPO_ROOT)
        selector = EngineSelector(orchestrator)
        req = EngineProfileRequest(
            genre="platformer",
            world_dimension="2d",
            camera_type="side-scroller",
            character_count=3,
            animation_complexity="basic-2d",
            physics_needs="deterministic-2d",
            graphic_quality="pixel-vector-2d",
            target_platforms=("windows", "linux", "android"),
            expected_performance="mobile-60fps-low-spec",
            development_complexity="low-mvp",
            licensing_preference="open-source-mit",
            automation_preference="headless-cli-priority",
            target_ram_budget_mb=256,
        )
        report = selector.evaluate(
            req,
            hardware_profile={"total_ram_gb": 11.74, "cpu_threads": 8, "has_dedicated_gpu": False},
        )
        self.assertEqual(report["recommended_engine"], "godot")
        self.assertEqual(report["executable_locally_now"], "godot")
        self.assertEqual(len(report["rankings"]), 3)
        self.assertEqual(len(report["rankings"][0]["criteria_breakdown"]), 14)
        self.assertIn("Godot", report["report_markdown"])

    def test_select_prefers_unity_for_csharp_modular_crossplatform(self) -> None:
        orchestrator = create_default_orchestrator(repo_root=REPO_ROOT)
        selector = EngineSelector(orchestrator)
        req = EngineProfileRequest(
            genre="tactical-rpg",
            world_dimension="3d-indie",
            camera_type="isometric",
            character_count=12,
            animation_complexity="standard-3d",
            physics_needs="rigidbody-3d",
            graphic_quality="stylized-3d",
            target_platforms=("windows", "android", "ios", "web"),
            expected_performance="desktop-60fps",
            development_complexity="medium",
            licensing_preference="free-royalty-ok",
            automation_preference="standard-ci",
            require_csharp=True,
        )
        report = selector.evaluate(
            req,
            hardware_profile={"total_ram_gb": 16.0, "cpu_threads": 8, "has_dedicated_gpu": False},
        )
        self.assertEqual(report["recommended_engine"], "unity")

    def test_select_prefers_unreal_for_aaa_cinematic_3d_and_flags_hw_limits(self) -> None:
        orchestrator = create_default_orchestrator(repo_root=REPO_ROOT)
        selector = EngineSelector(orchestrator)
        req = EngineProfileRequest(
            genre="action-adventure-3d",
            world_dimension="3d-aaa-large",
            camera_type="third-person-cinematic",
            character_count=30,
            animation_complexity="advanced-mocap-cinematic",
            physics_needs="advanced-destruction-cloth",
            graphic_quality="photorealistic-lumen-nanite",
            target_platforms=("windows", "linux"),
            expected_performance="high-end-gpu-60fps",
            development_complexity="aaa-scale",
            licensing_preference="free-royalty-ok",
            automation_preference="standard-ci",
        )
        # Em workstation alvo (32 GB + GPU DX12), Unreal lidera com clareza
        report_target = selector.evaluate(
            req,
            hardware_profile={"total_ram_gb": 32.0, "cpu_threads": 16, "has_dedicated_gpu": True},
        )
        self.assertEqual(report_target["recommended_engine"], "unreal")
        self.assertTrue(report_target["hardware_feasible_locally"])

        # No host atual (11.74 GB RAM, GPU integrada), o sistema deve alertar explicitamente sobre hardware insuficiente para Unreal
        report_host = selector.evaluate(
            req,
            hardware_profile={"total_ram_gb": 11.74, "cpu_threads": 8, "has_dedicated_gpu": False},
        )
        unreal_entry = next(r for r in report_host["rankings"] if r["engine_id"] == "unreal")
        self.assertFalse(unreal_entry["hardware_compatible"])
        self.assertTrue(any("Hardware local" in w for w in unreal_entry["warnings"]))

    def test_invalid_profile_request_fails_closed(self) -> None:
        bad_req = EngineProfileRequest(
            genre="rpg",
            world_dimension="4d-unknown",
            camera_type="side-scroller",
            character_count=1,
            animation_complexity="basic-2d",
            physics_needs="deterministic-2d",
            graphic_quality="pixel-vector-2d",
            target_platforms=("windows",),
            expected_performance="desktop-60fps",
            development_complexity="low-mvp",
        )
        with self.assertRaises(EngineSelectionError):
            bad_req.validate()

    def test_registry_extensibility_allows_custom_adapter(self) -> None:
        orchestrator = create_default_orchestrator(repo_root=REPO_ROOT)
        orchestrator.register(_DummyCustomAdapter())
        ids = [a.engine_id for a in orchestrator.list_adapters()]
        self.assertIn("love2d-custom", ids)
        selector = EngineSelector(orchestrator)
        req = EngineProfileRequest(
            genre="arcade",
            world_dimension="2d",
            camera_type="top-down",
            character_count=2,
            animation_complexity="basic-2d",
            physics_needs="deterministic-2d",
            graphic_quality="pixel-vector-2d",
            target_platforms=("windows",),
            expected_performance="mobile-60fps-low-spec",
            development_complexity="low-mvp",
        )
        report = selector.evaluate(req)
        self.assertEqual(len(report["rankings"]), 4)

    def test_godot_adapter_scaffolds_validates_and_runs_real_headless_test(self) -> None:
        adapter = GodotEngineAdapter(repo_root=REPO_ROOT)
        probe = adapter.probe_toolchain()
        self.assertTrue(probe.available, f"Godot esperado localmente no repo: {probe}")
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "godot_game"
            scaf = adapter.scaffold_project(proj_dir, {"game_id": "godot-smoke", "name": "Godot Smoke"})
            self.assertIn("project.godot", scaf.files_written)
            val = adapter.validate_project(proj_dir)
            self.assertTrue(val.passed, f"Erros inesperados: {val.issues}")
            res = adapter.run_tests(proj_dir)
            self.assertTrue(res.passed, f"Saida Godot headless: {res.stdout_tail}")
            self.assertTrue(res.executed)
            self.assertIn("GODOT_ADAPTER_SMOKE_PASS", res.stdout_tail)

    def test_unity_and_unreal_adapters_scaffold_validate_and_fail_closed_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unity = UnityEngineAdapter()
            u_dir = Path(tmp) / "unity_proj"
            u_scaf = unity.scaffold_project(u_dir, {"game_id": "unity-demo", "name": "Unity Demo"})
            self.assertIn("Packages/manifest.json", u_scaf.files_written)
            self.assertTrue(unity.validate_project(u_dir).passed)
            if not unity.probe_toolchain().available:
                with self.assertRaises(EngineToolchainUnavailableError):
                    unity.run_tests(u_dir)

            unreal = UnrealEngineAdapter()
            ue_dir = Path(tmp) / "unreal_proj"
            ue_scaf = unreal.scaffold_project(ue_dir, {"game_id": "dark-citadel", "name": "Dark Citadel"})
            self.assertTrue(any(p.endswith(".uproject") for p in ue_scaf.files_written))
            self.assertTrue(unreal.validate_project(ue_dir).passed)
            if not unreal.probe_toolchain().available:
                with self.assertRaises(EngineToolchainUnavailableError):
                    unreal.run_tests(ue_dir)

    def test_spec_engine_preserves_v1_strictness_and_supports_v2_multiengine(self) -> None:
        validator = SpecificationValidator()
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            gen = SpecificationGenerator(mgr)

            # v1 continua rejeitando "unreal"
            v1_spec = gen.build_default_spec("v1-game", "V1 Game", "idle-rpg")
            v1_spec["engine"] = "unreal"
            with self.assertRaises(ValidationError) as ctx:
                validator.validate_spec(v1_spec)
            self.assertEqual(ctx.exception.field, "engine")

            # v2 suporta unreal/unity/godot + campos expandidos opcionais
            v2_spec = gen.build_default_spec(
                "v2-unreal-game",
                "V2 Unreal Game",
                "action-rpg",
                engine="unreal",
                multiengine=True,
                tools_required=["unreal", "blender", "ffmpeg"],
            )
            v2_spec["camera_spec"] = {"type": "third-person-cinematic", "fov": 75}
            v2_spec["physics_spec"] = {"mode": "chaos-3d"}
            v2_spec["inventory_spec"] = {"slots": 40}
            v2_spec["quests_spec"] = {"main_quests": 5}
            validated = validator.validate_spec(v2_spec)
            self.assertEqual(validated["spec_schema_version"], 2)
            self.assertEqual(validated["engine"], "unreal")

            # Tipo invalido em campo opcional v2 deve falhar fechado
            bad_v2 = dict(v2_spec)
            bad_v2["camera_spec"] = "not-a-dict"
            with self.assertRaises(ValidationError) as ctx2:
                validator.validate_spec(bad_v2)
            self.assertEqual(ctx2.exception.field, "camera_spec")

            # evaluate_from_spec funciona com v2
            report = EngineSelector(create_default_orchestrator(repo_root=REPO_ROOT)).evaluate_from_spec(validated)
            self.assertEqual(len(report["rankings"]), 3)

    def test_cli_engine_commands_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(playforge_cli_main(["--repo-root", str(root), "init"]), 0)
            self.assertEqual(
                playforge_cli_main(
                    [
                        "--repo-root",
                        str(root),
                        "create",
                        "unreal-rpg",
                        "--name",
                        "Unreal RPG",
                        "--genre",
                        "action-rpg",
                        "--engine",
                        "unreal",
                    ]
                ),
                0,
            )
            self.assertEqual(playforge_cli_main(["--repo-root", str(root), "engine-matrix"]), 0)
            self.assertEqual(playforge_cli_main(["--repo-root", str(root), "engine-probe", "--engine", "unreal"]), 0)
            self.assertEqual(
                playforge_cli_main(
                    [
                        "--repo-root",
                        str(root),
                        "engine-select",
                        "--genre",
                        "action-rpg-3d",
                        "--dimension",
                        "3d-aaa-large",
                        "--camera",
                        "third-person-cinematic",
                        "--graphic",
                        "photorealistic-lumen-nanite",
                        "--animation",
                        "advanced-mocap-cinematic",
                        "--licensing",
                        "free-royalty-ok",
                        "--save-project",
                        "unreal-rpg",
                    ]
                ),
                0,
            )
            report_json = root / "games" / "unreal-rpg" / "specs" / "engine_selection_report.json"
            self.assertTrue(report_json.is_file())
            parsed = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertIn(parsed["recommended_engine"], ("godot", "unity", "unreal"))

            self.assertEqual(
                playforge_cli_main(["--repo-root", str(root), "engine-scaffold", "unreal-rpg", "--engine", "unreal"]),
                0,
            )
            self.assertTrue((root / "games" / "unreal-rpg" / "UnrealRpg.uproject").is_file())


if __name__ == "__main__":
    unittest.main()
