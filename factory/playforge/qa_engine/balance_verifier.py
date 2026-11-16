"""Balance Engine deterministico multi-genero da PlayForge Factory (Fase 8)."""
from __future__ import annotations

import json
import math
import random
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from factory.playforge.asset_pipeline.synthesizer import resolve_factory_godot_bin
from factory.playforge.models import ANCHOR_PROJECT_ID
from factory.playforge.registry import ProjectManager, _atomic_write_json, validate_project_id
from factory.playforge.spec_engine.schemas import SUPPORTED_GENRES

from .schemas import BALANCE_REPORT_SCHEMA_VERSION, BalanceVerificationError
from .static_analyzer import ensure_auditable_project, safe_log_qa_event, stage_isolated_godot_project

_ACTION_PROFILE_RE = re.compile(r"Profile\s+([A-Z0-9_]+)\s+\[(PASS|FAIL)\]")

_PROFILE_MODIFIERS: tuple[tuple[str, float, float, float], ...] = (
    # (profile_name, atk_mult, skill_acc_bonus, gold_spend_eff)
    ("F2P_PURE", 1.00, 0.00, 1.00),
    ("CASUAL_OPTIMAL", 1.08, 0.07, 1.05),
    ("HARDCORE_STRESS", 1.15, 0.12, 1.10),
)

GENRE_SIMULATION_PROFILES: dict[str, dict[str, Any]] = {
    "action-rpg": {
        "family": "combat_progression",
        "sustain_per_room": 0.25,
        "crit_chance": 0.20,
        "crit_mult": 1.50,
        "dodge_mitigation": 0.15,
        "hazard_dmg_ratio": 0.00,
        "upgrade_cost_base": 20.0,
        "upgrade_atk_step": 0.18,
        "max_steps_per_room": 250,
        "runs": 1,
    },
    "adventure": {
        "family": "combat_progression",
        "sustain_per_room": 0.30,
        "crit_chance": 0.15,
        "crit_mult": 1.50,
        "dodge_mitigation": 0.20,
        "hazard_dmg_ratio": 0.05,
        "upgrade_cost_base": 22.0,
        "upgrade_atk_step": 0.16,
        "max_steps_per_room": 250,
        "runs": 1,
    },
    "platformer-2d": {
        "family": "combat_progression",
        "sustain_per_room": 0.20,
        "crit_chance": 0.10,
        "crit_mult": 1.50,
        "dodge_mitigation": 0.25,
        "hazard_dmg_ratio": 0.10,
        "upgrade_cost_base": 25.0,
        "upgrade_atk_step": 0.15,
        "max_steps_per_room": 250,
        "runs": 1,
    },
    "arcade": {
        "family": "combat_progression",
        "sustain_per_room": 0.20,
        "crit_chance": 0.15,
        "crit_mult": 1.60,
        "dodge_mitigation": 0.30,
        "hazard_dmg_ratio": 0.08,
        "upgrade_cost_base": 18.0,
        "upgrade_atk_step": 0.15,
        "max_steps_per_room": 250,
        "runs": 1,
    },
    "roguelike": {
        "family": "combat_progression",
        "sustain_per_room": 0.15,
        "crit_chance": 0.22,
        "crit_mult": 1.60,
        "dodge_mitigation": 0.20,
        "hazard_dmg_ratio": 0.05,
        "upgrade_cost_base": 20.0,
        "upgrade_atk_step": 0.22,
        "max_steps_per_room": 250,
        "runs": 3,
    },
    "idle-rpg": {
        "family": "idle_scaling",
        "upgrade_cost_base": 15.0,
        "upgrade_cost_ratio": 1.18,
        "upgrade_atk_step": 0.20,
        "max_stall_ticks": 45,
        "max_total_ticks": 800,
    },
    "simulation": {
        "family": "idle_scaling",
        "upgrade_cost_base": 18.0,
        "upgrade_cost_ratio": 1.15,
        "upgrade_atk_step": 0.16,
        "max_stall_ticks": 50,
        "max_total_ticks": 800,
    },
    "strategy": {
        "family": "idle_scaling",
        "upgrade_cost_base": 22.0,
        "upgrade_cost_ratio": 1.20,
        "upgrade_atk_step": 0.18,
        "max_stall_ticks": 45,
        "max_total_ticks": 800,
    },
    "tower-defense": {
        "family": "idle_scaling",
        "upgrade_cost_base": 20.0,
        "upgrade_cost_ratio": 1.18,
        "upgrade_atk_step": 0.20,
        "max_stall_ticks": 45,
        "max_total_ticks": 800,
    },
    "puzzle": {
        "family": "puzzle_budget",
        "base_move_budget": 18,
        "crit_chance": 0.12,
        "upgrade_cost_base": 25.0,
        "upgrade_atk_step": 0.15,
        "max_turns": 300,
    },
    "ddtank-ballistics": {
        "family": "ballistics_turn",
        "base_hit_accuracy": 0.78,
        "wind_variance": 0.12,
        "crit_chance": 0.18,
        "crit_mult": 1.60,
        "upgrade_cost_base": 20.0,
        "upgrade_atk_step": 0.18,
        "max_turns_per_room": 60,
    },
}


@dataclass(frozen=True)
class _NormalizedSubject:
    genre: str
    hero_hp: float
    hero_atk: float
    rooms: tuple[dict[str, Any], ...]
    gacha_rates: dict[str, float]


def _ensure_finite_pos(val: Any, name: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise BalanceVerificationError(f"Parametro numerico invalido para '{name}': {val!r}.")
    num = float(val)
    if not math.isfinite(num) or num <= 0.0:
        raise BalanceVerificationError(f"Parametro '{name}' deve ser finito e positivo (> 0), obtido {num!r}.")
    return num


def _ensure_finite_nonneg(val: Any, name: str) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise BalanceVerificationError(f"Parametro numerico invalido para '{name}': {val!r}.")
    num = float(val)
    if not math.isfinite(num) or num < 0.0:
        raise BalanceVerificationError(f"Parametro '{name}' deve ser finito e >= 0, obtido {num!r}.")
    return num


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BalanceVerificationError(f"Falha ao ler JSON de balanceamento '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise BalanceVerificationError(f"Objeto JSON esperado em '{path}'.")
    return data


class BalanceVerifierEngine:
    """Simulador e auditor fail-closed de balanceamento parametrizado para todos os generos."""

    def __init__(
        self,
        manager: ProjectManager,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.manager = manager
        self._clock = clock

    def _now_timestamp(self) -> str:
        now = self._clock() if self._clock else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _extract_anchor_subject(self, genre_override: str | None) -> _NormalizedSubject:
        bal_path = self.manager.repo_root / "config" / "balance_v1.json"
        world_path = self.manager.repo_root / "config" / "action_world_v1.json"
        if not bal_path.is_file() or not world_path.is_file():
            raise BalanceVerificationError("Configs balance_v1.json/action_world_v1.json ausentes para 'zaikor'.")

        bal = _load_json_dict(bal_path)
        world_cfg = _load_json_dict(world_path)
        pcombat = world_cfg.get("player_combat", {})
        atk_curve = bal.get("upgrade_curves", {}).get("attack", {})

        hero_hp = _ensure_finite_pos(pcombat.get("base_max_hp", 260.0), "player_combat.base_max_hp")
        hero_atk = _ensure_finite_pos(atk_curve.get("base_value", 12.0), "upgrade_curves.attack.base_value")

        worlds = world_cfg.get("worlds", [])
        rooms: list[dict[str, Any]] = []
        for w in worlds:
            w_id = str(w.get("id", "world"))
            for r in w.get("rooms", []):
                enemies = r.get("enemies", [])
                total_hp = sum(float(e.get("hp", 50.0)) for e in enemies) if enemies else 50.0
                avg_atk = (
                    sum(float(e.get("damage", 8.0)) for e in enemies) / len(enemies)
                    if enemies
                    else 8.0
                )
                rooms.append(
                    {
                        "room_id": f"{w_id}:{r.get('id', 'room')}",
                        "enemy_hp": max(1.0, total_hp * 0.25),
                        "enemy_attack": max(0.0, avg_atk * 0.35),
                        "reward_gold": float(len(enemies) * 15.0 + 15.0),
                    }
                )
        if not rooms:
            raise BalanceVerificationError("Nenhuma sala encontrada em config/action_world_v1.json.")

        gacha_rates: dict[str, float] = {}
        banners = bal.get("gacha_banners", {})
        if isinstance(banners, dict) and banners:
            first_banner = next(iter(banners.values()))
            raw_rates = first_banner.get("rates", {}) if isinstance(first_banner, dict) else {}
            if isinstance(raw_rates, dict):
                gacha_rates = {str(k): float(v) for k, v in raw_rates.items()}

        genre = genre_override or "action-rpg"
        return _NormalizedSubject(
            genre=genre,
            hero_hp=hero_hp,
            hero_atk=hero_atk,
            rooms=tuple(rooms),
            gacha_rates=gacha_rates,
        )

    def _extract_project_subject(self, project_id: str, genre_override: str | None) -> _NormalizedSubject:
        spec_path = self.manager.resolve_game_path(project_id, "specs/game_specification.json")
        rt_path = self.manager.resolve_game_path(project_id, "config/template_defaults.json")

        spec: dict[str, Any] | None = None
        if spec_path.is_file():
            spec = _load_json_dict(spec_path)
        rt_cfg: dict[str, Any] | None = None
        if rt_path.is_file():
            rt_cfg = _load_json_dict(rt_path)

        if spec is None and rt_cfg is None:
            raise BalanceVerificationError(
                f"Projeto '{project_id}' nao possui specs/game_specification.json nem config/template_defaults.json."
            )

        proj_record = self.manager.get_project(project_id)
        genre = genre_override or (
            str(spec.get("genre")) if spec and spec.get("genre") else str(rt_cfg.get("genre") if rt_cfg else proj_record["genre"])
        )
        if genre not in GENRE_SIMULATION_PROFILES:
            raise BalanceVerificationError(f"Genero nao suportado no BalanceVerifierEngine: '{genre}'.")

        gacha_rates: dict[str, float] = {}
        if spec:
            mon = spec.get("monetization", {})
            eco = spec.get("economy", {})
            raw_rates = (mon.get("gacha_rates") if isinstance(mon, dict) else None) or (
                eco.get("gacha_rates") if isinstance(eco, dict) else None
            )
            if isinstance(raw_rates, dict):
                gacha_rates = {str(k): float(v) for k, v in raw_rates.items()}

        if rt_cfg is not None:
            hero = rt_cfg.get("hero", {})
            hero_hp = _ensure_finite_pos(hero.get("base_hp"), "hero.base_hp")
            hero_atk = _ensure_finite_pos(hero.get("base_attack"), "hero.base_attack")
            rooms: list[dict[str, Any]] = []
            for w in rt_cfg.get("worlds", []):
                for r in w.get("rooms", []):
                    rooms.append(
                        {
                            "room_id": str(r.get("room_id", "room")),
                            "enemy_hp": _ensure_finite_pos(r.get("enemy_hp"), "room.enemy_hp"),
                            "enemy_attack": _ensure_finite_nonneg(r.get("enemy_attack"), "room.enemy_attack"),
                            "reward_gold": _ensure_finite_nonneg(r.get("reward_gold"), "room.reward_gold"),
                        }
                    )
            if not rooms:
                raise BalanceVerificationError("config/template_defaults.json sem salas para simular.")
            return _NormalizedSubject(genre=genre, hero_hp=hero_hp, hero_atk=hero_atk, rooms=tuple(rooms), gacha_rates=gacha_rates)

        # Extracao direta de GameSpecification quando codigo Godot ainda nao foi gerado
        assert spec is not None
        chars = spec.get("characters", [])
        if not isinstance(chars, list) or not chars:
            raise BalanceVerificationError("GameSpecification sem characters.")
        player = next((c for c in chars if c.get("role") == "player"), chars[0])
        pstats = player.get("stats", {})
        hero_hp = _ensure_finite_pos(pstats.get("base_health"), "characters[player].stats.base_health")
        hero_atk = _ensure_finite_pos(pstats.get("base_attack"), "characters[player].stats.base_attack")

        enemies = spec.get("enemies", [])
        if not isinstance(enemies, list) or not enemies:
            raise BalanceVerificationError("GameSpecification sem enemies.")
        minion = next((e for e in enemies if e.get("type") == "minion"), enemies[0])
        boss = next((e for e in enemies if e.get("type") == "boss"), enemies[-1])

        diff = spec.get("difficulty", {})
        scaling = _ensure_finite_pos(diff.get("base_scaling", 1.15), "difficulty.base_scaling")
        boss_mult = _ensure_finite_pos(diff.get("boss_multiplier", 1.5), "difficulty.boss_multiplier")

        spec_worlds = spec.get("worlds_and_levels", {}).get("worlds", [])
        total_rooms = sum(len(w.get("rooms", [])) for w in spec_worlds)
        if total_rooms <= 0:
            raise BalanceVerificationError("GameSpecification sem worlds_and_levels.worlds[*].rooms.")

        rooms = []
        idx = 0
        for w in spec_worlds:
            for r in w.get("rooms", []):
                is_last = (idx == total_rooms - 1) and total_rooms > 1
                tpl = boss if is_last else minion
                factor = math.pow(scaling, idx)
                if is_last and tpl is not boss:
                    factor *= boss_mult
                rooms.append(
                    {
                        "room_id": str(r.get("room_id", f"room_{idx+1}")),
                        "enemy_hp": _ensure_finite_pos(tpl.get("base_health", 40.0) * factor, "enemy.base_health"),
                        "enemy_attack": _ensure_finite_nonneg(tpl.get("base_damage", 5.0) * factor, "enemy.base_damage"),
                        "reward_gold": round(25.0 * (2.0 if is_last else 1.0) * factor, 2),
                    }
                )
                idx += 1

        return _NormalizedSubject(genre=genre, hero_hp=hero_hp, hero_atk=hero_atk, rooms=tuple(rooms), gacha_rates=gacha_rates)

    def _validate_gacha_rates(self, gacha_rates: dict[str, float], findings: list[str]) -> None:
        if not gacha_rates:
            return
        total = 0.0
        for rarity, prob in gacha_rates.items():
            if not isinstance(prob, (int, float)) or not math.isfinite(float(prob)) or float(prob) < 0.0:
                findings.append(f"Taxa de gacha invalida em '{rarity}': {prob!r}.")
                return
            total += float(prob)
        if abs(total - 1.0) > 1e-4:
            findings.append(f"Soma das taxas de gacha diverge de 1.0 ({total:.6f}).")

    def _simulate_combat_progression(
        self,
        subject: _NormalizedSubject,
        model: dict[str, Any],
        rng: random.Random,
        atk_mult: float,
        gold_eff: float,
    ) -> dict[str, Any]:
        runs = int(model.get("runs", 1))
        total_clears = 0
        max_dmg_ratio = 0.0
        max_steps = 0
        final_gold = 0.0

        for _ in range(runs):
            hp = subject.hero_hp
            atk = subject.hero_atk * atk_mult
            gold = 0.0
            upg_cost = float(model["upgrade_cost_base"])
            cleared_rooms = 0
            run_steps = 0
            damage_taken_sum = 0.0

            for room in subject.rooms:
                enemy_hp = float(room["enemy_hp"])
                enemy_atk = float(room["enemy_attack"])
                room_steps = 0
                while enemy_hp > 0.0 and hp > 0.0 and room_steps < int(model["max_steps_per_room"]):
                    room_steps += 1
                    run_steps += 1
                    crit = rng.random() < float(model["crit_chance"])
                    enemy_hp -= atk * (float(model["crit_mult"]) if crit else 1.0)
                    if enemy_hp <= 0.0:
                        break
                    dodged = rng.random() < float(model["dodge_mitigation"])
                    if not dodged:
                        dmg = enemy_atk
                        hp -= dmg
                        damage_taken_sum += dmg
                if hp <= 0.0 or enemy_hp > 0.0:
                    break
                cleared_rooms += 1
                gold += float(room["reward_gold"]) * gold_eff
                # Dano ambiental leve entre salas para platformer/arcade/roguelike
                hp = max(1.0, hp - subject.hero_hp * float(model["hazard_dmg_ratio"]) * 0.25)
                hp = min(subject.hero_hp, hp + subject.hero_hp * float(model["sustain_per_room"]))
                while gold >= upg_cost:
                    gold -= upg_cost
                    atk *= 1.0 + float(model["upgrade_atk_step"])
                    upg_cost *= 1.35

            if cleared_rooms == len(subject.rooms) and hp > 0.0:
                total_clears += 1
            max_dmg_ratio = max(max_dmg_ratio, damage_taken_sum / max(1.0, subject.hero_hp * 2.5))
            max_steps = max(max_steps, run_steps)
            final_gold = gold

        clear_rate = total_clears / float(runs)
        ok = clear_rate >= 1.0 and max_dmg_ratio <= 1.25
        return {
            "ok": ok,
            "clear_rate": round(clear_rate, 3),
            "steps_elapsed": max_steps,
            "worst_case_damage_ratio": round(max_dmg_ratio, 4),
            "final_gold": round(final_gold, 2),
        }

    def _simulate_idle_scaling(
        self,
        subject: _NormalizedSubject,
        model: dict[str, Any],
        rng: random.Random,
        atk_mult: float,
        gold_eff: float,
    ) -> dict[str, Any]:
        atk = subject.hero_atk * atk_mult
        hp = subject.hero_hp
        gold = 0.0
        upg_cost = float(model["upgrade_cost_base"])
        cost_ratio = float(model["upgrade_cost_ratio"])
        atk_step = float(model["upgrade_atk_step"])
        max_stall = int(model["max_stall_ticks"])

        ticks = 0
        max_observed_stall = 0
        cleared_waves = 0
        for room in subject.rooms:
            enemy_hp = float(room["enemy_hp"])
            enemy_atk = float(room["enemy_attack"])
            wave_ticks = 0
            while enemy_hp > 0.0 and hp > 0.0 and wave_ticks < max_stall and ticks < int(model["max_total_ticks"]):
                ticks += 1
                wave_ticks += 1
                variance = 0.95 + rng.random() * 0.15
                enemy_hp -= atk * variance
                if enemy_hp <= 0.0:
                    break
                # Idle/TD tem cura passiva / barreira de torre entre waves
                hp -= enemy_atk * 0.35
                while gold >= upg_cost:
                    gold -= upg_cost
                    atk *= 1.0 + atk_step
                    upg_cost *= cost_ratio
            max_observed_stall = max(max_observed_stall, wave_ticks)
            if enemy_hp > 0.0 or hp <= 0.0 or not math.isfinite(gold):
                break
            cleared_waves += 1
            gold += float(room["reward_gold"]) * gold_eff
            hp = min(subject.hero_hp, hp + subject.hero_hp * 0.30)
            while gold >= upg_cost:
                gold -= upg_cost
                atk *= 1.0 + atk_step
                upg_cost *= cost_ratio

        clear_rate = 1.0 if cleared_waves == len(subject.rooms) else round(cleared_waves / len(subject.rooms), 3)
        ok = cleared_waves == len(subject.rooms) and max_observed_stall < max_stall and math.isfinite(gold)
        return {
            "ok": ok,
            "clear_rate": clear_rate,
            "steps_elapsed": ticks,
            "max_stall_ticks": max_observed_stall,
            "final_gold": round(gold, 2),
        }

    def _simulate_puzzle_budget(
        self,
        subject: _NormalizedSubject,
        model: dict[str, Any],
        rng: random.Random,
        atk_mult: float,
        gold_eff: float,
    ) -> dict[str, Any]:
        atk = subject.hero_atk * atk_mult
        hp = subject.hero_hp
        gold = 0.0
        upg_cost = float(model["upgrade_cost_base"])
        cleared = 0
        total_turns = 0
        for room in subject.rooms:
            target_score = float(room["enemy_hp"])
            hazard = float(room["enemy_attack"])
            budget = int(model["base_move_budget"])
            turns = 0
            while target_score > 0.0 and turns < budget and hp > 0.0:
                turns += 1
                total_turns += 1
                combo = 1.5 if rng.random() < float(model["crit_chance"]) else 1.0
                target_score -= atk * combo
                if target_score > 0.0:
                    hp -= hazard * 0.45
            if target_score > 0.0 or hp <= 0.0:
                break
            cleared += 1
            gold += float(room["reward_gold"]) * gold_eff
            hp = min(subject.hero_hp, hp + subject.hero_hp * 0.25)
            while gold >= upg_cost:
                gold -= upg_cost
                atk *= 1.0 + float(model["upgrade_atk_step"])
                upg_cost *= 1.35

        clear_rate = 1.0 if cleared == len(subject.rooms) else round(cleared / len(subject.rooms), 3)
        return {
            "ok": cleared == len(subject.rooms),
            "clear_rate": clear_rate,
            "steps_elapsed": total_turns,
            "final_gold": round(gold, 2),
        }

    def _simulate_ballistics_turn(
        self,
        subject: _NormalizedSubject,
        model: dict[str, Any],
        rng: random.Random,
        atk_mult: float,
        acc_bonus: float,
        gold_eff: float,
    ) -> dict[str, Any]:
        atk = subject.hero_atk * atk_mult
        hp = subject.hero_hp
        gold = 0.0
        upg_cost = float(model["upgrade_cost_base"])
        cleared = 0
        total_turns = 0
        eff_acc = min(0.98, float(model["base_hit_accuracy"]) + acc_bonus)

        for room in subject.rooms:
            enemy_hp = float(room["enemy_hp"])
            enemy_atk = float(room["enemy_attack"])
            turns = 0
            while enemy_hp > 0.0 and hp > 0.0 and turns < int(model["max_turns_per_room"]):
                turns += 1
                total_turns += 1
                wind_penalty = abs(rng.uniform(-float(model["wind_variance"]), float(model["wind_variance"]))) * 0.5
                if rng.random() <= (eff_acc - wind_penalty):
                    crit = rng.random() < float(model["crit_chance"])
                    enemy_hp -= atk * (float(model["crit_mult"]) if crit else 1.0)
                if enemy_hp <= 0.0:
                    break
                if rng.random() < 0.72:
                    hp -= enemy_atk
            if enemy_hp > 0.0 or hp <= 0.0:
                break
            cleared += 1
            gold += float(room["reward_gold"]) * gold_eff
            hp = min(subject.hero_hp, hp + subject.hero_hp * 0.30)
            while gold >= upg_cost:
                gold -= upg_cost
                atk *= 1.0 + float(model["upgrade_atk_step"])
                upg_cost *= 1.35

        clear_rate = 1.0 if cleared == len(subject.rooms) else round(cleared / len(subject.rooms), 3)
        return {
            "ok": cleared == len(subject.rooms),
            "clear_rate": clear_rate,
            "steps_elapsed": total_turns,
            "final_gold": round(gold, 2),
        }

    def _run_anchor_godot_action_verifier(self) -> dict[str, Any]:
        godot_bin = resolve_factory_godot_bin(self.manager.repo_root)
        if godot_bin is None or not godot_bin.is_file():
            raise BalanceVerificationError("Binario Godot CLI nao encontrado para verificar run_action_verifier.gd.")

        with tempfile.TemporaryDirectory(prefix="playforge_anchor_bal_") as tmp:
            tmp_root = Path(tmp)
            proj_dir = stage_isolated_godot_project(self.manager, ANCHOR_PROJECT_ID, tmp_root / "project")
            user_home = tmp_root / "user_home"
            user_home.mkdir(parents=True, exist_ok=True)
            import os

            env = os.environ.copy()
            env["APPDATA"] = str(user_home)
            env["LOCALAPPDATA"] = str(user_home)
            env["USERPROFILE"] = str(user_home)
            env["HOME"] = str(user_home)
            proc = subprocess.run(
                [
                    str(godot_bin),
                    "--headless",
                    "--no-header",
                    "--path",
                    str(proj_dir),
                    "--script",
                    "res://tests/integration/run_action_verifier.gd",
                ],
                capture_output=True,
                text=True,
                timeout=30.0,
                env=env,
                check=False,
            )
            combined = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
            profiles_found = _ACTION_PROFILE_RE.findall(combined)
            passed = proc.returncode == 0 and "ACTION BALANCE GATE PASSED" in combined and "SCRIPT ERROR:" not in combined
            return {
                "passed": passed,
                "returncode": proc.returncode,
                "profiles": {name: status for name, status in profiles_found},
                "output": combined,
            }

    def verify_project_balance(
        self,
        project_id: str,
        *,
        genre: str | None = None,
        seed: int = 2026,
        run_godot: bool = False,
        save_report: bool = True,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Executa simulacao deterministica de balanceamento por genero sobre project_id."""
        ensure_auditable_project(self.manager, project_id)
        if genre is not None and genre not in SUPPORTED_GENRES:
            raise BalanceVerificationError(
                f"Genero desconhecido '{genre}'. Suportados: {list(SUPPORTED_GENRES)}."
            )

        findings: list[str] = []
        subject: _NormalizedSubject | None = None
        try:
            subject = (
                self._extract_anchor_subject(genre)
                if project_id == ANCHOR_PROJECT_ID
                else self._extract_project_subject(project_id, genre)
            )
        except BalanceVerificationError as exc:
            findings.append(str(exc))

        profile_reports: list[dict[str, Any]] = []
        godot_anchor_result: dict[str, Any] | None = None

        if subject is not None:
            self._validate_gacha_rates(subject.gacha_rates, findings)
            model = GENRE_SIMULATION_PROFILES[subject.genre]
            family = model["family"]

            for idx, (prof_name, atk_mult, acc_bonus, gold_eff) in enumerate(_PROFILE_MODIFIERS):
                rng = random.Random(int(seed) + idx * 101)
                if family == "combat_progression":
                    sim_out = self._simulate_combat_progression(subject, model, rng, atk_mult, gold_eff)
                elif family == "idle_scaling":
                    sim_out = self._simulate_idle_scaling(subject, model, rng, atk_mult, gold_eff)
                elif family == "puzzle_budget":
                    sim_out = self._simulate_puzzle_budget(subject, model, rng, atk_mult, gold_eff)
                elif family == "ballistics_turn":
                    sim_out = self._simulate_ballistics_turn(subject, model, rng, atk_mult, acc_bonus, gold_eff)
                else:
                    raise BalanceVerificationError(f"Familia de simulador nao suportada: '{family}'.")

                entry = {"profile": prof_name, **sim_out}
                profile_reports.append(entry)
                if not entry["ok"]:
                    findings.append(
                        f"Perfil '{prof_name}' ({subject.genre}) falhou (clear_rate={entry['clear_rate']})."
                    )

            if run_godot and project_id == ANCHOR_PROJECT_ID:
                godot_anchor_result = self._run_anchor_godot_action_verifier()
                if not godot_anchor_result["passed"]:
                    findings.append("Godot ActionBalanceVerifier falhou em zaikor.")

        passed = len(findings) == 0 and len(profile_reports) == len(_PROFILE_MODIFIERS)
        report = {
            "balance_schema_version": BALANCE_REPORT_SCHEMA_VERSION,
            "project_id": project_id,
            "genre": subject.genre if subject else (genre or "unknown"),
            "simulator_family": GENRE_SIMULATION_PROFILES[subject.genre]["family"] if subject else "unknown",
            "seed": int(seed),
            "verified_at": self._now_timestamp(),
            "passed": passed,
            "rooms_evaluated": len(subject.rooms) if subject else 0,
            "profiles": profile_reports,
            "godot_verifier": godot_anchor_result,
            "findings": findings,
        }

        if save_report and project_id != ANCHOR_PROJECT_ID:
            report_path = self.manager.resolve_game_path(project_id, "specs/balance_report.json")
            _atomic_write_json(report_path, report)

        safe_log_qa_event(
            self.manager,
            "INFO" if passed else "ERROR",
            "BALANCE_AUDIT",
            project_id=project_id,
            genre=report["genre"],
            passed=passed,
            finding_count=len(findings),
        )

        if strict and not passed:
            raise BalanceVerificationError("; ".join(findings))
        return report
