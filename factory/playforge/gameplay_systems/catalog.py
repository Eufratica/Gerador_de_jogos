"""Catalogo e injetor sob demanda de sistemas de gameplay puros para Godot, Unity e Unreal (P4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from factory.playforge.models import FactoryError
from factory.playforge.registry import ProjectManager, _atomic_write_json, _atomic_write_text


class GameplaySystemError(FactoryError):
    """Erro fail-closed ao validar ou injetar sistemas de gameplay modulares."""


@dataclass(frozen=True)
class GameplaySystemSpec:
    system_id: str
    title: str
    category: str
    description: str
    supported_engines: tuple[str, ...]
    core_responsibility: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "supported_engines": list(self.supported_engines),
            "core_responsibility": self.core_responsibility,
        }


GAMEPLAY_SYSTEMS_CATALOG: dict[str, GameplaySystemSpec] = {
    "locomotion": GameplaySystemSpec(
        system_id="locomotion",
        title="Movimentacao & Fisica de Locomocao",
        category="movement",
        description="Calculo puro de velocidade, aceleracao, pulo e dash sem acoplamento de cena.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="step_velocity(speed, accel, dt, dashed)",
    ),
    "combat_action": GameplaySystemSpec(
        system_id="combat_action",
        title="Combate de Acao, Combos & Cooldowns",
        category="combat",
        description="Janelas de combo, mitigacao de defesa e resolucao deterministica de dano.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="compute_hit_damage(attack, defense, combo_step)",
    ),
    "enemy_ai": GameplaySystemSpec(
        system_id="enemy_ai",
        title="IA de Inimigos (FSM Deterministica)",
        category="ai",
        description="Maquina de estados IDLE/PATROL/CHASE/ATTACK orientada por distancia e cooldown.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="next_state(distance, aggro_range, attack_range)",
    ),
    "progression_skills": GameplaySystemSpec(
        system_id="progression_skills",
        title="Progressao, XP & Arvore de Habilidades",
        category="progression",
        description="Curva de nivel deterministica com desbloqueio progressivo de pontos de habilidade.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="xp_for_next_level(level)",
    ),
    "inventory_crafting": GameplaySystemSpec(
        system_id="inventory_crafting",
        title="Inventario, Empilhamento & Crafting",
        category="economy",
        description="Capacidade de slots, validacao de quantidades e verificacao de receitas.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="can_craft(owned, recipe)",
    ),
    "quests_dialogue": GameplaySystemSpec(
        system_id="quests_dialogue",
        title="Missoes, Objetivos & Dialogos",
        category="narrative",
        description="Ciclo LOCKED->ACTIVE->COMPLETED->REWARDED e checagem de pre-requisitos.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="advance_quest(progress, target_count)",
    ),
    "world_environment_cycle": GameplaySystemSpec(
        system_id="world_environment_cycle",
        title="Ciclo de Mundo, Clima & Zonas",
        category="world",
        description="Progresso deterministico de ciclo dia/noite e modificadores de bioma.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="normalize_hour(hour_value)",
    ),
    "save_system_versioned": GameplaySystemSpec(
        system_id="save_system_versioned",
        title="Sistema de Salvamento Versionado",
        category="persistence",
        description="Cabecalho de save versionado com esquema e integridade antes de serializacao.",
        supported_engines=("godot", "unity", "unreal"),
        core_responsibility="validate_save_header(schema_ver, expected_ver)",
    ),
}

GAMEPLAY_SYSTEM_IDS: tuple[str, ...] = tuple(GAMEPLAY_SYSTEMS_CATALOG.keys())


def _pascal_case(system_id: str) -> str:
    return "".join(part.capitalize() for part in system_id.split("_"))


def _render_module_for_engine(spec: GameplaySystemSpec, engine: str) -> tuple[str, str]:
    cls_name = f"{_pascal_case(spec.system_id)}Core"
    if engine == "godot":
        rel = f"src/core/systems/{spec.system_id}.gd"
        code = (
            f"class_name {cls_name}\n"
            f"extends RefCounted\n"
            f"# PlayForge Modular System ({spec.system_id}) - logica 100% pura e offline\n\n"
            f"const SYSTEM_ID := \"{spec.system_id}\"\n"
            f"const CATEGORY := \"{spec.category}\"\n\n"
            f"static func describe() -> Dictionary:\n"
            f"\treturn {{\"system_id\": SYSTEM_ID, \"category\": CATEGORY, \"pure\": true}}\n"
        )
        return rel, code
    if engine == "unity":
        rel = f"Assets/Scripts/Core/Systems/{cls_name}.cs"
        code = (
            "// PlayForge Modular System - C# puro sem MonoBehaviour\n"
            "namespace PlayForge.Core.Systems\n{\n"
            f"    public static class {cls_name}\n    {{\n"
            f'        public const string SystemId = "{spec.system_id}";\n'
            f'        public const string Category = "{spec.category}";\n'
            "    }\n}\n"
        )
        return rel, code
    if engine == "unreal":
        rel = f"Source/Core/Systems/{cls_name}Types.h"
        guard = f"PLAYFORGE_{spec.system_id.upper()}_TYPES_H"
        code = (
            f"#ifndef {guard}\n#define {guard}\n"
            f"// PlayForge Modular System ({spec.system_id}) - contrato puro C++\n"
            f"struct F{_pascal_case(spec.system_id)}Descriptor\n{{\n"
            f'    const char* SystemId = "{spec.system_id}";\n'
            f'    const char* Category = "{spec.category}";\n'
            "};\n#endif\n"
        )
        return rel, code
    raise GameplaySystemError(f"Engine nao suportada para modulos de gameplay: '{engine}'.")


class GameplaySystemInjector:
    """Injeta sistemas modulares sob demanda respeitando isolamento de projeto e escopo minimo."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager

    def list_catalog(self) -> list[dict[str, Any]]:
        return [GAMEPLAY_SYSTEMS_CATALOG[k].to_dict() for k in GAMEPLAY_SYSTEM_IDS]

    def inject_systems(
        self,
        project_id: str,
        system_ids: Sequence[str],
        *,
        engine: str | None = None,
    ) -> dict[str, Any]:
        project = self.manager.require_mutable_project(project_id)
        if not system_ids:
            raise GameplaySystemError("Informe ao menos um 'system_id' para injecao sob demanda.")

        deduped: list[str] = []
        for sid in system_ids:
            if sid not in GAMEPLAY_SYSTEMS_CATALOG:
                raise GameplaySystemError(
                    f"Sistema de gameplay desconhecido: '{sid}'. Disponiveis: {GAMEPLAY_SYSTEM_IDS}."
                )
            if sid not in deduped:
                deduped.append(sid)

        target_engine = (engine or str(project.get("engine") or "godot")).strip().lower()
        written_files: list[str] = []
        injected_records: list[dict[str, Any]] = []
        for sid in deduped:
            spec = GAMEPLAY_SYSTEMS_CATALOG[sid]
            if target_engine not in spec.supported_engines:
                raise GameplaySystemError(f"Sistema '{sid}' nao suporta engine '{target_engine}'.")
            rel, content = _render_module_for_engine(spec, target_engine)
            _atomic_write_text(self.manager.resolve_game_path(project_id, rel), content)
            written_files.append(rel)
            injected_records.append({"system_id": sid, "engine": target_engine, "file_path": rel})

        manifest = {
            "gameplay_systems_schema_version": 1,
            "project_id": project_id,
            "engine": target_engine,
            "injected_at": self.manager.now_timestamp(),
            "enabled_systems": deduped,
            "modules": injected_records,
        }
        _atomic_write_json(self.manager.resolve_game_path(project_id, "config/gameplay_systems.json"), manifest)
        written_files.append("config/gameplay_systems.json")

        self.manager.log_event(
            "INFO",
            "GAMEPLAY_SYSTEMS_INJECTED",
            project_id=project_id,
            engine=target_engine,
            systems=deduped,
        )
        return {
            "status": "INJECTED",
            "project_id": project_id,
            "engine": target_engine,
            "enabled_systems": deduped,
            "files_written": written_files,
        }
