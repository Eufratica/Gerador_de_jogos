"""Suíte de testes unitários do Factory Core da PlayForge Factory (Fase 2)."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from factory.playforge import cli
from factory.playforge.logging_utils import StructuredLogger
from factory.playforge.models import (
    ANCHOR_PROJECT_ID,
    APPROVAL_STAGES,
    KIND_ANCHOR,
    KIND_GAME,
    SCHEMA_VERSION,
    STAGES,
    ApprovalRequired,
    EvidenceRequired,
    InvalidProjectId,
    InvalidTransition,
    ProjectExists,
    ProjectNotFound,
    ProtectedProject,
    RegistryCorrupt,
    WorkspaceEscape,
    WorkspaceExists,
)
from factory.playforge.registry import PROJECT_SUBDIRS, ProjectManager, validate_project_id


class TestFactoryCoreModelsAndLogging(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_models_"))

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_validate_project_id_valid_slugs(self) -> None:
        valid_slugs = ["game-002", "ddtank-arena", "zaikor-v2", "abc", "a" * 40]
        for slug in valid_slugs:
            self.assertEqual(validate_project_id(slug), slug)

    def test_validate_project_id_invalid_slugs(self) -> None:
        invalid_slugs = [
            "",
            "123game",
            "Game-002",
            "game_002",
            "game 002",
            "ab",  # < 3 caracteres
            "a" * 41,  # > 40 caracteres
            "../escape",
            "/absolute",
            "game/sub",
        ]
        for slug in invalid_slugs:
            with self.assertRaises(InvalidProjectId, msg=f"Slug deveria ser invalido: {slug!r}"):
                validate_project_id(slug)

    def test_structured_logger_writes_json_lines(self) -> None:
        log_file = self.tmp_dir / "logs" / "test.jsonl"
        fake_clock = lambda: "2026-11-15T15:00:00+00:00"
        logger = StructuredLogger(log_file, clock=fake_clock)

        logger.log("INFO", "test_event_1", user="test_agent", code=42)
        logger.log("WARN", "test_event_2", reason="gate_blocked")

        self.assertTrue(log_file.exists())
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 2)

        record1 = json.loads(lines[0])
        self.assertEqual(record1["ts"], "2026-11-15T15:00:00+00:00")
        self.assertEqual(record1["level"], "INFO")
        self.assertEqual(record1["event"], "test_event_1")
        self.assertEqual(record1["user"], "test_agent")
        self.assertEqual(record1["code"], 42)

        record2 = json.loads(lines[1])
        self.assertEqual(record2["level"], "WARN")
        self.assertEqual(record2["event"], "test_event_2")


class TestProjectManager(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_pm_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        self.registry_path = self.tmp_dir / "data" / "registry" / "projects.json"
        self.games_root = self.repo_root / "games"
        self.log_path = self.tmp_dir / "data" / "logs" / "factory.jsonl"
        self.fixed_time = "2026-11-15T12:00:00+00:00"
        self.manager = ProjectManager(
            repo_root=self.repo_root,
            registry_path=self.registry_path,
            games_root=self.games_root,
            log_path=self.log_path,
            clock=lambda: self.fixed_time,
        )

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_init_registry_creates_protected_anchor(self) -> None:
        data = self.manager.init_registry()
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(data["created_at"], self.fixed_time)
        self.assertIn(ANCHOR_PROJECT_ID, data["projects"])

        anchor = data["projects"][ANCHOR_PROJECT_ID]
        self.assertEqual(anchor["project_id"], ANCHOR_PROJECT_ID)
        self.assertEqual(anchor["kind"], KIND_ANCHOR)
        self.assertTrue(anchor["protected"])
        self.assertEqual(anchor["workspace"], ".")
        self.assertEqual(anchor["stage"], "PREVIEW")
        self.assertTrue(self.registry_path.exists())

        # Chamada repetida deve ser idempotente
        data_second = self.manager.init_registry()
        self.assertEqual(data, data_second)

    def test_create_project_isolated_structure(self) -> None:
        project = self.manager.create_project(
            project_id="game-002",
            name="Shadow Arena 2D",
            genre="action-rpg",
        )
        self.assertEqual(project["project_id"], "game-002")
        self.assertEqual(project["kind"], KIND_GAME)
        self.assertFalse(project["protected"])
        self.assertEqual(project["stage"], STAGES[0])  # IDEIA
        self.assertEqual(project["version"], "0.1.0")

        # Verifica pastas isoladas no disco
        ws_dir = self.games_root / "game-002"
        self.assertTrue(ws_dir.exists())
        for subdir in PROJECT_SUBDIRS:
            self.assertTrue((ws_dir / subdir).is_dir())

        # Verifica manifesto no workspace
        manifest_path = ws_dir / "project_manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["project_id"], "game-002")
        self.assertEqual(manifest["name"], "Shadow Arena 2D")

    def test_create_duplicate_project_fails(self) -> None:
        self.manager.create_project("game-002", name="First", genre="idle")
        with self.assertRaises(ProjectExists):
            self.manager.create_project("game-002", name="Second", genre="idle")

    def test_create_project_cannot_overwrite_anchor(self) -> None:
        self.manager.init_registry()
        with self.assertRaises(ProtectedProject):
            self.manager.create_project(ANCHOR_PROJECT_ID, name="Fake Anchor", genre="action")

    def test_create_project_rejects_existing_workspace(self) -> None:
        # Pre-cria a pasta no filesystem antes de criar no registro
        orphan_dir = self.games_root / "orphan-game"
        orphan_dir.mkdir(parents=True)
        with self.assertRaises(WorkspaceExists):
            self.manager.create_project("orphan-game", name="Orphan", genre="puzzle")

    def test_resolve_game_path_confinement_and_anti_traversal(self) -> None:
        self.manager.create_project("sandbox-game", name="Sandbox", genre="arcade")
        ws = self.games_root / "sandbox-game"

        # Caminho válido dentro de specs
        valid_path = self.manager.resolve_game_path("sandbox-game", "specs/game_spec.json")
        self.assertEqual(valid_path, (ws / "specs" / "game_spec.json").resolve())

        # Tentativa de escape com ..
        with self.assertRaises(WorkspaceEscape):
            self.manager.resolve_game_path("sandbox-game", "../../etc/passwd")

        # Tentativa de caminho absoluto
        with self.assertRaises(WorkspaceEscape):
            self.manager.resolve_game_path("sandbox-game", str(self.tmp_dir / "escaped.txt"))

    def test_state_machine_sequential_advance(self) -> None:
        self.manager.create_project("flow-game", name="Flow", genre="rpg")

        # IDEIA -> RESEARCH
        res = self.manager.advance_stage(
            "flow-game",
            target_stage="RESEARCH",
            actor="research_agent",
            evidence="doc/research_v1.md aprovado",
            notes="Pesquisa de concorrentes",
        )
        self.assertEqual(res["stage"], "RESEARCH")
        self.assertEqual(len(res["history"]), 1)
        self.assertEqual(res["history"][0]["from"], "IDEIA")
        self.assertEqual(res["history"][0]["to"], "RESEARCH")
        self.assertEqual(res["history"][0]["evidence"], "doc/research_v1.md aprovado")

    def test_state_machine_rejects_without_evidence(self) -> None:
        self.manager.create_project("ev-game", name="Evidence Check", genre="puzzle")
        with self.assertRaises(EvidenceRequired):
            self.manager.advance_stage("ev-game", "RESEARCH", actor="agent", evidence="")
        with self.assertRaises(EvidenceRequired):
            self.manager.advance_stage("ev-game", "RESEARCH", actor="agent", evidence="   ")

    def test_state_machine_rejects_stage_skip(self) -> None:
        self.manager.create_project("skip-game", name="Skip Check", genre="arcade")
        # Tenta pular de IDEIA direto para GDD
        with self.assertRaises(InvalidTransition):
            self.manager.advance_stage("skip-game", "GDD", actor="agent", evidence="ev")

    def test_human_approval_gate_architecture(self) -> None:
        self.manager.create_project("gate-game", name="Gate Check", genre="strategy")
        # Avança até APROVACAO_HUMANA_ARQUITETURA:
        # IDEIA -> RESEARCH -> GDD -> GAME_SPECIFICATION -> ARQUITETURA -> APROVACAO_HUMANA_ARQUITETURA
        stages_to_reach = [
            "RESEARCH",
            "GDD",
            "GAME_SPECIFICATION",
            "ARQUITETURA",
            "APROVACAO_HUMANA_ARQUITETURA",
        ]
        for s in stages_to_reach:
            self.manager.advance_stage("gate-game", s, actor="agent", evidence=f"ev_{s}")

        # Tentar avançar para SELECAO_DE_TEMPLATE sem aprovação deve bloquear (fail-closed)
        with self.assertRaises(ApprovalRequired):
            self.manager.advance_stage("gate-game", "SELECAO_DE_TEMPLATE", actor="agent", evidence="spec_ok")

        # Registra aprovação humana
        appr = self.manager.record_approval(
            "gate-game",
            approval_stage="APROVACAO_HUMANA_ARQUITETURA",
            approver="lead_architect",
            decision_notes="Arquitetura validada conforme ADR-002 e ADR-006",
        )
        self.assertIn("APROVACAO_HUMANA_ARQUITETURA", appr["approvals"])
        self.assertTrue(appr["approvals"]["APROVACAO_HUMANA_ARQUITETURA"]["approved"])

        # Agora o avanço para SELECAO_DE_TEMPLATE deve ser destravado
        adv = self.manager.advance_stage(
            "gate-game",
            "SELECAO_DE_TEMPLATE",
            actor="agent",
            evidence="Aprovacao humana conferida no registro",
        )
        self.assertEqual(adv["stage"], "SELECAO_DE_TEMPLATE")

    def test_anchor_project_is_immutable_and_cannot_be_deleted(self) -> None:
        self.manager.init_registry()
        with self.assertRaises(ProtectedProject):
            self.manager.advance_stage(ANCHOR_PROJECT_ID, "BUILD", actor="agent", evidence="ev")

        with self.assertRaises(ProtectedProject):
            self.manager.record_approval(
                ANCHOR_PROJECT_ID,
                "APROVACAO_HUMANA_PREVIEW",
                approver="admin",
                decision_notes="note",
            )

        with self.assertRaises(ProtectedProject):
            self.manager.delete_project(ANCHOR_PROJECT_ID, confirm=True)

    def test_delete_mutable_project_requires_confirmation(self) -> None:
        self.manager.create_project("temp-game", name="Temporary", genre="casual")
        ws = self.games_root / "temp-game"
        self.assertTrue(ws.exists())

        # Sem confirm=True falha fail-closed
        with self.assertRaises(ApprovalRequired):
            self.manager.delete_project("temp-game", confirm=False)
        self.assertTrue(ws.exists())

        # Com confirm=True remove do registro e apaga pasta
        self.manager.delete_project("temp-game", confirm=True)
        self.assertFalse(ws.exists())
        with self.assertRaises(ProjectNotFound):
            self.manager.get_project("temp-game")

    def test_corrupted_registry_raises_registry_corrupt(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        # Escreve JSON inválido
        self.registry_path.write_text("{ broken json", encoding="utf-8")
        with self.assertRaises(RegistryCorrupt):
            self.manager.load_registry()

        # Escreve schema_version incompatível
        self.registry_path.write_text('{"schema_version": 999, "projects": {}}', encoding="utf-8")
        with self.assertRaises(RegistryCorrupt):
            self.manager.load_registry()


class TestFactoryCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_test_cli_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        # Inicializa registry
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

    def test_cli_list_contains_anchor(self) -> None:
        code, stdout, stderr = self._run_cli(["list"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout)
        projects = payload["projects"]
        pids = [p["project_id"] for p in projects]
        self.assertIn(ANCHOR_PROJECT_ID, pids)

    def test_cli_create_and_show_project(self) -> None:
        code, stdout, stderr = self._run_cli([
            "create",
            "cli-game",
            "--name",
            "CLI Game",
            "--genre",
            "2d-arcade",
        ])
        self.assertEqual(code, 0)
        created = json.loads(stdout)
        self.assertEqual(created["project_id"], "cli-game")

        # Exibe via show
        code, stdout, stderr = self._run_cli(["show", "cli-game"])
        self.assertEqual(code, 0)
        shown = json.loads(stdout)
        self.assertEqual(shown["name"], "CLI Game")

    def test_cli_error_returns_json_and_code_1(self) -> None:
        # Tenta criar projeto duplicado
        self._run_cli(["create", "dup-game", "--name", "Dup", "--genre", "idle"])
        code, stdout, stderr = self._run_cli(["create", "dup-game", "--name", "Dup2", "--genre", "idle"])
        self.assertEqual(code, 1)
        err = json.loads(stderr)
        self.assertEqual(err["error"], "ProjectExists")


if __name__ == "__main__":
    unittest.main()
