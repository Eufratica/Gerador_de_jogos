class_name BalanceVerifier
extends RefCounted
## Simulador headless e auditor fail-closed de balanco economico (72h x 3 perfis).
## Detecta progress walls, soft-locks, overflow de BigNum e quebras de Gacha/Offline/Prestigio.

const BigNumScript = preload("res://src/core/big_num.gd")
const SeededRngScript = preload("res://src/core/seeded_rng.gd")
const IdleEconomyScript = preload("res://src/core/idle_economy.gd")
const CombatFsmScript = preload("res://src/core/combat_fsm.gd")
const BallisticsScript = preload("res://src/core/ddtank_ballistics.gd")

const SIM_SECONDS: float = 259200.0 # 72 horas
const SIM_DT: float = 2.0
const MAX_STALL_SECONDS: float = 600.0
const MAX_PRESTIGE_RECOVERY_SECONDS: float = 900.0


static func _buy_greedy_upgrades(eco: Dictionary, cfg_raw: Dictionary) -> void:
	var gold: RefCounted = eco["gold"]
	if gold == null or gold.is_zero():
		return
	var curves: Dictionary = cfg_raw["upgrade_curves"]
	var priority: PackedStringArray = ["attack", "attack_speed", "crit_rate", "crit_damage", "penetration"]
	for _round in range(6):
		var bought_any: bool = false
		for key in priority:
			var cur_lv: int = int(eco["levels"][key])
			if key == "attack_speed" and IdleEconomyScript.compute_raw_upgrade_float(curves[key], cur_lv) >= 4.0 - 1e-6:
				continue
			# Mantem attack como motor principal (~60%) e auxiliares balanceados
			if key != "attack" and cur_lv > int(eco["levels"]["attack"]) * 0.7:
				continue
			var res: Dictionary = IdleEconomyScript.buy_upgrade(eco, key, 1, cfg_raw)
			if bool(res["ok"]):
				bought_any = true
		if not bought_any:
			break


static func _upgrade_highest_ki(eco: Dictionary, cfg_raw: Dictionary) -> void:
	var cur_tier: int = int(eco["active_ki_tier"])
	for tier in range(5, cur_tier, -1):
		if IdleEconomyScript.can_activate_ki_tier(eco, tier, cfg_raw):
			IdleEconomyScript.activate_ki_tier(eco, tier, cfg_raw)
			break


static func _simulate_profile(profile_name: String, cfg_raw: Dictionary, seed_val: int) -> Dictionary:
	var rng := SeededRngScript.new(seed_val)
	var base_ms: int = 1_700_000_000_000
	var fsm := CombatFsmScript.new(cfg_raw, rng, base_ms)
	var events: Array = []

	var bcfg: Dictionary = cfg_raw["ddtank_ballistics_config"]
	var use_ads: bool = (profile_name != "F2P_PURE")
	var buy_no_ads_at_s: float = 86400.0 if profile_name == "NO_ADS_PASS" else -1.0

	var sim_t: float = 0.0
	var last_progress_t: float = 0.0
	var max_stall_s: float = 0.0
	var run_best_stage: int = 1
	var best_stage_ever: int = 1
	var prestige_count: int = 0
	var prestige_started_t: float = -1.0
	var max_recovery_s: float = 0.0
	var farm_after_loss_s: float = 0.0
	var revive_used_this_boss: bool = false
	var last_day_idx: int = -1
	var last_boost_hour: int = -1
	var wave_start_t: float = 0.0
	var max_wave_s: float = 0.0

	while sim_t < SIM_SECONDS:
		var now_ms: int = base_ms + int(sim_t * 1000.0)
		var day_idx: int = int(floor(sim_t / 86400.0))

		if buy_no_ads_at_s >= 0.0 and sim_t >= buy_no_ads_at_s and not bool(fsm.economy["has_no_ads_pass"]):
			fsm.economy["has_no_ads_pass"] = true

		# Rotina diaria de Rewarded Ads / No-Ads Pass
		if (use_ads or bool(fsm.economy["has_no_ads_pass"])) and day_idx > last_day_idx:
			last_day_idx = day_idx
			for _ad_pull in range(3):
				IdleEconomyScript.execute_gacha_pull(
					fsm.economy, "weapons_mythic_v1", 10, true, true, rng, cfg_raw, now_ms
				)
			# Bau do Dragao 3x (8h offline simulado uma vez por dia)
			if sim_t > 0.0:
				var st_snap: Dictionary = IdleEconomyScript.compute_player_stats(fsm.economy, cfg_raw, now_ms)
				var gps: RefCounted = (fsm.enemy_gold as RefCounted).mul(st_snap["gold_multiplier"]).mul_float(0.2)
				var prev_seen: int = int(fsm.economy["last_seen_utc_ms"])
				fsm.economy["last_seen_utc_ms"] = now_ms - 28_800_000
				var off_res: Dictionary = IdleEconomyScript.compute_offline_reward(fsm.economy, gps, cfg_raw, now_ms, true, true)
				fsm.economy["last_seen_utc_ms"] = prev_seen
				if bool(off_res["ok"]):
					fsm.economy["gold"] = (fsm.economy["gold"] as RefCounted).add(off_res["gold"])

		# Boost Furia dos Deuses (20 min) a cada 3h para perfis com ads/pass
		var boost_slot: int = int(floor(sim_t / 10800.0))
		if (use_ads or bool(fsm.economy["has_no_ads_pass"])) and boost_slot > last_boost_hour:
			last_boost_hour = boost_slot
			fsm.economy["fury_boost_until_ms"] = now_ms + 1_200_000

		# Gasto de gemas acumuladas em Gacha 10x
		while int(fsm.economy["gems"]) >= 450:
			IdleEconomyScript.execute_gacha_pull(fsm.economy, "weapons_mythic_v1", 10, false, false, rng, cfg_raw, now_ms)

		events.clear()
		fsm.step(SIM_DT, now_ms, events)

		# Checagem de integridade BigNum
		if not bool((fsm.economy["gold"] as RefCounted).get("valid")) or not bool((fsm.enemy_hp as RefCounted).get("valid")):
			return {"ok": false, "profile": profile_name, "error": "Invalid BigNum encountered at t=%.1f" % sim_t}

		# Resolucao de estados interativos (DDTank, QTE, Revive)
		if fsm.state == CombatFsmScript.State.DDTANK_AIM:
			var px: float = float(bcfg["player_anchor_x"])
			var py: float = fsm.terrain.sample_height(px) + 32.0
			var sol: Dictionary = BallisticsScript.solve_aim_for_head(px, py, fsm.boss_hitbox, fsm.terrain, fsm.current_wind, bcfg)
			var ang: float = float(sol.get("angle_deg", 45.0))
			var pwr: float = float(sol.get("power_norm", 0.7))
			if not use_ads and not bool(fsm.economy["has_no_ads_pass"]) and rng.roll_chance(0.45):
				ang = clampf(ang - 4.0, float(bcfg["angle_min_deg"]), float(bcfg["angle_max_deg"]))
			fsm.release_ddtank_shot(ang, pwr, now_ms, events)

		if fsm.state == CombatFsmScript.State.BOSS_QTE:
			fsm.complete_boss_qte(true, now_ms + 400, events)

		if fsm.state == CombatFsmScript.State.DEFEAT_REVIVE_OFFER:
			if (use_ads or bool(fsm.economy["has_no_ads_pass"])) and not revive_used_this_boss:
				revive_used_this_boss = true
				fsm.resolve_defeat_revive(true, true, events)
			else:
				revive_used_this_boss = false
				fsm.resolve_defeat_revive(false, false, events)
				farm_after_loss_s = 0.0

		for ev in events:
			var etype: String = String(ev.get("type", ""))
			if etype == "enemy_defeated":
				if not bool(ev.get("is_boss", false)):
					var w_dur: float = sim_t - wave_start_t
					if not fsm.farming_same_stage_waves:
						max_wave_s = maxf(max_wave_s, w_dur)
				else:
					revive_used_this_boss = false
				wave_start_t = sim_t

		_buy_greedy_upgrades(fsm.economy, cfg_raw)
		_upgrade_highest_ki(fsm.economy, cfg_raw)

		if fsm.farming_same_stage_waves:
			farm_after_loss_s += SIM_DT
			if farm_after_loss_s >= 24.0:
				farm_after_loss_s = 0.0
				fsm.challenge_boss(events)

		var cur_stage: int = int(fsm.economy["current_stage"])
		var run_max: int = int(fsm.economy["max_stage_reached"])
		if cur_stage > run_best_stage:
			run_best_stage = cur_stage
			last_progress_t = sim_t
		elif run_max > run_best_stage:
			run_best_stage = run_max
			last_progress_t = sim_t
		best_stage_ever = maxi(best_stage_ever, run_best_stage)

		if prestige_started_t >= 0.0 and cur_stage >= 50:
			max_recovery_s = maxf(max_recovery_s, sim_t - prestige_started_t)
			prestige_started_t = -1.0

		var cur_stall: float = sim_t - last_progress_t
		# Executa Prestigio quando atingir >= 50 na run atual e travar >= 90s (ou ao superar best_stage + 25)
		var p_preview: Dictionary = IdleEconomyScript.compute_prestige_preview(fsm.economy, cfg_raw)
		var push_target: int = 75 if prestige_count == 0 else best_stage_ever + 25
		if bool(p_preview["eligible"]) and (cur_stall >= 90.0 or cur_stage >= push_target):
			var p_res: Dictionary = fsm.request_prestige(events)
			if bool(p_res["ok"]):
				prestige_count += 1
				run_best_stage = 1
				prestige_started_t = sim_t
				last_progress_t = sim_t
				cur_stall = 0.0
				revive_used_this_boss = false

		max_stall_s = maxf(max_stall_s, cur_stall)
		sim_t += SIM_DT

	return {
		"ok": true,
		"profile": profile_name,
		"best_stage": best_stage_ever,
		"prestige_count": prestige_count,
		"max_stall_s": max_stall_s,
		"max_wave_s": max_wave_s,
		"max_recovery_s": max_recovery_s,
		"final_gold": fsm.economy["gold"],
		"soul_orbs": fsm.economy["soul_orbs"],
	}


static func run_full_audit(cfg_raw: Dictionary) -> Dictionary:
	var errors: PackedStringArray = PackedStringArray()
	var reports: Array[Dictionary] = []

	for idx in range(3):
		var profiles: Array[String] = ["F2P_PURE", "F2P_REWARDED", "NO_ADS_PASS"]
		var rep: Dictionary = _simulate_profile(profiles[idx], cfg_raw, 1001 + idx * 77)
		reports.append(rep)
		if not bool(rep["ok"]):
			errors.append(String(rep.get("error", "Unknown sim error")))
			continue
		if float(rep["max_stall_s"]) > MAX_STALL_SECONDS:
			errors.append("[%s] Progress wall: max_stall_s=%.1fs > %.1fs (best_stage=%d)" % [
				rep["profile"], rep["max_stall_s"], MAX_STALL_SECONDS, rep["best_stage"]
			])
		if int(rep["best_stage"]) < 50 or int(rep["prestige_count"]) < 1:
			errors.append("[%s] Failed to reach Prestige stage 50 in 72h (best_stage=%d, prestiges=%d)" % [
				rep["profile"], rep["best_stage"], rep["prestige_count"]
			])
		if float(rep["max_recovery_s"]) > MAX_PRESTIGE_RECOVERY_SECONDS:
			errors.append("[%s] Prestige recovery too slow: %.1fs > %.1fs" % [
				rep["profile"], rep["max_recovery_s"], MAX_PRESTIGE_RECOVERY_SECONDS
			])

	if reports.size() == 3 and bool(reports[0]["ok"]) and bool(reports[1]["ok"]) and bool(reports[2]["ok"]):
		if int(reports[1]["best_stage"]) < int(reports[0]["best_stage"]):
			errors.append("Monotonicity violation: F2P_REWARDED (%d) < F2P_PURE (%d)" % [reports[1]["best_stage"], reports[0]["best_stage"]])

	return {
		"passed": errors.is_empty(),
		"errors": errors,
		"reports": reports,
	}
