"""Schemas, excecoes e validacao de parametros para ferramentas MCP da PlayForge Factory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from factory.playforge.models import FactoryError
from factory.playforge.registry import validate_project_id

JSONRPC_VERSION = "2.0"


class MCPToolError(FactoryError):
    """Erro base de execucao ou protocolo em servidor MCP."""


class MCPAccessDenied(MCPToolError):
    """Acesso bloqueado por politica de seguranca, projeto protegido ou isolamento (SEC-01)."""


class MCPToolValidationError(MCPToolError):
    """Parametros de entrada fora do schema declarado pela ferramenta MCP."""


class MCPToolNotFoundError(MCPToolError):
    """Ferramenta MCP nao registrada neste servidor."""


@dataclass(frozen=True)
class ToolSpec:
    """Especificacao formal de uma ferramenta MCP exposta via JSON-RPC 2.0."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    requires_project_id: bool = True

    def to_descriptor(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def _check_json_type(field: str, value: Any, expected: str) -> None:
    if expected == "string":
        if not isinstance(value, str):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser string.")
    elif expected == "boolean":
        if not isinstance(value, bool):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser boolean.")
    elif expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser integer.")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser number.")
    elif expected == "object":
        if not isinstance(value, dict):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser object.")
    elif expected == "array":
        if not isinstance(value, list):
            raise MCPToolValidationError(f"Parametro '{field}' deve ser array.")


def validate_tool_arguments(spec: ToolSpec, arguments: Any) -> dict[str, Any]:
    """Valida fail-closed os argumentos de uma tool MCP contra seu input_schema."""
    if not isinstance(arguments, dict):
        raise MCPToolValidationError("Campo 'arguments' deve ser objeto JSON.")

    schema = spec.input_schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional_allowed = schema.get("additionalProperties", False)

    for key in required:
        if key not in arguments:
            raise MCPToolValidationError(
                f"Parametro obrigatorio '{key}' ausente para tool '{spec.name}'."
            )

    if not additional_allowed:
        unexpected = sorted(k for k in arguments if k not in properties)
        if unexpected:
            raise MCPToolValidationError(
                f"Parametro(s) nao permitido(s) para tool '{spec.name}': {', '.join(unexpected)}."
            )

    for key, val in arguments.items():
        prop = properties.get(key)
        if isinstance(prop, dict):
            expected_type = prop.get("type")
            if isinstance(expected_type, str):
                _check_json_type(key, val, expected_type)

    if spec.requires_project_id:
        if "project_id" not in arguments:
            raise MCPToolValidationError(f"Tool '{spec.name}' exige 'project_id' explicito.")
        validate_project_id(arguments["project_id"])

    return dict(arguments)
