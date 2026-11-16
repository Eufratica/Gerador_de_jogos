"""Game Generator (MVP): geracao isolada, verificacao Godot headless e empacotamento."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from factory.playforge.registry import ProjectManager, _atomic_write_json, _atomic_write_text
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.validator import SpecificationValidator
from factory.playforge.template_registry.registry import TemplateRegistry
from factory.playforge.template_registry.validator import (
    TemplateValidationError,
    _safe_relative_path,
)
from factory.playforge.generator.config_mapper import (
    map_spec_to_runtime_config,
    render_generated_verification_test,
    render_project_godot,
)
from factory.playforge.generator.schemas import (
    GENERATION_MANIFEST_SCHEMA_VERSION,
    GenerationConflictError,
    GenerationVerificationError,
    GeneratorError,
    PREVIEW_REPORT_SCHEMA_VERSION,
)

_TEMPLATE_RUN_SCRIPT = "tests/unit/run_template_tests.gd"
_GENERATED_VERIFY_SCRIPT = "tests/unit/verify_generated_game.gd"
_ZIP_FIXED_DATE_TIME = (2026, 1, 1, 0, 0, 0)


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Grava bytes atomicamente via arquivo temporario no mesmo diretorio."""
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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class GameGenerator:
    """Gera projetos Godot isolados e verificaveis a partir de spec aprovada + template validado."""

    def __init__(
        self,
        manager: ProjectManager,
        template_registry: TemplateRegistry | None = None,
    ) -> None:
        self.manager = manager
        self.template_registry = template_registry or TemplateRegistry(repo_root=manager.repo_root)
        self.spec_generator = SpecificationGenerator(manager)
        self.spec_validator = SpecificationValidator()

    def _ensure_games_gdignore(self) -> None:
        self.manager.games_root.mkdir(parents=True, exist_ok=True)
        gdignore = self.manager.games_root / ".gdignore"
        if not gdignore.exists():
            _atomic_write_text(gdignore, "")

    def _resolve_godot_bin(self, godot_bin: Path | None = None) -> Path | None:
        if godot_bin is not None:
            cand = Path(godot_bin)
            return cand if cand.is_file() else None
        detected = self.template_registry.default_godot_bin()
        if detected is not None:
            return detected
        install_root = Path(__file__).resolve().parents[3]
        for rel in (
            "tools/godot/Godot_v4.4-stable_win64_console.exe",
            "tools/godot/Godot_v4.4-stable_linux.x86_64",
        ):
            cand = install_root / rel
            if cand.is_file():
                return cand
        return None

    def _load_validated_spec(self, project_id: str) -> dict[str, Any]:
        spec_path = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        if not spec_path.is_file():
            raise GeneratorError(
                f"GameSpecification ausente em {spec_path}; execute 'spec-generate' antes."
            )
        try:
            raw_spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GeneratorError(f"GameSpecification JSON malformado: {exc}") from exc
        return self.spec_validator.validate_spec(raw_spec)

    def _resolve_and_validate_template(
        self,
        project_id: str,
        spec: dict[str, Any],
        spec_sha256: str,
        *,
        prefer_template_id: str | None,
        verify_template_tests: bool,
        godot_bin: Path | None,
    ) -> dict[str, Any]:
        sel_path = self.manager.resolve_game_path(project_id, "specs/template_selection.json")

        if sel_path.is_file() and prefer_template_id is None:
            try:
                selection = json.loads(sel_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise GeneratorError(f"specs/template_selection.json invalido: {exc}") from exc
            if selection.get("project_id") != project_id:
                raise GenerationConflictError("template_selection.json pertence a outro project_id.")
            if selection.get("spec_sha256") != spec_sha256:
                raise GenerationConflictError(
                    "GameSpecification alterada apos specs/template_selection.json; re-execute template-select."
                )
            tpl_id = str(selection.get("template_id", ""))
            tpl_ver = str(selection.get("template_version", ""))
        else:
            if verify_template_tests and godot_bin is None:
                raise GenerationVerificationError(
                    "Binario Godot CLI nao encontrado para validar testes do template (TPL-01)."
                )
            selection = self.template_registry.select_template_for_project(
                self.manager,
                project_id,
                require_approved_spec=True,
                prefer_template_id=prefer_template_id,
                run_godot_tests=verify_template_tests,
                godot_bin=godot_bin,
            )
            tpl_id = selection["template_id"]
            tpl_ver = selection["template_version"]

        if verify_template_tests and godot_bin is None:
            raise GenerationVerificationError(
                "Binario Godot CLI nao encontrado para validar testes do template (TPL-01)."
            )

        tpl_report = self.template_registry.validate_template(
            tpl_id,
            tpl_ver,
            run_godot_tests=verify_template_tests,
            godot_bin=godot_bin,
        )
        # Reafirma compatibilidade e status ACTIVE fail-closed (impede uso de DEPRECATED)
        self.template_registry.check_spec_compatibility(tpl_report, spec)
        return tpl_report

    def _build_planned_files(
        self,
        *,
        spec: dict[str, Any],
        tpl_report: dict[str, Any],
    ) -> tuple[dict[str, bytes], dict[str, Any]]:
        manifest = tpl_report["manifest"]
        tpl_dir = Path(tpl_report["template_dir"])
        skeleton_dir = tpl_dir / "skeleton"

        runtime_cfg, balance_info = map_spec_to_runtime_config(spec)
        planned: dict[str, bytes] = {}

        for rel in manifest["file_structure"]:
            if rel == _TEMPLATE_RUN_SCRIPT:
                continue
            src_path = _safe_relative_path(rel, skeleton_dir, "file_structure")
            if rel == "project.godot":
                base_txt = src_path.read_text(encoding="utf-8")
                rendered = render_project_godot(
                    base_txt,
                    spec,
                    template_id=manifest["template_id"],
                    template_version=manifest["template_version"],
                )
                planned[rel] = rendered.encode("utf-8")
            elif rel == "config/template_defaults.json":
                cfg_txt = json.dumps(runtime_cfg, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
                planned[rel] = cfg_txt.encode("utf-8")
            else:
                planned[rel] = src_path.read_bytes()

        verify_gd = render_generated_verification_test(spec, runtime_cfg)
        planned[_GENERATED_VERIFY_SCRIPT] = verify_gd.encode("utf-8")

        return planned, balance_info

    def _verify_disk_hashes(self, project_id: str, expected_hashes: dict[str, str]) -> list[str]:
        """Retorna lista de desvios entre arquivos no disco e os hashes esperados."""
        mismatches: list[str] = []
        for rel, expected_digest in sorted(expected_hashes.items()):
            target = self.manager.resolve_game_path(project_id, rel)
            if not target.is_file():
                mismatches.append(f"ausente:{rel}")
                continue
            actual = _sha256_bytes(target.read_bytes())
            if actual != expected_digest:
                mismatches.append(f"adulterado:{rel}")
        return mismatches

    def generate_project(
        self,
        project_id: str,
        *,
        prefer_template_id: str | None = None,
        run_godot_tests: bool = True,
        verify_template_tests: bool = True,
        package_preview_build: bool = True,
        force: bool = False,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Gera ou valida idempotentemente o projeto Godot isolado para project_id."""
        project = self.manager.require_mutable_project(project_id)
        approval = self.spec_generator.verify_spec_approved(project_id)
        spec_sha256 = approval["spec_sha256"]
        spec = self._load_validated_spec(project_id)

        resolved_bin = self._resolve_godot_bin(godot_bin)
        tpl_report = self._resolve_and_validate_template(
            project_id,
            spec,
            spec_sha256,
            prefer_template_id=prefer_template_id,
            verify_template_tests=verify_template_tests,
            godot_bin=resolved_bin,
        )

        planned_files, balance_info = self._build_planned_files(spec=spec, tpl_report=tpl_report)
        planned_hashes = {rel: _sha256_bytes(data) for rel, data in sorted(planned_files.items())}

        gen_manifest_path = self.manager.resolve_game_path(project_id, "specs/generation_manifest.json")
        already_up_to_date = False

        if gen_manifest_path.is_file():
            try:
                old_manifest = json.loads(gen_manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                if not force:
                    raise GenerationConflictError(
                        f"specs/generation_manifest.json corrompido: {exc}"
                    ) from exc
                old_manifest = {}

            if not force:
                old_hashes = old_manifest.get("files_sha256", {})
                if not isinstance(old_hashes, dict) or not old_hashes:
                    raise GenerationConflictError(
                        "generation_manifest.json invalido; use --force para regenerar."
                    )
                disk_mismatches = self._verify_disk_hashes(project_id, old_hashes)
                if disk_mismatches:
                    raise GenerationConflictError(
                        f"Arquivos gerados modificados/ausentes no disco ({', '.join(disk_mismatches)}); "
                        "use --force para sobrescrever."
                    )
                same_inputs = (
                    old_manifest.get("spec_sha256") == spec_sha256
                    and old_manifest.get("template_id") == tpl_report["template_id"]
                    and old_manifest.get("template_version") == tpl_report["template_version"]
                    and old_manifest.get("skeleton_sha256") == tpl_report["skeleton_sha256"]
                    and old_hashes == planned_hashes
                )
                if not same_inputs:
                    raise GenerationConflictError(
                        "Projeto ja gerado com outros inputs/template; use --force para atualizar."
                    )
                already_up_to_date = True
        elif not force:
            collisions = [
                rel for rel in sorted(planned_files)
                if self.manager.resolve_game_path(project_id, rel).exists()
            ]
            if collisions:
                raise GenerationConflictError(
                    f"Arquivos pre-existentes bloqueiam geracao sem --force: {', '.join(collisions)}"
                )

        self._ensure_games_gdignore()

        if not already_up_to_date:
            for rel, payload in planned_files.items():
                target = self.manager.resolve_game_path(project_id, rel)
                _atomic_write_bytes(target, payload)

            gen_manifest = {
                "generation_schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
                "project_id": project_id,
                "game_name": spec["name"],
                "project_version": project["version"],
                "generated_at": self.manager.now_timestamp(),
                "spec_id": spec["spec_id"],
                "spec_version": spec["version"],
                "spec_sha256": spec_sha256,
                "template_id": tpl_report["template_id"],
                "template_version": tpl_report["template_version"],
                "skeleton_sha256": tpl_report["skeleton_sha256"],
                "balance_profile": balance_info,
                "files_sha256": planned_hashes,
            }
            _atomic_write_json(gen_manifest_path, gen_manifest)
        else:
            gen_manifest = json.loads(gen_manifest_path.read_text(encoding="utf-8"))

        verification_result: dict[str, Any] | None = None
        if run_godot_tests:
            verification_result = self.verify_generated_project(project_id, godot_bin=resolved_bin)

        package_result: dict[str, Any] | None = None
        if package_preview_build:
            package_result = self.package_preview_artifact(project_id)

        self.manager.log_event(
            "INFO",
            "GAME_GENERATED",
            project_id=project_id,
            status="UP_TO_DATE" if already_up_to_date else "GENERATED",
            template_id=tpl_report["template_id"],
            template_version=tpl_report["template_version"],
            file_count=len(planned_hashes),
            godot_verified=bool(verification_result and verification_result["passed"]),
        )

        return {
            "status": "UP_TO_DATE" if already_up_to_date else "GENERATED",
            "project_id": project_id,
            "workspace": str(self.manager.resolve_game_path(project_id, ".")),
            "template_id": tpl_report["template_id"],
            "template_version": tpl_report["template_version"],
            "skeleton_sha256": tpl_report["skeleton_sha256"],
            "spec_sha256": spec_sha256,
            "file_count": len(planned_hashes),
            "balance_profile": gen_manifest["balance_profile"],
            "verification": verification_result,
            "preview_package": package_result,
        }

    def verify_generated_project(
        self,
        project_id: str,
        *,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Verifica hashes em disco e executa testes Godot headless no projeto gerado."""
        self.manager.require_mutable_project(project_id)
        gen_manifest_path = self.manager.resolve_game_path(project_id, "specs/generation_manifest.json")
        if not gen_manifest_path.is_file():
            raise GenerationVerificationError(
                f"specs/generation_manifest.json ausente para '{project_id}'; gere o projeto primeiro."
            )
        try:
            gen_manifest = json.loads(gen_manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GenerationVerificationError(f"generation_manifest.json corrompido: {exc}") from exc

        files_sha = gen_manifest.get("files_sha256")
        if not isinstance(files_sha, dict) or not files_sha:
            raise GenerationVerificationError("generation_manifest.json sem files_sha256.")

        mismatches = self._verify_disk_hashes(project_id, files_sha)
        if mismatches:
            raise GenerationVerificationError(
                f"Falha de integridade antes dos testes: {', '.join(mismatches)}."
            )

        resolved_bin = self._resolve_godot_bin(godot_bin)
        if resolved_bin is None or not resolved_bin.is_file():
            raise GenerationVerificationError(
                "Binario Godot CLI nao encontrado; impossivel executar verificacao headless (GF-03)."
            )

        ws_dir = self.manager.resolve_game_path(project_id, ".")
        scripts = [f"res://{_GENERATED_VERIFY_SCRIPT}"]
        suite_results: list[dict[str, Any]] = []

        for script_res in scripts:
            try:
                res = self.template_registry.validator.run_demo_tests(
                    demo_dir=ws_dir,
                    test_script_res=script_res,
                    godot_bin=resolved_bin,
                )
            except TemplateValidationError as exc:
                raise GenerationVerificationError(
                    f"Teste Godot '{script_res}' falhou em '{project_id}': {exc.message}"
                ) from exc
            suite_results.append(res)

        report = {
            "verification_schema_version": 1,
            "project_id": project_id,
            "verified_at": self.manager.now_timestamp(),
            "passed": True,
            "file_integrity_ok": True,
            "suites": suite_results,
        }
        report_path = self.manager.resolve_game_path(project_id, "specs/verification_report.json")
        _atomic_write_json(report_path, report)
        self.manager.log_event(
            "INFO",
            "GAME_VERIFIED",
            project_id=project_id,
            suites_passed=len(suite_results),
        )
        return report

    def package_preview_artifact(self, project_id: str) -> dict[str, Any]:
        """Empacota o projeto gerado verificado em artefato ZIP deterministico dentro de builds/."""
        project = self.manager.require_mutable_project(project_id)
        gen_manifest_path = self.manager.resolve_game_path(project_id, "specs/generation_manifest.json")
        if not gen_manifest_path.is_file():
            raise GeneratorError(
                f"specs/generation_manifest.json ausente para '{project_id}'; execute game-generate antes."
            )
        gen_manifest = json.loads(gen_manifest_path.read_text(encoding="utf-8"))
        files_sha = gen_manifest.get("files_sha256", {})
        mismatches = self._verify_disk_hashes(project_id, files_sha)
        if mismatches:
            raise GenerationVerificationError(
                f"Empacotamento bloqueado (fail-closed) por integridade violada: {', '.join(mismatches)}"
            )

        bundle_rels = sorted(
            list(files_sha.keys()) + ["specs/game_specification.json", "specs/generation_manifest.json"]
        )
        ver_label = str(project.get("version", "0.1.0"))
        zip_name = f"{project_id}-{ver_label}-preview.zip"
        sha_name = f"{project_id}-{ver_label}-preview.sha256"
        rep_name = f"{project_id}-{ver_label}-preview-report.json"

        zip_path = self.manager.resolve_game_path(project_id, f"builds/{zip_name}")
        sha_path = self.manager.resolve_game_path(project_id, f"builds/{sha_name}")
        rep_path = self.manager.resolve_game_path(project_id, f"builds/{rep_name}")

        zip_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_zip = tempfile.mkstemp(prefix=".preview.", suffix=".zip", dir=str(zip_path.parent))
        os.close(fd)
        tmp_zip_path = Path(tmp_zip)
        try:
            with zipfile.ZipFile(tmp_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for rel in bundle_rels:
                    src = self.manager.resolve_game_path(project_id, rel)
                    zinfo = zipfile.ZipInfo(filename=rel, date_time=_ZIP_FIXED_DATE_TIME)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    zinfo.external_attr = 0o644 << 16
                    zf.writestr(zinfo, src.read_bytes())
            os.replace(str(tmp_zip_path), str(zip_path))
        except BaseException:
            if tmp_zip_path.exists():
                tmp_zip_path.unlink()
            raise

        artifact_bytes = zip_path.read_bytes()
        artifact_sha256 = _sha256_bytes(artifact_bytes)
        _atomic_write_text(sha_path, f"{artifact_sha256}  {zip_name}\n")

        verify_rep_path = self.manager.resolve_game_path(project_id, "specs/verification_report.json")
        godot_verified = False
        if verify_rep_path.is_file():
            try:
                godot_verified = bool(json.loads(verify_rep_path.read_text(encoding="utf-8")).get("passed"))
            except json.JSONDecodeError:
                godot_verified = False

        report = {
            "preview_report_schema_version": PREVIEW_REPORT_SCHEMA_VERSION,
            "project_id": project_id,
            "project_version": ver_label,
            "packaged_at": self.manager.now_timestamp(),
            "artifact_path": f"builds/{zip_name}",
            "checksum_path": f"builds/{sha_name}",
            "artifact_sha256": artifact_sha256,
            "artifact_size_bytes": len(artifact_bytes),
            "bundled_file_count": len(bundle_rels),
            "godot_verified": godot_verified,
        }
        _atomic_write_json(rep_path, report)
        self.manager.log_event(
            "INFO",
            "GAME_PACKAGED",
            project_id=project_id,
            artifact=f"builds/{zip_name}",
            artifact_sha256=artifact_sha256,
        )
        return report
