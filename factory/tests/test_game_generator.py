"""Suite de testes unitarios e integracao E2E do Game Generator MVP (Fase 5)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from factory.playforge import cli
from factory.playforge.generator.config_mapper import (
    map_spec_to_runtime_config,
    render_project_godot,
)
from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.generator.schemas import (
    GenerationConflictError,
    GenerationVerificationError,
    GeneratorError,
)
from factory.playforge.models import ANCHOR_PROJECT_ID, ApprovalRequired, ProtectedProject
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.template_registry.registry import TemplateRegistry
from factory.playforge.template_registry.validator import TemplateCompatibilityError

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_TEMPLATE_DIR = REPO_ROOT / "templates" / "godot-2d-action-rpg" / "1.0.0"


class TestConfigMapper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_gen_map_"))
        self.manager = ProjectManager(repo_root=self.tmp_dir)
        self.spec_gen = SpecificationGenerator(self.manager)

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_render_project_godot_parameterizes_portrait_resolution(self) -> None:
        spec = self.spec_gen.build_default_spec(
            game_id="sky-striker",
            name='Sky "Striker"',
            genre="idle-rpg",
            screen_orientation="portrait",
        )
        spec["ui_ux"]["resolution"] = "1080x1920"
        base_godot = (REAL_TEMPLATE_DIR / "skeleton" / "project.godot").read_text(encoding="utf-8")
        rendered = render_project_godot(
            base_godot,
            spec,
            template_id="godot-2d-action-rpg",
            template_version="1.0.0",
        )
        self.assertIn('config/name="Sky \'Striker\'"', rendered)
        self.assertIn("window/size/viewport_width=1080", rendered)
        self.assertIn("window/size/viewport_height=1920", rendered)
        self.assertIn("window/handheld/orientation=1", rendered)
        self.assertIn("game_id=sky-striker", rendered)

    def test_map_spec_normalizes_unwinnable_boss_and_rejects_bad_resolution(self) -> None:
        spec = self.spec_gen.build_default_spec(
            game_id="crono-blade",
            name="Crono Blade",
            genre="action-rpg",
        )
        runtime_cfg, balance_info = map_spec_to_runtime_config(spec)
        self.assertEqual(runtime_cfg["game_id"], "crono-blade")
        self.assertTrue(balance_info["normalized"])
        self.assertLessEqual(
            balance_info["effective_worst_case_damage"],
            balance_info["hero_max_hp"] * 0.75,
        )

        spec["ui_ux"]["resolution"] = "invalida"
        base_godot = (REAL_TEMPLATE_DIR / "skeleton" / "project.godot").read_text(encoding="utf-8")
        with self.assertRaises(GeneratorError):
            render_project_godot(
                base_godot,
                spec,
                template_id="godot-2d-action-rpg",
                template_version="1.0.0",
            )


class TestGameGeneratorMVP(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_gen_mvp_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        shutil.copytree(
            REAL_TEMPLATE_DIR,
            self.repo_root / "templates" / "godot-2d-action-rpg" / "1.0.0",
        )
        (self.repo_root / "templates" / ".gdignore").write_text("", encoding="utf-8")

        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.spec_gen = SpecificationGenerator(self.manager)
        self.tpl_reg = TemplateRegistry(repo_root=self.repo_root)
        self.generator = GameGenerator(self.manager, template_registry=self.tpl_reg)

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def _prepare_approved_project(
        self,
        project_id: str,
        name: str,
        genre: str = "action-rpg",
        orientation: str = "landscape",
    ) -> None:
        self.manager.create_project(project_id, name=name, genre=genre)
        spec = self.spec_gen.build_default_spec(
            game_id=project_id,
            name=name,
            genre=genre,
            screen_orientation=orientation,
        )
        self.spec_gen.generate_and_save_spec(project_id, custom_spec=spec)
        self.spec_gen.generate_and_save_gdd(project_id)
        self.spec_gen.approve_specification(project_id, approver="operador", decision_notes="OK MVP")

    def _godot_available(self) -> bool:
        return self.generator._resolve_godot_bin() is not None

    def test_anchor_and_unapproved_or_tampered_spec_blocked(self) -> None:
        with self.assertRaises(ProtectedProject):
            self.generator.generate_project(ANCHOR_PROJECT_ID)

        self.manager.create_project("blocked-game", name="Blocked", genre="action-rpg")
        self.spec_gen.generate_and_save_spec("blocked-game")
        self.spec_gen.generate_and_save_gdd("blocked-game")

        with self.assertRaises(ApprovalRequired):
            self.generator.generate_project(
                "blocked-game",
                run_godot_tests=False,
                verify_template_tests=False,
            )

        self.spec_gen.approve_specification("blocked-game", approver="op", decision_notes="ok")
        spec_path = self.manager.resolve_game_path("blocked-game", "specs/game_specification.json")
        tampered = json.loads(spec_path.read_text(encoding="utf-8"))
        tampered["name"] = "Adulterado"
        spec_path.write_text(json.dumps(tampered), encoding="utf-8")

        with self.assertRaises(ApprovalRequired):
            self.generator.generate_project(
                "blocked-game",
                run_godot_tests=False,
                verify_template_tests=False,
            )

    def test_deprecated_template_and_missing_godot_blocked_fail_closed(self) -> None:
        self._prepare_approved_project("stale-tpl-game", "Stale Game")
        self.tpl_reg.select_template_for_project(self.manager, "stale-tpl-game")
        self.tpl_reg.deprecate_template("godot-2d-action-rpg", "1.0.0", reason="Descontinuado")

        with self.assertRaises(TemplateCompatibilityError):
            self.generator.generate_project(
                "stale-tpl-game",
                run_godot_tests=False,
                verify_template_tests=False,
            )

        self._prepare_approved_project("no-godot-game", "No Godot")
        with self.assertRaises(GenerationVerificationError):
            self.generator.generate_project(
                "no-godot-game",
                godot_bin=self.tmp_dir / "nonexistent_godot_bin",
            )

    def test_generates_verifies_in_real_godot_and_packages_isolated_game(self) -> None:
        if not self._godot_available():
            self.skipTest("Binario Godot headless nao presente neste ambiente.")

        self._prepare_approved_project("crono-blade", "Crono Blade")
        res = self.generator.generate_project("crono-blade")

        self.assertEqual(res["status"], "GENERATED")
        self.assertEqual(res["project_id"], "crono-blade")
        self.assertEqual(res["template_id"], "godot-2d-action-rpg")
        self.assertEqual(res["file_count"], 10)
        self.assertTrue(res["verification"]["passed"])
        self.assertEqual(len(res["verification"]["suites"]), 1)
        self.assertIn("Assertions: 18 | Failed: 0", res["verification"]["suites"][0]["output"])
        self.assertTrue((self.manager.games_root / ".gdignore").is_file())

        # Confere conteudo parametrizado do jogo gerado
        proj_cfg = self.manager.resolve_game_path("crono-blade", "project.godot").read_text(encoding="utf-8")
        self.assertIn('config/name="Crono Blade"', proj_cfg)

        runtime_cfg = json.loads(
            self.manager.resolve_game_path("crono-blade", "config/template_defaults.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(runtime_cfg["game_id"], "crono-blade")
        self.assertEqual(runtime_cfg["game_name"], "Crono Blade")

        # Confere pacote ZIP deterministico e SHA-256
        pkg = res["preview_package"]
        self.assertTrue(pkg["godot_verified"])
        zip_path = self.manager.resolve_game_path("crono-blade", pkg["artifact_path"])
        sha_path = self.manager.resolve_game_path("crono-blade", pkg["checksum_path"])
        self.assertTrue(zip_path.is_file())
        self.assertTrue(sha_path.is_file())
        self.assertIn(pkg["artifact_sha256"], sha_path.read_text(encoding="utf-8"))

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            self.assertIn("project.godot", names)
            self.assertIn("tests/unit/verify_generated_game.gd", names)
            self.assertIn("specs/generation_manifest.json", names)

        # Determinismo do empacotamento ZIP
        pkg2 = self.generator.package_preview_artifact("crono-blade")
        self.assertEqual(pkg["artifact_sha256"], pkg2["artifact_sha256"])

    def test_idempotency_conflict_detection_and_multi_project_isolation(self) -> None:
        self._prepare_approved_project("game-alpha", "Game Alpha", genre="action-rpg")
        self._prepare_approved_project("game-beta", "Game Beta", genre="idle-rpg", orientation="portrait")

        res_a1 = self.generator.generate_project(
            "game-alpha",
            run_godot_tests=False,
            verify_template_tests=False,
        )
        self.assertEqual(res_a1["status"], "GENERATED")

        # 2a chamada sem alteracoes e idempotente (UP_TO_DATE)
        res_a2 = self.generator.generate_project(
            "game-alpha",
            run_godot_tests=False,
            verify_template_tests=False,
        )
        self.assertEqual(res_a2["status"], "UP_TO_DATE")

        # Gera projeto B paralelo
        res_b = self.generator.generate_project(
            "game-beta",
            run_godot_tests=False,
            verify_template_tests=False,
        )
        self.assertEqual(res_b["status"], "GENERATED")

        # Alteracao local manual em game-alpha bloqueia regeneracao sem --force e falha verificacao
        core_a = self.manager.resolve_game_path("game-alpha", "src/core/game_loop_core.gd")
        core_a.write_text(core_a.read_text(encoding="utf-8") + "\n# manual edit\n", encoding="utf-8")

        with self.assertRaises(GenerationConflictError):
            self.generator.generate_project(
                "game-alpha",
                run_godot_tests=False,
                verify_template_tests=False,
                force=False,
            )

        with self.assertRaises(GenerationVerificationError):
            self.generator.verify_generated_project(
                "game-alpha",
                godot_bin=self.tmp_dir / "nonexistent",
            )

        # Regeneracao com --force restaura game-alpha sem afetar game-beta
        res_a_forced = self.generator.generate_project(
            "game-alpha",
            run_godot_tests=False,
            verify_template_tests=False,
            force=True,
        )
        self.assertEqual(res_a_forced["status"], "GENERATED")

        beta_cfg = json.loads(
            self.manager.resolve_game_path("game-beta", "config/template_defaults.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(beta_cfg["game_id"], "game-beta")
        self.assertEqual(beta_cfg["genre"], "idle-rpg")


class TestGameGeneratorCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_gen_cli_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        shutil.copytree(
            REAL_TEMPLATE_DIR,
            self.repo_root / "templates" / "godot-2d-action-rpg" / "1.0.0",
        )
        (self.repo_root / "templates" / ".gdignore").write_text("", encoding="utf-8")
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def _run_cli(self, args: list[str]) -> tuple[int, str, str]:
        cmd_args = ["--repo-root", str(self.repo_root)] + args
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            try:
                code = cli.main(cmd_args)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
        return code, out_buf.getvalue(), err_buf.getvalue()

    def test_cli_mvp_end_to_end_pipeline(self) -> None:
        if GameGenerator(self.manager)._resolve_godot_bin() is None:
            self.skipTest("Binario Godot headless nao presente neste ambiente.")

        self.assertEqual(self._run_cli(["create", "pixel-odyssey", "--name", "Pixel Odyssey", "--genre", "action-rpg"])[0], 0)
        self.assertEqual(self._run_cli(["spec-generate", "pixel-odyssey"])[0], 0)
        self.assertEqual(self._run_cli(["gdd-generate", "pixel-odyssey"])[0], 0)

        # Sem aprovacao deve bloquear game-generate
        code_blocked, _, err_blocked = self._run_cli(["game-generate", "pixel-odyssey"])
        self.assertEqual(code_blocked, 1)
        self.assertEqual(json.loads(err_blocked)["error"], "ApprovalRequired")

        self.assertEqual(
            self._run_cli(["spec-approve", "pixel-odyssey", "--approver", "op", "--notes", "Aprovado MVP"])[0],
            0,
        )
        self.assertEqual(self._run_cli(["template-select", "pixel-odyssey"])[0], 0)

        code_gen, out_gen, err_gen = self._run_cli(["game-generate", "pixel-odyssey"])
        self.assertEqual(code_gen, 0, msg=err_gen)
        gen_data = json.loads(out_gen)
        self.assertEqual(gen_data["status"], "GENERATED")
        self.assertTrue(gen_data["verification"]["passed"])
        self.assertTrue(gen_data["preview_package"]["godot_verified"])

        code_ver, out_ver, _ = self._run_cli(["game-verify", "pixel-odyssey"])
        self.assertEqual(code_ver, 0)
        self.assertTrue(json.loads(out_ver)["passed"])

        code_pkg, out_pkg, _ = self._run_cli(["game-package", "pixel-odyssey"])
        self.assertEqual(code_pkg, 0)
        self.assertEqual(json.loads(out_pkg)["artifact_sha256"], gen_data["preview_package"]["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
