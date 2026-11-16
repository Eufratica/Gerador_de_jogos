"""Model Router local, auditoria de hardware e cliente Ollama fail-closed (Fase 6)."""
from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from factory.playforge.registry import validate_project_id
from factory.playforge.security_utils import append_jsonl_record

from .schemas import (
    DEFAULT_MODEL_CATALOG,
    DEFAULT_OLLAMA_BASE_URL,
    MODEL_TIER_LARGE,
    MODEL_TIER_MEDIUM,
    MODEL_TIER_SMALL,
    ModelSpec,
    PolicyViolationError,
    ProviderUnavailableError,
    UntrustedOutputError,
    VALID_MODEL_TIERS,
    build_ai_telemetry_record,
    extract_and_validate_json_output,
)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

OllamaTransport = Callable[[str, str, dict[str, Any] | None, float], dict[str, Any]]


def validate_local_endpoint(base_url: str) -> tuple[str, str]:
    """Garante que apenas endpoints locais (Ollama loopback) sejam aceitos (SEC-02)."""
    if not isinstance(base_url, str) or not base_url.strip():
        raise PolicyViolationError("Endpoint Ollama vazio ou invalido.")
    parsed = urllib.parse.urlparse(base_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise PolicyViolationError(f"Esquema de URL nao suportado para Ollama local: '{parsed.scheme}'.")
    host = (parsed.hostname or "").lower()
    if host not in _LOOPBACK_HOSTS:
        raise PolicyViolationError(
            f"Endpoint nao-local '{host or base_url}' bloqueado pela politica Zero Cost / Local-First (SEC-02)."
        )
    return base_url.strip().rstrip("/"), host


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _detect_total_ram_gb() -> float | None:
    """Inspeciona RAM fisica total do sistema operacional sem valores simulados."""
    if os.name == "nt":
        try:
            mem = _MemoryStatusEx()
            mem.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                return round(mem.ullTotalPhys / (1024 ** 3), 2)
        except Exception:
            return None
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        try:
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / (1024 ** 2), 2)
        except Exception:
            return None
    return None


def _detect_ollama_binary() -> tuple[bool, str | None]:
    resolved = shutil.which("ollama")
    if resolved:
        return True, resolved
    candidates: list[Path] = []
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        candidates.append(Path(local_app) / "Programs" / "Ollama" / "ollama.exe")
    candidates.append(Path("C:/Program Files/Ollama/ollama.exe"))
    candidates.append(Path("/usr/local/bin/ollama"))
    candidates.append(Path("/usr/bin/ollama"))
    for cand in candidates:
        if cand.is_file():
            return True, str(cand)
    return False, None


@dataclass(frozen=True)
class HardwareProfile:
    """Retrato auditado de hardware e disponibilidade real do Ollama."""

    os_name: str
    architecture: str
    cpu_threads: int
    total_ram_gb: float | None
    has_dedicated_gpu: bool
    gpu_note: str
    ollama_bin_found: bool
    ollama_bin_path: str | None
    ollama_daemon_reachable: bool
    installed_models: tuple[str, ...]
    supported_tiers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "os_name": self.os_name,
            "architecture": self.architecture,
            "cpu_threads": self.cpu_threads,
            "total_ram_gb": self.total_ram_gb,
            "has_dedicated_gpu": self.has_dedicated_gpu,
            "gpu_note": self.gpu_note,
            "ollama_bin_found": self.ollama_bin_found,
            "ollama_bin_path": self.ollama_bin_path,
            "ollama_daemon_reachable": self.ollama_daemon_reachable,
            "installed_models": list(self.installed_models),
            "supported_tiers": list(self.supported_tiers),
        }


def compute_supported_tiers(total_ram_gb: float | None, has_dedicated_gpu: bool) -> tuple[str, ...]:
    """Determina tiers locais suportados com base em RAM real e presenca de GPU dedicada."""
    tiers: list[str] = []
    if total_ram_gb is None or total_ram_gb >= 4.0:
        tiers.append(MODEL_TIER_SMALL)
    if total_ram_gb is not None and total_ram_gb >= 8.0:
        tiers.append(MODEL_TIER_MEDIUM)
    if has_dedicated_gpu and total_ram_gb is not None and total_ram_gb >= 24.0:
        tiers.append(MODEL_TIER_LARGE)
    return tuple(tiers)


class OllamaClient:
    """Cliente HTTP minimo (stdlib) para Ollama local com transporte injetavel para testes."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        *,
        timeout_seconds: float = 15.0,
        transport: OllamaTransport | None = None,
    ) -> None:
        self.base_url, self.host = validate_local_endpoint(base_url)
        self.timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        validate_local_endpoint(self.base_url)
        eff_timeout = float(timeout_seconds if timeout_seconds is not None else self.timeout_seconds)
        if self._transport is not None:
            try:
                raw = self._transport(method, path, payload, eff_timeout)
            except ProviderUnavailableError:
                raise
            except Exception as exc:
                raise ProviderUnavailableError(
                    f"Ollama local indisponivel ({self.base_url}{path}): {exc}"
                ) from exc
            if not isinstance(raw, dict):
                raise UntrustedOutputError("Resposta invalida do transporte Ollama (esperado objeto JSON).")
            return raw

        url = f"{self.base_url}{path}"
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=eff_timeout) as resp:
                raw_bytes = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError(
                f"Ollama daemon inacessivel em '{self.base_url}'; nenhum fallback pago sera usado (SEC-02): {exc}"
            ) from exc

        try:
            decoded = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UntrustedOutputError(f"Resposta HTTP nao-JSON do Ollama em '{path}': {exc}") from exc

        if not isinstance(decoded, dict):
            raise UntrustedOutputError(f"Payload inesperado do Ollama em '{path}'.")
        return decoded

    def list_models(self, *, timeout_seconds: float | None = None) -> list[str]:
        """Consulta /api/tags e retorna nomes dos modelos instalados localmente."""
        data = self._request_json("GET", "/api/tags", None, timeout_seconds=timeout_seconds)
        models = data.get("models", [])
        if not isinstance(models, list):
            raise UntrustedOutputError("Campo 'models' invalido em /api/tags.")
        names: list[str] = []
        for entry in models:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str) and entry["name"].strip():
                names.append(entry["name"].strip())
        return names

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None = None,
        format_json: bool = True,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executa POST /api/generate sincrono (stream=False) contra o Ollama local."""
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"
        if options:
            payload["options"] = options

        resp = self._request_json("POST", "/api/generate", payload)
        if not isinstance(resp.get("response"), str):
            raise UntrustedOutputError("Resposta de /api/generate sem campo textual 'response'.")
        return resp


def inspect_environment(
    *,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    client: OllamaClient | None = None,
    timeout_s: float = 0.75,
) -> HardwareProfile:
    """Inspeciona hardware local e estado real do Ollama sem mascarar indisponibilidade."""
    effective_client = client or OllamaClient(base_url=ollama_base_url, timeout_seconds=timeout_s)
    total_ram = _detect_total_ram_gb()
    has_nvidia = shutil.which("nvidia-smi") is not None
    gpu_note = "nvidia-smi detectado" if has_nvidia else "Sem GPU dedicada CUDA detectada (modo CPU/integrada)"
    bin_found, bin_path = _detect_ollama_binary()

    reachable = False
    installed: tuple[str, ...] = ()
    try:
        installed = tuple(effective_client.list_models(timeout_seconds=timeout_s))
        reachable = True
    except (ProviderUnavailableError, UntrustedOutputError):
        reachable = False
        installed = ()

    return HardwareProfile(
        os_name=f"{platform.system()} {platform.release()}".strip(),
        architecture=platform.machine() or "unknown",
        cpu_threads=os.cpu_count() or 1,
        total_ram_gb=total_ram,
        has_dedicated_gpu=has_nvidia,
        gpu_note=gpu_note,
        ollama_bin_found=bin_found,
        ollama_bin_path=bin_path,
        ollama_daemon_reachable=reachable,
        installed_models=installed,
        supported_tiers=compute_supported_tiers(total_ram, has_nvidia),
    )


class ModelRouter:
    """Roteador de modelos locais por tier (S/M/L) com falha fechada e telemetria auditavel."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        client: OllamaClient | None = None,
        catalog: Sequence[ModelSpec] = DEFAULT_MODEL_CATALOG,
        hardware_profile: HardwareProfile | None = None,
        telemetry_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[3]
        self.client = client or OllamaClient(base_url=DEFAULT_OLLAMA_BASE_URL)
        self.catalog = tuple(catalog)
        self._fixed_profile = hardware_profile
        self.telemetry_path = (
            Path(telemetry_path)
            if telemetry_path
            else (self.repo_root / "data" / "logs" / "ai_router.jsonl")
        )
        self._clock = clock

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_hardware_profile(self, *, probe_timeout_s: float = 0.75) -> HardwareProfile:
        if self._fixed_profile is not None:
            return self._fixed_profile
        return inspect_environment(client=self.client, timeout_s=probe_timeout_s)

    def health_report(self, *, probe_timeout_s: float = 0.75) -> dict[str, Any]:
        """Retorna diagnostico real de hardware, tiers e disponibilidade do Ollama."""
        profile = self.get_hardware_profile(probe_timeout_s=probe_timeout_s)
        if not profile.ollama_daemon_reachable:
            status = "DAEMON_UNAVAILABLE"
        elif not profile.installed_models:
            status = "NO_MODELS_INSTALLED"
        else:
            status = "READY"

        return {
            "status": status,
            "ollama_base_url": self.client.base_url,
            "zero_cost_policy": "ENFORCED_LOCAL_ONLY",
            "paid_fallback_enabled": False,
            "hardware": profile.to_dict(),
            "allowed_catalog": [m.to_dict() for m in self.catalog],
        }

    def select_model(
        self,
        tier: str,
        *,
        preferred_model: str | None = None,
        require_installed: bool = False,
        profile: HardwareProfile | None = None,
    ) -> ModelSpec:
        """Seleciona modelo compativel com tier e hardware (fail-closed)."""
        if tier not in VALID_MODEL_TIERS:
            raise PolicyViolationError(f"Tier invalido '{tier}'. Permitidos: {VALID_MODEL_TIERS}.")

        hw = profile or self.get_hardware_profile()
        if tier not in hw.supported_tiers:
            raise PolicyViolationError(
                f"Tier '{tier}' indisponivel no hardware atual "
                f"(RAM={hw.total_ram_gb} GB, GPU dedicada={hw.has_dedicated_gpu}, "
                f"tiers suportados={hw.supported_tiers})."
            )

        candidates = [m for m in self.catalog if m.tier == tier]
        if preferred_model:
            candidates = [m for m in candidates if m.model_id == preferred_model]
        if not candidates:
            raise PolicyViolationError(
                f"Nenhum modelo autorizado no catalogo para tier='{tier}', preferido='{preferred_model}'."
            )

        eligible: list[ModelSpec] = []
        for spec in candidates:
            if spec.requires_dedicated_gpu and not hw.has_dedicated_gpu:
                continue
            if hw.total_ram_gb is not None and hw.total_ram_gb < spec.min_ram_gb:
                continue
            eligible.append(spec)

        if not eligible:
            raise PolicyViolationError(
                f"Hardware insuficiente para os modelos de tier '{tier}'."
            )

        if require_installed:
            if not hw.ollama_daemon_reachable:
                raise ProviderUnavailableError(
                    f"Ollama local inacessivel em '{self.client.base_url}' (require_installed=True)."
                )
            for spec in eligible:
                if spec.model_id in hw.installed_models:
                    return spec
            raise ProviderUnavailableError(
                f"Nenhum modelo do tier '{tier}' esta instalado no Ollama local "
                f"(instalados={list(hw.installed_models)})."
            )

        for spec in eligible:
            if spec.model_id in hw.installed_models:
                return spec
        return eligible[0]

    def invoke_structured(
        self,
        *,
        project_id: str,
        agent_id: str,
        tier: str,
        prompt: str,
        prompt_version: str = "1.0",
        system: str | None = None,
        preferred_model: str | None = None,
        required_keys: Sequence[str] | None = None,
        allowed_keys: Sequence[str] | None = None,
        tools_used: Sequence[str] = (),
        require_installed: bool = False,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoca Ollama local com resposta JSON obrigatoria, validacao estrita e telemetria."""
        validate_project_id(project_id)
        started = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        selected_model_id = preferred_model or f"tier-{tier}"
        selected_version = "unknown"
        result_status = "ERROR"
        error_text: str | None = None

        try:
            hw = self.get_hardware_profile()
            spec = self.select_model(
                tier,
                preferred_model=preferred_model,
                require_installed=require_installed,
                profile=hw,
            )
            selected_model_id = spec.model_id
            selected_version = spec.version

            raw_resp = self.client.generate(
                model=spec.model_id,
                prompt=prompt,
                system=system,
                format_json=True,
                options=options,
            )
            parsed = extract_and_validate_json_output(
                raw_resp["response"],
                expected_type=dict,
                required_keys=required_keys,
                allowed_keys=allowed_keys,
            )
            result_status = "SUCCESS"
            return {
                "request_id": request_id,
                "model_id": spec.model_id,
                "tier": spec.tier,
                "output": parsed,
            }
        except Exception as exc:
            result_status = f"FAILED:{exc.__class__.__name__}"
            error_text = str(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            record = build_ai_telemetry_record(
                request_id=request_id,
                timestamp=self._now_timestamp(),
                project_id=project_id,
                agent_id=agent_id,
                model_id=selected_model_id,
                model_version=selected_version,
                prompt_version=prompt_version,
                tools_used=tools_used,
                latency_ms=elapsed_ms,
                result=result_status,
                tier=tier,
                endpoint_host=self.client.host,
                error=error_text,
            )
            append_jsonl_record(self.telemetry_path, record)
