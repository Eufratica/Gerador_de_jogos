"""Testes do Build Manager multi-plataforma (Fase 10 / P3)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from factory.playforge import cli
from factory.playforge.asset_pipeline import AssetRegistry
from factory.playforge.build_system import (
    BuildIntegrityError,
    BuildManager,
    BuildPrerequisiteError,
    BuildTargetUnavailableError,
    ReleaseApprovalRequiredError,
)
from factory.playforge.engine_orchestrator import GodotEngineAdapter
from factory.playforge.models import ProtectedProject
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator


class TestBuildSystem(unittest.TestCase):
    def _prepare_godot_project(self, tmp: str, project_id: str = "build-demo") -> tuple[ProjectManager, BuildManager]:
        mgr = ProjectManager(Path(tmp), games_root=Path(tmp) / "games")
        mgr.init_registry()
        mgr.create_project(
            project_id=project_id,
            name="Build Demo",
            genre="action-rpg",
            engine="godot",
            engine_version="4.4-stable",
        )
        gen = SpecificationGenerator(mgr)
        gen.generate_and_save_spec(project_id)
        ws = mgr.resolve_game_path(project_id, ".")
        GodotEngineAdapter(repo_root=REPO_ROOT).scaffold_project(ws, {"game_id": project_id, "name": "Build Demo"})
        return mgr, BuildManager(mgr)

    def test_probe_toolchains_is_truthful_and_zero_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            bm = BuildManager(mgr)
            probe = bm.probe_build_toolchains()
            self.assertFalse(probe["paid_services_enabled"])
            self.assertTrue(probe["structural_bundle_always_available"])
            self.assertIn("godot", probe["engines"])
            self.assertIn("windows", probe["native_export_ready"])

    def test_anchor_project_is_protected_from_builds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            bm = BuildManager(mgr)
            with self.assertRaises(ProtectedProject):
                bm.build_target("zaikor", "windows")

    def test_build_target_validates_prereqs_and_runs_godot_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr, bm = self._prepare_godot_project(tmp)
            manifest = bm.build_target("build-demo", "windows")
            self.assertEqual(manifest["artifact_kind"], "structural-source-bundle")
            self.assertFalse(manifest["native_export_performed"])
            self.assertEqual(manifest["release_status"], "UNAPPROVED")
            smoke = manifest["post_build_checks"]["engine_smoke_test"]
            self.assertEqual(smoke["status"], "PASSED", f"Smoke test inesperado: {smoke}")

            ver = bm.verify_build("build-demo", manifest["version"], "windows")
            self.assertTrue(ver["passed"])
            self.assertGreaterEqual(ver["file_count"], 5)

    def test_build_blocks_secrets_temp_files_and_untargeted_platforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr, bm = self._prepare_godot_project(tmp)
            with self.assertRaises(BuildPrerequisiteError):
                bm.build_target("build-demo", "ios")  # nao esta em target_platforms default

            secret_env = mgr.resolve_game_path("build-demo", ".env")
            secret_env.write_text("SECRET_KEY=leaked\n", encoding="utf-8")
            with self.assertRaises(BuildPrerequisiteError):
                bm.build_target("build-demo", "windows")
            secret_env.unlink()

            tmp_junk = mgr.resolve_game_path("build-demo", "junk.tmp")
            tmp_junk.write_text("tmp", encoding="utf-8")
            with self.assertRaises(BuildPrerequisiteError):
                bm.build_target("build-demo", "windows")
            tmp_junk.unlink()

            with self.assertRaises(BuildTargetUnavailableError):
                bm.build_target("build-demo", "windows", allow_structural_bundle=False)

    def test_build_integrates_asset_audit_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr, bm = self._prepare_godot_project(tmp)
            reg = AssetRegistry(mgr)
            reg.generate_default_pack("build-demo")
            orphan = mgr.resolve_game_path("build-demo", "assets/orphan.bin")
            orphan.write_bytes(b"unregistered")
            with self.assertRaises(BuildPrerequisiteError):
                bm.build_target("build-demo", "android")
            orphan.unlink()
            manifest = bm.build_target("build-demo", "android")
            self.assertEqual(manifest["target"], "android")
            self.assertEqual(manifest["android_permissions"], [])
            self.assertTrue(manifest["post_build_checks"]["asset_audit"]["passed"])

    def test_verify_detects_tampering_and_approve_release_requires_human(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr, bm = self._prepare_godot_project(tmp)
            manifest = bm.build_target("build-demo", "linux")
            ver = manifest["version"]

            with self.assertRaises(ReleaseApprovalRequiredError):
                bm.approve_release("build-demo", ver, "linux", approver="", notes="ok")

            approved = bm.approve_release(
                "build-demo",
                ver,
                "linux",
                approver="gerson.marques",
                notes="Aprovado para validacao interna Linux",
            )
            self.assertEqual(approved["release_status"], "RELEASE_APPROVED")
            self.assertFalse(approved["approval"]["published_externally"])

            zip_path = mgr.resolve_game_path("build-demo", f"builds/{ver}/linux/{approved['artifact']}")
            zip_path.write_bytes(b"corrupted-zip-payload")
            with self.assertRaises(BuildIntegrityError):
                bm.verify_build("build-demo", ver, "linux")

    def test_cli_build_commands_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = ["--repo-root", tmp]
            self.assertEqual(cli.main(base + ["init"]), 0)
            self.assertEqual(cli.main(base + ["create", "cli-bld", "--name", "Cli Build", "--genre", "action-rpg"]), 0)
            self.assertEqual(cli.main(base + ["spec-generate", "cli-bld"]), 0)
            self.assertEqual(cli.main(base + ["engine-scaffold", "cli-bld", "--engine", "godot"]), 0)
            self.assertEqual(cli.main(base + ["build-toolchains"]), 0)
            self.assertEqual(cli.main(base + ["build-package", "cli-bld", "--target", "windows"]), 0)
            self.assertEqual(
                cli.main(base + ["build-verify", "cli-bld", "--target", "windows", "--version", "0.1.0"]),
                0,
            )
            self.assertEqual(
                cli.main(
                    base
                    + [
                        "build-approve-release",
                        "cli-bld",
                        "--target",
                        "windows",
                        "--version",
                        "0.1.0",
                        "--approver",
                        "gerson",
                        "--notes",
                        "Release candidato verificado",
                    ]
                ),
                0,
            )
            rep = Path(tmp) / "games" / "cli-bld" / "builds" / "0.1.0" / "windows" / "build_manifest.json"
            self.assertTrue(rep.is_file())
            parsed = json.loads(rep.read_text(encoding="utf-8"))
            self.assertEqual(parsed["release_status"], "RELEASE_APPROVED")


if __name__ == "__main__":
    unittest.main()
