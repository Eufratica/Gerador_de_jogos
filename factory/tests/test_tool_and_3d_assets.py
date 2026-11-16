"""Testes de orquestracao de ferramentas, assets 3D/PBR e novos formatos (Incremento P2)."""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from factory.playforge.asset_pipeline import AssetRegistry, AssetValidationError
from factory.playforge.asset_pipeline.synthesizer import (
    inspect_media_toolchain,
    synthesize_glb_mesh,
    synthesize_gltf_mesh,
    synthesize_obj_mesh,
    synthesize_pbr_texture_set,
)
from factory.playforge.asset_pipeline.validator import (
    inspect_fbx,
    inspect_glb,
    inspect_gltf,
    inspect_jpeg,
    inspect_mp3,
    inspect_obj,
    inspect_png,
    validate_asset_record,
)
from factory.playforge.registry import ProjectManager


def _minimal_jpeg(width: int = 8, height: int = 6) -> bytes:
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    return b"\xff\xd8" + sof + b"\xff\xda\x00\x08\x03\x01\x00\x02\x11\x00" + b"\x00" * 120 + b"\xff\xd9"


class TestModelAndMediaInspectors(unittest.TestCase):
    def test_gltf_glb_obj_roundtrip_and_flags(self) -> None:
        info = inspect_gltf(synthesize_gltf_mesh(name="a", with_material=True, with_rig=True))
        self.assertTrue(info["has_materials"])
        self.assertTrue(info["has_rig"])
        self.assertEqual(info["animation_count"], 1)
        plain = inspect_gltf(synthesize_gltf_mesh(name="b", with_material=False))
        self.assertFalse(plain["has_materials"])
        self.assertFalse(plain["has_rig"])
        glb = inspect_glb(synthesize_glb_mesh(name="c"))
        self.assertEqual(glb["format"], "glb")
        self.assertEqual(glb["mesh_count"], 1)
        obj = inspect_obj(synthesize_obj_mesh(name="d"))
        self.assertEqual(obj["vertex_count"], 8)
        self.assertEqual(obj["face_count"], 12)
        self.assertTrue(obj["has_materials"])

    def test_corrupt_models_fail_closed(self) -> None:
        with self.assertRaises(AssetValidationError):
            inspect_gltf(b'{"asset": {"version": "1.0"}, "meshes": [{}]} ' * 2)
        glb = bytearray(synthesize_glb_mesh(name="c"))
        with self.assertRaises(AssetValidationError):
            inspect_glb(bytes(glb[:-4]))
        glb[0:4] = b"xxxx"
        with self.assertRaises(AssetValidationError):
            inspect_glb(bytes(glb))
        with self.assertRaises(AssetValidationError):
            inspect_obj(b"o empty\nv 0 0 0\nf 1 2 3\n")
        with self.assertRaises(AssetValidationError):
            inspect_fbx(b"not an fbx file at all, definitely not.")

    def test_fbx_signature_accepted(self) -> None:
        info = inspect_fbx(b"Kaydara FBX Binary  \x00\x1a\x00" + b"\x00" * 32)
        self.assertEqual(info["fbx_encoding"], "binary")

    def test_jpeg_and_mp3(self) -> None:
        info = inspect_jpeg(_minimal_jpeg(8, 6))
        self.assertEqual((info["width"], info["height"]), (8, 6))
        with self.assertRaises(AssetValidationError):
            inspect_jpeg(b"\x00" * 200)
        mp3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + b"\x00" * 200
        self.assertEqual(inspect_mp3(mp3)["format"], "mp3")
        with self.assertRaises(AssetValidationError):
            inspect_mp3(b"\x00" * 300)

    def test_pbr_texture_set_is_valid_and_distinct(self) -> None:
        maps = synthesize_pbr_texture_set(width=16, height=16, surface="stone")
        self.assertEqual(set(maps), {"albedo", "normal", "roughness", "metallic", "ao"})
        for data in maps.values():
            self.assertEqual(inspect_png(data)["width"], 16)
        self.assertEqual(len({bytes(v) for v in maps.values()}), 5)
        with self.assertRaises(AssetValidationError):
            synthesize_pbr_texture_set(surface="plasma")

    def test_toolchain_marks_fmod_wwise_optional(self) -> None:
        tc = inspect_media_toolchain(repo_root=REPO_ROOT)
        audio = tc["tool_orchestration"]["audio"]
        self.assertFalse(audio["fmod"]["mandatory"])
        self.assertFalse(audio["wwise"]["mandatory"])
        self.assertTrue(audio["engine_native"]["mandatory"])
        self.assertFalse(tc["paid_services_enabled"])

    def test_extended_fields_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            mgr.create_project(project_id="ext-game", name="Ext", genre="action-rpg", engine="godot", engine_version="4.4-stable")
            reg = AssetRegistry(mgr)
            pack = reg.generate_3d_pbr_pack("ext-game")
            entry = dict(pack["assets"][0])
            entry["lod_level"] = -1
            with self.assertRaises(AssetValidationError):
                validate_asset_record(entry)
            entry = dict(pack["assets"][0])
            entry["has_rig"] = "yes"
            with self.assertRaises(AssetValidationError):
                validate_asset_record(entry)


class TestAssetRegistry3D(unittest.TestCase):
    def test_generate_3d_pack_audit_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            mgr.create_project(project_id="game3d", name="Game 3D", genre="action-rpg", engine="godot", engine_version="4.4-stable")
            reg = AssetRegistry(mgr)
            pack = reg.generate_3d_pbr_pack("game3d")
            self.assertEqual(pack["asset_count"], 9)
            report = reg.audit_project_assets("game3d")
            self.assertTrue(report["passed"])
            self.assertEqual(report["asset_count"], 9)
            self.assertEqual(report["duplicate_hashes"], [])
            self.assertEqual(report["models_missing_materials"], [])
            self.assertEqual(report["animations_missing_rig"], [])
            pack2 = reg.generate_3d_pbr_pack("game3d")
            self.assertEqual([a["sha256_hash"] for a in pack["assets"]], [a["sha256_hash"] for a in pack2["assets"]])

    def test_audit_detects_missing_material_and_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(Path(tmp))
            mgr.init_registry()
            mgr.create_project(project_id="game3d", name="Game 3D", genre="action-rpg", engine="godot", engine_version="4.4-stable")
            reg = AssetRegistry(mgr)
            target = mgr.resolve_game_path("game3d", "assets/models/bare.obj")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(synthesize_obj_mesh(name="bare", with_material=False))
            reg.register_existing_asset(
                project_id="game3d", asset_id="bare-mesh", name="Bare", asset_type="model_3d",
                rel_path="assets/models/bare.obj", license_name="OWN_ORIGINAL_PROCEDURAL",
                origin="procedural_local", restrictions="Gerado proceduralmente offline",
            )
            report = reg.audit_project_assets("game3d")
            self.assertFalse(report["passed"])
            self.assertEqual(report["models_missing_materials"], ["bare-mesh"])
            target.write_bytes(synthesize_obj_mesh(name="bare2", with_material=False))
            with self.assertRaises(AssetValidationError):
                reg.audit_project_assets("game3d")

    def test_cli_3d_pack_and_tool_status(self) -> None:
        from factory.playforge import cli

        with tempfile.TemporaryDirectory() as tmp:
            base = ["--repo-root", tmp]
            self.assertEqual(cli.main(base + ["init"]), 0)
            self.assertEqual(cli.main(base + ["create", "cli3d", "--name", "Cli 3D", "--genre", "action-rpg"]), 0)
            self.assertEqual(cli.main(base + ["asset-generate-3d-pack", "cli3d"]), 0)
            self.assertEqual(cli.main(base + ["tool-status"]), 0)
            self.assertTrue((Path(tmp) / "games" / "cli3d" / "assets" / "models" / "crate.glb").is_file())
            registry = json.loads((Path(tmp) / "games" / "cli3d" / "assets" / "asset_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["assets"]), 9)


if __name__ == "__main__":
    unittest.main()
