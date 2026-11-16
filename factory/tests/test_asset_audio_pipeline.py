"""Suite de testes unitarios e E2E do Pipeline de Assets e Audio (Fase 7)."""
from __future__ import annotations

import io
import json
import shutil
import struct
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from factory.playforge import cli
from factory.playforge.asset_pipeline.registry import AssetRegistry
from factory.playforge.asset_pipeline.schemas import (
    ASSET_REGISTRY_REQUIRED_FIELDS,
    AssetLicenseError,
    AssetValidationError,
)
from factory.playforge.asset_pipeline.synthesizer import (
    inspect_media_toolchain,
    resolve_factory_godot_bin,
    synthesize_png_sprite,
    synthesize_wav_audio,
)
from factory.playforge.asset_pipeline.validator import (
    compute_sha256_bytes,
    inspect_ogg,
    inspect_png,
    inspect_wav,
    validate_license_and_provenance,
)
from factory.playforge.mcp.schemas import MCPAccessDenied
from factory.playforge.mcp.servers import create_asset_mcp, create_audio_mcp
from factory.playforge.models import ANCHOR_PROJECT_ID, ProtectedProject
from factory.playforge.registry import ProjectManager

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestSynthesizersAndValidators(unittest.TestCase):
    def test_toolchain_audit_and_procedural_png_wav_roundtrip(self) -> None:
        info = inspect_media_toolchain(repo_root=REPO_ROOT)
        self.assertFalse(info["paid_services_enabled"])
        self.assertEqual(info["zero_cost_policy"], "ENFORCED_LOCAL_ONLY")
        self.assertIn("stdlib-png-rgba-v1", info["builtin_synthesizers"])
        self.assertIn("stdlib-wav-pcm16-v1", info["builtin_synthesizers"])

        for idx, pattern in enumerate(
            ("hero_silhouette", "enemy_silhouette", "ui_panel", "icon_gem", "backdrop_gradient")
        ):
            raw_png = synthesize_png_sprite(width=48 + idx * 8, height=32 + idx * 8, pattern=pattern, seed=42 + idx)
            parsed = inspect_png(raw_png)
            self.assertEqual(parsed["format"], "png")
            self.assertEqual(parsed["width"], 48 + idx * 8)
            self.assertEqual(parsed["height"], 32 + idx * 8)

        for preset in ("slash", "hit", "dash", "ui_click", "victory_chime", "dark_ambient_loop"):
            raw_wav = synthesize_wav_audio(preset=preset, seed=99)
            metrics = inspect_wav(raw_wav, reject_clipping=True)
            self.assertEqual(metrics["format"], "wav")
            self.assertEqual(metrics["channels"], 1)
            self.assertEqual(metrics["sample_rate"], 22050)
            self.assertEqual(metrics["clipped_samples"], 0)
            self.assertLess(metrics["peak_dbfs"], 0.0)
            self.assertGreater(metrics["duration_s"], 0.05)

    def test_corrupt_media_clipping_and_bad_licenses_fail_closed(self) -> None:
        valid_png = bytearray(synthesize_png_sprite(width=16, height=16))
        with self.assertRaises(AssetValidationError):
            inspect_png(b"NOT_A_PNG_HEADER")
        # Adultera 1 byte no CRC de IHDR
        valid_png[29] ^= 0xFF
        with self.assertRaises(AssetValidationError):
            inspect_png(bytes(valid_png))

        # WAV com clipping saturado (32767) deve falhar fechado
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(struct.pack("<100h", *([32767] * 100)))
        with self.assertRaises(AssetValidationError):
            inspect_wav(buf.getvalue(), reject_clipping=True)

        # OGG valido vs corrompido
        valid_ogg = b"OggS" + b"\x00" * 24 + b"\x01vorbis" + b"\x00" * 40
        self.assertEqual(inspect_ogg(valid_ogg)["format"], "ogg")
        with self.assertRaises(AssetValidationError):
            inspect_ogg(b"BAD_OGG" + b"\x00" * 64)

        # Licencas e proveniencia fail-closed
        base = {
            "origin": "open_source_verified",
            "author_or_provider": "Artist",
            "tool_used": "Krita",
            "model_used": "n/a",
            "prompt_or_seed": "n/a",
            "license": "CC0-1.0",
            "restrictions": "Dominio publico CC0",
        }
        validate_license_and_provenance(base)

        for bad_lic in ("UNKNOWN", "CC-BY-NC-4.0", "ALL_RIGHTS_RESERVED", "PROPRIETARY"):
            with self.assertRaises(AssetLicenseError):
                validate_license_and_provenance(dict(base, license=bad_lic))

        # Atribuicao obrigatoria em CC-BY-4.0 nao pode ser placeholder vazio/"none"
        with self.assertRaises(AssetLicenseError):
            validate_license_and_provenance(dict(base, license="CC-BY-4.0", restrictions="none"))

        # Origem IA local exige model_used e prompt_or_seed reais
        with self.assertRaises(AssetLicenseError):
            validate_license_and_provenance(
                dict(base, origin="local_ai_verified", model_used="none", prompt_or_seed="seed=1")
            )
        validate_license_and_provenance(
            dict(
                base,
                origin="local_ai_verified",
                license="CC0-1.0",
                model_used="open-local-pixel-v1",
                prompt_or_seed="seed=77",
            )
        )


class TestAssetRegistryAndGodotVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_asset_reg_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.manager.create_project("shadow-forge", "Shadow Forge", "action-rpg")
        self.asset_reg = AssetRegistry(self.manager)

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def test_default_pack_registers_all_fields_and_passes_real_godot_headless(self) -> None:
        pack = self.asset_reg.generate_default_pack("shadow-forge")
        self.assertEqual(pack["status"], "PACK_GENERATED")
        self.assertEqual(pack["asset_count"], 7)

        listed = self.asset_reg.list_assets("shadow-forge")
        self.assertEqual(len(listed), 7)
        for item in listed:
            for req in ASSET_REGISTRY_REQUIRED_FIELDS:
                self.assertIn(req, item)

        godot_bin = resolve_factory_godot_bin(self.repo_root)
        self.assertIsNotNone(godot_bin)
        audit = self.asset_reg.audit_project_assets("shadow-forge", verify_godot=True, godot_bin=godot_bin)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["asset_count"], 7)
        self.assertTrue(audit["godot_verified"])
        self.assertEqual(audit["godot_result"]["verified_count"], 7)
        self.assertIn("AssetsVerified:7 | Failed: 0", audit["godot_result"]["output"])
        self.assertTrue(
            self.manager.resolve_game_path("shadow-forge", "specs/asset_audit_report.json").is_file()
        )

    def test_guards_zaikor_paths_tampering_orphans_and_temp_files(self) -> None:
        with self.assertRaises(ProtectedProject):
            self.asset_reg.generate_default_pack(ANCHOR_PROJECT_ID)

        with self.assertRaises(AssetValidationError):
            self.asset_reg.generate_procedural_image_asset(
                project_id="shadow-forge",
                asset_id="bad-path",
                name="Outside Media",
                rel_path="src/evil.png",
            )

        self.asset_reg.generate_default_pack("shadow-forge")

        # Adulteracao de hash detectada pelo audit fail-closed
        hero_path = self.manager.resolve_game_path("shadow-forge", "assets/sprites/hero.png")
        hero_path.write_bytes(synthesize_png_sprite(width=32, height=32, seed=999))
        with self.assertRaises(AssetValidationError):
            self.asset_reg.audit_project_assets("shadow-forge")

        # Re-gera pack valido e introduz arquivo orfao
        self.asset_reg.generate_default_pack("shadow-forge")
        orphan = self.manager.resolve_game_path("shadow-forge", "assets/sprites/orphan.png")
        orphan.write_bytes(synthesize_png_sprite(width=16, height=16))
        with self.assertRaises(AssetValidationError):
            self.asset_reg.audit_project_assets("shadow-forge")
        orphan.unlink()

        # Introduz arquivo temporario proibido
        tmp_file = self.manager.resolve_game_path("shadow-forge", "audio/sfx/scratch.tmp")
        tmp_file.write_text("temp", encoding="utf-8")
        with self.assertRaises(AssetValidationError):
            self.asset_reg.audit_project_assets("shadow-forge")


class TestAssetAndAudioMCPAndCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="playforge_asset_cli_"))
        self.repo_root = self.tmp_dir / "repo"
        self.repo_root.mkdir(parents=True)
        self.manager = ProjectManager(repo_root=self.repo_root)
        self.manager.init_registry()
        self.manager.create_project("pixel-arena", "Pixel Arena", "action-rpg")
        self.audit_log = self.repo_root / "data" / "logs" / "mcp_audit.jsonl"

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            shutil.rmtree(str(self.tmp_dir))

    def _run_cli(self, *args: str) -> tuple[int, dict[str, Any]]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(["--repo-root", str(self.repo_root), *args])
        raw = stdout.getvalue() if code == 0 else stderr.getvalue()
        return code, json.loads(raw)

    def test_asset_and_audio_mcp_servers_respect_agent_least_privilege(self) -> None:
        asset_srv = create_asset_mcp(self.manager, audit_log_path=self.audit_log)
        audio_srv = create_audio_mcp(self.manager, audit_log_path=self.audit_log)

        gen_img = asset_srv.call_tool(
            "asset_generate_sprite",
            {
                "project_id": "pixel-arena",
                "asset_id": "boss-icon",
                "name": "Boss Icon",
                "rel_path": "assets/ui/boss.png",
                "pattern": "icon_gem",
                "width": 32,
                "height": 32,
            },
            agent_id="art-asset",
        )
        self.assertEqual(gen_img["status"], "GENERATED")

        gen_wav = audio_srv.call_tool(
            "audio_generate_sfx",
            {
                "project_id": "pixel-arena",
                "asset_id": "dash-sfx",
                "name": "Dash SFX",
                "rel_path": "audio/sfx/dash.wav",
                "preset": "dash",
            },
            agent_id="audio",
        )
        self.assertEqual(gen_wav["status"], "GENERATED")

        metrics = audio_srv.call_tool(
            "audio_inspect_wav",
            {"project_id": "pixel-arena", "rel_path": "audio/sfx/dash.wav"},
            agent_id="qa",
        )
        self.assertEqual(metrics["clipped_samples"], 0)

        # QA nao pode gerar/escrever assets; art-asset nao pode tocar zaikor
        with self.assertRaises(MCPAccessDenied):
            asset_srv.call_tool(
                "asset_generate_sprite",
                {
                    "project_id": "pixel-arena",
                    "asset_id": "bad-qa",
                    "name": "Bad QA",
                    "rel_path": "assets/ui/bad.png",
                },
                agent_id="qa",
            )
        with self.assertRaises(MCPAccessDenied):
            asset_srv.call_tool(
                "asset_generate_sprite",
                {
                    "project_id": ANCHOR_PROJECT_ID,
                    "asset_id": "hack-anchor",
                    "name": "Hack",
                    "rel_path": "assets/ui/hack.png",
                },
                agent_id="art-asset",
            )

        audit_res = asset_srv.call_tool(
            "asset_audit",
            {"project_id": "pixel-arena", "verify_godot": False},
            agent_id="auditor",
        )
        self.assertTrue(audit_res["passed"])
        self.assertEqual(audit_res["asset_count"], 2)

    def test_cli_asset_audio_end_to_end_and_real_godot_verify(self) -> None:
        code, toolchain = self._run_cli("asset-toolchain")
        self.assertEqual(code, 0)
        self.assertFalse(toolchain["paid_services_enabled"])

        code, pack = self._run_cli("asset-generate-pack", "pixel-arena")
        self.assertEqual(code, 0)
        self.assertEqual(pack["asset_count"], 7)

        # Registra um asset manual valido vs licenca proibida
        custom_path = self.manager.resolve_game_path("pixel-arena", "assets/ui/gem.png")
        custom_bytes = synthesize_png_sprite(width=32, height=32, pattern="icon_gem")
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        custom_path.write_bytes(custom_bytes)

        bad_code, bad_err = self._run_cli(
            "asset-register",
            "pixel-arena",
            "--asset-id",
            "custom-gem",
            "--name",
            "Gem Icon",
            "--type",
            "ui_icon",
            "--path",
            "assets/ui/gem.png",
            "--license",
            "CC-BY-NC-4.0",
        )
        self.assertEqual(bad_code, 1)
        self.assertEqual(bad_err["error"], "AssetLicenseError")

        code, registered = self._run_cli(
            "asset-register",
            "pixel-arena",
            "--asset-id",
            "custom-gem",
            "--name",
            "Gem Icon",
            "--type",
            "ui_icon",
            "--path",
            "assets/ui/gem.png",
            "--license",
            "CC0-1.0",
            "--restrictions",
            "CC0 sem restricoes",
        )
        self.assertEqual(code, 0)
        self.assertEqual(registered["sha256_hash"], compute_sha256_bytes(custom_bytes))

        code, listed = self._run_cli("asset-list", "pixel-arena")
        self.assertEqual(code, 0)
        self.assertEqual(listed["count"], 8)

        code, wav_info = self._run_cli("audio-inspect", "pixel-arena", "audio/sfx/slash.wav")
        self.assertEqual(code, 0)
        self.assertEqual(wav_info["clipped_samples"], 0)

        code, audited = self._run_cli("asset-audit", "pixel-arena", "--verify-godot")
        self.assertEqual(code, 0)
        self.assertTrue(audited["passed"])
        self.assertTrue(audited["godot_verified"])
        self.assertEqual(audited["asset_count"], 8)


if __name__ == "__main__":
    unittest.main()
