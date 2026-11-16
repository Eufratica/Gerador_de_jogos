"""Catalogo versionado, busca, comparacao e selecao de templates da PlayForge Factory."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from factory.playforge.models import ApprovalRequired, FactoryError
from factory.playforge.registry import ProjectManager, _atomic_write_json
from factory.playforge.spec_engine.generator import SpecificationGenerator
from factory.playforge.spec_engine.validator import parse_semver
from factory.playforge.template_registry.schemas import (
    APPROVED_OPEN_SOURCE_LICENSES,
    TEMPLATE_ID_RE,
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_DEPRECATED,
)
from factory.playforge.template_registry.validator import (
    TemplateCompatibilityError,
    TemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateValidator,
    _extract_engine_major_minor,
)


def _summarize_record(validated: dict[str, Any]) -> dict[str, Any]:
    manifest = validated["manifest"]
    return {
        "template_id": validated["template_id"],
        "name": manifest["name"],
        "template_version": validated["template_version"],
        "status": manifest["status"],
        "engine": manifest["engine"],
        "engine_version": manifest["engine_version"],
        "supported_genres": manifest["supported_genres"],
        "supported_platforms": manifest["supported_platforms"],
        "license": manifest["license"],
        "available_systems": manifest["available_systems"],
        "file_count": validated["file_count"],
        "skeleton_sha256": validated["skeleton_sha256"],
        "template_dir": validated["template_dir"],
    }


class TemplateRegistry:
    """Gerenciador fail-closed do catalogo versionado de templates (templates/<id>/<ver>/)."""

    def __init__(
        self,
        repo_root: Path | None = None,
        templates_root: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repo_root = (
            Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[3]
        )
        self.templates_root = (
            Path(templates_root).resolve() if templates_root else (self.repo_root / "templates")
        )
        self._clock = clock
        self.validator = TemplateValidator()

    def now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def default_godot_bin(self) -> Path | None:
        """Localiza o binario Godot CLI local do repositorio quando disponivel."""
        candidates = [
            self.repo_root / "tools" / "godot" / "Godot_v4.4-stable_win64_console.exe",
            self.repo_root / "tools" / "godot" / "Godot_v4.4-stable_linux.x86_64",
        ]
        for cand in candidates:
            if cand.is_file():
                return cand
        for name in ("godot4", "godot"):
            resolved = shutil.which(name)
            if resolved:
                return Path(resolved)
        return None

    def _semver_key(self, version: str) -> tuple[int, int, int]:
        try:
            return parse_semver(version)
        except FactoryError as exc:
            raise TemplateValidationError("template_version", str(exc)) from exc

    def _discover_version_dirs(self) -> list[Path]:
        if not self.templates_root.is_dir():
            return []
        found: list[Path] = []
        for tpl_dir in sorted(self.templates_root.iterdir()):
            if not tpl_dir.is_dir() or tpl_dir.name.startswith("."):
                continue
            for ver_dir in sorted(tpl_dir.iterdir()):
                if not ver_dir.is_dir() or ver_dir.name.startswith("."):
                    continue
                found.append(ver_dir)
        return found

    def list_templates(
        self,
        *,
        include_deprecated: bool = False,
        summarize: bool = True,
    ) -> list[dict[str, Any]]:
        """Lista templates validados ordenados por template_id e SemVer decrescente."""
        records: list[dict[str, Any]] = []
        for ver_dir in self._discover_version_dirs():
            validated = self.validator.validate_template_dir(ver_dir)
            if not include_deprecated and validated["template_status"] != TEMPLATE_STATUS_ACTIVE:
                continue
            records.append(validated)

        records.sort(
            key=lambda r: (
                r["template_id"],
                tuple(-p for p in self._semver_key(r["template_version"])),
            )
        )
        if summarize:
            return [_summarize_record(r) for r in records]
        return records

    def search_templates(
        self,
        *,
        genre: str | None = None,
        engine: str | None = None,
        platform: str | None = None,
        include_deprecated: bool = False,
    ) -> list[dict[str, Any]]:
        """Filtra templates validados por genero, engine e plataforma."""
        all_records = self.list_templates(include_deprecated=include_deprecated, summarize=False)
        matched: list[dict[str, Any]] = []
        for rec in all_records:
            m = rec["manifest"]
            if genre is not None and genre not in m["supported_genres"]:
                continue
            if engine is not None and m["engine"] != engine:
                continue
            if platform is not None and platform not in m["supported_platforms"]:
                continue
            matched.append(_summarize_record(rec))
        return matched

    def get_template(
        self,
        template_id: str,
        version: str | None = None,
        *,
        include_deprecated: bool = True,
    ) -> dict[str, Any]:
        """Retorna registro validado de um template especifico (ou sua versao mais recente)."""
        if not isinstance(template_id, str) or not TEMPLATE_ID_RE.match(template_id):
            raise TemplateValidationError("template_id", f"template_id invalido: {template_id!r}")

        tpl_root = self.templates_root / template_id
        if not tpl_root.is_dir():
            raise TemplateNotFoundError(f"Template '{template_id}' nao encontrado em {self.templates_root}.")

        if version is not None:
            self._semver_key(version)
            ver_dir = tpl_root / version
            if not ver_dir.is_dir():
                raise TemplateNotFoundError(f"Versao '{version}' de '{template_id}' nao encontrada.")
            validated = self.validator.validate_template_dir(ver_dir)
            if not include_deprecated and validated["template_status"] != TEMPLATE_STATUS_ACTIVE:
                raise TemplateNotFoundError(f"Versao '{version}' de '{template_id}' esta DEPRECATED.")
            return validated

        candidates: list[dict[str, Any]] = []
        for entry in sorted(tpl_root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            validated = self.validator.validate_template_dir(entry)
            if include_deprecated or validated["template_status"] == TEMPLATE_STATUS_ACTIVE:
                candidates.append(validated)

        if not candidates:
            raise TemplateNotFoundError(f"Nenhuma versao disponivel para o template '{template_id}'.")

        candidates.sort(
            key=lambda r: (
                1 if r["template_status"] == TEMPLATE_STATUS_ACTIVE else 0,
                self._semver_key(r["template_version"]),
            ),
            reverse=True,
        )
        return candidates[0]

    def validate_template(
        self,
        template_id: str,
        version: str | None = None,
        *,
        run_godot_tests: bool = False,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Executa validacao completa (e testes Godot headless opcionais) de um template."""
        rec = self.get_template(template_id, version, include_deprecated=True)
        resolved_bin = godot_bin or self.default_godot_bin()
        return self.validator.validate_template_dir(
            Path(rec["template_dir"]),
            run_godot_tests=run_godot_tests,
            godot_bin=resolved_bin,
        )

    def _evaluate_compatibility(
        self,
        template_record: dict[str, Any],
        validated_spec: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        manifest = template_record["manifest"]

        if manifest["status"] != TEMPLATE_STATUS_ACTIVE:
            reasons.append(f"Template '{manifest['template_id']}@{manifest['template_version']}' esta {manifest['status']}.")

        if manifest["license"] not in APPROVED_OPEN_SOURCE_LICENSES:
            reasons.append(f"Licenca nao aprovada: {manifest['license']}.")

        if manifest["spec_schema_version"] != validated_spec["spec_schema_version"]:
            reasons.append(
                f"spec_schema_version incompativel: template={manifest['spec_schema_version']}, "
                f"spec={validated_spec['spec_schema_version']}."
            )

        if manifest["engine"] != validated_spec["engine"]:
            reasons.append(f"Engine incompativel: template={manifest['engine']}, spec={validated_spec['engine']}.")
        else:
            tpl_mm = _extract_engine_major_minor(manifest["engine_version"])
            spec_mm = _extract_engine_major_minor(validated_spec["engine_version"])
            if tpl_mm != spec_mm:
                reasons.append(
                    f"Versao de engine incompativel: template={manifest['engine_version']}, "
                    f"spec={validated_spec['engine_version']}."
                )

        if validated_spec["genre"] not in manifest["supported_genres"]:
            reasons.append(
                f"Genero '{validated_spec['genre']}' nao suportado por {manifest['supported_genres']}."
            )

        missing_platforms = [
            p for p in validated_spec["target_platforms"] if p not in manifest["supported_platforms"]
        ]
        if missing_platforms:
            reasons.append(f"Plataformas sem suporte no template: {', '.join(missing_platforms)}.")

        return reasons

    def check_spec_compatibility(
        self,
        template_record: dict[str, Any],
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        """Verifica se o template atende fail-closed aos requisitos de GameSpecification."""
        validated_spec = self.validator.spec_validator.validate_spec(spec)
        reasons = self._evaluate_compatibility(template_record, validated_spec)
        if reasons:
            raise TemplateCompatibilityError(
                f"Template incompativel com spec '{validated_spec['spec_id']}': {'; '.join(reasons)}",
                reasons=reasons,
            )
        manifest = template_record["manifest"]
        return {
            "compatible": True,
            "template_id": manifest["template_id"],
            "template_version": manifest["template_version"],
            "spec_id": validated_spec["spec_id"],
            "engine": manifest["engine"],
            "engine_version": manifest["engine_version"],
            "skeleton_sha256": template_record["skeleton_sha256"],
        }

    def select_best_template(
        self,
        spec: dict[str, Any],
        *,
        prefer_template_id: str | None = None,
    ) -> dict[str, Any]:
        """Seleciona o melhor template ACTIVE compativel com a GameSpecification."""
        validated_spec = self.validator.spec_validator.validate_spec(spec)
        active_templates = self.list_templates(include_deprecated=False, summarize=False)
        if not active_templates:
            raise TemplateNotFoundError("Nenhum template ACTIVE encontrado no catalogo.")

        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        rejection_reasons: list[str] = []

        for rec in active_templates:
            reasons = self._evaluate_compatibility(rec, validated_spec)
            manifest = rec["manifest"]
            if reasons:
                rejection_reasons.append(
                    f"{manifest['template_id']}@{manifest['template_version']}: {'; '.join(reasons)}"
                )
                continue

            prefer_bonus = 1 if prefer_template_id and manifest["template_id"] == prefer_template_id else 0
            primary_genre_bonus = 1 if manifest["supported_genres"][0] == validated_spec["genre"] else 0
            platform_cov = len(set(validated_spec["target_platforms"]) & set(manifest["supported_platforms"]))
            systems_score = len(manifest["available_systems"])
            ver_tuple = self._semver_key(manifest["template_version"])

            sort_key = (
                prefer_bonus,
                primary_genre_bonus,
                platform_cov,
                systems_score,
                ver_tuple,
            )
            candidates.append((sort_key, rec))

        if not candidates:
            raise TemplateCompatibilityError(
                f"Nenhum template ACTIVE compativel para '{validated_spec['game_id']}' ({validated_spec['genre']}). "
                + " | ".join(rejection_reasons),
                reasons=rejection_reasons,
            )

        candidates.sort(key=lambda item: (item[0], item[1]["template_id"]), reverse=True)
        # Reordena mantendo deterministicamente menor template_id em caso de empate total de score
        top_score = candidates[0][0]
        tied = [rec for score, rec in candidates if score == top_score]
        tied.sort(key=lambda r: r["template_id"])
        best = tied[0]
        manifest = best["manifest"]

        return {
            "selected": True,
            "template_id": manifest["template_id"],
            "template_version": manifest["template_version"],
            "skeleton_sha256": best["skeleton_sha256"],
            "engine": manifest["engine"],
            "engine_version": manifest["engine_version"],
            "license": manifest["license"],
            "available_systems": manifest["available_systems"],
            "template_dir": best["template_dir"],
            "spec_id": validated_spec["spec_id"],
        }

    def select_template_for_project(
        self,
        manager: ProjectManager,
        project_id: str,
        *,
        require_approved_spec: bool = True,
        prefer_template_id: str | None = None,
        run_godot_tests: bool = False,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Seleciona e registra o template validado no workspace do projeto alvo."""
        manager.require_mutable_project(project_id)

        spec_path = manager.resolve_game_path(project_id, "specs/game_specification.json")
        if not spec_path.is_file():
            raise TemplateNotFoundError(
                f"GameSpecification ausente para projeto '{project_id}'. Execute 'spec-generate' antes."
            )

        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateValidationError("game_specification.json", f"JSON invalido: {exc}") from exc

        spec_sha256 = ""
        if require_approved_spec:
            approval = SpecificationGenerator(manager).verify_spec_approved(project_id)
            spec_sha256 = approval["spec_sha256"]
        else:
            spec_sha256 = self.validator.spec_validator.compute_spec_digest(
                self.validator.spec_validator.validate_spec(spec)
            )

        selection = self.select_best_template(spec, prefer_template_id=prefer_template_id)

        val_report = self.validate_template(
            selection["template_id"],
            selection["template_version"],
            run_godot_tests=run_godot_tests,
            godot_bin=godot_bin,
        )

        record = {
            "selection_schema_version": 1,
            "project_id": project_id,
            "selected_at": self.now_timestamp(),
            "spec_id": selection["spec_id"],
            "spec_sha256": spec_sha256,
            "template_id": selection["template_id"],
            "template_version": selection["template_version"],
            "skeleton_sha256": val_report["skeleton_sha256"],
            "engine": selection["engine"],
            "engine_version": selection["engine_version"],
            "license": selection["license"],
            "godot_tests_verified": bool(val_report["godot_test_result"] and val_report["godot_test_result"]["passed"]),
        }

        out_path = manager.resolve_game_path(project_id, "specs/template_selection.json")
        _atomic_write_json(out_path, record)
        manager.log_event(
            "INFO",
            "TEMPLATE_SELECTED",
            project_id=project_id,
            template_id=record["template_id"],
            template_version=record["template_version"],
            skeleton_sha256=record["skeleton_sha256"],
            godot_tests_verified=record["godot_tests_verified"],
        )
        return record

    def compare_templates(
        self,
        template_id_a: str,
        version_a: str | None,
        template_id_b: str,
        version_b: str | None,
    ) -> dict[str, Any]:
        """Compara sistemas, plataformas, generos, arquivos e checksum entre dois templates."""
        rec_a = self.get_template(template_id_a, version_a, include_deprecated=True)
        rec_b = self.get_template(template_id_b, version_b, include_deprecated=True)
        ma = rec_a["manifest"]
        mb = rec_b["manifest"]

        sys_a = set(ma["available_systems"])
        sys_b = set(mb["available_systems"])
        files_a = set(ma["file_structure"])
        files_b = set(mb["file_structure"])

        return {
            "left": {
                "template_id": ma["template_id"],
                "template_version": ma["template_version"],
                "status": ma["status"],
                "engine": ma["engine"],
                "engine_version": ma["engine_version"],
                "skeleton_sha256": rec_a["skeleton_sha256"],
                "file_count": rec_a["file_count"],
            },
            "right": {
                "template_id": mb["template_id"],
                "template_version": mb["template_version"],
                "status": mb["status"],
                "engine": mb["engine"],
                "engine_version": mb["engine_version"],
                "skeleton_sha256": rec_b["skeleton_sha256"],
                "file_count": rec_b["file_count"],
            },
            "shared_systems": sorted(sys_a & sys_b),
            "only_in_left_systems": sorted(sys_a - sys_b),
            "only_in_right_systems": sorted(sys_b - sys_a),
            "shared_files": sorted(files_a & files_b),
            "only_in_left_files": sorted(files_a - files_b),
            "only_in_right_files": sorted(files_b - files_a),
            "same_skeleton_sha256": rec_a["skeleton_sha256"] == rec_b["skeleton_sha256"],
        }

    def deprecate_template(
        self,
        template_id: str,
        version: str,
        reason: str,
        *,
        deprecated_by: str = "operator",
    ) -> dict[str, Any]:
        """Marca uma versao especifica como DEPRECATED sem remover arquivos nem quebrar projetos."""
        if not isinstance(reason, str) or not reason.strip():
            raise TemplateValidationError("reason", "Justificativa obrigatoria para depreciar versao.")
        if not isinstance(deprecated_by, str) or not deprecated_by.strip():
            raise TemplateValidationError("deprecated_by", "Identificacao de autor obrigatoria.")

        rec = self.get_template(template_id, version, include_deprecated=True)
        if rec["template_status"] == TEMPLATE_STATUS_DEPRECATED:
            raise TemplateError(f"Template '{template_id}@{version}' ja esta marcado como DEPRECATED.")

        tpl_dir = Path(rec["template_dir"])
        manifest_path = tpl_dir / "template_manifest.json"
        updated = dict(rec["manifest"])
        updated["status"] = TEMPLATE_STATUS_DEPRECATED
        updated["deprecation"] = {
            "deprecated_at": self.now_timestamp(),
            "deprecated_by": deprecated_by.strip(),
            "reason": reason.strip(),
        }

        self.validator.validate_manifest(updated)
        _atomic_write_json(manifest_path, updated)

        return {
            "template_id": template_id,
            "template_version": version,
            "status": TEMPLATE_STATUS_DEPRECATED,
            "deprecation": updated["deprecation"],
            "manifest_path": str(manifest_path),
        }
