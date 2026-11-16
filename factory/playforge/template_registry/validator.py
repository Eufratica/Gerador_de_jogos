"""Validacao fail-closed e verificacao de integridade de templates de jogo."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from factory.playforge.models import FactoryError
from factory.playforge.spec_engine.schemas import (
    SPEC_SCHEMA_VERSION,
    SUPPORTED_ENGINES,
    SUPPORTED_GENRES,
    SUPPORTED_PLATFORMS,
)
from factory.playforge.spec_engine.validator import SpecificationValidator, parse_semver
from factory.playforge.template_registry.schemas import (
    ALLOWED_TEST_RUNNERS,
    APPROVED_OPEN_SOURCE_LICENSES,
    TEMPLATE_ALL_ALLOWED_FIELDS,
    TEMPLATE_ID_RE,
    TEMPLATE_MANIFEST_SCHEMA_VERSION,
    TEMPLATE_REQUIRED_FIELDS,
    TEMPLATE_STATUSES,
    TEMPLATE_STATUS_DEPRECATED,
)


class TemplateError(FactoryError):
    """Erro base do subsistema Game Template Registry."""


class TemplateNotFoundError(TemplateError):
    """Template ou versao solicitada nao existe."""


class TemplateValidationError(TemplateError):
    """Falha fail-closed na validacao estrutural ou de integridade do template."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"[{field}] {message}")


class TemplateCompatibilityError(TemplateError):
    """Template nao atende aos requisitos da GameSpecification."""

    def __init__(self, message: str, reasons: list[str] | None = None) -> None:
        self.reasons = reasons or [message]
        super().__init__(message)


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _ensure_non_empty_str(val: Any, field: str) -> str:
    if not isinstance(val, str) or not val.strip():
        raise TemplateValidationError(field, "Deve ser string nao vazia.")
    return val


def _extract_engine_major_minor(version_str: str, field: str = "engine_version") -> tuple[int, int]:
    """Extrai (major, minor) de strings como '4.4-stable' ou '4.4.stable'."""
    if not isinstance(version_str, str) or not version_str.strip():
        raise TemplateValidationError(field, "Versao de engine invalida.")
    clean = version_str.strip().split("-")[0]
    parts = clean.split(".")
    if len(parts) < 2:
        raise TemplateValidationError(field, f"Formato de engine_version invalido: '{version_str}'.")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise TemplateValidationError(field, f"Versao numerica da engine invalida: '{version_str}'.") from exc


def _safe_relative_path(raw_path: str, base_dir: Path, field: str) -> Path:
    """Resolve caminho relativo estritamente dentro de base_dir, bloqueando traversal."""
    path_str = _ensure_non_empty_str(raw_path, field).strip()
    if "\x00" in path_str or "\\" in path_str or path_str.startswith("/") or ":" in path_str:
        raise TemplateValidationError(field, f"Caminho relativo inseguro ou absoluto proibido: '{raw_path}'.")
    parts = [p for p in path_str.split("/") if p != ""]
    if not parts or any(p in (".", "..") for p in parts):
        raise TemplateValidationError(field, f"Traversal ou segmento invalido em '{raw_path}'.")
    base_resolved = base_dir.resolve()
    target = (base_resolved / Path(*parts)).resolve()
    if not target.is_relative_to(base_resolved) or target == base_resolved:
        raise TemplateValidationError(field, f"Caminho '{raw_path}' escapa do diretorio raiz permitido.")
    return target


def _validate_str_list(
    raw: Any,
    field: str,
    *,
    allow_empty: bool = False,
    allowed_values: tuple[str, ...] | None = None,
    require_unique: bool = True,
) -> list[str]:
    if not isinstance(raw, list):
        raise TemplateValidationError(field, "Deve ser uma lista.")
    if not allow_empty and len(raw) == 0:
        raise TemplateValidationError(field, "Lista nao pode ser vazia.")
    seen: set[str] = set()
    result: list[str] = []
    for idx, item in enumerate(raw):
        item_str = _ensure_non_empty_str(item, f"{field}[{idx}]")
        if allowed_values is not None and item_str not in allowed_values:
            raise TemplateValidationError(
                f"{field}[{idx}]",
                f"Valor '{item_str}' nao permitido. Suportados: {', '.join(allowed_values)}.",
            )
        if require_unique and item_str in seen:
            raise TemplateValidationError(f"{field}[{idx}]", f"Item duplicado: '{item_str}'.")
        seen.add(item_str)
        result.append(item_str)
    return result


class TemplateValidator:
    """Validador estrutural, de integridade de arquivos e de runner Godot para templates."""

    def __init__(self) -> None:
        self.spec_validator = SpecificationValidator()

    def validate_manifest(self, manifest: Any) -> dict[str, Any]:
        """Valida o dicionario de template_manifest.json em modo fail-closed."""
        if not isinstance(manifest, dict):
            raise TemplateValidationError("manifest", "Manifesto deve ser um objeto JSON.")

        for key in manifest:
            if key not in TEMPLATE_ALL_ALLOWED_FIELDS:
                raise TemplateValidationError(key, f"Campo desconhecido nao permitido no manifesto: '{key}'.")

        for req in TEMPLATE_REQUIRED_FIELDS:
            if req not in manifest:
                raise TemplateValidationError(req, f"Campo obrigatorio ausente no manifesto: '{req}'.")

        schema_ver = manifest["template_manifest_schema_version"]
        if not _is_strict_int(schema_ver) or schema_ver != TEMPLATE_MANIFEST_SCHEMA_VERSION:
            raise TemplateValidationError(
                "template_manifest_schema_version",
                f"Versao de schema suportada e {TEMPLATE_MANIFEST_SCHEMA_VERSION}, recebido: {schema_ver!r}.",
            )

        tpl_id = _ensure_non_empty_str(manifest["template_id"], "template_id")
        if not TEMPLATE_ID_RE.match(tpl_id):
            raise TemplateValidationError(
                "template_id",
                f"template_id '{tpl_id}' invalido; use kebab-case (3-64 chars).",
            )

        _ensure_non_empty_str(manifest["name"], "name")
        _ensure_non_empty_str(manifest["description"], "description")

        tpl_ver = _ensure_non_empty_str(manifest["template_version"], "template_version")
        try:
            parse_semver(tpl_ver)
        except FactoryError as exc:
            raise TemplateValidationError("template_version", str(exc)) from exc

        engine = _ensure_non_empty_str(manifest["engine"], "engine")
        if engine not in SUPPORTED_ENGINES:
            raise TemplateValidationError(
                "engine",
                f"Engine '{engine}' nao suportada. Permitidas: {', '.join(SUPPORTED_ENGINES)}.",
            )

        engine_version = _ensure_non_empty_str(manifest["engine_version"], "engine_version")
        _extract_engine_major_minor(engine_version, field="engine_version")

        _validate_str_list(
            manifest["supported_genres"],
            "supported_genres",
            allowed_values=SUPPORTED_GENRES,
        )
        _validate_str_list(
            manifest["supported_platforms"],
            "supported_platforms",
            allowed_values=SUPPORTED_PLATFORMS,
        )

        status = _ensure_non_empty_str(manifest["status"], "status")
        if status not in TEMPLATE_STATUSES:
            raise TemplateValidationError(
                "status",
                f"Status '{status}' invalido. Permitidos: {', '.join(TEMPLATE_STATUSES)}.",
            )
        if status == TEMPLATE_STATUS_DEPRECATED and "deprecation" in manifest:
            dep = manifest["deprecation"]
            if not isinstance(dep, dict):
                raise TemplateValidationError("deprecation", "Bloco deprecation deve ser um objeto JSON.")
            _ensure_non_empty_str(dep.get("deprecated_at"), "deprecation.deprecated_at")
            _ensure_non_empty_str(dep.get("reason"), "deprecation.reason")

        spec_ver = manifest["spec_schema_version"]
        if not _is_strict_int(spec_ver) or spec_ver != SPEC_SCHEMA_VERSION:
            raise TemplateValidationError(
                "spec_schema_version",
                f"spec_schema_version esperado {SPEC_SCHEMA_VERSION}, recebido: {spec_ver!r}.",
            )

        license_name = _ensure_non_empty_str(manifest["license"], "license")
        if license_name not in APPROVED_OPEN_SOURCE_LICENSES:
            raise TemplateValidationError(
                "license",
                f"Licenca '{license_name}' fora da politica Zero Cost/Free Open Source: {APPROVED_OPEN_SOURCE_LICENSES}.",
            )

        _validate_str_list(manifest["available_systems"], "available_systems")
        reusable = _validate_str_list(manifest["reusable_components"], "reusable_components")

        asset_slots = manifest["asset_slots"]
        if not isinstance(asset_slots, dict):
            raise TemplateValidationError("asset_slots", "asset_slots deve ser um dicionario.")
        for slot_name, slot_cfg in asset_slots.items():
            _ensure_non_empty_str(slot_name, "asset_slots")
            if not isinstance(slot_cfg, dict):
                raise TemplateValidationError(f"asset_slots.{slot_name}", "Definicao de slot deve ser objeto.")

        _validate_str_list(manifest["dependencies"], "dependencies", allow_empty=True)

        allowed_exts = _validate_str_list(manifest["allowed_extensions"], "allowed_extensions")
        for idx, ext in enumerate(allowed_exts):
            if not ext.startswith(".") or len(ext) < 2 or "/" in ext or "\\" in ext or ".." in ext or ext != ext.lower():
                raise TemplateValidationError(
                    f"allowed_extensions[{idx}]",
                    f"Extensao invalida '{ext}'; use formato '.ext' minusculo.",
                )
        allowed_ext_set = set(allowed_exts)

        file_structure = _validate_str_list(manifest["file_structure"], "file_structure")
        for idx, rel in enumerate(file_structure):
            suffix = Path(rel).suffix.lower()
            if suffix not in allowed_ext_set:
                raise TemplateValidationError(
                    f"file_structure[{idx}]",
                    f"Arquivo '{rel}' possui extensao '{suffix}' fora de allowed_extensions.",
                )

        file_set = set(file_structure)
        for idx, comp in enumerate(reusable):
            if comp not in file_set:
                raise TemplateValidationError(
                    f"reusable_components[{idx}]",
                    f"Componente reutilizavel '{comp}' deve constar em file_structure.",
                )

        tests_cfg = manifest["tests"]
        if not isinstance(tests_cfg, dict):
            raise TemplateValidationError("tests", "Campo tests deve ser um objeto.")
        runner = _ensure_non_empty_str(tests_cfg.get("runner"), "tests.runner")
        if runner not in ALLOWED_TEST_RUNNERS:
            raise TemplateValidationError("tests.runner", f"Runner '{runner}' nao suportado.")
        script = _ensure_non_empty_str(tests_cfg.get("script"), "tests.script")
        if not script.startswith("res://") or not script.endswith(".gd"):
            raise TemplateValidationError("tests.script", "tests.script deve comecar com 'res://' e terminar com '.gd'.")

        _ensure_non_empty_str(manifest["documentation"], "documentation")
        _ensure_non_empty_str(manifest["demo_project_path"], "demo_project_path")

        return manifest

    def compute_skeleton_digest(self, skeleton_dir: Path, file_structure: list[str]) -> str:
        """Calcula hash SHA-256 deterministico sobre os caminhos normalizados e conteudos do skeleton/."""
        digest = hashlib.sha256()
        base = skeleton_dir.resolve()
        for rel in sorted(file_structure):
            target = _safe_relative_path(rel, base, "file_structure")
            if not target.is_file():
                raise TemplateValidationError("file_structure", f"Arquivo ausente para digest: '{rel}'.")
            file_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            digest.update(f"{rel}\0{file_hash}\n".encode("utf-8"))
        return digest.hexdigest()

    def validate_template_dir(
        self,
        template_dir: Path,
        *,
        run_godot_tests: bool = False,
        godot_bin: Path | None = None,
    ) -> dict[str, Any]:
        """Valida manifesto, estrutura de pastas, extensoes, digest e testes do template."""
        if not template_dir.exists() or not template_dir.is_dir():
            raise TemplateNotFoundError(f"Diretorio de template nao encontrado: {template_dir}")

        manifest_path = template_dir / "template_manifest.json"
        if not manifest_path.is_file():
            raise TemplateValidationError("template_manifest.json", f"Manifesto ausente em {template_dir}.")

        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TemplateValidationError("template_manifest.json", f"JSON malformado: {exc}") from exc

        manifest = self.validate_manifest(raw_manifest)

        # Garante coerencia entre caminho em disco (<template_id>/<version>) e manifesto
        if template_dir.name != manifest["template_version"] or template_dir.parent.name != manifest["template_id"]:
            raise TemplateValidationError(
                "template_dir",
                (
                    f"Caminho '{template_dir}' diverge de "
                    f"'{manifest['template_id']}/{manifest['template_version']}'."
                ),
            )

        doc_target = _safe_relative_path(manifest["documentation"], template_dir, "documentation")
        if not doc_target.is_file():
            raise TemplateValidationError("documentation", f"Documentacao '{manifest['documentation']}' ausente.")

        skeleton_dir = template_dir / "skeleton"
        if not skeleton_dir.is_dir():
            raise TemplateValidationError("skeleton", f"Diretorio skeleton/ ausente em {template_dir}.")

        declared_files = set(manifest["file_structure"])
        for rel in manifest["file_structure"]:
            target = _safe_relative_path(rel, skeleton_dir, "file_structure")
            if not target.is_file():
                raise TemplateValidationError("file_structure", f"Arquivo declarado ausente em skeleton/: '{rel}'.")

        allowed_ext_set = set(manifest["allowed_extensions"])
        skeleton_resolved = skeleton_dir.resolve()
        for entry in skeleton_resolved.rglob("*"):
            if entry.is_dir():
                continue
            rel_posix = entry.relative_to(skeleton_resolved).as_posix()
            if entry.suffix.lower() not in allowed_ext_set:
                raise TemplateValidationError(
                    "allowed_extensions",
                    f"Arquivo com extensao proibida detectado em skeleton/: '{rel_posix}'.",
                )
            if rel_posix not in declared_files:
                raise TemplateValidationError(
                    "file_structure",
                    f"Arquivo nao declarado no manifesto presente em skeleton/: '{rel_posix}'.",
                )

        demo_dir = _safe_relative_path(manifest["demo_project_path"], template_dir, "demo_project_path")
        if not demo_dir.is_dir():
            raise TemplateValidationError("demo_project_path", f"Projeto demo ausente: '{manifest['demo_project_path']}'.")
        if not (demo_dir / "project.godot").is_file():
            raise TemplateValidationError("demo_project_path", "project.godot ausente no projeto demo.")

        script_rel = manifest["tests"]["script"][len("res://") :]
        demo_script = _safe_relative_path(script_rel, demo_dir, "tests.script")
        skeleton_script = _safe_relative_path(script_rel, skeleton_dir, "tests.script")
        if not demo_script.is_file() or not skeleton_script.is_file():
            raise TemplateValidationError(
                "tests.script",
                f"Script de teste '{manifest['tests']['script']}' deve existir em skeleton/ e demo/.",
            )

        skeleton_sha256 = self.compute_skeleton_digest(skeleton_dir, manifest["file_structure"])

        godot_test_result: dict[str, Any] | None = None
        if run_godot_tests:
            if godot_bin is None or not Path(godot_bin).is_file():
                raise TemplateValidationError(
                    "tests",
                    f"Binario Godot CLI nao encontrado para executar testes do template: {godot_bin}",
                )
            godot_test_result = self.run_demo_tests(
                demo_dir=demo_dir,
                test_script_res=manifest["tests"]["script"],
                godot_bin=Path(godot_bin),
            )

        return {
            "status": "VALID",
            "template_id": manifest["template_id"],
            "template_version": manifest["template_version"],
            "template_status": manifest["status"],
            "engine": manifest["engine"],
            "engine_version": manifest["engine_version"],
            "license": manifest["license"],
            "skeleton_sha256": skeleton_sha256,
            "file_count": len(manifest["file_structure"]),
            "manifest": manifest,
            "template_dir": str(template_dir.resolve()),
            "godot_test_result": godot_test_result,
        }

    def run_demo_tests(
        self,
        *,
        demo_dir: Path,
        test_script_res: str,
        godot_bin: Path,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]:
        """Executa o projeto demo do template em copia temporaria limpa via Godot CLI headless."""
        with tempfile.TemporaryDirectory(prefix="playforge_tpl_demo_") as tmp:
            tmp_path = Path(tmp)
            proj_copy = tmp_path / "project"
            user_home = tmp_path / "user_home"
            user_home.mkdir(parents=True, exist_ok=True)
            shutil.copytree(demo_dir, proj_copy)

            env = os.environ.copy()
            env["APPDATA"] = str(user_home)
            env["LOCALAPPDATA"] = str(user_home)
            env["USERPROFILE"] = str(user_home)
            env["HOME"] = str(user_home)

            cmd = [
                str(godot_bin),
                "--headless",
                "--no-header",
                "--path",
                str(proj_copy),
                "--script",
                test_script_res,
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
                check=False,
            )
            combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
            if proc.returncode != 0 or "SCRIPT ERROR:" in combined or "Failed: 0" not in combined:
                raise TemplateValidationError(
                    "tests",
                    f"Execucao headless do template falhou (code={proc.returncode}): {combined}",
                )
            return {
                "passed": True,
                "returncode": proc.returncode,
                "script": test_script_res,
                "output": combined,
            }
