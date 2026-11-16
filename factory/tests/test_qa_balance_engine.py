"""Suite de testes unitarios, balanceamento multi-genero e QA Engine E2E no Godot 4.4 (Fase 8)."""
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
from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.generator.config_mapper import map_spec_to_runtime_config
from factory.playforge.generator.game_generator import GameGenerator
from factory.playforge.mcp.schemas import MCPAccessDenied
from factory.playforge.mcp.servers import create_testing_mcp
from factory.playforge.qa_engine import (
    BalanceVerificationError,
    BalanceVerifierEngine,
    QAEngine,
    QAValidationError,
    StaticAnalyzer,
)
from factory.playforge.registry import ProjectManager
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.schemas import SUPPORTED_GENRES

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_TEMPLATE_DIR = REPO_ROOT / "templates" / "godot-2d-action-rpg" / "1.0.0"


def _run_cli(repo_root: Path, *args: str) -> tuple[int, str, str]:
    out_buf, err_buf = io.StringIO(), io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        code = cli.main(["--repo-root", str(repo_root), *args])
    return code, out_buf.getvalue(), err_buf.getvalue()


def _create_approved_project(
    repo_root: Path,
    *,
    project_id: str = "qa-hero",
    genre: str = "action-rpg",
    with_godot_project: bool = False,
) -> tuple[ProjectManager, SpecificationGenerator]:
    manager = ProjectManager(repo_root=repo_root)
    if not (repo_root / "data" / "projects.json").exists():
        manager.init_registry()
    manager.create_project(project_id, name=f"Game {project_id}", genre=genre)
    spec_gen = SpecificationGenerator(manager)
    spec_gen.generate_and_save_spec(project_id)
    spec_gen.generate_and_save_gdd(project_id)
    spec_gen.approve_specification(project_id, approver="operador", decision_notes="QA test")
    if with_godot_project:
        GameGenerator(manager).generate_project(
            project_id,
            run_godot_tests=False,
            verify_template_tests=False,
            package_preview_build=False,
        )
    return manager, spec_gen


class TestStaticAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_qa_static_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        shutil.copytree(
            REAL_TEMPLATE_DIR,
            self.repo_root / "templates" / "godot-2d-action-rpg" / "1.0.0",
        )
        (self.repo_root / "templates" / ".gdignore").write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_real_anchor_zaikor_passes_static_audit_read_only(self) -> None:
        manager = ProjectManager(repo_root=REPO_ROOT)
        report = StaticAnalyzer(manager).audit_project("zaikor")
        self.assertTrue(report["passed"], msg=f"Violacoes inesperadas no zaikor: {report['violations']}")
        self.assertGreaterEqual(report["core_files_checked"], 6)
        self.assertGreaterEqual(report["res_refs_checked"], 1)
        self.assertEqual(report["violations"], [])

    def test_rejects_core_purity_broken_res_secrets_and_hash_tampering(self) -> None:
        manager, _ = _create_approved_project(self.repo_root, project_id="static-fail", with_godot_project=True)
        analyzer = StaticAnalyzer(manager)
        ok_report = analyzer.audit_project("static-fail")
        self.assertTrue(ok_report["passed"], msg=str(ok_report["violations"]))

        # 1. Violacao GT-01 em src/core/ (comentarios '#' nao geram falso positivo, codigo real sim)
        core_file = manager.resolve_game_path("static-fail", "src/core/game_loop_core.gd")
        core_file.write_text(
            core_file.read_text(encoding="utf-8") + "\n# Node FileAccess comentario permitido\nvar bad := FileAccess.open(\"res://a\", FileAccess.READ)\n",
            encoding="utf-8",
        )
        # 2. Referencia res:// quebrada em src/engine/
        main_gd = manager.resolve_game_path("static-fail", "src/engine/main.gd")
        main_gd.write_text(
            main_gd.read_text(encoding="utf-8") + '\nconst MISSING := preload("res://src/nao_existe.gd")\n',
            encoding="utf-8",
        )
        # 3. Credencial literal + arquivo .env proibido
        cfg_file = manager.resolve_game_path("static-fail", "config/leaked.cfg")
        cfg_file.write_text('api_key = "sk-live-secret-1234567890abcdef"\n', encoding="utf-8")
        env_file = manager.resolve_game_path("static-fail", ".env")
        env_file.write_text("SECRET=123\n", encoding="utf-8")

        bad_report = analyzer.audit_project("static-fail")
        self.assertFalse(bad_report["passed"])
        rules = {v["rule"] for v in bad_report["violations"]}
        self.assertIn("GT-01_CORE_PURITY", rules)
        self.assertIn("GT-03_RES_REFERENCE", rules)
        self.assertIn("SEC_HARDCODED_SECRET", rules)
        self.assertIn("SEC_FORBIDDEN_FILE", rules)
        self.assertIn("GEN_INTEGRITY", rules)


class TestBalanceVerifierEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_qa_balance_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_all_11_genres_simulate_deterministically_with_seed(self) -> None:
        manager = ProjectManager(repo_root=self.repo_root)
        manager.init_registry()
        spec_gen = SpecificationGenerator(manager)
        bal = BalanceVerifierEngine(manager)

        for idx, genre in enumerate(SUPPORTED_GENRES):
            pid = f"bal-g-{idx}"
            manager.create_project(pid, name=f"Genre {genre}", genre=genre)
            spec = spec_gen.generate_and_save_spec(pid)
            runtime_cfg, _ = map_spec_to_runtime_config(spec)
            rt_path = manager.resolve_game_path(pid, "config/template_defaults.json")
            rt_path.parent.mkdir(parents=True, exist_ok=True)
            rt_path.write_text(json.dumps(runtime_cfg, indent=2), encoding="utf-8")

            r1 = bal.verify_project_balance(pid, seed=2026)
            r2 = bal.verify_project_balance(pid, seed=2026)
            self.assertTrue(r1["passed"], msg=f"Genero {genre} falhou inesperadamente: {r1}")
            self.assertEqual(r1["genre"], genre)
            self.assertEqual(len(r1["profiles"]), 3)
            self.assertEqual(r1["profiles"], r2["profiles"])
            self.assertTrue(manager.resolve_game_path(pid, "specs/balance_report.json").is_file())

    def test_rejects_unwinnable_campaign_and_bad_gacha_rates_fail_closed(self) -> None:
        manager, _ = _create_approved_project(self.repo_root, project_id="unwinnable-game")
        spec_path = manager.resolve_game_path("unwinnable-game", "specs/game_specification.json")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["characters"][0]["stats"]["base_health"] = 50
        spec["characters"][0]["stats"]["base_attack"] = 5
        spec["enemies"][-1]["base_health"] = 50000
        spec["enemies"][-1]["base_damage"] = 900
        spec["monetization"]["gacha_rates"] = {"common": 0.5, "epic": 0.25}
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

        engine = BalanceVerifierEngine(manager)
        rep = engine.verify_project_balance("unwinnable-game", strict=False)
        self.assertFalse(rep["passed"])
        self.assertGreaterEqual(len(rep["findings"]), 2)
        with self.assertRaises(BalanceVerificationError):
            engine.verify_project_balance("unwinnable-game", strict=True)

    def test_real_anchor_zaikor_passes_balance_and_godot_action_verifier(self) -> None:
        manager = ProjectManager(repo_root=REPO_ROOT)
        rep = BalanceVerifierEngine(manager).verify_project_balance("zaikor", run_godot=True)
        self.assertTrue(rep["passed"], msg=str(rep["findings"]))
        self.assertIsNotNone(rep["godot_verifier"])
        self.assertTrue(rep["godot_verifier"]["passed"])
        self.assertEqual(rep["godot_verifier"]["profiles"].get("F2P_PURE"), "PASS")
        self.assertEqual(rep["godot_verifier"]["profiles"].get("F2P_REWARDED"), "PASS")


class TestQAEngineRealGodotAndMCP(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_qa_e2e_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        shutil.copytree(
            REAL_TEMPLATE_DIR,
            self.repo_root / "templates" / "godot-2d-action-rpg" / "1.0.0",
        )
        (self.repo_root / "templates" / ".gdignore").write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_full_4_pillar_qa_pipeline_e2e_with_real_godot_and_assets(self) -> None:
        manager, _ = _create_approved_project(
            self.repo_root,
            project_id="qa-e2e",
            genre="action-rpg",
            with_godot_project=True,
        )
        AssetRegistry(manager).generate_default_pack("qa-e2e")

        qa = QAEngine(manager)
        report = qa.run_qa_pipeline(
            "qa-e2e",
            with_godot=True,
            with_assets=True,
            require_assets=True,
            frames=5,
            strict=True,
        )
        self.assertTrue(report["passed"], msg=str(report))
        self.assertEqual(report["failed_pillars"], [])
        pillars = report["pillars"]
        self.assertTrue(pillars["static"]["passed"])
        self.assertTrue(pillars["balance"]["passed"])
        self.assertTrue(pillars["godot_suites"]["passed"])
        self.assertTrue(pillars["godot_profile"]["passed"])
        metrics = pillars["godot_profile"]["metrics"]
        self.assertGreater(metrics["boot_ms"], 0.0)
        self.assertGreater(metrics["static_memory_bytes"], 0)
        self.assertEqual(metrics["orphan_nodes_after_free"], 0)
        self.assertTrue(pillars["assets"]["passed"])
        self.assertTrue(pillars["assets"]["godot_verified"])
        self.assertTrue(manager.resolve_game_path("qa-e2e", "specs/qa_report.json").is_file())

    def test_detects_real_godot_orphan_node_leak_fail_closed(self) -> None:
        manager, _ = _create_approved_project(
            self.repo_root,
            project_id="leak-proj",
            with_godot_project=True,
        )
        main_gd = manager.resolve_game_path("leak-proj", "src/engine/main.gd")
        main_gd.write_text(
            main_gd.read_text(encoding="utf-8") + "\nfunc _enter_tree() -> void:\n\tvar _leaked := Node.new()\n",
            encoding="utf-8",
        )
        qa = QAEngine(manager)
        prof = qa.profile_project_godot("leak-proj", frames=3, strict=False)
        self.assertFalse(prof["passed"])
        self.assertGreater(prof["metrics"]["orphan_nodes_after_free"], 0)
        with self.assertRaises(QAValidationError):
            qa.profile_project_godot("leak-proj", frames=3, strict=True)

    def test_real_anchor_zaikor_passes_godot_profile_probe(self) -> None:
        manager = ProjectManager(repo_root=REPO_ROOT)
        prof = QAEngine(manager).profile_project_godot("zaikor", frames=3, strict=True)
        self.assertTrue(prof["passed"])
        self.assertEqual(prof["metrics"]["orphan_nodes_after_free"], 0)
        self.assertGreater(prof["metrics"]["static_memory_bytes"], 0)

    def test_mcp_testing_tools_least_privilege_and_cli_roundtrip(self) -> None:
        manager, _ = _create_approved_project(
            self.repo_root,
            project_id="qa-cli-mcp",
            genre="idle-rpg",
            with_godot_project=True,
        )
        mcp = create_testing_mcp(manager)

        # qa e balance autorizados; research bloqueado por minimo privilegio
        static_res = mcp.call_tool("qa_run_static_audit", {"project_id": "qa-cli-mcp"}, agent_id="qa")
        self.assertTrue(static_res["passed"])

        bal_res = mcp.call_tool("qa_run_balance_audit", {"project_id": "qa-cli-mcp"}, agent_id="balance")
        self.assertTrue(bal_res["passed"])

        full_res = mcp.call_tool(
            "qa_run_full_pipeline",
            {"project_id": "qa-cli-mcp", "with_godot": False, "with_assets": False},
            agent_id="qa",
        )
        self.assertTrue(full_res["passed"])
        read_res = mcp.call_tool("qa_read_report", {"project_id": "qa-cli-mcp"}, agent_id="auditor")
        self.assertEqual(read_res["project_id"], "qa-cli-mcp")

        with self.assertRaises(MCPAccessDenied):
            mcp.call_tool("qa_run_full_pipeline", {"project_id": "qa-cli-mcp"}, agent_id="research")

        # CLI roundtrip (qa-static, qa-balance, qa-profile, qa-run --strict)
        c1, out1, _ = _run_cli(self.repo_root, "qa-static", "qa-cli-mcp", "--strict")
        self.assertEqual(c1, 0, msg=out1)
        self.assertTrue(json.loads(out1)["passed"])

        c2, out2, _ = _run_cli(self.repo_root, "qa-balance", "qa-cli-mcp", "--genre", "ddtank-ballistics", "--strict")
        self.assertEqual(c2, 0, msg=out2)
        self.assertTrue(json.loads(out2)["passed"])

        c3, out3, _ = _run_cli(self.repo_root, "qa-profile", "qa-cli-mcp", "--frames", "3")
        self.assertEqual(c3, 0, msg=out3)
        self.assertEqual(json.loads(out3)["metrics"]["orphan_nodes_after_free"], 0)

        c4, out4, _ = _run_cli(self.repo_root, "qa-run", "qa-cli-mcp", "--strict")
        self.assertEqual(c4, 0, msg=out4)
        self.assertTrue(json.loads(out4)["passed"])
