"""Servidor base MCP (JSON-RPC 2.0 stdio + auditoria e autorizacao fail-closed)."""
from __future__ import annotations

import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO

from factory.playforge.ai.agents import AgentRegistry
from factory.playforge.ai.schemas import AgentContractError, PolicyViolationError
from factory.playforge.models import FactoryError, ProtectedProject, WorkspaceEscape
from factory.playforge.security_utils import append_jsonl_record, scrub_secrets

from .schemas import (
    JSONRPC_VERSION,
    MCPAccessDenied,
    MCPToolError,
    MCPToolNotFoundError,
    MCPToolValidationError,
    ToolSpec,
    validate_tool_arguments,
)

MCP_PROTOCOL_VERSION = "2024-11-05"


def _jsonrpc_ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": result}


def _jsonrpc_error(req_id: Any, code: int, message: str, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = scrub_secrets(data)
    return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "error": err}


class MCPServer:
    """Servidor MCP confinavel com JSON-RPC 2.0, minimo privilegio por agente e log sanitizado."""

    def __init__(
        self,
        server_name: str,
        *,
        version: str = "1.0.0",
        agent_registry: AgentRegistry | None = None,
        audit_log_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.server_name = server_name
        self.version = version
        self.agent_registry = agent_registry or AgentRegistry()
        self.audit_log_path = audit_log_path
        self._clock = clock
        self._tools: dict[str, ToolSpec] = {}

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def register_tool(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def list_tools(self) -> list[dict[str, Any]]:
        return [self._tools[name].to_descriptor() for name in sorted(self._tools)]

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Valida permissao, executa tool confinada e persiste auditoria sanitizada."""
        started = time.perf_counter()
        execution_id = uuid.uuid4().hex[:12]
        raw_args = arguments if arguments is not None else {}
        project_id_for_log = (
            str(raw_args.get("project_id"))
            if isinstance(raw_args, dict) and isinstance(raw_args.get("project_id"), str)
            else "factory-global"
        )
        status = "ERROR"
        files_touched: list[str] = []
        error_text: str | None = None

        try:
            spec = self._tools.get(tool_name)
            if spec is None:
                raise MCPToolNotFoundError(
                    f"Tool '{tool_name}' nao existe no servidor '{self.server_name}'."
                )

            if agent_id is not None:
                try:
                    self.agent_registry.authorize_tool(agent_id, tool_name)
                except (PolicyViolationError, AgentContractError) as exc:
                    raise MCPAccessDenied(str(exc)) from exc

            validated = validate_tool_arguments(spec, raw_args)
            if "project_id" in validated:
                project_id_for_log = validated["project_id"]

            try:
                output = spec.handler(validated)
            except (ProtectedProject, WorkspaceEscape, PolicyViolationError, MCPAccessDenied) as exc:
                raise MCPAccessDenied(f"{exc.__class__.__name__}: {exc}") from exc

            if not isinstance(output, dict):
                raise MCPToolError(f"Handler da tool '{tool_name}' deve retornar dict.")

            touched = output.get("files_touched", [])
            if isinstance(touched, list):
                files_touched = [str(item) for item in touched]
            status = "SUCCESS"
            return output
        except MCPAccessDenied as exc:
            status = "DENIED"
            error_text = str(exc)
            raise
        except Exception as exc:
            status = f"FAILED:{exc.__class__.__name__}"
            error_text = str(exc)
            raise
        finally:
            if self.audit_log_path is not None:
                duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
                audit_record: dict[str, Any] = {
                    "execution_id": execution_id,
                    "timestamp": self._now_timestamp(),
                    "server_name": self.server_name,
                    "agent_id": agent_id or "operator-cli",
                    "project_id": project_id_for_log,
                    "tool_name": tool_name,
                    "duration": duration_ms,
                    "status": status,
                    "files_touched": files_touched,
                }
                if error_text:
                    audit_record["error"] = error_text
                append_jsonl_record(self.audit_log_path, audit_record)

    def handle_jsonrpc(self, raw_message: str | dict[str, Any]) -> dict[str, Any] | None:
        """Processa uma mensagem JSON-RPC 2.0 (initialize, tools/list, tools/call)."""
        if isinstance(raw_message, str):
            try:
                msg = json.loads(raw_message)
            except json.JSONDecodeError as exc:
                return _jsonrpc_error(None, -32700, f"Parse error JSON-RPC: {exc}")
        elif isinstance(raw_message, dict):
            msg = raw_message
        else:
            return _jsonrpc_error(None, -32600, "Mensagem JSON-RPC invalida.")

        if not isinstance(msg, dict) or msg.get("jsonrpc") != JSONRPC_VERSION:
            return _jsonrpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Versao JSON-RPC invalida.")

        req_id = msg.get("id")
        method = msg.get("method")
        if not isinstance(method, str) or not method:
            return _jsonrpc_error(req_id, -32600, "Campo 'method' ausente ou invalido.")

        if req_id is None and method.startswith("notifications/"):
            return None

        params = msg.get("params") or {}
        if not isinstance(params, dict):
            return _jsonrpc_error(req_id, -32602, "Campo 'params' deve ser objeto JSON.")

        if method == "initialize":
            return _jsonrpc_ok(
                req_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.server_name, "version": self.version},
                },
            )

        if method == "tools/list":
            return _jsonrpc_ok(req_id, {"tools": self.list_tools()})

        if method == "tools/call":
            tool_name = params.get("name")
            if not isinstance(tool_name, str) or not tool_name:
                return _jsonrpc_error(req_id, -32602, "Campo 'params.name' obrigatorio.")
            arguments = params.get("arguments", {})
            meta = params.get("_meta")
            agent_id = meta.get("agent_id") if isinstance(meta, dict) else None
            if agent_id is not None and not isinstance(agent_id, str):
                return _jsonrpc_error(req_id, -32602, "Campo '_meta.agent_id' deve ser string.")

            try:
                payload = self.call_tool(tool_name, arguments, agent_id=agent_id)
            except MCPToolNotFoundError as exc:
                return _jsonrpc_error(req_id, -32601, str(exc))
            except MCPToolValidationError as exc:
                return _jsonrpc_error(req_id, -32602, str(exc))
            except MCPAccessDenied as exc:
                return _jsonrpc_error(req_id, -32003, str(exc))
            except FactoryError as exc:
                return _jsonrpc_error(req_id, -32000, str(exc))

            safe_payload = scrub_secrets(payload)
            return _jsonrpc_ok(
                req_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(safe_payload, indent=2, sort_keys=True, ensure_ascii=True),
                        }
                    ],
                    "structuredContent": safe_payload,
                    "isError": False,
                },
            )

        return _jsonrpc_error(req_id, -32601, f"Metodo JSON-RPC nao suportado: '{method}'.")

    def serve_stdio(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> int:
        """Loop sincrono JSON-RPC 2.0 via linhas em stdin/stdout ate EOF."""
        in_stream = stdin or sys.stdin
        out_stream = stdout or sys.stdout
        for raw_line in in_stream:
            line = raw_line.strip()
            if not line:
                continue
            response = self.handle_jsonrpc(line)
            if response is not None:
                out_stream.write(json.dumps(response, ensure_ascii=True) + "\n")
                out_stream.flush()
        return 0
