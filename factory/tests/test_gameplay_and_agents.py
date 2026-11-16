"""Testes de sistemas modulares de gameplay e alinhamento de agentes da Secao 10 (P4)."""
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
from factory.playforge.ai import AgentRegistry, get_engineering_role_catalog
from factory.playforge.gameplay_systems import (
    GAMEPLAY_SYSTEM_IDS,
    GameplaySystemError,
    GameplaySystemInjector,
)
from factory.playforge.models import ProtectedProject
from factory.playforge.registry import ProjectManager


class TestGameplaySystemsAndAgents(unittest.TestCase):
    def test_catalog_exposes_8_systems_multi_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            items = GameplaySystemInjector(mgr).list_catalog()
            self.assertEqual(len(items), 8)
            self.assertEqual(set(GAMEPLAY_SYSTEM_IDS), {item["system_id"] for item in items})
            for item in items:
                self.assertEqual(item["supported_engines"], ["godot", "unity", "unreal"])

    def test_inject_on_demand_writes_only_requested_systems_per_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            mgr.create_project("g-godot", name="Godot Game", genre="action-rpg", engine="godot", engine_version="4.4-stable")
            mgr.create_project("g-unity", name="Unity Game", genre="action-rpg", engine="unity", engine_version="6000.0-lts")
            mgr.create_project("g-unreal", name="Unreal Game", genre="action-rpg", engine="unreal", engine_version="5.4")

            inj = GameplaySystemInjector(mgr)

            res_g = inj.inject_systems("g-godot", ["locomotion", "combat_action"])
            self.assertEqual(res_g["enabled_systems"], ["locomotion", "combat_action"])
            self.assertTrue((mgr.resolve_game_path("g-godot", "src/core/systems/locomotion.gd")).is_file())
            self.assertTrue((mgr.resolve_game_path("g-godot", "src/core/systems/combat_action.gd")).is_file())
            # Regra da Secao 8: sistemas nao solicitados nao devem ser gerados
            self.assertFalse((mgr.resolve_game_path("g-godot", "src/core/systems/quests_dialogue.gd")).exists())
            self.assertFalse((mgr.resolve_game_path("g-godot", "src/core/systems/inventory_crafting.gd")).exists())

            res_u = inj.inject_systems("g-unity", ["inventory_crafting"])
            self.assertTrue((mgr.resolve_game_path("g-unity", "Assets/Scripts/Core/Systems/InventoryCraftingCore.cs")).is_file())
            self.assertEqual(res_u["engine"], "unity")

            res_ue = inj.inject_systems("g-unreal", ["quests_dialogue"])
            self.assertTrue((mgr.resolve_game_path("g-unreal", "Source/Core/Systems/QuestsDialogueCoreTypes.h")).is_file())
            self.assertEqual(res_ue["engine"], "unreal")

    def test_inject_protects_anchor_and_fails_closed_on_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            mgr.create_project("g-test", name="G Test", genre="action-rpg")
            inj = GameplaySystemInjector(mgr)

            with self.assertRaises(ProtectedProject):
                inj.inject_systems("zaikor", ["locomotion"])
            with self.assertRaises(GameplaySystemError):
                inj.inject_systems("g-test", [])
            with self.assertRaises(GameplaySystemError):
                inj.inject_systems("g-test", ["nonexistent_system"])
            with self.assertRaises(GameplaySystemError):
                inj.inject_systems("g-test", ["locomotion"], engine="cryengine")

    def test_section10_13_roles_alignment_preserves_14_contracts(self) -> None:
        reg = AgentRegistry()
        self.assertEqual(len(reg.list_agents()), 14)
        roles = get_engineering_role_catalog(reg)
        self.assertEqual(len(roles), 13)
        role_ids = [r["role_id"] for r in roles]
        self.assertIn("engine_selection", role_ids)
        self.assertIn("modeling_3d", role_ids)
        self.assertIn("build_export", role_ids)
        for r in roles:
            self.assertTrue(r["mapped_agent_ids"])
            self.assertTrue(r["autonomy_bounds"])

    def test_cli_gameplay_and_agent_roles_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = ["--repo-root", tmp]
            self.assertEqual(cli.main(base + ["init"]), 0)
            self.assertEqual(cli.main(base + ["create", "gmp-cli", "--name", "Gmp Cli", "--genre", "action-rpg"]), 0)
            self.assertEqual(cli.main(base + ["gameplay-catalog"]), 0)
            self.assertEqual(
                cli.main(base + ["gameplay-inject", "gmp-cli", "--systems", "locomotion", "save_system_versioned"]),
                0,
            )
            self.assertEqual(cli.main(base + ["agent-roles"]), 0)
            manifest = json.loads(
                (Path(tmp) / "games" / "gmp-cli" / "config" / "gameplay_systems.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["enabled_systems"], ["locomotion", "save_system_versioned"])


if __name__ == "__main__":
    unittest.main()
