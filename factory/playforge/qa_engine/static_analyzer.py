"""Analise estatica multi-projeto, integridade res://, pureza de core e higiene de segredos (Fase 8)."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from factory.playforge.models import ANCHOR_PROJECT_ID
from factory.playforge.registry import ProjectManager, validate_project_id
from factory.playforge.security_utils import is_forbidden_secret_relpath
from factory.playforge.spec_engine.validator import SpecificationValidator, ValidationError

from .schemas import (
    ANCHOR_GAME_DIRS,
    ANCHOR_GAME_FILES,
    CORE_FORBIDDEN_BASE_CLASSES,
    CORE_FORBIDDEN_CALLS,
    CORE_FORBIDDEN_SYMBOLS,
    IGNORED_WORKSPACE_DIRS,
    TEXT_SCAN_EXTENSIONS,
)

_EXTENDS_RE = re.compile(r"^\s*extends\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_FORBIDDEN_SYMBOL_RE = re.compile(
    r"\b(" + "|".join(re.escape(sym) for sym in CORE_FORBIDDEN_SYMBOLS) + r")\b"
)
_FORBIDDEN_CALL_RE = re.compile(
    r"\b(" + "|".join(re.escape(call) for call in CORE_FORBIDDEN_CALLS) + r")\b"
)

_GODOT_MAIN_SCENE_RE = re.compile(r'^\s*run/main_scene\s*=\s*"(res://[^"]+)"')
_TSCN_EXT_RES_RE = re.compile(r'path\s*=\s*"(res://[^"]+)"')
_GD_LOAD_RE = re.compile(r'\b(?:preload|load|ResourceLoader\.load)\s*\(\s*"(res://[^"]+)"')

_HARDCODED_SECRET_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_sk_token", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("github_pat_token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_\-]{20,}\b")),
    ("private_key_pem", re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----")),
    ("bearer_literal", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}")),
    (
        "credential_assignment",
        re.compile(
            r"""(?:api_key|secret_key|private_key|password|passwd|access_token|auth_token)\s*[:=]\s*["']([^"'\s]{8,})["']""",
            re.IGNORECASE,
        ),
    ),
)

_PLACEHOLDER_SECRET_WORDS = frozenset({
    "placeholder",
    "example",
    "changeme",
    "redacted",
    "dummy",
    "test_only",
    "none",
    "null",
})


def ensure_auditable_project(manager: ProjectManager, project_id: str) -> bool:
    """Valida que project_id pode ser auditado; permite leitura do âncora antes de 'init'."""
    validate_project_id(project_id)
    if (
        project_id == ANCHOR_PROJECT_ID
        and not manager.registry_path.is_file()
        and (manager.repo_root / "project.godot").is_file()
    ):
        return False
    manager.get_project(project_id)
    return True


def safe_log_qa_event(
    manager: ProjectManager,
    level: str,
    event: str,
    *,
    project_id: str,
    **fields: Any,
) -> None:
    """Registra log estruturado apenas quando o workspace ja possui registry/dados inicializados."""
    if project_id == ANCHOR_PROJECT_ID and not manager.registry_path.is_file():
        return
    manager.log_event(level, event, project_id=project_id, **fields)


def collect_project_files(manager: ProjectManager, project_id: str) -> tuple[Path, list[tuple[str, Path]]]:
    """Retorna (ws_root, [(rel_posix, path)]) respeitando escopo isolado do projeto ou âncora."""
    ensure_auditable_project(manager, project_id)

    files: list[tuple[str, Path]] = []
    if project_id == ANCHOR_PROJECT_ID:
        ws_root = manager.repo_root.resolve()
        for fname in ANCHOR_GAME_FILES:
            candidate = ws_root / fname
            if candidate.is_file():
                files.append((fname, candidate))
        for dname in ANCHOR_GAME_DIRS:
            sub_dir = ws_root / dname
            if not sub_dir.is_dir():
                continue
            for item in sorted(sub_dir.rglob("*")):
                if any(part in IGNORED_WORKSPACE_DIRS for part in item.relative_to(ws_root).parts):
                    continue
                if item.is_file():
                    files.append((item.relative_to(ws_root).as_posix(), item))
        return ws_root, sorted(files, key=lambda pair: pair[0])

    ws_root = manager.resolve_game_path(project_id, ".").resolve()
    for item in sorted(ws_root.rglob("*")):
        rel_parts = item.relative_to(ws_root).parts
        if any(part in IGNORED_WORKSPACE_DIRS for part in rel_parts):
            continue
        if item.is_file():
            files.append((item.relative_to(ws_root).as_posix(), item))
    return ws_root, sorted(files, key=lambda pair: pair[0])


def stage_isolated_godot_project(manager: ProjectManager, project_id: str, dest_dir: Path) -> Path:
    """Copia apenas os arquivos de jogo do projeto para dest_dir sem poluir o workspace original."""
    _, files = collect_project_files(manager, project_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for rel, src in files:
        if rel.startswith("specs/") or rel.startswith("gdd/"):
            continue
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest_dir


def _strip_gd_comments_outside_strings(line: str, *, strip_strings: bool = False) -> str:
    """Remove comentarios '#' fora de literais de string; opcionalmente apaga conteudo de strings."""
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for ch in line:
        if quote is not None:
            if not strip_strings:
                out.append(ch)
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == quote:
                quote = None
                if strip_strings:
                    out.append(ch)
            continue

        if ch == "#":
            break
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            continue
        out.append(ch)
    return "".join(out)


def _is_placeholder_literal(value: str) -> bool:
    norm = value.strip().lower()
    if norm in _PLACEHOLDER_SECRET_WORDS:
        return True
    return norm.startswith("***redacted") or norm.startswith("<") and norm.endswith(">")


class StaticAnalyzer:
    """Auditor estatico multi-projeto para layout Godot, res://, segredos e pureza src/core/."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager
        self.spec_validator = SpecificationValidator()

    def audit_project(self, project_id: str) -> dict[str, Any]:
        """Executa auditoria estatica completa fail-closed sobre project_id."""
        ws_root, project_files = collect_project_files(self.manager, project_id)
        file_map = {rel: path for rel, path in project_files}
        violations: list[dict[str, Any]] = []

        self._check_project_godot_and_main_scene(file_map, violations)
        self._check_secret_hygiene(project_files, violations)
        res_refs_checked = self._check_res_references(project_files, ws_root, violations)
        core_files_checked = self._check_core_purity(project_files, violations)
        spec_ok, gen_integrity_ok = self._check_factory_metadata(project_id, file_map, violations)

        passed = len(violations) == 0
        safe_log_qa_event(
            self.manager,
            "INFO" if passed else "ERROR",
            "QA_STATIC_AUDIT",
            project_id=project_id,
            passed=passed,
            violation_count=len(violations),
            core_files_checked=core_files_checked,
            res_refs_checked=res_refs_checked,
        )
        return {
            "passed": passed,
            "project_id": project_id,
            "workspace_root": str(ws_root),
            "files_scanned": len(project_files),
            "core_files_checked": core_files_checked,
            "res_refs_checked": res_refs_checked,
            "spec_valid": spec_ok,
            "generation_integrity_ok": gen_integrity_ok,
            "violations": violations,
        }

    def _add_violation(
        self,
        violations: list[dict[str, Any]],
        *,
        rule: str,
        file: str,
        line: int | None,
        detail: str,
    ) -> None:
        violations.append(
            {
                "rule": rule,
                "file": file,
                "line": line,
                "detail": detail,
            }
        )

    def _check_project_godot_and_main_scene(
        self,
        file_map: dict[str, Path],
        violations: list[dict[str, Any]],
    ) -> None:
        pg_path = file_map.get("project.godot")
        if pg_path is None:
            self._add_violation(
                violations,
                rule="GODOT_LAYOUT",
                file="project.godot",
                line=None,
                detail="Arquivo obrigatorio project.godot ausente no workspace.",
            )
            return

        main_scene_rel: str | None = None
        for idx, raw_line in enumerate(pg_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            m = _GODOT_MAIN_SCENE_RE.match(raw_line)
            if m:
                main_scene_rel = m.group(1)
                target = m.group(1)[len("res://") :]
                if target not in file_map:
                    self._add_violation(
                        violations,
                        rule="GT-03_RES_REFERENCE",
                        file="project.godot",
                        line=idx,
                        detail=f"Cena principal '{main_scene_rel}' aponta para arquivo inexistente '{target}'.",
                    )
                break

        if main_scene_rel is None:
            self._add_violation(
                violations,
                rule="GODOT_LAYOUT",
                file="project.godot",
                line=None,
                detail="Chave run/main_scene ausente em project.godot.",
            )

    def _check_secret_hygiene(
        self,
        project_files: list[tuple[str, Path]],
        violations: list[dict[str, Any]],
    ) -> None:
        for rel, path in project_files:
            if is_forbidden_secret_relpath(rel):
                self._add_violation(
                    violations,
                    rule="SEC_FORBIDDEN_FILE",
                    file=rel,
                    line=None,
                    detail=f"Arquivo proibido ou potencial keystore/credencial detectado: '{rel}'.",
                )
                continue

            if path.suffix.lower() not in TEXT_SCAN_EXTENSIONS:
                continue

            text = path.read_text(encoding="utf-8", errors="replace")
            for idx, line in enumerate(text.splitlines(), start=1):
                for rule_name, pattern in _HARDCODED_SECRET_RULES:
                    match = pattern.search(line)
                    if not match:
                        continue
                    if rule_name == "credential_assignment" and _is_placeholder_literal(match.group(1)):
                        continue
                    self._add_violation(
                        violations,
                        rule="SEC_HARDCODED_SECRET",
                        file=rel,
                        line=idx,
                        detail=f"Padrao de credencial suspeita ({rule_name}) encontrado em arquivo de jogo.",
                    )

    def _check_res_references(
        self,
        project_files: list[tuple[str, Path]],
        ws_root: Path,
        violations: list[dict[str, Any]],
    ) -> int:
        checked = 0
        for rel, path in project_files:
            suffix = path.suffix.lower()
            if suffix in (".tscn", ".tres"):
                pattern = _TSCN_EXT_RES_RE
                strip_comments = False
            elif suffix == ".gd" and rel.startswith("src/"):
                pattern = _GD_LOAD_RE
                strip_comments = True
            else:
                continue

            text = path.read_text(encoding="utf-8", errors="replace")
            for idx, raw_line in enumerate(text.splitlines(), start=1):
                scan_line = _strip_gd_comments_outside_strings(raw_line) if strip_comments else raw_line
                for match in pattern.finditer(scan_line):
                    checked += 1
                    res_uri = match.group(1)
                    target_rel = res_uri[len("res://") :]
                    if ".." in Path(target_rel).parts:
                        self._add_violation(
                            violations,
                            rule="GT-03_RES_REFERENCE",
                            file=rel,
                            line=idx,
                            detail=f"Travessia proibida em referencia '{res_uri}'.",
                        )
                        continue
                    target_path = (ws_root / target_rel).resolve()
                    try:
                        target_path.relative_to(ws_root)
                    except ValueError:
                        self._add_violation(
                            violations,
                            rule="GT-03_RES_REFERENCE",
                            file=rel,
                            line=idx,
                            detail=f"Referencia '{res_uri}' escapa do workspace.",
                        )
                        continue
                    if not target_path.exists():
                        self._add_violation(
                            violations,
                            rule="GT-03_RES_REFERENCE",
                            file=rel,
                            line=idx,
                            detail=f"Referencia quebrada '{res_uri}' (arquivo nao encontrado).",
                        )
        return checked

    def _check_core_purity(
        self,
        project_files: list[tuple[str, Path]],
        violations: list[dict[str, Any]],
    ) -> int:
        core_checked = 0
        for rel, path in project_files:
            if not (rel.startswith("src/core/") and path.suffix.lower() == ".gd"):
                continue
            core_checked += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for idx, raw_line in enumerate(text.splitlines(), start=1):
                code_line = _strip_gd_comments_outside_strings(raw_line, strip_strings=True)
                if not code_line.strip():
                    continue

                ext_match = _EXTENDS_RE.match(code_line)
                if ext_match and ext_match.group(1) in CORE_FORBIDDEN_BASE_CLASSES:
                    self._add_violation(
                        violations,
                        rule="GT-01_CORE_PURITY",
                        file=rel,
                        line=idx,
                        detail=f"src/core/ nao pode herdar classe de engine '{ext_match.group(1)}'.",
                    )
                    continue

                sym_match = _FORBIDDEN_SYMBOL_RE.search(code_line)
                if sym_match:
                    self._add_violation(
                        violations,
                        rule="GT-01_CORE_PURITY",
                        file=rel,
                        line=idx,
                        detail=f"Simbolo de engine/I/O proibido em src/core/: '{sym_match.group(1)}'.",
                    )
                    continue

                call_match = _FORBIDDEN_CALL_RE.search(code_line)
                if call_match:
                    self._add_violation(
                        violations,
                        rule="GT-01_CORE_PURITY",
                        file=rel,
                        line=idx,
                        detail=f"Chamada de SO/SceneTree proibida em src/core/: '{call_match.group(1)}'.",
                    )
        return core_checked

    def _check_factory_metadata(
        self,
        project_id: str,
        file_map: dict[str, Path],
        violations: list[dict[str, Any]],
    ) -> tuple[bool | None, bool | None]:
        if project_id == ANCHOR_PROJECT_ID:
            return None, None

        spec_ok: bool | None = None
        spec_path = file_map.get("specs/game_specification.json")
        if spec_path is not None:
            try:
                spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
                self.spec_validator.validate_spec(spec_data)
                spec_ok = True
            except (json.JSONDecodeError, ValidationError) as exc:
                spec_ok = False
                self._add_violation(
                    violations,
                    rule="SPEC_INVALID",
                    file="specs/game_specification.json",
                    line=None,
                    detail=f"GameSpecification invalida na auditoria estatica: {exc}",
                )

        gen_ok: bool | None = None
        gen_path = file_map.get("specs/generation_manifest.json")
        if gen_path is not None:
            try:
                manifest = json.loads(gen_path.read_text(encoding="utf-8"))
                hashes = manifest.get("files_sha256", {})
                if not isinstance(hashes, dict) or not hashes:
                    raise ValueError("files_sha256 ausente ou vazio.")
                mismatches = 0
                for target_rel, expected_sha in sorted(hashes.items()):
                    target_path = file_map.get(target_rel)
                    if target_path is None:
                        mismatches += 1
                        self._add_violation(
                            violations,
                            rule="GEN_INTEGRITY",
                            file=target_rel,
                            line=None,
                            detail="Arquivo declarado em generation_manifest.json esta ausente.",
                        )
                        continue
                    actual_sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
                    if actual_sha != expected_sha:
                        mismatches += 1
                        self._add_violation(
                            violations,
                            rule="GEN_INTEGRITY",
                            file=target_rel,
                            line=None,
                            detail="SHA-256 no disco diverge de generation_manifest.json.",
                        )
                gen_ok = mismatches == 0
            except (json.JSONDecodeError, ValueError) as exc:
                gen_ok = False
                self._add_violation(
                    violations,
                    rule="GEN_INTEGRITY",
                    file="specs/generation_manifest.json",
                    line=None,
                    detail=f"generation_manifest.json corrompido: {exc}",
                )

        return spec_ok, gen_ok
