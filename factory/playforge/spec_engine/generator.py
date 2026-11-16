"""Gerador estruturado e fluxo de aprovação de GameSpecification e GDD (Fase 3)."""
from __future__ import annotations

import json
from typing import Any, Optional

from ..models import ApprovalRequired
from ..registry import ProjectManager, _atomic_write_json, _atomic_write_text
from .schemas import (
    GDD_SCHEMA_VERSION,
    GDD_SECTIONS,
    SPEC_SCHEMA_VERSION,
    SPEC_SCHEMA_VERSION_MULTIENGINE,
)
from .validator import SpecificationValidator, ValidationError, compute_spec_digest


class SpecificationGenerator:
    """Produz, valida, vincula e aprova GameSpecification e GDD no workspace isolado do projeto."""

    def __init__(self, manager: ProjectManager) -> None:
        self.manager = manager
        self.validator = SpecificationValidator()

    def build_default_spec(
        self,
        game_id: str,
        name: str,
        genre: str,
        subgenre: str = "core-loop",
        target_platforms: Optional[list[str]] = None,
        screen_orientation: str = "landscape",
        engine: str = "godot",
        engine_version: Optional[str] = None,
        multiengine: bool = False,
        tools_required: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Constrói uma GameSpecification completa com todas as dimensões preenchidas e validadas."""
        platforms = target_platforms or ["windows", "linux", "android"]
        default_versions = {
            "godot": "4.4-stable",
            "unity": "6000.0-lts",
            "unreal": "5.4",
        }
        resolved_engine_version = engine_version or default_versions.get(engine, "1.0.0")
        use_v2 = bool(multiengine or engine != "godot" or tools_required is not None)
        schema_ver = SPEC_SCHEMA_VERSION_MULTIENGINE if use_v2 else SPEC_SCHEMA_VERSION
        spec: dict[str, Any] = {
            "spec_id": f"spec-{game_id}-v1",
            "game_id": game_id,
            "name": name,
            "version": "0.1.0",
            "spec_schema_version": schema_ver,
            "genre": genre,
            "subgenre": subgenre,
            "target_platforms": platforms,
            "engine": engine,
            "engine_version": resolved_engine_version,
            "target_audience": {
                "demographic": "Jogadores de 16-35 anos apreciadores de mecânicas determinísticas",
                "playstyle": "Sessões curtas a médias (5-20 min) com progressão constante",
            },
            "product_goals": [
                f"Construir experiência sólida e balanceada do gênero {genre}",
                "Garantir taxa de quadros estável em plataformas alvo",
                "Operar 100% offline com persistência local confiável",
            ],
            "value_proposition": f"Gameplay envolvente de {genre} com progressão justa e zero atrito técnico.",
            "references": [
                "Zaikor: Zenkai Infinite (arquitetura determinística e balanceamento fail-closed)"
            ],
            "core_gameplay": {
                "camera": "2D side-view or top-down",
                "perspective": "2D",
                "physics_mode": "custom-deterministic",
            },
            "core_loop": "Entrar em fase -> Executar mecânicas -> Coletar recursos -> Aprimorar atributos -> Desafiar chefe",
            "controls": {
                "primary_input": "keyboard_and_touch",
                "actions": ["move_left", "move_right", "jump", "primary_action", "skill_action"],
            },
            "mechanics": [
                {
                    "id": "mech_core_loop",
                    "name": "Progressão de Fases",
                    "description": "Limpar inimigos da sala para destravar portal seguinte",
                },
                {
                    "id": "mech_combat",
                    "name": "Combate Tático",
                    "description": "Ataques com tempo de recarga e janelas de esquiva",
                },
            ],
            "characters": [
                {
                    "id": "char_hero",
                    "name": "Protagonista",
                    "role": "player",
                    "stats": {"base_health": 100, "base_attack": 10, "speed": 150},
                }
            ],
            "enemies": [
                {
                    "id": "enemy_minion",
                    "name": "Sentinela Menor",
                    "type": "minion",
                    "base_health": 40,
                    "base_damage": 5,
                },
                {
                    "id": "enemy_boss",
                    "name": "Guardião do Abismo",
                    "type": "boss",
                    "base_health": 300,
                    "base_damage": 20,
                },
            ],
            "worlds_and_levels": {
                "total_rooms": 2,
                "worlds": [
                    {
                        "world_id": "world_1",
                        "name": "Floresta Sombria",
                        "rooms": [
                            {
                                "room_id": "room_1",
                                "name": "Entrada",
                                "connections": [{"target_room_id": "room_2"}],
                            },
                            {
                                "room_id": "room_2",
                                "name": "Câmara do Chefe",
                                "connections": [{"target_room_id": "room_1"}],
                            },
                        ],
                    }
                ],
            },
            "progression": {
                "curve_type": "exponential_soft_cap",
                "max_level": 50,
            },
            "difficulty": {
                "base_scaling": 1.15,
                "boss_multiplier": 2.5,
            },
            "economy": {
                "currencies": ["gold", "gems"],
                "gacha_rates": {
                    "common": 0.70,
                    "rare": 0.25,
                    "legendary": 0.05,
                },
            },
            "ui_ux": {
                "screen_orientation": screen_orientation,
                "resolution": "1920x1080",
                "elements": ["health_bar", "currency_counter", "skill_buttons", "pause_menu"],
            },
            "accessibility": {
                "colorblind_mode": True,
                "subtitles": True,
                "configurable_controls": True,
            },
            "narrative": {
                "lore_summary": "O herói desafia os guardiões ancestrais para restaurar o equilíbrio do reino.",
                "dialogue_style": "minimalist_in_game_banners",
            },
            "audio": {
                "music_style": "atmospheric_synth",
                "procedural_sfx": True,
            },
            "art_and_assets": {
                "style": "high_contrast_2d_silhouette",
                "palette": ["#0f0f14", "#ffffff", "#e63946", "#457b9d"],
            },
            "persistence": {
                "save_format": "json_atomic",
                "slots": 3,
            },
            "technical_requirements": {
                "target_fps": 60,
                "max_ram_mb": 256,
                "headless_compatible": True,
            },
            "security": {
                "anti_tamper": True,
                "offline_only": True,
            },
            "monetization": {
                "enabled": False,
                "model": "f2p_pure",
            },
            "acceptance_criteria": [
                "Execução de testes determinísticos em modo headless em tempo inferior a 1s",
                "Nenhum travamento ou soft-lock durante transições entre salas do mundo 1",
                "Soma das taxas de sorteio transparente igual a 100%",
            ],
        }
        if use_v2:
            spec["tools_required"] = list(tools_required) if tools_required is not None else [engine]
        return self.validator.validate_spec(spec)

    def generate_and_save_spec(
        self,
        project_id: str,
        custom_spec: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Gera e salva game_specification.json no workspace isolado games/<project_id>/specs/."""
        project = self.manager.require_mutable_project(project_id)
        if custom_spec is not None:
            spec = self.validator.validate_spec(custom_spec)
            if spec["game_id"] != project_id:
                raise ValidationError(
                    "game_id",
                    f"Isolamento violado: spec pertence a '{spec['game_id']}', mas alvo é '{project_id}'.",
                )
        else:
            project_engine = str(project.get("engine", "godot"))
            spec = self.build_default_spec(
                game_id=project["project_id"],
                name=project["name"],
                genre=project["genre"],
                engine=project_engine,
            )

        spec_file = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        _atomic_write_json(spec_file, spec)
        self.manager.log_event(
            "INFO",
            "spec_generated",
            project_id=project_id,
            spec_id=spec["spec_id"],
            spec_version=spec["version"],
            sha256=compute_spec_digest(spec),
        )
        return spec

    def build_default_gdd(
        self,
        project_id: str,
        title: str,
        genre: str,
        linked_spec_id: Optional[str] = None,
        linked_spec_version: Optional[str] = None,
    ) -> dict[str, Any]:
        """Constrói um GDD com as 25 seções obrigatórias e vínculo opcional com a Spec."""
        gdd: dict[str, Any] = {
            "gdd_schema_version": GDD_SCHEMA_VERSION,
            "project_id": project_id,
            "title": title,
            "linked_spec_id": linked_spec_id or f"spec-{project_id}-v1",
            "linked_spec_version": linked_spec_version or "0.1.0",
            "sections": {
                "concept": f"Jogo do gênero {genre} focado em mecânicas determinísticas e experiência imersiva.",
                "vision": "Criar um título autônomo com alta fidelidade de controles e progressão transparente.",
                "genre": genre,
                "target_audience": "Jogadores apreciadores de desafios táticos e ritmo contínuo.",
                "differentials": "Simulação 100% livre de microtransações predatórias e física determinística.",
                "references": "Inspirado em padrões consolidados de gameplay da fábrica PlayForge.",
                "core_loop": "Entrar em fase -> Superar desafios -> Coletar recompensas -> Evoluir atributos.",
                "gameplay_loop": "Movimento preciso, esquivas pontuais e uso estratégico de habilidades.",
                "mechanics": "Sistema de vida, vigor, dano por acerto e recompensas exponenciais escalonadas.",
                "controls": "Suporte simultâneo a teclado e botões de toque mobile.",
                "characters": "Protagonista customizável com habilidades de avanço e esquiva.",
                "enemies": "Inimigos comuns com patrulha e chefes de sala com padrões de ataque em fases.",
                "environments": "Cenários 2D em paralaxe com contraste elevado.",
                "levels_and_worlds": "Estrutura modular de salas interligadas por portais dimensionais.",
                "progression": "Curvas matemáticas balanceadas sem picos abruptos de bloqueio (progress walls).",
                "economy": "Ouro e gemas conquistados exclusivamente por mérito in-game.",
                "difficulty": "Curva adaptativa com multiplicadores graduais por sala.",
                "ui_ux": "HUD limpo com exibição de vida, recursos e comandos imediatos.",
                "audio": "Efeitos sonoros procedurais gerados diretamente em memória e trilha ambiente.",
                "visual_direction": "Estética estilizada em silhuetas e partículas contrastantes.",
                "accessibility": "Suporte a remapeamento de controles e modos de alto contraste.",
                "monetization": "Desativada (Zero Cost / Free First).",
                "technical_requirements": "Godot 4.x, 60 FPS estáveis, consumo inferior a 256 MB de RAM.",
                "mvp_scope": "1 mundo funcional com 2 salas conectadas, 1 inimigo comum e 1 chefe.",
                "acceptance_criteria": "Todos os testes unitários passando em tempo < 1s e zero soft-locks.",
            },
        }
        return self.validator.validate_gdd(gdd)

    def _load_project_spec(self, project_id: str) -> dict[str, Any]:
        spec_file = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        if not spec_file.exists():
            raise ValidationError("game_specification", f"Especificação não encontrada para '{project_id}'.")
        try:
            raw = json.loads(spec_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("game_specification", f"Falha ao ler JSON da especificação: {exc}") from exc
        validated = self.validator.validate_spec(raw)
        if validated["game_id"] != project_id:
            raise ValidationError("game_id", f"Spec em disk pertence a '{validated['game_id']}', esperado '{project_id}'.")
        return validated

    def _load_project_gdd(self, project_id: str) -> dict[str, Any]:
        gdd_file = self.manager.resolve_game_path(project_id, "gdd/gdd.json")
        if not gdd_file.exists():
            raise ValidationError("gdd", f"GDD não encontrado para '{project_id}'.")
        try:
            raw = json.loads(gdd_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("gdd", f"Falha ao ler JSON do GDD: {exc}") from exc
        validated = self.validator.validate_gdd(raw)
        if validated["project_id"] != project_id:
            raise ValidationError("project_id", f"GDD pertence a '{validated['project_id']}', esperado '{project_id}'.")
        return validated

    def generate_and_save_gdd(self, project_id: str) -> dict[str, Any]:
        """Gera e salva gdd.json e gdd.md atomicamente em games/<project_id>/gdd/."""
        project = self.manager.require_mutable_project(project_id)

        spec_file = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        linked_spec_id = None
        linked_spec_version = None
        if spec_file.exists():
            spec = self._load_project_spec(project_id)
            linked_spec_id = spec["spec_id"]
            linked_spec_version = spec["version"]

        gdd = self.build_default_gdd(
            project_id=project["project_id"],
            title=project["name"],
            genre=project["genre"],
            linked_spec_id=linked_spec_id,
            linked_spec_version=linked_spec_version,
        )

        gdd_json_file = self.manager.resolve_game_path(project_id, "gdd/gdd.json")
        _atomic_write_json(gdd_json_file, gdd)

        md_lines = [
            f"# Game Design Document — {gdd['title']}",
            "",
            f"- **Project ID:** `{gdd['project_id']}`",
            f"- **GDD Schema Version:** `{gdd['gdd_schema_version']}`",
            f"- **Linked Spec:** `{gdd.get('linked_spec_id')}` (`v{gdd.get('linked_spec_version')}`)",
            "",
            "---",
            "",
        ]
        for idx, sec in enumerate(GDD_SECTIONS, start=1):
            sec_title = sec.replace("_", " ").title()
            content = gdd["sections"][sec]
            md_lines.append(f"## {idx}. {sec_title}")
            md_lines.append("")
            md_lines.append(str(content))
            md_lines.append("")

        gdd_md_file = self.manager.resolve_game_path(project_id, "gdd/gdd.md")
        _atomic_write_text(gdd_md_file, "\n".join(md_lines))
        self.manager.log_event(
            "INFO",
            "gdd_generated",
            project_id=project_id,
            linked_spec_id=gdd.get("linked_spec_id"),
            linked_spec_version=gdd.get("linked_spec_version"),
        )
        return gdd

    def approve_specification(
        self,
        project_id: str,
        approver: str,
        decision_notes: str,
        require_gdd: bool = True,
    ) -> dict[str, Any]:
        """Valida Spec (+ GDD vinculado) e registra aprovação humana com SHA-256 imutável."""
        self.manager.require_mutable_project(project_id)
        if not isinstance(approver, str) or not approver.strip():
            raise ApprovalRequired("Identificação do aprovador humano obrigatória.")
        if not isinstance(decision_notes, str) or not decision_notes.strip():
            raise ApprovalRequired("Notas de justificativa da aprovação obrigatórias.")

        spec = self._load_project_spec(project_id)
        gdd_linked = False
        if require_gdd:
            gdd = self._load_project_gdd(project_id)
            if gdd.get("linked_spec_id") and gdd["linked_spec_id"] != spec["spec_id"]:
                raise ValidationError(
                    "linked_spec_id",
                    f"GDD aponta para '{gdd['linked_spec_id']}', mas spec atual é '{spec['spec_id']}'.",
                )
            gdd_linked = True

        digest = compute_spec_digest(spec)
        approval_record = {
            "approved": True,
            "project_id": project_id,
            "spec_id": spec["spec_id"],
            "spec_version": spec["version"],
            "spec_schema_version": spec["spec_schema_version"],
            "spec_sha256": digest,
            "gdd_linked": gdd_linked,
            "approver": approver.strip(),
            "notes": decision_notes.strip(),
            "approved_at": self.manager.now_timestamp(),
        }
        approval_file = self.manager.resolve_game_path(project_id, "specs/spec_approval.json")
        _atomic_write_json(approval_file, approval_record)
        self.manager.log_event(
            "INFO",
            "spec_approved",
            project_id=project_id,
            spec_id=spec["spec_id"],
            spec_sha256=digest,
            approver=approval_record["approver"],
        )
        return approval_record

    def verify_spec_approved(self, project_id: str) -> dict[str, Any]:
        """Verifica fail-closed se a spec atual possui aprovação válida e íntegra (mesmo SHA-256)."""
        spec = self._load_project_spec(project_id)
        approval_file = self.manager.resolve_game_path(project_id, "specs/spec_approval.json")
        if not approval_file.exists():
            raise ApprovalRequired(
                f"Especificação de '{project_id}' ainda não foi aprovada pelo operador."
            )
        try:
            approval = json.loads(approval_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ApprovalRequired(f"Registro de aprovação de spec corrompido: {exc}") from exc

        if not isinstance(approval, dict) or approval.get("approved") is not True:
            raise ApprovalRequired(f"Aprovação da spec de '{project_id}' não está marcada como aprovada.")

        current_digest = compute_spec_digest(spec)
        if approval.get("spec_sha256") != current_digest:
            raise ApprovalRequired(
                f"Especificação de '{project_id}' foi alterada após aprovação (hash divergente); exige nova aprovação."
            )
        return approval
