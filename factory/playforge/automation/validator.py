"""Validador fail-closed de exports JSON do n8n (zero credenciais, zero APIs pagas) (Fase 9)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from factory.playforge.security_utils import is_forbidden_secret_relpath

from .schemas import (
    ALLOWED_LOOPBACK_HOSTS,
    FORBIDDEN_COMMERCIAL_DOMAINS,
    OFFICIAL_WORKFLOW_CATALOG,
    WorkflowDefinition,
    WorkflowValidationError,
)

_URL_RE = re.compile(r"https?://[^\s'\"`<>]+", re.IGNORECASE)
_SECRET_LITERAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_sk_token", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("github_pat_token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[A-Za-z0-9_\-]{20,}\b")),
    ("bearer_literal", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}")),
    ("private_key_pem", re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE KEY-----")),
)
_SUSPICIOUS_KEY_NAMES = frozenset({
    "apikey",
    "api_key",
    "secret",
    "password",
    "passwd",
    "access_token",
    "auth_token",
    "private_key",
})


def _scan_payload_security(value: Any, path_prefix: str, issues: list[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            key_str = str(k)
            key_lower = key_str.lower()
            next_path = f"{path_prefix}.{key_str}"
            if key_lower == "credentials" and v:
                issues.append(f"Credenciais n8n nao sao permitidas em exports versionados ({next_path}).")
            if key_lower in _SUSPICIOUS_KEY_NAMES and isinstance(v, str) and v.strip():
                issues.append(f"Campo sensivel preenchido no export ({next_path}).")
            _scan_payload_security(v, next_path, issues)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_payload_security(item, f"{path_prefix}[{idx}]", issues)
    elif isinstance(value, str):
        for label, pat in _SECRET_LITERAL_PATTERNS:
            if pat.search(value):
                issues.append(f"Possivel segredo/token ({label}) detectado em {path_prefix}.")
        lower_val = value.lower()
        for domain in FORBIDDEN_COMMERCIAL_DOMAINS:
            if domain in lower_val:
                issues.append(f"Dominio comercial externo proibido ({domain}) em {path_prefix}.")
        for url_match in _URL_RE.findall(value):
            parsed = urlparse(url_match)
            host = (parsed.hostname or "").lower()
            if host and host not in ALLOWED_LOOPBACK_HOSTS:
                issues.append(
                    f"URL externa fora de loopback nao permitida em export n8n ({url_match}) em {path_prefix}."
                )


def validate_workflow_export(
    data: Any,
    *,
    expected_def: WorkflowDefinition | None = None,
) -> list[str]:
    """Valida um workflow exportado n8n; retorna lista de falhas (vazia quando valido)."""
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["Export JSON raiz deve ser um objeto Dictionary."]

    for req_field in ("name", "nodes", "connections", "active", "settings", "meta"):
        if req_field not in data:
            issues.append(f"Campo obrigatorio ausente no export n8n: '{req_field}'.")

    if isinstance(data.get("active"), bool) and data.get("active") is True:
        issues.append("Export versionado deve possuir 'active: false' para importacao segura.")
    elif not isinstance(data.get("active"), bool):
        issues.append("Campo 'active' deve ser boolean.")

    nodes = data.get("nodes")
    node_names: set[str] = set()
    if not isinstance(nodes, list) or not nodes:
        issues.append("Lista 'nodes' deve ser nao vazia.")
        nodes = []

    has_if_gate = False
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            issues.append(f"Node[{idx}] invalido (esperado dict).")
            continue
        for nf in ("id", "name", "type", "position"):
            if nf not in node:
                issues.append(f"Node[{idx}] sem campo obrigatorio '{nf}'.")
        n_name = node.get("name")
        if isinstance(n_name, str) and n_name:
            if n_name in node_names:
                issues.append(f"Nome de node duplicado no workflow: '{n_name}'.")
            node_names.add(n_name)
        if node.get("type") == "n8n-nodes-base.if":
            has_if_gate = True

    connections = data.get("connections")
    if isinstance(connections, dict):
        for src_name, targets_map in connections.items():
            if src_name not in node_names:
                issues.append(f"Conexao aponta origem inexistente '{src_name}'.")
            if not isinstance(targets_map, dict):
                issues.append(f"Bloco de conexoes invalido para '{src_name}'.")
                continue
            for port_lists in targets_map.values():
                if not isinstance(port_lists, list):
                    continue
                for group in port_lists:
                    if not isinstance(group, list):
                        continue
                    for edge in group:
                        if isinstance(edge, dict):
                            tgt = edge.get("node")
                            if tgt not in node_names:
                                issues.append(f"Conexao '{src_name}' -> '{tgt}' aponta node inexistente.")
    else:
        issues.append("Campo 'connections' deve ser dict.")

    _scan_payload_security(data, "workflow", issues)

    if expected_def is not None:
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        if meta.get("workflowId") != expected_def.workflow_id:
            issues.append(
                f"meta.workflowId esperado '{expected_def.workflow_id}', recebido {meta.get('workflowId')!r}."
            )
        if meta.get("zeroCostPolicy") != "ENFORCED_LOCAL_ONLY":
            issues.append("meta.zeroCostPolicy ausente ou divergente de 'ENFORCED_LOCAL_ONLY'.")
        if expected_def.requires_human_gate:
            if not bool(meta.get("requiresHumanGate")):
                issues.append(f"{expected_def.workflow_id} exige meta.requiresHumanGate=true.")
            if not has_if_gate:
                issues.append(f"{expected_def.workflow_id} exige node de gate condicional 'n8n-nodes-base.if'.")

    return issues


def validate_exports_directory(
    exports_dir: Path,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Audita completude de WF-001..WF-020, orfaos, segredos e schema em exports_dir."""
    issues_by_file: dict[str, list[str]] = {}
    validated_ids: list[str] = []

    if not exports_dir.is_dir():
        err_msg = f"Diretorio de exports nao encontrado: '{exports_dir}'."
        if strict:
            raise WorkflowValidationError(err_msg)
        return {
            "passed": False,
            "exports_dir": str(exports_dir),
            "expected_count": len(OFFICIAL_WORKFLOW_CATALOG),
            "validated_count": 0,
            "issues": {"directory": [err_msg]},
        }

    expected_filenames = {defn.filename for defn in OFFICIAL_WORKFLOW_CATALOG}

    for item in sorted(exports_dir.rglob("*")):
        if item.is_dir():
            continue
        rel = item.relative_to(exports_dir).as_posix()
        if is_forbidden_secret_relpath(rel):
            issues_by_file.setdefault(rel, []).append("Arquivo sensivel/proibido detectado em automation/exports/.")
            continue
        if rel not in expected_filenames:
            issues_by_file.setdefault(rel, []).append("Arquivo nao catalogado/orfao em automation/exports/.")

    for defn in OFFICIAL_WORKFLOW_CATALOG:
        path = exports_dir / defn.filename
        if not path.is_file():
            issues_by_file.setdefault(defn.filename, []).append(
                f"Workflow obrigatorio ausente: '{defn.filename}' ({defn.workflow_id})."
            )
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues_by_file.setdefault(defn.filename, []).append(f"JSON invalido: {exc}")
            continue
        file_issues = validate_workflow_export(raw, expected_def=defn)
        if file_issues:
            issues_by_file[defn.filename] = file_issues
        else:
            validated_ids.append(defn.workflow_id)

    passed = len(issues_by_file) == 0 and len(validated_ids) == len(OFFICIAL_WORKFLOW_CATALOG)
    report = {
        "passed": passed,
        "exports_dir": str(exports_dir),
        "expected_count": len(OFFICIAL_WORKFLOW_CATALOG),
        "validated_count": len(validated_ids),
        "validated_ids": validated_ids,
        "issues": issues_by_file,
    }
    if strict and not passed:
        summary = "; ".join(f"{k}: {', '.join(v)}" for k, v in sorted(issues_by_file.items()))
        raise WorkflowValidationError(f"Auditoria n8n reprovada: {summary}")
    return report
