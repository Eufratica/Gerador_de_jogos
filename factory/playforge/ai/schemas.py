"""Schemas, excecoes, catalogo de modelos e validadores estritos de saida para IA."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Sequence

from factory.playforge.models import FactoryError
from factory.playforge.security_utils import scan_prompt_injection, scrub_secrets

MODEL_TIER_SMALL = "S"
MODEL_TIER_MEDIUM = "M"
MODEL_TIER_LARGE = "L"
VALID_MODEL_TIERS: tuple[str, ...] = (MODEL_TIER_SMALL, MODEL_TIER_MEDIUM, MODEL_TIER_LARGE)

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
TELEMETRY_SCHEMA_VERSION = 1

_CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


class AIError(FactoryError):
    """Erro base da camada de IA e orquestracao da PlayForge Factory."""


class ProviderUnavailableError(AIError):
    """Provedor local (Ollama) indisponivel — falha fechada sem fallback pago (SEC-02)."""


class PolicyViolationError(AIError):
    """Violacao de politica de seguranca, custo zero, endpoint, hardware ou privilegio."""


class UntrustedOutputError(AIError):
    """Saida de LLM rejeitada por sintaxe invalida, schema divergente ou padrao inseguro."""


class LoopLimitExceededError(AIError):
    """Execucao interrompida por limite anti-loop (iteracoes, retries ou timeout)."""


class AgentContractError(AIError):
    """Contrato de agente incompleto ou invalido."""


@dataclass(frozen=True)
class ModelSpec:
    """Definicao de modelo local permitido pelo Model Router."""

    model_id: str
    tier: str
    provider: str
    quantization: str
    min_ram_gb: float
    requires_dedicated_gpu: bool
    max_context_tokens: int
    version: str = "latest"
    supports_json_mode: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "tier": self.tier,
            "provider": self.provider,
            "quantization": self.quantization,
            "min_ram_gb": self.min_ram_gb,
            "requires_dedicated_gpu": self.requires_dedicated_gpu,
            "max_context_tokens": self.max_context_tokens,
            "version": self.version,
            "supports_json_mode": self.supports_json_mode,
        }


DEFAULT_MODEL_CATALOG: tuple[ModelSpec, ...] = (
    ModelSpec(
        model_id="qwen2.5:3b",
        tier=MODEL_TIER_SMALL,
        provider="ollama",
        quantization="Q4_K_M",
        min_ram_gb=4.0,
        requires_dedicated_gpu=False,
        max_context_tokens=8192,
    ),
    ModelSpec(
        model_id="qwen2.5-coder:3b",
        tier=MODEL_TIER_SMALL,
        provider="ollama",
        quantization="Q4_K_M",
        min_ram_gb=4.0,
        requires_dedicated_gpu=False,
        max_context_tokens=8192,
    ),
    ModelSpec(
        model_id="llama3.2:3b",
        tier=MODEL_TIER_SMALL,
        provider="ollama",
        quantization="Q4_K_M",
        min_ram_gb=4.0,
        requires_dedicated_gpu=False,
        max_context_tokens=8192,
    ),
    ModelSpec(
        model_id="qwen2.5-coder:7b",
        tier=MODEL_TIER_MEDIUM,
        provider="ollama",
        quantization="Q4_K_M",
        min_ram_gb=8.0,
        requires_dedicated_gpu=False,
        max_context_tokens=8192,
    ),
    ModelSpec(
        model_id="qwen2.5-coder:32b",
        tier=MODEL_TIER_LARGE,
        provider="ollama",
        quantization="Q4_K_M",
        min_ram_gb=24.0,
        requires_dedicated_gpu=True,
        max_context_tokens=16384,
    ),
)


def _scan_nested_strings(payload: Any) -> list[str]:
    findings: list[str] = []
    if isinstance(payload, str):
        findings.extend(scan_prompt_injection(payload))
    elif isinstance(payload, dict):
        for val in payload.values():
            findings.extend(_scan_nested_strings(val))
    elif isinstance(payload, list):
        for item in payload:
            findings.extend(_scan_nested_strings(item))
    return findings


def extract_and_validate_json_output(
    raw_text: str,
    *,
    expected_type: type[Any] = dict,
    required_keys: Sequence[str] | None = None,
    allowed_keys: Sequence[str] | None = None,
) -> Any:
    """Extrai JSON estrito de saida de modelo nao confiavel com validacao fail-closed."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise UntrustedOutputError("Resposta vazia ou nao-textual do modelo local.")

    top_findings = scan_prompt_injection(raw_text)
    if top_findings:
        raise UntrustedOutputError(
            f"Marcadores suspeitos detectados na resposta do modelo: {', '.join(sorted(set(top_findings)))}."
        )

    candidate = raw_text.strip()
    fence_match = _CODE_FENCE_RE.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise UntrustedOutputError(f"Saida do modelo nao e JSON valido: {exc}") from exc

    if not isinstance(parsed, expected_type):
        raise UntrustedOutputError(
            f"Tipo JSON invalido: esperado {expected_type.__name__}, recebido {type(parsed).__name__}."
        )

    nested_findings = _scan_nested_strings(parsed)
    if nested_findings:
        raise UntrustedOutputError(
            f"Conteudo suspeito detectado em campos JSON: {', '.join(sorted(set(nested_findings)))}."
        )

    if isinstance(parsed, dict):
        if required_keys:
            missing = [k for k in required_keys if k not in parsed]
            if missing:
                raise UntrustedOutputError(
                    f"Campos obrigatorios ausentes na saida JSON: {', '.join(missing)}."
                )
        if allowed_keys is not None:
            allowed_set = set(allowed_keys)
            unexpected = sorted(k for k in parsed.keys() if k not in allowed_set)
            if unexpected:
                raise UntrustedOutputError(
                    f"Campos nao permitidos na saida JSON: {', '.join(unexpected)}."
                )

    return parsed


def build_ai_telemetry_record(
    *,
    request_id: str,
    timestamp: str,
    project_id: str,
    agent_id: str,
    model_id: str,
    model_version: str,
    prompt_version: str,
    tools_used: Sequence[str],
    latency_ms: float,
    result: str,
    tier: str,
    endpoint_host: str,
    error: str | None = None,
) -> dict[str, Any]:
    """Constroi registro de telemetria conforme docs/MODEL_ROUTER.md sem segredos."""
    payload: dict[str, Any] = {
        "telemetry_schema_version": TELEMETRY_SCHEMA_VERSION,
        "timestamp": timestamp,
        "request_id": request_id,
        "project_id": project_id,
        "agent_id": agent_id,
        "model_id": model_id,
        "model_version": model_version,
        "prompt_version": prompt_version,
        "tools_used": list(tools_used),
        "latency_ms": round(float(latency_ms), 2),
        "result": result,
        "tier": tier,
        "endpoint_host": endpoint_host,
    }
    if error:
        payload["error"] = error
    return scrub_secrets(payload)
