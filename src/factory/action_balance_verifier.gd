class_name ActionBalanceVerifier
extends RefCounted
## Simulador e auditor fail-closed de combate 2D lateral, Mundos Interconectados e Altares.
## Executa bot deterministico em 20 Hz validando Mundo 1 -> Mundo 2 sem soft-locks.

const SeededRngScript = preload("res://src/core/seeded_rng.gd")
const IdleEconomyScript = preload("res://src/core/idle_economy.gd")
const ActionCoreScript = preload("res://src/core/action_combat_core.gd")

const SIM_DT: float = 0.05
const MAX_SIM_SECONDS: float = 480.0


static func _buy_altar_upgrades(core: RefCounted, balance_cfg: Dictionary, events: Array) -> void:
	var priority: PackedStringArray = ["attack", "attack_speed", "crit_rate", "crit_damage", "penetration"]
	for _r in range(8):
		var bought: bool = false
		for key in priority:
			var cur_lv: int = int(core.economy["levels"][key])
			if key != "attack" and cur_lv > int(core.economy["levels"]["attack"]) * 0.75:
				continue
			var res: Dictionary = core.buy_forge_upgrade(key, 1, events)
			if bool(res.get("ok", false)):
				bought = true
		if not bought:
			break


static func _pick_target_portal(core: RefCounted, visited_rooms: Dictionary) -> Dictionary:
	var portals: Array = core.current_room_def.get("portals", [])
	for p in portals:
		var twid: String = String(p["target_world_id"])
		var trid: String = String(p["target_room_id"])
		var key: String = "%s::%s" % [twid, trid]
		if not visited_rooms.has(key) and bool(core.get_portal_state(p)["unlocked"]):
			return p
	for p in portals:
		var pid: String = String(p["id"])
		if not pid.ends_with("_back") and pid != "p_w2_to_world1" and bool(core.get_portal_state(p)["unlocked"]):
			return p
	return portals[0] if not portals.is_empty() else {}


static func _nearest_enemy(core: RefCounted) -> Dictionary:
	var best: Dictionary = {}
	var best_d: float = 1e12
	for e in core.enemies:
		if int(e["ai_state"]) == ActionCoreScript.EnemyAi.DEAD:
			continue
		var d: float = absf(float(e["x"]) - core.px) + absf(float(e["y"]) - core.py) * 0.6
		if d < best_d:
			best_d = d
			best = e
	return best


static func _simulate_campaign(profile_name: String, balance_cfg: Dictionary, world_cfg: Dictionary, seed_val: int) -> Dictionary:
	var rng := SeededRngScript.new(seed_val)
	var base_ms: int = 1_700_000_000_000
	var core := ActionCoreScript.new(balance_cfg, world_cfg, rng, base_ms)
	var events: Array = []

	var use_ads: bool = (profile_name != "F2P_PURE")
	var visited_rooms: Dictionary = {}
	var used_altars: Dictionary = {}
	var revive_used_room: Dictionary = {}
	var skills_cast: int = 0
	var qte_successes: int = 0
	var dodges: int = 0
	var deaths: int = 0
	var altars_used: int = 0

	var sim_t: float = 0.0
	var magics: Array = world_cfg["player_combat"]["magic_powers"]

	while sim_t < MAX_SIM_SECONDS:
		var now_ms: int = base_ms + int(round(sim_t * 1000.0))
		visited_rooms["%s::%s" % [core.current_world_id, core.current_room_id]] = true

		if core.game_phase == ActionCoreScript.GamePhase.CAMPAIGN_CLEARED:
			break

		if core.game_phase == ActionCoreScript.GamePhase.DEFEATED_REVIVE_OFFER:
			deaths += 1
			var rkey: String = "%s::%s" % [core.current_world_id, core.current_room_id]
			if use_ads and not revive_used_room.has(rkey):
				revive_used_room[rkey] = true
				core.resolve_defeat_revive(true, true, events)
			else:
				core.resolve_defeat_revive(false, false, events)
			sim_t += SIM_DT
			continue

		var cmd: Dictionary = {}
		if core.game_phase == ActionCoreScript.GamePhase.BOSS_QTE:
			cmd["qte_pressed"] = true
		else:
			# Puxa Gacha 10x sempre que juntar 450 gemas
			while int(core.economy["gems"]) >= 450:
				IdleEconomyScript.execute_gacha_pull(core.economy, "weapons_mythic_v1", 10, false, false, rng, balance_cfg, now_ms)

			# Prioridade 1: Usar Altar de Salvamento na sala atual se ainda nao ativado ou HP < 85%
			var target_altar: Dictionary = {}
			for a in core.current_room_def.get("altars", []):
				var aid: String = String(a["id"])
				if not used_altars.has(aid):
					target_altar = a
					break

			var alive_count: int = core.get_room_enemies_alive()
			if not target_altar.is_empty():
				var ax: float = float(target_altar["x"])
				var dx_a: float = ax - core.px
				if absf(dx_a) <= 65.0:
					cmd["interact_pressed"] = true
					used_altars[String(target_altar["id"])] = true
					_buy_altar_upgrades(core, balance_cfg, events)
				else:
					cmd["move_x"] = 1.0 if dx_a > 0.0 else -1.0
			elif alive_count > 0:
				var tgt: Dictionary = _nearest_enemy(core)
				var dx: float = float(tgt["x"]) - core.px
				var dy: float = float(tgt["y"]) - core.py
				var abs_dx: float = absf(dx)
				var eff_rate: float = 0.35 if float(tgt.get("freeze_s", 0.0)) > 0.0 else 1.0
				var windup_real_left: float = float(tgt["ai_timer_s"]) / eff_rate
				var enemy_winding: bool = int(tgt["ai_state"]) == ActionCoreScript.EnemyAi.WINDUP and windup_real_left <= 0.14

				if enemy_winding and abs_dx <= float(tgt["attack_range"]) + 35.0 and core.dash_cooldown_s <= 0.0:
					cmd["dash_pressed"] = true
					cmd["move_x"] = 1.0 if dx >= 0.0 else -1.0
				elif abs_dx > 135.0:
					cmd["move_x"] = 1.0 if dx > 0.0 else -1.0
					if dy > 45.0 and core.on_ground and abs_dx < 260.0:
						cmd["jump_pressed"] = true
					# Usa Raio Celestial (slot 2) se alcancavel a distancia
					if core.skill_cooldowns[2] <= 0.0 and core.mana >= float(magics[2]["mana_cost"]) and abs_dx <= 680.0:
						cmd["cast_skill_idx"] = 2
				else:
					cmd["move_x"] = 0.15 if dx >= 0.0 else -0.15
					if dy > 45.0 and core.on_ground:
						cmd["jump_pressed"] = true
					if core.rage_ratio >= 1.0 and not core.is_rage_active():
						cmd["rage_pressed"] = true
					var cast_idx: int = -1
					for s_idx in [3, 0, 1, 2]:
						if core.skill_cooldowns[s_idx] <= 0.0 and core.mana >= float(magics[s_idx]["mana_cost"]):
							cast_idx = s_idx
							break
					if cast_idx >= 0:
						cmd["cast_skill_idx"] = cast_idx
					else:
						cmd["attack_pressed"] = true
			else:
				# Sala limpa: compra upgrades se houver ouro sobrando e atravessa proximo portal
				_buy_altar_upgrades(core, balance_cfg, events)
				var portal: Dictionary = _pick_target_portal(core, visited_rooms)
				if not portal.is_empty():
					var pdx: float = float(portal["x"]) - core.px
					if absf(pdx) <= 65.0:
						cmd["interact_pressed"] = true
					else:
						cmd["move_x"] = 1.0 if pdx > 0.0 else -1.0

		events.clear()
		core.step(SIM_DT, cmd, now_ms, events)
		for ev in events:
			var et: String = String(ev.get("type", ""))
			if et == "magic_cast":
				skills_cast += 1
			elif et == "boss_qte_finisher" and bool(ev.get("success", false)):
				qte_successes += 1
			elif et == "player_dodged":
				dodges += 1
			elif et == "altar_activated":
				altars_used += 1

		if not bool((core.economy["gold"] as RefCounted).get("valid")) or not bool((core.hp as RefCounted).get("valid")):
			return {"ok": false, "profile": profile_name, "error": "Invalid BigNum at t=%.2fs" % sim_t}

		sim_t += SIM_DT

	return {
		"ok": core.game_phase == ActionCoreScript.GamePhase.CAMPAIGN_CLEARED,
		"profile": profile_name,
		"elapsed_sim_s": sim_t,
		"worlds_cleared": core.defeated_boss_worlds.size(),
		"rooms_visited": visited_rooms.size(),
		"altars_used": altars_used,
		"skills_cast": skills_cast,
		"qte_successes": qte_successes,
		"dodges": dodges,
		"deaths": deaths,
		"final_gold": core.economy["gold"],
		"attack_lv": int(core.economy["levels"]["attack"]),
	}


static func run_full_audit(balance_cfg: Dictionary, world_cfg: Dictionary) -> Dictionary:
	var errors: PackedStringArray = PackedStringArray()
	var reports: Array[Dictionary] = []
	var profiles: Array[String] = ["F2P_PURE", "F2P_REWARDED"]

	for idx in range(profiles.size()):
		var rep: Dictionary = _simulate_campaign(profiles[idx], balance_cfg, world_cfg, 2025 + idx * 31)
		reports.append(rep)
		if not bool(rep["ok"]):
			errors.append("[%s] Failed to clear World 1 -> World 2 campaign within %.1fs (error=%s)" % [
				rep["profile"], MAX_SIM_SECONDS, String(rep.get("error", "Timeout / soft-lock"))
			])
		if int(rep.get("altars_used", 0)) < 2:
			errors.append("[%s] Expected at least 2 Save Altars used, got %d" % [rep["profile"], int(rep.get("altars_used", 0))])
		if int(rep.get("skills_cast", 0)) < 4:
			errors.append("[%s] Expected >= 4 magic skill casts, got %d" % [rep["profile"], int(rep.get("skills_cast", 0))])
		if int(rep.get("qte_successes", 0)) < 1:
			errors.append("[%s] Expected >= 1 Boss QTE Finisher, got %d" % [rep["profile"], int(rep.get("qte_successes", 0))])
		if int(rep.get("dodges", 0)) < 1:
			errors.append("[%s] Expected >= 1 telegraphed dodge (dash i-frame), got %d" % [rep["profile"], int(rep.get("dodges", 0))])

	return {
		"passed": errors.is_empty(),
		"errors": errors,
		"reports": reports,
	}
