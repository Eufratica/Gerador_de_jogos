"""Utilitarios compartilhados de seguranca, sanitizacao e auditoria da PlayForge Factory."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SENSITIVE_KEY_TOKENS = (
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "authorization",
)

_SECRET_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}\b"), "***REDACTED_SK***"),
    (re.compile(r"\bghp_[A-Za-z0-9]{10,}\b"), "***REDACTED_GHP***"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{10,}\b"), "***REDACTED_AIZA***"),
    (
        re.compile(
            r"((?:api_key|secret|password|passwd|access_token|auth_token)\s*[:=]\s*['\"]?)([^\s'\",}]+)",
            re.IGNORECASE,
        ),
        r"\1***REDACTED***",
    ),
)

_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("null_byte", re.compile(r"\x00")),
    ("chat_template_marker", re.compile(r"<\|(?:im_start|im_end|system|assistant)\|>", re.IGNORECASE)),
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|prompts?)\b",
            re.IGNORECASE,
        ),
    ),
    ("script_tag", re.compile(r"<\s*script\b", re.IGNORECASE)),
)

_FORBIDDEN_EXACT_NAMES = frozenset({
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
})
_FORBIDDEN_SUFFIXES = (".keystore", ".jks", ".p12", ".pfx", ".pem", ".key")
_ALLOWED_ENV_TEMPLATES = frozenset({".env.example", ".env.template"})


def _is_sensitive_key(key: str) -> bool:
    norm = key.strip().lower()
    if any(tok in norm for tok in _SENSITIVE_KEY_TOKENS):
        return True
    return norm == "token" or norm.endswith("_token")


def scrub_secrets_in_text(text: str) -> str:
    """Mascara tokens e credenciais comuns em strings de log."""
    masked = text
    for pattern, repl in _SECRET_TEXT_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked


def scrub_secrets(data: Any) -> Any:
    """Remove ou mascara recursivamente campos e padroes sensiveis antes de persistir logs."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            key_str = str(k)
            if _is_sensitive_key(key_str) and not isinstance(v, (int, float, bool)):
                sanitized[key_str] = "***REDACTED***"
            else:
                sanitized[key_str] = scrub_secrets(v)
        return sanitized
    if isinstance(data, list):
        return [scrub_secrets(item) for item in data]
    if isinstance(data, tuple):
        return [scrub_secrets(item) for item in data]
    if isinstance(data, str):
        return scrub_secrets_in_text(data)
    return data


def is_forbidden_secret_relpath(rel_path: str) -> bool:
    """Bloqueia caminhos de segredos, keystores e metadados internos do Git."""
    normalized = rel_path.replace("\\", "/").strip()
    parts = [p.lower() for p in Path(normalized).parts]
    if not parts:
        return True
    if ".git" in parts or ".." in parts:
        return True
    basename = parts[-1]
    if basename in _ALLOWED_ENV_TEMPLATES:
        return False
    if basename.startswith(".env.") or basename in _FORBIDDEN_EXACT_NAMES:
        return True
    return any(basename.endswith(suffix) for suffix in _FORBIDDEN_SUFFIXES)


def scan_prompt_injection(text: str) -> list[str]:
    """Identifica marcadores suspeitos de prompt injection ou payloads inseguros em texto."""
    findings: list[str] = []
    for label, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(label)
    return findings


def append_jsonl_record(path: Path, record: dict[str, Any]) -> None:
    """Adiciona registro JSONL sanitizado ao arquivo de auditoria especificado."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_record = scrub_secrets(record)
    line = json.dumps(clean_record, sort_keys=True, ensure_ascii=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
