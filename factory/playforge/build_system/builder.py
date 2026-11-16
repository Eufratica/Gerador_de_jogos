"""Build Manager multi-plataforma: pacote auditavel, hashes, verificacao e aprovacao de release (Fase 10).

Honestidade tecnica: sem SDK/export-templates nativos o artefato gerado e um *bundle estrutural de fontes*
(`structural-source-bundle`), claramente marcado como tal no manifesto. Nenhuma publicacao externa e feita.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from factory.playforge.registry import ProjectManager, _atomic_write_json, _atomic_write_text
from factory.playforge.security_utils import is_forbidden_secret_relpath
from factory.playforge.spec_engine.validator import SpecificationValidator, ValidationError

from .schemas import (
    ARTIFACT_KIND_STRUCTURAL,
    BUILD_EXCLUDED_DIRS,
    BUILD_MANIFEST_SCHEMA_VERSION,
    BUILD_VERSION_RE,
    RELEASE_STATUS_APPROVED,
    RELEASE_STATUS_UNAPPROVED,
    SUPPORTED_BUILD_TARGETS,
    BuildError,
    BuildIntegrityError,
    BuildPrerequisiteError,
    BuildTargetUnavailableError,
    ReleaseApprovalRequiredError,
)

_ZIP_FIXED_DATE_TIME = (2026, 1, 1, 0, 0, 0)
_TEMP_SUFFIXES = (".tmp", ".bak", ".swp", ".part", ".crdownload")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class BuildManager:
    """Empacota projetos isolados e mantem manifestos de build verificaveis."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    # ------------------------------------------------------------------ toolchains
    def probe_build_toolchains(self) -> dict[str, Any]:
        from factory.playforge.asset_pipeline.synthesizer import resolve_factory_godot_bin
        from factory.playforge.engine_orchestrator import create_default_orchestrator

        godot_bin = resolve_factory_godot_bin(repo_root=self.manager.repo_root)
        engines = {p.engine_id: p.to_dict() for p in create_default_orchestrator(self.manager.repo_root).probe_all()}
        sdk_env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        android_sdk = sdk_env if sdk_env and Path(sdk_env).is_dir() else None
        tools = {
            "godot": str(godot_bin) if godot_bin else None,
            "java": shutil.which("java"),
            "keytool": shutil.which("keytool"),
            "adb": shutil.which("adb"),
            "android_sdk": android_sdk,
        }
        godot_templates = None
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                tpl = Path(appdata) / "Godot" / "export_templates"
                godot_templates = str(tpl) if tpl.is_dir() else None
        native_ready = {
            "windows": bool(tools["godot"] and godot_templates),
            "linux": bool(tools["godot"] and godot_templates),
            "web": bool(tools["godot"] and godot_templates),
            "android": bool(tools["godot"] and godot_templates and tools["java"] and android_sdk),
            "macos": False,
            "ios": False,
        }
        return {
            "tools": tools,
            "godot_export_templates": godot_templates,
            "engines": engines,
            "native_export_ready": native_ready,
            "structural_bundle_always_available": True,
            "paid_services_enabled": False,
        }

    # ------------------------------------------------------------------ helpers
    def _builds_dir(self, project_id: str, version: str, target: str) -> Path:
        return self.manager.resolve_game_path(project_id, f"builds/{version}/{target}")

    def _validate_version_target(self, version: str, target: str) -> None:
        if target not in SUPPORTED_BUILD_TARGETS:
            raise BuildPrerequisiteError(f"Alvo de build invalido '{target}'. Suportados: {SUPPORTED_BUILD_TARGETS}.")
        if not isinstance(version, str) or not BUILD_VERSION_RE.match(version):
            raise BuildPrerequisiteError(f"Versao de build invalida: '{version}'.")

    def _collect_files(self, project_id: str) -> list[str]:
        root = self.manager.resolve_game_path(project_id, ".").resolve()
        rels: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in BUILD_EXCLUDED_DIRS)
            for fname in sorted(filenames):
                rel = (Path(dirpath) / fname).relative_to(root).as_posix()
                if is_forbidden_secret_relpath(rel):
                    raise BuildPrerequisiteError(f"Arquivo sensivel/proibido bloqueia o build: '{rel}'.")
                if rel.lower().endswith(_TEMP_SUFFIXES) or fname.startswith("~$"):
                    raise BuildPrerequisiteError(f"Arquivo temporario bloqueia o build: '{rel}'.")
                rels.append(rel)
        return sorted(rels)

    def _godot_smoke(self, project_id: str, engine: str) -> dict[str, Any]:
        from factory.playforge.asset_pipeline.synthesizer import resolve_factory_godot_bin

        if engine != "godot":
            return {"status": "SKIPPED", "reason": f"engine '{engine}' sem smoke test automatizado neste host"}
        ws = self.manager.resolve_game_path(project_id, ".")
        if not (ws / "project.godot").is_file():
            return {"status": "SKIPPED", "reason": "project.godot ausente no workspace"}
        godot_bin = resolve_factory_godot_bin(repo_root=self.manager.repo_root)
        if godot_bin is None or not Path(godot_bin).is_file():
            return {"status": "SKIPPED", "reason": "binario Godot CLI nao encontrado"}
        with tempfile.TemporaryDirectory(prefix="playforge_build_smoke_") as tmp:
            tmp_path = Path(tmp)
            proj = tmp_path / "project"
            home = tmp_path / "home"
            home.mkdir()
            shutil.copytree(ws, proj, ignore=shutil.ignore_patterns(".godot", "builds"))
            env = os.environ.copy()
            for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME"):
                env[key] = str(home)
            try:
                proc = subprocess.run(
                    [str(godot_bin), "--headless", "--no-header", "--path", str(proj), "--quit"],
                    capture_output=True, text=True, timeout=60, env=env, check=False,
                )
            except subprocess.TimeoutExpired:
                return {"status": "FAILED", "reason": "timeout de 60s no smoke test Godot"}
            combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
            ok = proc.returncode == 0 and "SCRIPT ERROR:" not in combined
            return {"status": "PASSED" if ok else "FAILED", "returncode": proc.returncode, "output_tail": combined[-300:]}

    # ------------------------------------------------------------------ build
    def build_target(
        self,
        project_id: str,
        target: str,
        *,
        version: str | None = None,
        allow_structural_bundle: bool = True,
    ) -> dict[str, Any]:
        project = self.manager.require_mutable_project(project_id)
        ver = version or str(project.get("version", "0.1.0"))
        self._validate_version_target(ver, target)

        spec_path = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        if not spec_path.is_file():
            raise BuildPrerequisiteError(f"GameSpecification ausente para '{project_id}'; execute spec-generate.")
        try:
            spec = SpecificationValidator().validate_spec(json.loads(spec_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise BuildPrerequisiteError(f"GameSpecification invalida bloqueia o build: {exc}") from exc
        if target not in spec["target_platforms"]:
            raise BuildPrerequisiteError(
                f"Alvo '{target}' nao consta em target_platforms da spec: {spec['target_platforms']}."
            )

        registry_file = self.manager.resolve_game_path(project_id, "assets/asset_registry.json")
        asset_audit: dict[str, Any] | None = None
        if registry_file.is_file():
            from factory.playforge.asset_pipeline import AssetRegistry
            from factory.playforge.models import FactoryError

            try:
                asset_audit = AssetRegistry(self.manager).audit_project_assets(project_id)
            except FactoryError as exc:
                raise BuildPrerequisiteError(f"Auditoria de assets reprovada: {exc}") from exc
            if not asset_audit.get("passed"):
                raise BuildPrerequisiteError("Auditoria de assets reportou pendencias; build bloqueado.")

        probe = self.probe_build_toolchains()
        native_ready = bool(probe["native_export_ready"].get(target))
        if not allow_structural_bundle:
            raise BuildTargetUnavailableError(
                f"Export nativo '{target}' nao implementado/disponivel e bundle estrutural nao permitido."
            )

        files = self._collect_files(project_id)
        file_hashes: dict[str, str] = {}
        out_dir = self._builds_dir(project_id, ver, target)
        out_dir.mkdir(parents=True, exist_ok=True)
        zip_name = f"{project_id}-{ver}-{target}.zip"
        zip_path = out_dir / zip_name
        fd, tmp_zip = tempfile.mkstemp(prefix=".build.", suffix=".zip", dir=str(out_dir))
        os.close(fd)
        tmp_zip_path = Path(tmp_zip)
        try:
            with zipfile.ZipFile(tmp_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for rel in files:
                    data = self.manager.resolve_game_path(project_id, rel).read_bytes()
                    file_hashes[rel] = _sha256(data)
                    info = zipfile.ZipInfo(filename=rel, date_time=_ZIP_FIXED_DATE_TIME)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    zf.writestr(info, data)
            os.replace(str(tmp_zip_path), str(zip_path))
        except BaseException:
            if tmp_zip_path.exists():
                tmp_zip_path.unlink()
            raise

        artifact_bytes = zip_path.read_bytes()
        smoke = self._godot_smoke(project_id, str(project.get("engine", "godot")))
        manifest: dict[str, Any] = {
            "build_manifest_schema_version": BUILD_MANIFEST_SCHEMA_VERSION,
            "project_id": project_id,
            "version": ver,
            "target": target,
            "engine": project.get("engine"),
            "built_at": self.manager.now_timestamp(),
            "artifact_kind": ARTIFACT_KIND_STRUCTURAL,
            "native_export_performed": False,
            "native_export_toolchain_ready": native_ready,
            "native_export_note": (
                "Export nativo ainda nao automatizado pela fabrica; artefato e bundle estrutural de fontes."
                if native_ready
                else "Toolchain de export nativo ausente neste host; artefato e bundle estrutural de fontes."
            ),
            "artifact": zip_name,
            "artifact_sha256": _sha256(artifact_bytes),
            "artifact_size_bytes": len(artifact_bytes),
            "file_count": len(files),
            "files_sha256": file_hashes,
            "post_build_checks": {
                "spec_valid": True,
                "secrets_scan": "CLEAN",
                "asset_audit": (
                    {"passed": True, "asset_count": asset_audit["asset_count"]} if asset_audit else "NOT_APPLICABLE"
                ),
                "engine_smoke_test": smoke,
            },
            "android_permissions": [] if target == "android" else None,
            "offline_only": bool(spec.get("security", {}).get("offline_only", False)),
            "release_status": RELEASE_STATUS_UNAPPROVED,
            "approval": None,
        }
        _atomic_write_json(out_dir / "build_manifest.json", manifest)
        _atomic_write_text(out_dir / "build_report.md", self._render_report(manifest))
        _atomic_write_text(out_dir / f"{zip_name}.sha256", f"{manifest['artifact_sha256']}  {zip_name}\n")
        self.manager.log_event(
            "INFO", "BUILD_PACKAGED", project_id=project_id, target=target, version=ver,
            artifact_sha256=manifest["artifact_sha256"],
        )
        return manifest

    @staticmethod
    def _render_report(m: dict[str, Any]) -> str:
        smoke = m["post_build_checks"]["engine_smoke_test"]
        return (
            f"# Build Report — `{m['project_id']}` `{m['version']}` ({m['target']})\n\n"
            f"- **Artefato:** `{m['artifact']}` (`{m['artifact_size_bytes']}` bytes)\n"
            f"- **SHA-256:** `{m['artifact_sha256']}`\n"
            f"- **Tipo:** `{m['artifact_kind']}` (export nativo executado: `{m['native_export_performed']}`)\n"
            f"- **Arquivos:** `{m['file_count']}`\n"
            f"- **Smoke test da engine:** `{smoke.get('status')}`\n"
            f"- **Release:** `{m['release_status']}`\n\n"
            f"> {m['native_export_note']}\n"
        )

    # ------------------------------------------------------------------ verify / approve
    def _load_manifest(self, project_id: str, version: str, target: str) -> tuple[dict[str, Any], Path]:
        self._validate_version_target(version, target)
        out_dir = self._builds_dir(project_id, version, target)
        mpath = out_dir / "build_manifest.json"
        if not mpath.is_file():
            raise BuildError(f"build_manifest.json ausente para '{project_id}' {version}/{target}.")
        try:
            return json.loads(mpath.read_text(encoding="utf-8")), out_dir
        except json.JSONDecodeError as exc:
            raise BuildIntegrityError(f"build_manifest.json corrompido: {exc}") from exc

    def verify_build(self, project_id: str, version: str, target: str) -> dict[str, Any]:
        manifest, out_dir = self._load_manifest(project_id, version, target)
        zip_path = out_dir / str(manifest.get("artifact", ""))
        if not zip_path.is_file():
            raise BuildIntegrityError("Artefato ZIP ausente.")
        data = zip_path.read_bytes()
        if _sha256(data) != manifest.get("artifact_sha256"):
            raise BuildIntegrityError("SHA-256 do artefato diverge do manifesto (adulteracao detectada).")
        declared: dict[str, str] = manifest.get("files_sha256", {})
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = sorted(zf.namelist())
                if names != sorted(declared):
                    raise BuildIntegrityError("Lista de arquivos do ZIP diverge do manifesto.")
                for name in names:
                    if _sha256(zf.read(name)) != declared[name]:
                        raise BuildIntegrityError(f"Hash divergente para '{name}' dentro do ZIP.")
        except zipfile.BadZipFile as exc:
            raise BuildIntegrityError(f"ZIP corrompido: {exc}") from exc
        approval = manifest.get("approval")
        if manifest.get("release_status") == RELEASE_STATUS_APPROVED:
            if not approval or approval.get("artifact_sha256") != manifest["artifact_sha256"]:
                raise BuildIntegrityError("Aprovacao de release nao corresponde ao artefato atual.")
        return {
            "passed": True,
            "project_id": project_id,
            "version": version,
            "target": target,
            "artifact_sha256": manifest["artifact_sha256"],
            "file_count": len(names),
            "release_status": manifest.get("release_status"),
        }

    def approve_release(
        self, project_id: str, version: str, target: str, *, approver: str, notes: str
    ) -> dict[str, Any]:
        self.manager.require_mutable_project(project_id)
        if not isinstance(approver, str) or not approver.strip() or not isinstance(notes, str) or not notes.strip():
            raise ReleaseApprovalRequiredError("Aprovacao humana exige 'approver' e 'notes' nao vazios.")
        verified = self.verify_build(project_id, version, target)
        manifest, out_dir = self._load_manifest(project_id, version, target)
        manifest["release_status"] = RELEASE_STATUS_APPROVED
        manifest["approval"] = {
            "approver": approver.strip(),
            "notes": notes.strip(),
            "approved_at": self.manager.now_timestamp(),
            "artifact_sha256": verified["artifact_sha256"],
            "published_externally": False,
        }
        _atomic_write_json(out_dir / "build_manifest.json", manifest)
        _atomic_write_text(out_dir / "build_report.md", self._render_report(manifest))
        self.manager.log_event(
            "INFO", "RELEASE_APPROVED", project_id=project_id, target=target, version=version, approver=approver.strip(),
        )
        return manifest
