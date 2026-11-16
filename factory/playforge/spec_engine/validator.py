"""Validador fail-closed para GameSpecification e GameDesignDocument."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Optional

from ..models import FactoryError, PROJECT_ID_RE
from .schemas import (
    GDD_ALLOWED_FIELDS,
    GDD_REQUIRED_FIELDS,
    GDD_SCHEMA_VERSION,
    GDD_SECTIONS,
    SEMVER_RE,
    SPEC_REQUIRED_FIELDS,
    SPEC_SCHEMA_VERSION,
    SPEC_SCHEMA_VERSION_MULTIENGINE,
    SPEC_V2_OPTIONAL_FIELDS,
    SUPPORTED_ENGINES,
    SUPPORTED_GENRES,
    SUPPORTED_MULTIENGINE_ENGINES,
    SUPPORTED_ORIENTATIONS,
    SUPPORTED_PLATFORMS,
)


class ValidationError(FactoryError):
    """Erro de validação de schema ou consistência semântica."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"Erro no campo '{field}': {message}")


class SchemaCompatibilityError(FactoryError):
    """Erro de compatibilidade de versão entre Spec, Schema ou Engine."""


def compute_spec_digest(spec: dict[str, Any]) -> str:
    """Calcula SHA-256 canônico da GameSpecification para auditoria e aprovação."""
    canonical = json.dumps(spec, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_semver(version: str) -> tuple[int, int, int]:
    """Converte string MAJOR.MINOR.PATCH validada em tupla inteira."""
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        raise ValidationError("version", f"SemVer inválida: '{version}'. Use MAJOR.MINOR.PATCH (ex: 0.1.0).")
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


class SpecificationValidator:
    """Valida especificações técnicas e GDDs com política fail-closed e relatórios detalhados."""

    @staticmethod
    def _assert_type(field: str, value: Any, expected_type: type | tuple[type, ...]) -> None:
        # Em Python, bool é subclasse de int; impedir coerção silenciosa de True/False para int/float.
        if isinstance(value, bool) and expected_type is not bool:
            raise ValidationError(field, "Tipo inválido: esperado número/objeto, encontrado bool.")
        if not isinstance(value, expected_type):
            type_names = (
                ", ".join(t.__name__ for t in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            raise ValidationError(
                field,
                f"Tipo inválido: esperado {type_names}, encontrado {type(value).__name__}.",
            )

    @staticmethod
    def _assert_bool(field: str, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValidationError(field, f"Tipo inválido: esperado bool, encontrado {type(value).__name__}.")
        return value

    @staticmethod
    def _assert_number(field: str, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(field, f"Tipo inválido: esperado numérico, encontrado {type(value).__name__}.")
        if math.isnan(float(value)) or math.isinf(float(value)):
            raise ValidationError(field, "Valor numérico inválido (NaN ou infinito).")
        return float(value)

    @staticmethod
    def _assert_int(field: str, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(field, f"Tipo inválido: esperado int, encontrado {type(value).__name__}.")
        return value

    @staticmethod
    def _assert_non_empty_str(field: str, value: Any) -> str:
        SpecificationValidator._assert_type(field, value, str)
        val = value.strip()
        if not val:
            raise ValidationError(field, "Não pode ser string vazia.")
        return val

    @staticmethod
    def _reject_unknown_keys(context: str, data: dict[str, Any], allowed: tuple[str, ...]) -> None:
        extras = sorted(set(data.keys()) - set(allowed))
        if extras:
            raise ValidationError(
                f"{context}.{extras[0]}" if context != "root" else extras[0],
                f"Campo desconhecido não permitido pelo contrato estrito: {extras}.",
            )

    def _validate_worlds(self, worlds_spec: Any) -> None:
        self._assert_type("worlds_and_levels", worlds_spec, dict)
        worlds = worlds_spec.get("worlds")
        self._assert_type("worlds_and_levels.worlds", worlds, list)
        if not worlds:
            raise ValidationError("worlds_and_levels.worlds", "Deve conter pelo menos um mundo.")

        counted_rooms = 0
        for w_idx, world in enumerate(worlds):
            self._assert_type(f"worlds_and_levels.worlds[{w_idx}]", world, dict)
            world_id = self._assert_non_empty_str(
                f"worlds_and_levels.worlds[{w_idx}].world_id", world.get("world_id")
            )
            rooms = world.get("rooms")
            self._assert_type(f"worlds_and_levels.worlds[{w_idx}].rooms", rooms, list)
            if not rooms:
                raise ValidationError(f"worlds_and_levels.worlds[{w_idx}].rooms", "Mundo deve conter salas.")

            room_ids: set[str] = set()
            for r_idx, room in enumerate(rooms):
                self._assert_type(f"world[{world_id}].rooms[{r_idx}]", room, dict)
                r_id = self._assert_non_empty_str(f"world[{world_id}].rooms[{r_idx}].room_id", room.get("room_id"))
                if r_id in room_ids:
                    raise ValidationError(
                        f"world[{world_id}].rooms[{r_idx}].room_id",
                        f"ID de sala duplicado: '{r_id}'.",
                    )
                room_ids.add(r_id)
                counted_rooms += 1

            for r_idx, room in enumerate(rooms):
                connections = room.get("connections", [])
                self._assert_type(f"world[{world_id}].rooms[{r_idx}].connections", connections, list)
                for conn in connections:
                    self._assert_type(f"world[{world_id}].rooms[{r_idx}].connections[]", conn, dict)
                    target_room = conn.get("target_room_id")
                    if target_room and target_room not in room_ids:
                        raise ValidationError(
                            f"world[{world_id}].rooms[{r_idx}].connections",
                            f"Conexão aponta para sala inexistente '{target_room}' no mundo '{world_id}'.",
                        )

        if "total_rooms" in worlds_spec:
            declared_total = self._assert_int("worlds_and_levels.total_rooms", worlds_spec["total_rooms"])
            if declared_total != counted_rooms:
                raise ValidationError(
                    "worlds_and_levels.total_rooms",
                    f"Inconsistência semântica: total_rooms={declared_total}, mas há {counted_rooms} salas declaradas.",
                )

    def _validate_economy(self, economy: Any) -> None:
        self._assert_type("economy", economy, dict)
        currencies = economy.get("currencies")
        self._assert_type("economy.currencies", currencies, list)
        if not currencies:
            raise ValidationError("economy.currencies", "Deve conter pelo menos uma moeda.")
        for idx, curr in enumerate(currencies):
            self._assert_non_empty_str(f"economy.currencies[{idx}]", curr)

        gacha_rates = economy.get("gacha_rates")
        if gacha_rates is not None:
            self._assert_type("economy.gacha_rates", gacha_rates, dict)
            total_rate = 0.0
            for tier, rate in gacha_rates.items():
                val = self._assert_number(f"economy.gacha_rates.{tier}", rate)
                if val < 0.0 or val > 1.0:
                    raise ValidationError(
                        f"economy.gacha_rates.{tier}",
                        f"Probabilidade inválida: {val}. Deve estar entre 0.0 e 1.0.",
                    )
                total_rate += val
            if not math.isclose(total_rate, 1.0, rel_tol=1e-5, abs_tol=1e-5):
                raise ValidationError(
                    "economy.gacha_rates",
                    f"A soma das taxas de gacha deve ser exatamente 1.0 (soma calculada: {total_rate:.4f}).",
                )

    def _validate_engineering_sections(self, data: dict[str, Any]) -> None:
        prog = data["progression"]
        self._assert_type("progression", prog, dict)
        self._assert_non_empty_str("progression.curve_type", prog.get("curve_type"))
        max_lv = self._assert_int("progression.max_level", prog.get("max_level"))
        if max_lv < 1:
            raise ValidationError("progression.max_level", "Deve ser >= 1.")

        diff = data["difficulty"]
        self._assert_type("difficulty", diff, dict)
        if self._assert_number("difficulty.base_scaling", diff.get("base_scaling")) <= 0.0:
            raise ValidationError("difficulty.base_scaling", "Deve ser > 0.")
        if self._assert_number("difficulty.boss_multiplier", diff.get("boss_multiplier")) < 1.0:
            raise ValidationError("difficulty.boss_multiplier", "Deve ser >= 1.0.")

        acc = data["accessibility"]
        self._assert_type("accessibility", acc, dict)
        for key in ("colorblind_mode", "subtitles", "configurable_controls"):
            if key in acc:
                self._assert_bool(f"accessibility.{key}", acc[key])

        narrative = data["narrative"]
        self._assert_type("narrative", narrative, dict)
        self._assert_non_empty_str("narrative.lore_summary", narrative.get("lore_summary"))

        audio = data["audio"]
        self._assert_type("audio", audio, dict)
        self._assert_non_empty_str("audio.music_style", audio.get("music_style"))
        if "procedural_sfx" in audio:
            self._assert_bool("audio.procedural_sfx", audio["procedural_sfx"])

        art = data["art_and_assets"]
        self._assert_type("art_and_assets", art, dict)
        self._assert_non_empty_str("art_and_assets.style", art.get("style"))
        palette = art.get("palette")
        self._assert_type("art_and_assets.palette", palette, list)
        if not palette:
            raise ValidationError("art_and_assets.palette", "Deve conter ao menos uma cor na paleta.")

        persistence = data["persistence"]
        self._assert_type("persistence", persistence, dict)
        self._assert_non_empty_str("persistence.save_format", persistence.get("save_format"))
        slots = self._assert_int("persistence.slots", persistence.get("slots"))
        if slots < 1:
            raise ValidationError("persistence.slots", "Deve ter pelo menos 1 slot de save.")

        tech = data["technical_requirements"]
        self._assert_type("technical_requirements", tech, dict)
        if self._assert_int("technical_requirements.target_fps", tech.get("target_fps")) <= 0:
            raise ValidationError("technical_requirements.target_fps", "Deve ser > 0.")
        if self._assert_int("technical_requirements.max_ram_mb", tech.get("max_ram_mb")) <= 0:
            raise ValidationError("technical_requirements.max_ram_mb", "Deve ser > 0.")

        sec = data["security"]
        self._assert_type("security", sec, dict)
        self._assert_bool("security.anti_tamper", sec.get("anti_tamper"))
        self._assert_bool("security.offline_only", sec.get("offline_only"))

        mon = data["monetization"]
        self._assert_type("monetization", mon, dict)
        self._assert_bool("monetization.enabled", mon.get("enabled"))
        self._assert_non_empty_str("monetization.model", mon.get("model"))

    def validate_spec(self, data: Any) -> dict[str, Any]:
        """Valida integralmente uma GameSpecification (contrato estrito v1 + multi-engine v2)."""
        self._assert_type("root", data, dict)

        if "spec_schema_version" not in data:
            raise ValidationError("spec_schema_version", "Campo obrigatório ausente.")

        schema_ver = self._assert_int("spec_schema_version", data["spec_schema_version"])
        if schema_ver == SPEC_SCHEMA_VERSION:
            allowed_root = SPEC_REQUIRED_FIELDS
            supported_engines = SUPPORTED_ENGINES
        elif schema_ver == SPEC_SCHEMA_VERSION_MULTIENGINE:
            allowed_root = SPEC_REQUIRED_FIELDS + SPEC_V2_OPTIONAL_FIELDS
            supported_engines = SUPPORTED_MULTIENGINE_ENGINES
        else:
            raise ValidationError(
                "spec_schema_version",
                f"Versão incompatível: esperada {SPEC_SCHEMA_VERSION} ou {SPEC_SCHEMA_VERSION_MULTIENGINE}, encontrada {schema_ver}.",
            )

        self._reject_unknown_keys("root", data, allowed_root)

        for req in SPEC_REQUIRED_FIELDS:
            if req not in data:
                raise ValidationError(req, "Campo obrigatório ausente.")

        self._assert_non_empty_str("spec_id", data["spec_id"])
        game_id = self._assert_non_empty_str("game_id", data["game_id"])
        if not PROJECT_ID_RE.match(game_id):
            raise ValidationError("game_id", f"Slug inválido '{game_id}'. Use ^[a-z][a-z0-9-]{{2,39}}$.")
        self._assert_non_empty_str("name", data["name"])
        parse_semver(data["version"])

        genre = self._assert_non_empty_str("genre", data["genre"])
        if genre not in SUPPORTED_GENRES:
            raise ValidationError(
                "genre",
                f"Gênero não suportado: '{genre}'. Suportados: {SUPPORTED_GENRES}.",
            )
        self._assert_non_empty_str("subgenre", data["subgenre"])

        engine = self._assert_non_empty_str("engine", data["engine"])
        if engine not in supported_engines:
            raise ValidationError(
                "engine",
                f"Engine não suportada: '{engine}'. Suportadas: {supported_engines}.",
            )
        self._assert_non_empty_str("engine_version", data["engine_version"])

        platforms = data["target_platforms"]
        self._assert_type("target_platforms", platforms, list)
        if not platforms:
            raise ValidationError("target_platforms", "Deve conter pelo menos uma plataforma alvo.")
        for i, plat in enumerate(platforms):
            if plat not in SUPPORTED_PLATFORMS:
                raise ValidationError(
                    f"target_platforms[{i}]",
                    f"Plataforma '{plat}' inválida. Suportadas: {SUPPORTED_PLATFORMS}.",
                )

        self._assert_type("target_audience", data["target_audience"], dict)
        self._assert_type("product_goals", data["product_goals"], list)
        if not data["product_goals"]:
            raise ValidationError("product_goals", "Deve conter pelo menos um objetivo de produto.")
        self._assert_non_empty_str("value_proposition", data["value_proposition"])
        self._assert_type("references", data["references"], list)

        self._assert_type("core_gameplay", data["core_gameplay"], dict)
        self._assert_non_empty_str("core_loop", data["core_loop"])
        self._assert_type("controls", data["controls"], dict)

        mechanics = data["mechanics"]
        self._assert_type("mechanics", mechanics, list)
        if not mechanics:
            raise ValidationError("mechanics", "Deve definir pelo menos uma mecânica de jogo.")
        for i, mech in enumerate(mechanics):
            self._assert_type(f"mechanics[{i}]", mech, dict)
            for req_key in ("id", "name", "description"):
                self._assert_non_empty_str(f"mechanics[{i}].{req_key}", mech.get(req_key))

        characters = data["characters"]
        self._assert_type("characters", characters, list)
        if not characters:
            raise ValidationError("characters", "Deve conter pelo menos um personagem.")
        for i, char in enumerate(characters):
            self._assert_type(f"characters[{i}]", char, dict)
            for req_key in ("id", "name", "role"):
                self._assert_non_empty_str(f"characters[{i}].{req_key}", char.get(req_key))

        enemies = data["enemies"]
        self._assert_type("enemies", enemies, list)
        for i, enemy in enumerate(enemies):
            self._assert_type(f"enemies[{i}]", enemy, dict)
            for req_key in ("id", "name", "type"):
                self._assert_non_empty_str(f"enemies[{i}].{req_key}", enemy.get(req_key))
            if "base_health" in enemy:
                if self._assert_number(f"enemies[{i}].base_health", enemy["base_health"]) <= 0.0:
                    raise ValidationError(f"enemies[{i}].base_health", "Deve ser > 0.")
            if "base_damage" in enemy:
                if self._assert_number(f"enemies[{i}].base_damage", enemy["base_damage"]) < 0.0:
                    raise ValidationError(f"enemies[{i}].base_damage", "Não pode ser negativo.")

        self._validate_worlds(data["worlds_and_levels"])
        self._validate_economy(data["economy"])

        ui_ux = data["ui_ux"]
        self._assert_type("ui_ux", ui_ux, dict)
        orientation = ui_ux.get("screen_orientation")
        if orientation not in SUPPORTED_ORIENTATIONS:
            raise ValidationError(
                "ui_ux.screen_orientation",
                f"Orientação '{orientation}' inválida. Suportadas: {SUPPORTED_ORIENTATIONS}.",
            )

        self._validate_engineering_sections(data)

        criteria = data["acceptance_criteria"]
        self._assert_type("acceptance_criteria", criteria, list)
        if not criteria:
            raise ValidationError("acceptance_criteria", "Deve conter pelo menos um critério de aceitação.")
        for i, item in enumerate(criteria):
            self._assert_non_empty_str(f"acceptance_criteria[{i}]", item)

        if schema_ver >= SPEC_SCHEMA_VERSION_MULTIENGINE:
            self._validate_v2_optional_fields(data)

        return data

    def _validate_v2_optional_fields(self, data: dict[str, Any]) -> None:
        """Valida campos opcionais introduzidos no spec_schema_version=2 (multi-engine)."""
        if "tools_required" in data:
            tools = data["tools_required"]
            self._assert_type("tools_required", tools, list)
            for i, entry in enumerate(tools):
                if isinstance(entry, dict):
                    self._assert_non_empty_str(f"tools_required[{i}].id", entry.get("id"))
                else:
                    self._assert_non_empty_str(f"tools_required[{i}]", entry)

        for dict_field in (
            "camera_spec",
            "physics_spec",
            "inventory_spec",
            "quests_spec",
            "engine_selection_report",
        ):
            if dict_field in data:
                self._assert_type(dict_field, data[dict_field], dict)

    def validate_gdd(self, data: Any) -> dict[str, Any]:
        """Valida um Game Design Document garantindo preenchimento estrito dos 25 itens obrigatórios."""
        self._assert_type("root", data, dict)
        self._reject_unknown_keys("root", data, GDD_ALLOWED_FIELDS)

        for req in GDD_REQUIRED_FIELDS:
            if req not in data:
                raise ValidationError(req, "Campo obrigatório do GDD ausente.")

        schema_ver = self._assert_int("gdd_schema_version", data.get("gdd_schema_version"))
        if schema_ver != GDD_SCHEMA_VERSION:
            raise ValidationError(
                "gdd_schema_version",
                f"Versão de GDD incompatível: esperada {GDD_SCHEMA_VERSION}, encontrada {schema_ver}.",
            )

        self._assert_non_empty_str("project_id", data.get("project_id"))
        self._assert_non_empty_str("title", data.get("title"))

        if "linked_spec_id" in data and data["linked_spec_id"] is not None:
            self._assert_non_empty_str("linked_spec_id", data["linked_spec_id"])
        if "linked_spec_version" in data and data["linked_spec_version"] is not None:
            parse_semver(data["linked_spec_version"])

        sections = data.get("sections")
        self._assert_type("sections", sections, dict)
        self._reject_unknown_keys("sections", sections, GDD_SECTIONS)

        for sec in GDD_SECTIONS:
            if sec not in sections:
                raise ValidationError(f"sections.{sec}", "Seção obrigatória do GDD ausente.")
            sec_data = sections[sec]
            if not isinstance(sec_data, (str, dict, list)) or not sec_data:
                raise ValidationError(f"sections.{sec}", "Seção do GDD não pode ser vazia.")
            if isinstance(sec_data, str) and not sec_data.strip():
                raise ValidationError(f"sections.{sec}", "Seção do GDD não pode ser string em branco.")

        return data

    def check_compatibility(
        self,
        spec: dict[str, Any],
        required_schema_version: int = SPEC_SCHEMA_VERSION,
        required_engine: Optional[str] = "godot",
        required_engine_version: Optional[str] = None,
        required_spec_major: Optional[int] = None,
    ) -> dict[str, Any]:
        """Verifica compatibilidade de contrato entre GameSpecification, schema e template alvo."""
        validated = self.validate_spec(spec)
        if validated["spec_schema_version"] != required_schema_version:
            raise SchemaCompatibilityError(
                f"Schema incompatível: spec={validated['spec_schema_version']}, exigido={required_schema_version}."
            )
        if required_engine is not None and validated["engine"] != required_engine:
            raise SchemaCompatibilityError(
                f"Engine incompatível: spec='{validated['engine']}', exigida='{required_engine}'."
            )
        if required_engine_version is not None:
            norm_spec = validated["engine_version"].replace(".stable", "-stable")
            norm_req = required_engine_version.replace(".stable", "-stable")
            if norm_spec != norm_req:
                raise SchemaCompatibilityError(
                    f"Versão de engine incompatível: spec='{validated['engine_version']}', exigida='{required_engine_version}'."
                )
        major, _, _ = parse_semver(validated["version"])
        if required_spec_major is not None and major != required_spec_major:
            raise SchemaCompatibilityError(
                f"Versão MAJOR da especificação incompatível: spec={major}, exigida={required_spec_major}."
            )
        return {
            "compatible": True,
            "spec_id": validated["spec_id"],
            "spec_version": validated["version"],
            "spec_schema_version": validated["spec_schema_version"],
            "digest": compute_spec_digest(validated),
        }
