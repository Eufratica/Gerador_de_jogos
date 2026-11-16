"""Suite de testes unitarios e de integracao do Game Template Registry (Fase 4)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from factory.playforge import cli
from factory.playforge.models import ANCHOR_PROJECT_ID, ApprovalRequired, ProtectedProject
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.template_registry.registry import TemplateRegistry
from factory.playforge.template_registry.schemas import (
    TEMPLATE_MANIFEST_SCHEMA_VERSION,
    TEMPLATE_REQUIRED_FIELDS,
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_DEPRECATED,
)
from factory.playforge.template_registry.validator import (
    TemplateCompatibilityError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateValidator,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _create_sample_template(
    templates_root: Path,
    *,
    template_id: str = "sample-action-2d",
    version: str = "1.0.0",
    manifest_overrides: dict[str, Any] | None = None,
    extra_systems: list[str] | None = None,
) -> Path:
    """Cria um template minimo valido em diretorio temporario isolado."""
    tpl_dir = templates_root / template_id / version
    skeleton_dir = tpl_dir / "skeleton"
    demo_dir = tpl_dir / "demo"

    base_files: dict[str, str] = {
        "project.godot": 'config_version=5\n[application]\nconfig/name="Sample"\n',
        "src/core/loop.gd": "class_name SampleLoop\nextends RefCounted\n",
        "tests/unit/run_tests.gd": "extends SceneTree\nfunc _initialize():\n\tquit(0)\n",
    }

    for target_root in (skeleton_dir, demo_dir):
        for rel, content in base_files.items():
            file_path = target_root / rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    (tpl_dir / "README.md").write_text(f"# {template_id} {version}\n", encoding="utf-8")

    manifest: dict[str, Any] = {
        "template_manifest_schema_version": TEMPLATE_MANIFEST_SCHEMA_VERSION,
        "template_id": template_id,
        "name": f"Sample {template_id}",
        "template_version": version,
        "engine": "godot",
        "engine_version": "4.4-stable",
        "supported_genres": ["action-rpg"],
        "supported_platforms": ["android", "windows", "linux"],
        "status": TEMPLATE_STATUS_ACTIVE,
        "spec_schema_version": 1,
        "license": "MIT",
        "description": "Template de teste isolado.",
        "documentation": "README.md",
        "available_systems": ["core-loop"] + (extra_systems or []),
        "reusable_components": ["src/core/loop.gd"],
        "asset_slots": {"hero": {"type": "sprite_2d_optional", "required": False}},
        "dependencies": [],
        "allowed_extensions": [".gd", ".godot", ".json"],
        "file_structure": sorted(base_files.keys()),
        "tests": {
            "runner": "godot-headless",
            "script": "res://tests/unit/run_tests.gd",
        },
        "demo_project_path": "demo",
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)

    (tpl_dir / "template_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return tpl_dir


class TestShippedTemplate(unittest.TestCase):
    """Valida o template real godot-2d-action-rpg v1.0.0 entregue na Fase 4."""

    def test_shipped_godot_2d_action_rpg_manifest_and_structure(self) -> None:
        registry = TemplateRegistry(repo_root=REPO_ROOT)
        templates = registry.list_templates()
        ids = {(t["template_id"], t["template_version"]) for t in templates}
        self.assertIn(("godot-2d-action-rpg", "1.0.0"), ids)

        report = registry.validate_template("godot-2d-action-rpg", "1.0.0")
        self.assertEqual(report["status"], "VALID")
        self.assertEqual(report["license"], "MIT")
        self.assertEqual(report["file_count"], 10)
        self.assertEqual(len(report["skeleton_sha256"]), 64)

    def test_shipped_template_executes_real_godot_headless_tests(self) -> None:
        registry = TemplateRegistry(repo_root=REPO_ROOT)
        godot_bin = registry.default_godot_bin()
        if godot_bin is None:
            self.skipTest("Binario Godot headless nao presente neste ambiente.")
        report = registry.validate_template(
            "godot-2d-action-rpg",
            "1.0.0",
            run_godot_tests=True,
            godot_bin=godot_bin,
        )
        godot_res = report["godot_test_result"]
        self.assertIsNotNone(godot_res)
        self.assertTrue(godot_res["passed"])
        self.assertEqual(godot_res["returncode"], 0)
        self.assertIn("Failed: 0", godot_res["output"])


class TestTemplateValidatorFailClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_tpl_val_"))
        self.templates_root = self.tmp_dir / "templates"
        self.validator = TemplateValidator()
        self.tpl_dir = _create_sample_template(self.templates_root)
        self.manifest = json.loads((self.tpl_dir / "template_manifest.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_unknown_root_field_rejected_fail_closed(self) -> None:
        corrupt = dict(self.manifest)
        corrupt["rogue_field"] = "unexpected"
        with self.assertRaises(TemplateValidationError) as ctx:
            self.validator.validate_manifest(corrupt)
        self.assertEqual(ctx.exception.field, "rogue_field")

    def test_missing_required_fields_rejected_fail_closed(self) -> None:
        for field in TEMPLATE_REQUIRED_FIELDS:
            corrupt = dict(self.manifest)
            del corrupt[field]
            with self.assertRaises(TemplateValidationError, msg=f"Deveria rejeitar sem '{field}'") as ctx:
                self.validator.validate_manifest(corrupt)
            self.assertEqual(ctx.exception.field, field)

    def test_bool_cannot_masquerade_as_schema_version(self) -> None:
        for field in ("template_manifest_schema_version", "spec_schema_version"):
            corrupt = dict(self.manifest)
            corrupt[field] = True
            with self.assertRaises(TemplateValidationError) as ctx:
                self.validator.validate_manifest(corrupt)
            self.assertEqual(ctx.exception.field, field)

    def test_disallowed_license_rejected_by_zero_cost_policy(self) -> None:
        corrupt = dict(self.manifest, license="Commercial-Proprietary")
        with self.assertRaises(TemplateValidationError) as ctx:
            self.validator.validate_manifest(corrupt)
        self.assertEqual(ctx.exception.field, "license")

    def test_missing_file_in_skeleton_fails_validation(self) -> None:
        (self.tpl_dir / "skeleton" / "src" / "core" / "loop.gd").unlink()
        with self.assertRaises(TemplateValidationError) as ctx:
            self.validator.validate_template_dir(self.tpl_dir)
        self.assertEqual(ctx.exception.field, "file_structure")

    def test_forbidden_extension_or_undeclared_file_in_skeleton_rejected(self) -> None:
        # Arquivo extra nao declarado
        extra = self.tpl_dir / "skeleton" / "src" / "core" / "undeclared.gd"
        extra.write_text("# extra", encoding="utf-8")
        with self.assertRaises(TemplateValidationError) as ctx:
            self.validator.validate_template_dir(self.tpl_dir)
        self.assertEqual(ctx.exception.field, "file_structure")
        extra.unlink()

        # Arquivo com extensao proibida (.exe)
        binary = self.tpl_dir / "skeleton" / "payload.exe"
        binary.write_bytes(b"MZ")
        with self.assertRaises(TemplateValidationError) as ctx2:
            self.validator.validate_template_dir(self.tpl_dir)
        self.assertEqual(ctx2.exception.field, "allowed_extensions")

    def test_path_traversal_rejected_fail_closed(self) -> None:
        bad_file_struct = dict(self.manifest, file_structure=["../escape.gd"])
        with self.assertRaises(TemplateValidationError):
            self.validator.validate_manifest(bad_file_struct)
        (self.tpl_dir / "template_manifest.json").write_text(
            json.dumps(dict(self.manifest, demo_project_path="../outside_demo")),
            encoding="utf-8",
        )
        with self.assertRaises(TemplateValidationError) as ctx:
            self.validator.validate_template_dir(self.tpl_dir)
        self.assertEqual(ctx.exception.field, "demo_project_path")

    def test_skeleton_tampering_changes_sha256_digest(self) -> None:
        before = self.validator.validate_template_dir(self.tpl_dir)["skeleton_sha256"]
        target = self.tpl_dir / "skeleton" / "src" / "core" / "loop.gd"
        target.write_text(target.read_text(encoding="utf-8") + "\n# modified\n", encoding="utf-8")
        after = self.validator.validate_template_dir(self.tpl_dir)["skeleton_sha256"]
        self.assertNotEqual(before, after)


class TestTemplateRegistrySelectionAndLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_tpl_reg_"))
        self.repo_root = self.tmp_dir / "repo"
        self.templates_root = self.repo_root / "templates"
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.spec_gen = SpecificationGenerator(self.manager)

        _create_sample_template(
            self.templates_root,
            template_id="godot-2d-action-rpg",
            version="1.0.0",
        )
        _create_sample_template(
            self.templates_root,
            template_id="godot-2d-action-rpg",
            version="1.2.0",
            extra_systems=["save-checkpoint"],
        )
        _create_sample_template(
            self.templates_root,
            template_id="godot-2d-action-rpg",
            version="2.0.0",
            manifest_overrides={"status": TEMPLATE_STATUS_DEPRECATED},
        )
        self.registry = TemplateRegistry(repo_root=self.repo_root)

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_list_and_search_respects_semver_and_deprecated_flag(self) -> None:
        active = self.registry.list_templates()
        versions = [t["template_version"] for t in active]
        self.assertEqual(versions, ["1.2.0", "1.0.0"])

        all_items = self.registry.list_templates(include_deprecated=True)
        self.assertEqual([t["template_version"] for t in all_items], ["2.0.0", "1.2.0", "1.0.0"])

        matched = self.registry.search_templates(genre="action-rpg", engine="godot", platform="android")
        self.assertEqual(len(matched), 2)
        self.assertEqual(self.registry.search_templates(platform="web"), [])

    def test_compatibility_checks_and_selection_from_spec(self) -> None:
        spec_ok = self.spec_gen.build_default_spec(
            game_id="blade-hero",
            name="Blade Hero",
            genre="action-rpg",
            target_platforms=["android"],
        )
        selected = self.registry.select_best_template(spec_ok)
        self.assertEqual(selected["template_id"], "godot-2d-action-rpg")
        # Seleciona a versao ACTIVE mais recente (1.2.0), ignorando 2.0.0 DEPRECATED
        self.assertEqual(selected["template_version"], "1.2.0")

        spec_bad_genre = self.spec_gen.build_default_spec(
            game_id="puzzle-run",
            name="Puzzle Run",
            genre="puzzle",
            target_platforms=["android"],
        )
        with self.assertRaises(TemplateCompatibilityError):
            self.registry.select_best_template(spec_bad_genre)

        spec_bad_engine_ver = dict(spec_ok, engine_version="4.2-stable")
        with self.assertRaises(TemplateCompatibilityError):
            self.registry.select_best_template(spec_bad_engine_ver)

        spec_bad_platform = self.spec_gen.build_default_spec(
            game_id="web-hero",
            name="Web Hero",
            genre="action-rpg",
            target_platforms=["android", "web"],
        )
        with self.assertRaises(TemplateCompatibilityError):
            self.registry.select_best_template(spec_bad_platform)

    def test_project_selection_requires_approved_spec_and_guards_anchor(self) -> None:
        with self.assertRaises(ProtectedProject):
            self.registry.select_template_for_project(self.manager, ANCHOR_PROJECT_ID)

        self.manager.create_project("hero-quest", name="Hero Quest", genre="action-rpg")
        self.spec_gen.generate_and_save_spec("hero-quest")
        self.spec_gen.generate_and_save_gdd("hero-quest")

        # Fail-closed sem aprovacao humana da spec
        with self.assertRaises(ApprovalRequired):
            self.registry.select_template_for_project(self.manager, "hero-quest")

        self.spec_gen.approve_specification("hero-quest", approver="op", decision_notes="Spec ok")
        selection = self.registry.select_template_for_project(self.manager, "hero-quest")
        self.assertEqual(selection["template_id"], "godot-2d-action-rpg")
        self.assertEqual(selection["template_version"], "1.2.0")

        sel_file = self.manager.resolve_game_path("hero-quest", "specs/template_selection.json")
        self.assertTrue(sel_file.is_file())
        saved = json.loads(sel_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["skeleton_sha256"], selection["skeleton_sha256"])

    def test_compare_and_deprecate_preserves_older_versions(self) -> None:
        diff = self.registry.compare_templates(
            "godot-2d-action-rpg",
            "1.0.0",
            "godot-2d-action-rpg",
            "1.2.0",
        )
        self.assertEqual(diff["only_in_right_systems"], ["save-checkpoint"])
        self.assertTrue(diff["same_skeleton_sha256"])

        dep = self.registry.deprecate_template(
            "godot-2d-action-rpg",
            "1.0.0",
            reason="Substituida pela versao 1.2.0",
            deprecated_by="architect",
        )
        self.assertEqual(dep["status"], TEMPLATE_STATUS_DEPRECATED)

        # Arquivos da versao 1.0.0 permanecem intactos e legiveis para projetos legados
        old_rec = self.registry.get_template("godot-2d-action-rpg", "1.0.0", include_deprecated=True)
        self.assertEqual(old_rec["template_status"], TEMPLATE_STATUS_DEPRECATED)
        self.assertTrue((self.templates_root / "godot-2d-action-rpg" / "1.0.0" / "skeleton" / "project.godot").is_file())

        # Versao 1.2.0 segue ativa
        active = self.registry.list_templates()
        self.assertEqual([t["template_version"] for t in active], ["1.2.0"])


class TestTemplateCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_tpl_cli_"))
        self.repo_root = self.tmp_dir / "repo"
        self.templates_root = self.repo_root / "templates"
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        _create_sample_template(
            self.templates_root,
            template_id="godot-2d-action-rpg",
            version="1.0.0",
        )
        _create_sample_template(
            self.templates_root,
            template_id="godot-2d-action-rpg",
            version="1.1.0",
            extra_systems=["inventory-lite"],
        )

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

    def test_cli_template_lifecycle_end_to_end(self) -> None:
        code, stdout, _ = self._run_cli(["template-list", "--genre", "action-rpg"])
        self.assertEqual(code, 0)
        listed = json.loads(stdout)
        self.assertEqual(listed["count"], 2)

        code, stdout, _ = self._run_cli(["template-show", "godot-2d-action-rpg", "--version", "1.1.0"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["template_version"], "1.1.0")

        code, stdout, _ = self._run_cli(["template-validate", "godot-2d-action-rpg"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "VALID")

        code, stdout, _ = self._run_cli(
            [
                "template-compare",
                "godot-2d-action-rpg",
                "godot-2d-action-rpg",
                "--left-version",
                "1.0.0",
                "--right-version",
                "1.1.0",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["only_in_right_systems"], ["inventory-lite"])

        code, stdout, _ = self._run_cli(
            [
                "template-deprecate",
                "godot-2d-action-rpg",
                "--version",
                "1.0.0",
                "--reason",
                "Obsoleta",
                "--by",
                "qa",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], TEMPLATE_STATUS_DEPRECATED)

        # Selecao no projeto exige spec aprovada
        self._run_cli(["create", "cli-rpg", "--name", "CLI RPG", "--genre", "action-rpg"])
        self._run_cli(["spec-generate", "cli-rpg"])
        self._run_cli(["gdd-generate", "cli-rpg"])

        code_blocked, _, err_blocked = self._run_cli(["template-select", "cli-rpg"])
        self.assertEqual(code_blocked, 1)
        self.assertEqual(json.loads(err_blocked)["error"], "ApprovalRequired")

        self._run_cli(
            [
                "spec-approve",
                "cli-rpg",
                "--approver",
                "operador",
                "--notes",
                "Aprovado",
            ]
        )
        code_ok, out_ok, _ = self._run_cli(["template-select", "cli-rpg"])
        self.assertEqual(code_ok, 0)
        sel = json.loads(out_ok)
        self.assertEqual(sel["template_id"], "godot-2d-action-rpg")
        self.assertEqual(sel["template_version"], "1.1.0")


if __name__ == "__main__":
    unittest.main()
