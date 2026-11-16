"""Suíte de testes unitários do Game Specification Engine (Fase 3)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from factory.playforge import cli
from factory.playforge.models import ANCHOR_PROJECT_ID, ApprovalRequired, ProtectedProject
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.schemas import (
    GDD_SCHEMA_VERSION,
    GDD_SECTIONS,
    SPEC_REQUIRED_FIELDS,
    SPEC_SCHEMA_VERSION,
)
from factory.playforge.spec_engine.validator import (
    SchemaCompatibilityError,
    SpecificationValidator,
    ValidationError,
)


class TestSpecificationValidator(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = SpecificationValidator()
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_spec_val_"))
        self.manager = ProjectManager(repo_root=self.tmp_dir)
        self.generator = SpecificationGenerator(self.manager)
        self.valid_spec = self.generator.build_default_spec(
            game_id="tank-clash",
            name="Tank Clash",
            genre="ddtank-ballistics",
        )

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_valid_spec_passes_validation(self) -> None:
        validated = self.validator.validate_spec(self.valid_spec)
        self.assertEqual(validated["spec_id"], "spec-tank-clash-v1")
        self.assertEqual(validated["game_id"], "tank-clash")
        self.assertEqual(validated["spec_schema_version"], SPEC_SCHEMA_VERSION)

    def test_missing_required_field_raises_validation_error(self) -> None:
        for field in SPEC_REQUIRED_FIELDS:
            corrupt = dict(self.valid_spec)
            del corrupt[field]
            with self.assertRaises(ValidationError, msg=f"Deveria falhar sem campo '{field}'") as ctx:
                self.validator.validate_spec(corrupt)
            self.assertEqual(ctx.exception.field, field)

    def test_invalid_schema_version_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, spec_schema_version=99)
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "spec_schema_version")

    def test_unsupported_genre_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, genre="mmo-sandbox-unknown")
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "genre")

    def test_unsupported_engine_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, engine="unreal")
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "engine")

    def test_empty_platforms_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, target_platforms=[])
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "target_platforms")

    def test_invalid_platform_in_list_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, target_platforms=["windows", "playstation-1"])
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertIn("target_platforms", ctx.exception.field)

    def test_gacha_rates_sum_must_equal_one(self) -> None:
        # Soma = 0.80 (inválida)
        corrupt = json.loads(json.dumps(self.valid_spec))
        corrupt["economy"]["gacha_rates"] = {"common": 0.50, "rare": 0.30}
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "economy.gacha_rates")
        self.assertIn("soma das taxas", ctx.exception.message)

    def test_room_connection_to_nonexistent_room_raises_validation_error(self) -> None:
        corrupt = json.loads(json.dumps(self.valid_spec))
        # Altera conexão da sala 1 para apontar para sala 99 inexistente
        corrupt["worlds_and_levels"]["worlds"][0]["rooms"][0]["connections"] = [
            {"target_room_id": "room_99_ghost"}
        ]
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertIn("connections", ctx.exception.field)
        self.assertIn("room_99_ghost", ctx.exception.message)

    def test_duplicate_room_id_raises_validation_error(self) -> None:
        corrupt = json.loads(json.dumps(self.valid_spec))
        rooms = corrupt["worlds_and_levels"]["worlds"][0]["rooms"]
        # Duplica sala com mesmo room_id
        rooms.append({"room_id": rooms[0]["room_id"], "name": "Dup", "connections": []})
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertIn("duplicado", ctx.exception.message)

    def test_empty_acceptance_criteria_raises_validation_error(self) -> None:
        corrupt = dict(self.valid_spec, acceptance_criteria=[])
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "acceptance_criteria")

    def test_valid_gdd_passes_validation(self) -> None:
        gdd = self.generator.build_default_gdd("tank-clash", "Tank Clash", "ddtank-ballistics")
        validated = self.validator.validate_gdd(gdd)
        self.assertEqual(validated["gdd_schema_version"], GDD_SCHEMA_VERSION)
        self.assertEqual(len(validated["sections"]), len(GDD_SECTIONS))

    def test_gdd_missing_section_raises_validation_error(self) -> None:
        gdd = self.generator.build_default_gdd("tank-clash", "Tank Clash", "ddtank-ballistics")
        del gdd["sections"]["monetization"]
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_gdd(gdd)
        self.assertEqual(ctx.exception.field, "sections.monetization")

    def test_unknown_root_field_rejected_fail_closed(self) -> None:
        corrupt = dict(self.valid_spec)
        corrupt["injected_extra_field"] = "unexpected"
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "injected_extra_field")

    def test_unknown_gdd_section_rejected_fail_closed(self) -> None:
        gdd = self.generator.build_default_gdd("tank-clash", "Tank Clash", "ddtank-ballistics")
        gdd["sections"]["secret_backdoor"] = "should fail"
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_gdd(gdd)
        self.assertIn("secret_backdoor", ctx.exception.field)

    def test_bool_cannot_masquerade_as_int_or_float(self) -> None:
        corrupt = dict(self.valid_spec, spec_schema_version=True)
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt)
        self.assertEqual(ctx.exception.field, "spec_schema_version")

        corrupt_enemy = json.loads(json.dumps(self.valid_spec))
        corrupt_enemy["enemies"][0]["base_health"] = True
        with self.assertRaises(ValidationError) as ctx2:
            self.validator.validate_spec(corrupt_enemy)
        self.assertIn("base_health", ctx2.exception.field)

    def test_invalid_semver_and_total_rooms_mismatch_rejected(self) -> None:
        corrupt_ver = dict(self.valid_spec, version="1.2")
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate_spec(corrupt_ver)
        self.assertEqual(ctx.exception.field, "version")

        corrupt_rooms = json.loads(json.dumps(self.valid_spec))
        corrupt_rooms["worlds_and_levels"]["total_rooms"] = 99
        with self.assertRaises(ValidationError) as ctx2:
            self.validator.validate_spec(corrupt_rooms)
        self.assertEqual(ctx2.exception.field, "worlds_and_levels.total_rooms")

    def test_check_compatibility_version_and_engine(self) -> None:
        compat = self.validator.check_compatibility(
            self.valid_spec,
            required_engine="godot",
            required_engine_version="4.4.stable",
            required_spec_major=0,
        )
        self.assertTrue(compat["compatible"])
        self.assertEqual(len(compat["digest"]), 64)

        with self.assertRaises(SchemaCompatibilityError):
            self.validator.check_compatibility(self.valid_spec, required_spec_major=2)

        with self.assertRaises(SchemaCompatibilityError):
            self.validator.check_compatibility(self.valid_spec, required_engine_version="4.3-stable")


class TestSpecificationGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_spec_gen_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.generator = SpecificationGenerator(self.manager)
        # Cria projeto para testes
        self.manager.create_project(
            project_id="rogue-clash",
            name="Rogue Clash",
            genre="roguelike",
        )

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_generate_and_save_spec_creates_file_in_project_workspace(self) -> None:
        spec = self.generator.generate_and_save_spec("rogue-clash")
        self.assertEqual(spec["game_id"], "rogue-clash")
        self.assertEqual(spec["genre"], "roguelike")

        spec_path = self.manager.resolve_game_path("rogue-clash", "specs/game_specification.json")
        self.assertTrue(spec_path.exists())

        saved = json.loads(spec_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["spec_id"], spec["spec_id"])

        # Re-validação a partir do disco
        validated = self.generator.validator.validate_spec(saved)
        self.assertEqual(validated["name"], "Rogue Clash")

    def test_generate_and_save_gdd_creates_json_and_markdown(self) -> None:
        gdd = self.generator.generate_and_save_gdd("rogue-clash")
        self.assertEqual(gdd["title"], "Rogue Clash")

        # Verifica gdd.json
        gdd_json_path = self.manager.resolve_game_path("rogue-clash", "gdd/gdd.json")
        self.assertTrue(gdd_json_path.exists())

        # Verifica gdd.md
        gdd_md_path = self.manager.resolve_game_path("rogue-clash", "gdd/gdd.md")
        self.assertTrue(gdd_md_path.exists())
        md_text = gdd_md_path.read_text(encoding="utf-8")
        self.assertIn("# Game Design Document — Rogue Clash", md_text)
        self.assertIn("## 1. Concept", md_text)
        self.assertIn("## 25. Acceptance Criteria", md_text)

    def test_anchor_project_is_protected_from_spec_and_gdd_writes(self) -> None:
        with self.assertRaises(ProtectedProject):
            self.generator.generate_and_save_spec(ANCHOR_PROJECT_ID)
        with self.assertRaises(ProtectedProject):
            self.generator.generate_and_save_gdd(ANCHOR_PROJECT_ID)

    def test_custom_spec_cross_project_isolation_blocked(self) -> None:
        foreign_spec = self.generator.build_default_spec("other-game", "Other", "arcade")
        with self.assertRaises(ValidationError) as ctx:
            self.generator.generate_and_save_spec("rogue-clash", custom_spec=foreign_spec)
        self.assertEqual(ctx.exception.field, "game_id")

    def test_spec_approval_flow_and_tamper_detection(self) -> None:
        self.generator.generate_and_save_spec("rogue-clash")
        # Exige GDD por padrão antes de aprovar
        with self.assertRaises(ValidationError):
            self.generator.approve_specification("rogue-clash", approver="op", decision_notes="ok")

        # Gera GDD vinculado e aprova
        self.generator.generate_and_save_gdd("rogue-clash")
        approval = self.generator.approve_specification(
            "rogue-clash",
            approver="lead_designer",
            decision_notes="Spec e GDD validados",
        )
        self.assertTrue(approval["approved"])
        self.assertTrue(approval["gdd_linked"])

        # Verificação confirma integridade SHA-256
        verified = self.generator.verify_spec_approved("rogue-clash")
        self.assertEqual(verified["spec_sha256"], approval["spec_sha256"])

        # Alteração pós-aprovação quebra integridade (fail-closed)
        spec_path = self.manager.resolve_game_path("rogue-clash", "specs/game_specification.json")
        tampered = json.loads(spec_path.read_text(encoding="utf-8"))
        tampered["name"] = "Rogue Clash Tampered"
        spec_path.write_text(json.dumps(tampered), encoding="utf-8")

        with self.assertRaises(ApprovalRequired):
            self.generator.verify_spec_approved("rogue-clash")


class TestSpecificationCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_spec_cli_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.manager.create_project("cli-spec-game", name="CLI Spec Game", genre="platformer-2d")

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

    def test_cli_spec_generate_and_validate(self) -> None:
        # Gera spec via CLI
        code, stdout, stderr = self._run_cli(["spec-generate", "cli-spec-game"])
        self.assertEqual(code, 0)
        res = json.loads(stdout)
        self.assertEqual(res["status"], "GENERATED")

        # Valida spec gerada via CLI
        spec_path = self.manager.resolve_game_path("cli-spec-game", "specs/game_specification.json")
        code, stdout, stderr = self._run_cli(["spec-validate", str(spec_path)])
        self.assertEqual(code, 0)
        val_res = json.loads(stdout)
        self.assertEqual(val_res["status"], "VALID")
        self.assertEqual(val_res["game_id"], "cli-spec-game")

    def test_cli_spec_validate_corrupt_file_returns_code_1(self) -> None:
        corrupt_file = self.tmp_dir / "bad_spec.json"
        corrupt_file.write_text('{"spec_id": "bad"}', encoding="utf-8")
        code, stdout, stderr = self._run_cli(["spec-validate", str(corrupt_file)])
        self.assertEqual(code, 1)
        err = json.loads(stderr)
        self.assertEqual(err["error"], "ValidationError")

    def test_cli_gdd_generate(self) -> None:
        code, stdout, stderr = self._run_cli(["gdd-generate", "cli-spec-game"])
        self.assertEqual(code, 0)
        res = json.loads(stdout)
        self.assertEqual(res["status"], "GENERATED")
        self.assertEqual(res["title"], "CLI Spec Game")

    def test_cli_spec_validate_malformed_json_returns_code_1(self) -> None:
        broken_file = self.tmp_dir / "broken.json"
        broken_file.write_text("{broken json", encoding="utf-8")
        code, stdout, stderr = self._run_cli(["spec-validate", str(broken_file)])
        self.assertEqual(code, 1)
        err = json.loads(stderr)
        self.assertEqual(err["error"], "ValidationError")

    def test_cli_spec_validate_by_project_and_approve(self) -> None:
        self._run_cli(["spec-generate", "cli-spec-game"])
        self._run_cli(["gdd-generate", "cli-spec-game"])

        code, stdout, _ = self._run_cli(["spec-validate", "cli-spec-game", "--project"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["status"], "VALID")

        code_app, stdout_app, _ = self._run_cli([
            "spec-approve",
            "cli-spec-game",
            "--approver",
            "operador",
            "--notes",
            "Aprovado para selecao de template",
        ])
        self.assertEqual(code_app, 0)
        app_res = json.loads(stdout_app)
        self.assertTrue(app_res["approved"])
        self.assertEqual(app_res["project_id"], "cli-spec-game")


if __name__ == "__main__":
    unittest.main()
