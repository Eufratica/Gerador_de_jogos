"""AssetRegistry versionado por projeto, gerador de pack padrao e auditoria Godot (Fase 7)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from factory.playforge.models import FactoryError
from factory.playforge.registry import (
    ProjectManager,
    _atomic_write_json,
    _atomic_write_text,
    validate_project_id,
)
from factory.playforge.security_utils import is_forbidden_secret_relpath
from factory.playforge.template_registry.registry import TemplateRegistry

from .schemas import (
    ASSET_REGISTRY_SCHEMA_VERSION,
    MODEL_3D_ASSET_TYPES,
    TEMP_OR_FORBIDDEN_SUFFIXES,
    AssetNotFoundError,
    AssetValidationError,
)
from .synthesizer import (
    resolve_factory_godot_bin,
    synthesize_glb_mesh,
    synthesize_gltf_mesh,
    synthesize_obj_mesh,
    synthesize_pbr_texture_set,
    synthesize_png_sprite,
    synthesize_wav_audio,
)
from .validator import compute_sha256_bytes, inspect_media_bytes, validate_asset_record


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(str(tmp_path), str(path))
    except BaseException:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _godot_verify_assets_script(asset_entries: list[dict[str, Any]]) -> str:
    """Gera script GDScript headless para validar decodificacao PNG e WAV em Godot 4.4."""
    checks: list[str] = [
        "extends SceneTree",
        "func _initialize() -> void:",
        "\tvar failed := 0",
    ]
    for idx, entry in enumerate(asset_entries):
        res_path = f"res://{entry['file_path']}"
        fmt = entry["format"]
        if fmt == "png":
            w = int(entry["dimensions"]["width"])
            h = int(entry["dimensions"]["height"])
            checks.extend(
                [
                    f'\tvar img_{idx} := Image.load_from_file(ProjectSettings.globalize_path("{res_path}"))',
                    f"\tif img_{idx} == null or img_{idx}.is_empty() or img_{idx}.get_width() != {w} or img_{idx}.get_height() != {h}:",
                    f'\t\tprinterr("FAIL PNG: {res_path}")',
                    "\t\tfailed += 1",
                ]
            )
        elif fmt == "wav":
            sr = int(entry["dimensions"]["sample_rate"])
            checks.extend(
                [
                    f'\tvar wav_{idx} := AudioStreamWAV.load_from_file(ProjectSettings.globalize_path("{res_path}"))',
                    f"\tif wav_{idx} == null or wav_{idx}.get_length() <= 0.0 or wav_{idx}.mix_rate != {sr}:",
                    f'\t\tprinterr("FAIL WAV: {res_path}")',
                    "\t\tfailed += 1",
                ]
            )

    checks.extend(
        [
            f'\tprint("AssetsVerified:{len(asset_entries)} | Failed: %d" % failed)',
            "\tquit(0 if failed == 0 else 1)",
        ]
    )
    return "\n".join(checks) + "\n"


class AssetRegistry:
    """Gerenciador fail-closed do AssetRegistry e pipeline local de midia por projeto."""

    def __init__(
        self,
        manager: ProjectManager,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.manager = manager
        self.template_registry = TemplateRegistry(repo_root=manager.repo_root)
        self._clock = clock

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _registry_relpath(self) -> str:
        return "assets/asset_registry.json"

    def _resolve_media_path(self, project_id: str, rel_path: str) -> tuple[str, Path]:
        validate_project_id(project_id)
        cleaned = rel_path.replace("\\", "/").strip()
        if not cleaned or cleaned.startswith("/") or (len(cleaned) >= 2 and cleaned[1] == ":"):
            raise AssetValidationError(f"Caminho absoluto nao permitido para asset: '{rel_path}'.")
        if is_forbidden_secret_relpath(cleaned):
            raise AssetValidationError(f"Caminho proibido pela politica de seguranca: '{rel_path}'.")
        if not (cleaned.startswith("assets/") or cleaned.startswith("audio/")):
            raise AssetValidationError(
                f"Assets devem residir estritamente dentro de 'assets/' ou 'audio/': '{rel_path}'."
            )
        if cleaned == self._registry_relpath():
            raise AssetValidationError("Nao e permitido registrar assets sobre 'assets/asset_registry.json'.")
        lower = cleaned.lower()
        if any(lower.endswith(suf) for suf in TEMP_OR_FORBIDDEN_SUFFIXES):
            raise AssetValidationError(f"Arquivo temporario proibido como asset: '{rel_path}'.")

        target = self.manager.resolve_game_path(project_id, cleaned)
        ws_root = self.manager.resolve_game_path(project_id, ".").resolve()
        try:
            target.resolve().relative_to(ws_root)
        except ValueError as exc:
            raise AssetValidationError(f"Caminho fora do workspace do projeto '{project_id}': '{rel_path}'.") from exc
        return cleaned, target

    def _load_registry(self, project_id: str) -> dict[str, Any]:
        reg_path = self.manager.resolve_game_path(project_id, self._registry_relpath())
        if not reg_path.is_file():
            return {
                "asset_registry_schema_version": ASSET_REGISTRY_SCHEMA_VERSION,
                "project_id": project_id,
                "updated_at": self._now_timestamp(),
                "assets": {},
            }
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AssetValidationError(f"asset_registry.json corrompido em '{project_id}': {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("assets"), dict):
            raise AssetValidationError(f"Estrutura invalida em asset_registry.json de '{project_id}'.")
        return data

    def _save_registry(self, project_id: str, registry_data: dict[str, Any]) -> None:
        self.manager.require_mutable_project(project_id)
        registry_data["updated_at"] = self._now_timestamp()
        reg_path = self.manager.resolve_game_path(project_id, self._registry_relpath())
        _atomic_write_json(reg_path, registry_data)

    def _store_and_register(
        self,
        *,
        project_id: str,
        asset_id: str,
        name: str,
        asset_type: str,
        rel_path: str,
        fmt: str,
        raw_bytes: bytes,
        version: str,
        origin: str,
        author_or_provider: str,
        tool_used: str,
        model_used: str,
        prompt_or_seed: str,
        license_name: str,
        restrictions: str,
        write_bytes: bool,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.manager.require_mutable_project(project_id)
        clean_rel, target = self._resolve_media_path(project_id, rel_path)
        media_info = inspect_media_bytes(fmt, raw_bytes, reject_clipping=True)

        entry: dict[str, Any] = {
            "asset_id": asset_id,
            "name": name,
            "asset_type": asset_type,
            "project_id": project_id,
            "game_id": project_id,
            "version": version,
            "file_path": clean_rel,
            "format": media_info["format"],
            "dimensions": media_info["dimensions"],
            "resolution": media_info["resolution"],
            "byte_size": len(raw_bytes),
            "origin": origin,
            "author_or_provider": author_or_provider,
            "tool_used": tool_used,
            "model_used": model_used,
            "prompt_or_seed": prompt_or_seed,
            "license": license_name,
            "restrictions": restrictions,
            "sha256_hash": compute_sha256_bytes(raw_bytes),
            "validation_status": "VALIDATED",
            "registered_at": self._now_timestamp(),
        }
        for flag in ("has_materials", "has_rig"):
            if flag in media_info:
                entry[flag] = bool(media_info[flag])
        if extra_fields:
            entry.update(extra_fields)
        validated = validate_asset_record(entry, raw_bytes=raw_bytes, reject_clipping=True)

        if write_bytes:
            _atomic_write_bytes(target, raw_bytes)

        reg_data = self._load_registry(project_id)
        reg_data["assets"][asset_id] = validated
        self._save_registry(project_id, reg_data)
        self.manager.log_event(
            "INFO",
            "ASSET_REGISTERED",
            project_id=project_id,
            asset_id=asset_id,
            asset_type=asset_type,
            file_path=clean_rel,
            license=license_name,
            sha256_hash=validated["sha256_hash"],
        )
        return validated

    def register_existing_asset(
        self,
        *,
        project_id: str,
        asset_id: str,
        name: str,
        asset_type: str,
        rel_path: str,
        version: str = "1.0.0",
        origin: str = "created_in_house",
        author_or_provider: str = "PlayForge Studio",
        tool_used: str = "manual-import",
        model_used: str = "n/a",
        prompt_or_seed: str = "n/a",
        license_name: str,
        restrictions: str = "Comercial liberado internamente",
    ) -> dict[str, Any]:
        """Valida e registra asset ja presente no workspace do projeto mutavel."""
        self.manager.require_mutable_project(project_id)
        clean_rel, target = self._resolve_media_path(project_id, rel_path)
        if not target.is_file():
            raise AssetNotFoundError(f"Arquivo de asset ausente em '{project_id}': '{clean_rel}'.")
        fmt = target.suffix.lstrip(".").lower()
        raw_bytes = target.read_bytes()
        return self._store_and_register(
            project_id=project_id,
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            rel_path=clean_rel,
            fmt=fmt,
            raw_bytes=raw_bytes,
            version=version,
            origin=origin,
            author_or_provider=author_or_provider,
            tool_used=tool_used,
            model_used=model_used,
            prompt_or_seed=prompt_or_seed,
            license_name=license_name,
            restrictions=restrictions,
            write_bytes=False,
        )

    def generate_procedural_image_asset(
        self,
        *,
        project_id: str,
        asset_id: str,
        name: str,
        asset_type: str = "sprite_2d",
        rel_path: str,
        width: int = 64,
        height: int = 64,
        pattern: str = "hero_silhouette",
        seed: int = 2026,
        version: str = "1.0.0",
    ) -> dict[str, Any]:
        """Sintetiza PNG RGBA local gratuito, valida bytes e registra proveniencia."""
        raw_bytes = synthesize_png_sprite(width=width, height=height, pattern=pattern, seed=seed)
        return self._store_and_register(
            project_id=project_id,
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            rel_path=rel_path,
            fmt="png",
            raw_bytes=raw_bytes,
            version=version,
            origin="procedural_local",
            author_or_provider="PlayForge Procedural Synthesizer",
            tool_used="stdlib-png-rgba-v1",
            model_used="deterministic-math",
            prompt_or_seed=f"pattern={pattern};seed={seed};size={width}x{height}",
            license_name="OWN_ORIGINAL_PROCEDURAL",
            restrictions="Gerado proceduralmente offline sem custos nem terceiros.",
            write_bytes=True,
        )

    def generate_procedural_audio_asset(
        self,
        *,
        project_id: str,
        asset_id: str,
        name: str,
        asset_type: str = "sfx",
        rel_path: str,
        preset: str = "slash",
        duration_s: float | None = None,
        sample_rate: int = 22050,
        seed: int = 2026,
        version: str = "1.0.0",
    ) -> dict[str, Any]:
        """Sintetiza WAV PCM16 mono sem clipping, valida e registra proveniencia."""
        raw_bytes = synthesize_wav_audio(
            preset=preset,
            duration_s=duration_s,
            sample_rate=sample_rate,
            seed=seed,
        )
        return self._store_and_register(
            project_id=project_id,
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            rel_path=rel_path,
            fmt="wav",
            raw_bytes=raw_bytes,
            version=version,
            origin="procedural_local",
            author_or_provider="PlayForge Procedural Audio",
            tool_used="stdlib-wav-pcm16-v1",
            model_used="deterministic-dsp",
            prompt_or_seed=f"preset={preset};seed={seed};sr={sample_rate}",
            license_name="OWN_ORIGINAL_PROCEDURAL",
            restrictions="Sintese DSP offline gratuita sem amostras externas.",
            write_bytes=True,
        )

    def generate_default_pack(self, project_id: str) -> dict[str, Any]:
        """Gera pack inicial completo (sprites + UI + SFX + BGM) para um projeto isolado."""
        self.manager.require_mutable_project(project_id)
        created: list[dict[str, Any]] = [
            self.generate_procedural_image_asset(
                project_id=project_id,
                asset_id="hero-sprite-base",
                name="Hero Sprite Base",
                asset_type="sprite_2d",
                rel_path="assets/sprites/hero.png",
                width=64,
                height=64,
                pattern="hero_silhouette",
            ),
            self.generate_procedural_image_asset(
                project_id=project_id,
                asset_id="enemy-sprite-base",
                name="Enemy Sprite Base",
                asset_type="sprite_2d",
                rel_path="assets/sprites/enemy.png",
                width=64,
                height=64,
                pattern="enemy_silhouette",
            ),
            self.generate_procedural_image_asset(
                project_id=project_id,
                asset_id="ui-panel-frame",
                name="UI Panel Frame",
                asset_type="ui_icon",
                rel_path="assets/ui/panel.png",
                width=128,
                height=64,
                pattern="ui_panel",
            ),
            self.generate_procedural_audio_asset(
                project_id=project_id,
                asset_id="sfx-slash-base",
                name="Slash SFX",
                asset_type="sfx",
                rel_path="audio/sfx/slash.wav",
                preset="slash",
            ),
            self.generate_procedural_audio_asset(
                project_id=project_id,
                asset_id="sfx-hit-base",
                name="Hit Impact SFX",
                asset_type="sfx",
                rel_path="audio/sfx/hit.wav",
                preset="hit",
            ),
            self.generate_procedural_audio_asset(
                project_id=project_id,
                asset_id="sfx-ui-click",
                name="UI Click SFX",
                asset_type="sfx",
                rel_path="audio/sfx/ui_click.wav",
                preset="ui_click",
            ),
            self.generate_procedural_audio_asset(
                project_id=project_id,
                asset_id="bgm-theme-loop",
                name="Theme Ambient Loop",
                asset_type="bgm",
                rel_path="audio/bgm/theme_loop.wav",
                preset="dark_ambient_loop",
            ),
        ]
        return {
            "status": "PACK_GENERATED",
            "project_id": project_id,
            "asset_count": len(created),
            "assets": created,
            "files_touched": [self._registry_relpath(), *[item["file_path"] for item in created]],
        }

    def generate_3d_pbr_pack(self, project_id: str) -> dict[str, Any]:
        """Gera pack 3D/PBR procedural (glTF, GLB, OBJ, glTF rigged + 5 mapas PBR) e registra proveniencia."""
        self.manager.require_mutable_project(project_id)
        engines = ["godot", "unity", "unreal"]
        created: list[dict[str, Any]] = []

        def reg(asset_id: str, name: str, asset_type: str, rel: str, fmt: str, raw: bytes, tool: str, seed: str, extra: dict[str, Any] | None = None) -> None:
            created.append(
                self._store_and_register(
                    project_id=project_id,
                    asset_id=asset_id,
                    name=name,
                    asset_type=asset_type,
                    rel_path=rel,
                    fmt=fmt,
                    raw_bytes=raw,
                    version="1.0.0",
                    origin="procedural_local",
                    author_or_provider="PlayForge Procedural 3D",
                    tool_used=tool,
                    model_used="deterministic-math",
                    prompt_or_seed=seed,
                    license_name="OWN_ORIGINAL_PROCEDURAL",
                    restrictions="Gerado proceduralmente offline sem custos nem terceiros.",
                    write_bytes=True,
                    extra_fields={"compatible_engines": engines, "lod_level": 0, **(extra or {})},
                )
            )

        tool = "stdlib-3d-mesh-v1"
        reg("prop-crate-gltf", "Crate glTF", "model_3d", "assets/models/crate.gltf", "gltf",
            synthesize_gltf_mesh(name="crate", with_material=True), tool, "kind=cube;fmt=gltf")
        reg("prop-crate-glb", "Crate GLB", "model_3d", "assets/models/crate.glb", "glb",
            synthesize_glb_mesh(name="crate-glb", with_material=True), tool, "kind=cube;fmt=glb")
        reg("env-block-obj", "Environment Block OBJ", "environment_mesh", "assets/models/env_block.obj", "obj",
            synthesize_obj_mesh(name="env_block", with_material=True), tool, "kind=cube;fmt=obj")
        reg("rig-prop-gltf", "Rigged Prop glTF", "animation_3d", "assets/models/rigged_prop.gltf", "gltf",
            synthesize_gltf_mesh(name="rigged-prop", with_material=True, with_rig=True), tool, "kind=cube;rig=1;anim=idle")

        maps = synthesize_pbr_texture_set(width=32, height=32, surface="metal")
        type_by_map = {
            "albedo": "texture_albedo",
            "normal": "texture_normal",
            "roughness": "texture_roughness",
            "metallic": "texture_metallic",
            "ao": "texture_ao",
        }
        pbr_ids = {m: f"pbr-metal-{m}" for m in type_by_map}
        for map_name, asset_type in type_by_map.items():
            reg(pbr_ids[map_name], f"PBR Metal {map_name}", asset_type, f"assets/materials/metal_{map_name}.png", "png",
                maps[map_name], "stdlib-pbr-synthesizer-v1", "surface=metal;size=32x32", {"pbr_maps": dict(pbr_ids)})

        return {
            "status": "PACK_3D_PBR_GENERATED",
            "project_id": project_id,
            "asset_count": len(created),
            "assets": created,
            "files_touched": [self._registry_relpath(), *[item["file_path"] for item in created]],
        }

    def list_assets(self, project_id: str, *, asset_type: str | None = None) -> list[dict[str, Any]]:
        validate_project_id(project_id)
        data = self._load_registry(project_id)
        entries = list(data["assets"].values())
        if asset_type:
            entries = [item for item in entries if item.get("asset_type") == asset_type]
        return sorted(entries, key=lambda item: item.get("asset_id", ""))

    def verify_assets_in_godot(
        self,
        project_id: str,
        entries: list[dict[str, Any]],
        *,
        godot_bin: Path | None = None,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]:
        """Executa Godot 4.4 headless em copia isolada validando Image/AudioStreamWAV reais."""
        resolved_bin = godot_bin or resolve_factory_godot_bin(self.manager.repo_root)
        if resolved_bin is None or not Path(resolved_bin).is_file():
            raise AssetValidationError(
                "Binario Godot CLI nao encontrado; impossivel executar validacao headless de assets."
            )

        ws_dir = self.manager.resolve_game_path(project_id, ".")
        with tempfile.TemporaryDirectory(prefix="playforge_asset_godot_") as tmp:
            tmp_path = Path(tmp)
            proj_copy = tmp_path / "project"
            user_home = tmp_path / "user_home"
            user_home.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ws_dir, proj_copy, ignore=shutil.ignore_patterns(".godot"))

            if not (proj_copy / "project.godot").is_file():
                _atomic_write_text(
                    proj_copy / "project.godot",
                    f'config_version=5\n[application]\nconfig/name="AssetAudit-{project_id}"\n',
                )

            rel_script = "tests/unit/_verify_assets_tmp.gd"
            _atomic_write_text(proj_copy / rel_script, _godot_verify_assets_script(entries))

            env = os.environ.copy()
            for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME"):
                env[key] = str(user_home)

            proc = subprocess.run(
                [
                    str(resolved_bin),
                    "--headless",
                    "--no-header",
                    "--path",
                    str(proj_copy),
                    "--script",
                    f"res://{rel_script}",
                ],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                check=False,
            )
            combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p).strip()
            if proc.returncode != 0 or "SCRIPT ERROR:" in combined or "Failed: 0" not in combined:
                raise AssetValidationError(
                    f"Verificacao Godot headless de assets falhou (code={proc.returncode}): {combined}"
                )
            return {
                "passed": True,
                "returncode": proc.returncode,
                "verified_count": len(entries),
                "output": combined,
            }

    def audit_project_assets(
        self,
        project_id: str,
        *,
        verify_godot: bool = False,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Audita hashes, licencas, ausencia de orfaos/temporarios e opcionalmente Godot headless."""
        validate_project_id(project_id)
        reg_data = self._load_registry(project_id)
        entries = list(reg_data["assets"].values())
        registered_paths: dict[str, dict[str, Any]] = {}

        for entry in entries:
            clean_rel, target = self._resolve_media_path(project_id, entry["file_path"])
            if not target.is_file():
                raise AssetValidationError(
                    f"Asset registrado ausente no disco em '{project_id}': '{clean_rel}'."
                )
            raw_bytes = target.read_bytes()
            validate_asset_record(entry, raw_bytes=raw_bytes, reject_clipping=True)
            registered_paths[clean_rel] = entry

        # Anti-orphan e bloqueio de arquivos temporarios dentro de assets/ e audio/
        ws_root = self.manager.resolve_game_path(project_id, ".").resolve()
        for folder_name in ("assets", "audio"):
            folder = ws_root / folder_name
            if not folder.is_dir():
                continue
            for item in sorted(folder.rglob("*")):
                if item.is_dir():
                    continue
                rel_posix = item.relative_to(ws_root).as_posix()
                if rel_posix == self._registry_relpath():
                    continue
                if any(rel_posix.lower().endswith(suf) for suf in TEMP_OR_FORBIDDEN_SUFFIXES) or item.name.startswith("~$"):
                    raise AssetValidationError(
                        f"Arquivo temporario detectado no workspace de midia '{project_id}': '{rel_posix}'."
                    )
                if item.suffix.lower() == ".import":
                    continue
                if rel_posix not in registered_paths:
                    raise AssetValidationError(
                        f"Asset orfao sem registro de proveniencia/licenca em '{project_id}': '{rel_posix}'."
                    )

        godot_result: dict[str, Any] | None = None
        if verify_godot:
            godot_result = self.verify_assets_in_godot(
                project_id,
                list(registered_paths.values()),
                godot_bin=godot_bin,
            )

        hash_groups: dict[str, list[str]] = {}
        for entry in entries:
            hash_groups.setdefault(entry["sha256_hash"], []).append(entry["asset_id"])
        duplicate_hashes = sorted(sorted(ids) for ids in hash_groups.values() if len(ids) > 1)
        models_missing_materials = sorted(
            e["asset_id"]
            for e in entries
            if e.get("asset_type") in MODEL_3D_ASSET_TYPES and e.get("has_materials") is False
        )
        animations_missing_rig = sorted(
            e["asset_id"]
            for e in entries
            if e.get("asset_type") == "animation_3d" and e.get("has_rig") is not True
        )
        audit_ok = not models_missing_materials and not animations_missing_rig

        report = {
            "audit_schema_version": 1,
            "project_id": project_id,
            "audited_at": self._now_timestamp(),
            "passed": audit_ok,
            "asset_count": len(registered_paths),
            "orphans_detected": 0,
            "duplicate_hashes": duplicate_hashes,
            "models_missing_materials": models_missing_materials,
            "animations_missing_rig": animations_missing_rig,
            "godot_verified": bool(godot_result and godot_result["passed"]),
            "godot_result": godot_result,
        }
        project_info = self.manager.get_project(project_id)
        if not project_info.get("protected"):
            _atomic_write_json(
                self.manager.resolve_game_path(project_id, "specs/asset_audit_report.json"),
                report,
            )
        self.manager.log_event(
            "INFO",
            "ASSET_AUDIT_PASSED",
            project_id=project_id,
            asset_count=len(registered_paths),
            godot_verified=report["godot_verified"],
        )
        return report
