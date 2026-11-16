"""Gerador deterministico de exports JSON n8n Community livres de credenciais (Fase 9)."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from factory.playforge.registry import _atomic_write_json

from .schemas import AUTOMATION_SCHEMA_VERSION, OFFICIAL_WORKFLOW_CATALOG, WorkflowDefinition

_NAMESPACE_PLAYFORGE_N8N = uuid.UUID("a4f38d4c-3f1d-4d8a-9f5c-70a9e0f20260")


def _det_uuid(seed_key: str) -> str:
    return str(uuid.uuid5(_NAMESPACE_PLAYFORGE_N8N, seed_key))


def build_workflow_export(
    defn: WorkflowDefinition,
    *,
    bridge_base_url: str = "http://127.0.0.1:8787",
) -> dict[str, Any]:
    """Constroi definicao JSON importavel pelo n8n Community sem credenciais."""
    wf_id = defn.workflow_id
    trigger_node_name = "Schedule Trigger" if defn.trigger_type == "schedule" else "Webhook Trigger"
    if defn.trigger_type == "schedule":
        trigger_node: dict[str, Any] = {
            "id": _det_uuid(f"{wf_id}:trigger"),
            "name": trigger_node_name,
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [240, 300],
            "parameters": {
                "rule": {
                    "interval": [{"field": "minutes", "minutesInterval": 15}],
                }
            },
        }
    else:
        trigger_node = {
            "id": _det_uuid(f"{wf_id}:trigger"),
            "name": trigger_node_name,
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2.0,
            "position": [240, 300],
            "webhookId": _det_uuid(f"{wf_id}:webhook"),
            "parameters": {
                "httpMethod": "POST",
                "path": f"playforge/{wf_id}",
                "responseMode": "responseNode",
                "options": {},
            },
        }

    bridge_node: dict[str, Any] = {
        "id": _det_uuid(f"{wf_id}:bridge"),
        "name": "Call PlayForge Bridge",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [520, 300],
        "parameters": {
            "method": "POST",
            "url": f"{bridge_base_url.rstrip('/')}/webhook/{wf_id}",
            "authentication": "none",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ $json.body ?? $json }}",
            "options": {"timeout": 30000},
        },
    }

    gate_condition_field = "={{ $json.gate_cleared ?? $json.passed ?? false }}"
    gate_node: dict[str, Any] = {
        "id": _det_uuid(f"{wf_id}:gate"),
        "name": "Gate Check",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [800, 300],
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [
                    {
                        "id": _det_uuid(f"{wf_id}:cond"),
                        "leftValue": gate_condition_field,
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }
                ],
                "combinator": "and",
            },
            "options": {},
        },
    }

    if defn.trigger_type == "schedule":
        approved_node: dict[str, Any] = {
            "id": _det_uuid(f"{wf_id}:ok"),
            "name": "Audit Passed",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [1080, 220],
            "parameters": {},
        }
        blocked_node: dict[str, Any] = {
            "id": _det_uuid(f"{wf_id}:blocked"),
            "name": "Escalate Alert",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [1080, 420],
            "parameters": {},
        }
    else:
        approved_node = {
            "id": _det_uuid(f"{wf_id}:ok"),
            "name": "Respond Approved",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1080, 220],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {"responseCode": 200},
            },
        }
        blocked_node = {
            "id": _det_uuid(f"{wf_id}:blocked"),
            "name": "Respond Blocked",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1.1,
            "position": [1080, 420],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {"responseCode": 202 if defn.requires_human_gate else 422},
            },
        }

    ok_name = str(approved_node["name"])
    blocked_name = str(blocked_node["name"])

    connections = {
        trigger_node_name: {
            "main": [[{"node": "Call PlayForge Bridge", "type": "main", "index": 0}]],
        },
        "Call PlayForge Bridge": {
            "main": [[{"node": "Gate Check", "type": "main", "index": 0}]],
        },
        "Gate Check": {
            "main": [
                [{"node": ok_name, "type": "main", "index": 0}],
                [{"node": blocked_name, "type": "main", "index": 0}],
            ],
        },
    }

    return {
        "id": _det_uuid(wf_id),
        "name": f"{wf_id}: {defn.name}",
        "active": False,
        "nodes": [trigger_node, bridge_node, gate_node, approved_node, blocked_node],
        "connections": connections,
        "pinData": {},
        "settings": {
            "executionOrder": "v1",
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner",
        },
        "versionId": _det_uuid(f"{wf_id}:v{AUTOMATION_SCHEMA_VERSION}"),
        "meta": {
            "schemaVersion": AUTOMATION_SCHEMA_VERSION,
            "instanceId": "playforge-factory-local",
            "workflowId": wf_id,
            "cliCommand": defn.cli_command,
            "requiresHumanGate": defn.requires_human_gate,
            "approvalStage": defn.approval_stage,
            "zeroCostPolicy": "ENFORCED_LOCAL_ONLY",
            "description": defn.description,
        },
        "tags": [{"name": "playforge"}] + [{"name": tag} for tag in defn.tags],
    }


def generate_official_exports(
    exports_dir: Path,
    *,
    bridge_base_url: str = "http://127.0.0.1:8787",
    overwrite: bool = True,
) -> list[Path]:
    """Gera e grava todos os 20 arquivos WF-001..WF-020 em exports_dir."""
    exports_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for defn in OFFICIAL_WORKFLOW_CATALOG:
        target = exports_dir / defn.filename
        if target.exists() and not overwrite:
            written.append(target)
            continue
        payload = build_workflow_export(defn, bridge_base_url=bridge_base_url)
        _atomic_write_json(target, payload)
        written.append(target)
    return written
