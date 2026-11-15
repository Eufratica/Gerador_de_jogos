class_name CombatFsm
extends RefCounted
## Maquina de estados pura e deterministica de combate (Idle, Furia, DDTank, Boss QTE, Revive e Prestigio).
## Zero dependencia de Node, SceneTree, UI ou rede.

const BigNumScript = preload("res://src/core/big_num.gd")
const IdleEconomyScript = preload("res://src/core/idle_economy.gd")
const TerrainScript = preload("res://src/core/terrain_heightmap.gd")
const BallisticsScript = preload("res://src/core/ddtank_ballistics.gd")

enum State {
	IDLE_AUTO = 0,
	RAGE_BERSERK = 1,
	DDTANK_AIM = 2,
	DDTANK_FLIGHT = 3,
	BOSS_QTE = 4,
	DEFEAT_REVIVE_OFFER = 5,
	PRESTIGE_RESET = 6,
}

const RAGE_DURATION_S: float = 10.0

var state: int = State.IDLE_AUTO
var economy: Dictionary = {}
var cfg_raw: Dictionary = {}
var rng: RefCounted = null
var terrain: TerrainScript = null

var wave: int = 1
var is_boss_active: bool = false
var is_titanic_boss: bool = false
var farming_same_stage_waves: bool = false

var enemy_hp: RefCounted = null
var enemy_max_hp: RefCounted = null
var enemy_armor: RefCounted = null
var enemy_gold: RefCounted = null
var enemy_posture: float = 0.0
var enemy_posture_max: float = 100.0

var player_hp_ratio: float = 1.0
var rage_ratio: float = 0.0
var rage_remaining_s: float = 0.0
var pow_charge: float = 0.0
var current_wind: float = 0.0
var boss_elapsed_s: float = 0.0
var boss_enrage_s: float = 45.0
var qte_started_ms: int = 0
var attack_accum_s: float = 0.0
var auto_rage: bool = true

var boss_hitbox: Dictionary = {}
var _shot_buf: Dictionary = {}
var _ballistic_res_buf: Dictionary = {}


func _init(p_cfg_raw: Dictionary, p_rng: RefCounted, now_utc_ms: int = 0) -> void:
	cfg_raw = p_cfg_raw
	rng = p_rng
	economy = IdleEconomyScript.create_initial_state(now_utc_ms)
	var bcfg: Dictionary = cfg_raw.get("ddtank_ballistics_config", {})
	var arena_w: float = float(bcfg.get("arena_logical_width", 1920.0))
	terrain = TerrainScript.new(arena_w, 180.0, 40.0)
	var empty_events: Array = []
	_spawn_current_encounter(empty_events)


func _spawn_current_encounter(events_out: Array) -> void:
	var stg: int = int(economy["current_stage"])
	var info: Dictionary = IdleEconomyScript.compute_enemy_params(stg, wave, cfg_raw)
	is_boss_active = bool(info["is_boss"])
	is_titanic_boss = bool(info["is_titanic"])
	enemy_max_hp = info["hp"]
	enemy_hp = (enemy_max_hp as RefCounted).duplicate_num()
	enemy_armor = info["armor"]
	enemy_gold = info["gold_drop"]
	enemy_posture_max = float(info["posture_max"])
	enemy_posture = enemy_posture_max
	boss_enrage_s = float(info["enrage_seconds"])
	boss_elapsed_s = 0.0
	player_hp_ratio = 1.0

	var bcfg: Dictionary = cfg_raw["ddtank_ballistics_config"]
	var bx_min: float = float(bcfg["boss_anchor_x_min"])
	var bx_max: float = float(bcfg["boss_anchor_x_max"])
	var boss_x: float = rng.range_float(bx_min, bx_max) if rng != null else 0.5 * (bx_min + bx_max)
	var ground_y: float = terrain.sample_height(boss_x)
	boss_hitbox = {
		"head_x": boss_x,
		"head_y": ground_y + 240.0,
		"head_radius": 42.0,
		"body_x": boss_x,
		"body_y": ground_y + 100.0,
		"body_radius": 92.0,
		"limb_x": boss_x - 85.0,
		"limb_y": ground_y + 95.0,
		"limb_radius": 38.0,
	}

	events_out.append({
		"type": "encounter_spawned",
		"stage": stg,
		"wave": wave,
		"is_boss": is_boss_active,
		"is_titanic": is_titanic_boss,
	})

	# Decisao 2A: Chefes Titanicos abrem automaticamente DDTANK_AIM com POW carregado.
	if is_titanic_boss:
		pow_charge = 1.0
		trigger_ddtank_aim(events_out)


func trigger_ddtank_aim(events_out: Array) -> Dictionary:
	if state != State.IDLE_AUTO and state != State.RAGE_BERSERK:
		return {"ok": false, "error": "Cannot enter DDTANK_AIM from current state"}
	if not is_boss_active or pow_charge < 1.0 - 1e-6:
		return {"ok": false, "error": "DDTANK_AIM requires active boss and full POW charge"}

	var bcfg: Dictionary = cfg_raw["ddtank_ballistics_config"]
	current_wind = rng.range_float(float(bcfg["wind_min"]), float(bcfg["wind_max"])) if rng != null else 0.0
	state = State.DDTANK_AIM
	events_out.append({"type": "ddtank_aim_started", "wind": current_wind})
	return {"ok": true, "wind": current_wind}


func release_ddtank_shot(angle_deg: float, power_norm: float, now_utc_ms: int, events_out: Array) -> Dictionary:
	if state != State.DDTANK_AIM:
		return {"ok": false, "error": "Not in DDTANK_AIM"}

	var bcfg: Dictionary = cfg_raw["ddtank_ballistics_config"]
	var px: float = float(bcfg["player_anchor_x"])
	var py: float = terrain.sample_height(px) + 32.0
	_shot_buf["origin_x"] = px
	_shot_buf["origin_y"] = py
	_shot_buf["angle_deg"] = angle_deg
	_shot_buf["power_norm"] = power_norm
	_shot_buf["wind"] = current_wind

	state = State.DDTANK_FLIGHT
	BallisticsScript.simulate_shot_into(_shot_buf, boss_hitbox, terrain, bcfg, _ballistic_res_buf)
	if not bool(_ballistic_res_buf.get("valid", false)):
		state = State.DDTANK_AIM
		return {"ok": false, "error": String(_ballistic_res_buf.get("error", "Invalid shot"))}

	pow_charge = 0.0
	var zone: int = int(_ballistic_res_buf["zone"])
	var dmg_mult: float = float(_ballistic_res_buf["damage_multiplier"])
	var posture_ratio: float = float(_ballistic_res_buf["posture_damage_ratio"])

	if bool(_ballistic_res_buf["carve_terrain"]):
		terrain.carve_crater(
			float(_ballistic_res_buf["impact_x"]),
			float(_ballistic_res_buf["impact_y"]),
			float(bcfg["crater_radius_px"])
		)
		events_out.append({
			"type": "crater_carved",
			"x": _ballistic_res_buf["impact_x"],
			"y": _ballistic_res_buf["impact_y"],
		})

	if dmg_mult > 0.0:
		var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, cfg_raw, now_utc_ms)
		var dmg: RefCounted = IdleEconomyScript.compute_hit_damage(stats, enemy_armor, true, dmg_mult * 4.0)
		enemy_hp = (enemy_hp as RefCounted).sub_clamped(dmg)
		if is_titanic_boss:
			enemy_posture = maxf(0.0, enemy_posture - (enemy_posture_max * posture_ratio))
		events_out.append({
			"type": "ddtank_hit",
			"zone": zone,
			"is_nuclear_pow": bool(_ballistic_res_buf["is_nuclear_pow"]),
			"damage": dmg,
		})

	if (enemy_hp as RefCounted).is_zero():
		state = State.IDLE_AUTO
		_handle_enemy_defeated(now_utc_ms, events_out)
		return {"ok": true, "outcome": _ballistic_res_buf.duplicate()}

	if zone == BallisticsScript.HitZone.HEAD_CORE or (is_titanic_boss and enemy_posture <= 0.0):
		state = State.BOSS_QTE
		qte_started_ms = now_utc_ms
		events_out.append({
			"type": "boss_qte_started",
			"window_ms": int(cfg_raw["enemy_stage_config"]["qte_window_ms"]),
		})
		return {"ok": true, "outcome": _ballistic_res_buf.duplicate()}

	state = State.IDLE_AUTO
	return {"ok": true, "outcome": _ballistic_res_buf.duplicate()}


func complete_boss_qte(success: bool, now_utc_ms: int, events_out: Array) -> Dictionary:
	if state != State.BOSS_QTE:
		return {"ok": false, "error": "Not in BOSS_QTE"}

	var window_ms: int = int(cfg_raw["enemy_stage_config"]["qte_window_ms"])
	var elapsed_ms: int = now_utc_ms - qte_started_ms
	var in_time: bool = (elapsed_ms >= 0 and elapsed_ms <= window_ms)

	enemy_posture = enemy_posture_max
	state = State.IDLE_AUTO

	if success and in_time:
		var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, cfg_raw, now_utc_ms)
		var finisher_dmg: RefCounted = IdleEconomyScript.compute_hit_damage(stats, enemy_armor, true, 12.0)
		enemy_hp = (enemy_hp as RefCounted).sub_clamped(finisher_dmg)
		events_out.append({"type": "qte_finisher_success", "damage": finisher_dmg})
		if (enemy_hp as RefCounted).is_zero():
			_handle_enemy_defeated(now_utc_ms, events_out)
		return {"ok": true, "finisher_applied": true}

	events_out.append({"type": "qte_finisher_missed"})
	return {"ok": true, "finisher_applied": false}


func resolve_defeat_revive(accepted: bool, reward_verified: bool, events_out: Array) -> Dictionary:
	if state != State.DEFEAT_REVIVE_OFFER:
		return {"ok": false, "error": "Not in DEFEAT_REVIVE_OFFER"}

	if accepted:
		if not (reward_verified or bool(economy["has_no_ads_pass"])):
			return {"ok": false, "error": "Revive reward not verified"}
		player_hp_ratio = 1.0
		rage_ratio = 0.0
		rage_remaining_s = RAGE_DURATION_S
		pow_charge = 1.0
		boss_elapsed_s = 0.0
		state = State.RAGE_BERSERK
		events_out.append({"type": "revived_in_rage_mode"})
		return {"ok": true, "revived": true}

	# Decisao 1A: recuar para farm automatico de waves normais no mesmo estagio.
	var waves_per_stage: int = int(cfg_raw["enemy_stage_config"]["waves_per_stage"])
	farming_same_stage_waves = true
	wave = maxi(1, waves_per_stage - 1)
	state = State.IDLE_AUTO
	_spawn_current_encounter(events_out)
	events_out.append({"type": "boss_retreat_to_same_stage_farm", "stage": economy["current_stage"]})
	return {"ok": true, "revived": false}


func challenge_boss(events_out: Array) -> Dictionary:
	if state != State.IDLE_AUTO and state != State.RAGE_BERSERK:
		return {"ok": false, "error": "Cannot challenge boss from current state"}
	var waves_per_stage: int = int(cfg_raw["enemy_stage_config"]["waves_per_stage"])
	farming_same_stage_waves = false
	wave = waves_per_stage
	_spawn_current_encounter(events_out)
	return {"ok": true}


func request_prestige(events_out: Array) -> Dictionary:
	if state != State.IDLE_AUTO and state != State.RAGE_BERSERK:
		return {"ok": false, "error": "Cannot prestige during active special/boss modal"}
	state = State.PRESTIGE_RESET
	var res: Dictionary = IdleEconomyScript.execute_prestige(economy, cfg_raw)
	if not bool(res["ok"]):
		state = State.IDLE_AUTO
		return res

	wave = 1
	farming_same_stage_waves = false
	rage_ratio = 0.0
	rage_remaining_s = 0.0
	pow_charge = 0.0
	attack_accum_s = 0.0
	terrain.reset_flat(180.0)
	state = State.IDLE_AUTO
	_spawn_current_encounter(events_out)
	events_out.append({"type": "prestige_completed", "gained_orbs": res["gained_orbs"]})
	return res


func _handle_enemy_defeated(now_utc_ms: int, events_out: Array) -> void:
	var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, cfg_raw, now_utc_ms)
	var gained_gold: RefCounted = (enemy_gold as RefCounted).mul(stats["gold_multiplier"])
	economy["gold"] = (economy["gold"] as RefCounted).add(gained_gold)
	economy["ki_energy"] = float(economy["ki_energy"]) + (12.0 if is_boss_active else 3.0)

	var gained_gems: int = 0
	if is_boss_active:
		gained_gems = 15 if is_titanic_boss else 5
		economy["gems"] = int(economy["gems"]) + gained_gems

	events_out.append({
		"type": "enemy_defeated",
		"stage": economy["current_stage"],
		"wave": wave,
		"is_boss": is_boss_active,
		"gold": gained_gold,
		"gems": gained_gems,
	})

	var waves_per_stage: int = int(cfg_raw["enemy_stage_config"]["waves_per_stage"])
	if is_boss_active:
		economy["current_stage"] = int(economy["current_stage"]) + 1
		economy["max_stage_reached"] = maxi(int(economy["max_stage_reached"]), int(economy["current_stage"]))
		economy["best_stage_lifetime"] = maxi(int(economy.get("best_stage_lifetime", 1)), int(economy["max_stage_reached"]))
		wave = 1
		farming_same_stage_waves = false
	elif farming_same_stage_waves:
		wave = maxi(1, waves_per_stage - 1)
	else:
		wave += 1

	_spawn_current_encounter(events_out)


func _try_activate_rage(events_out: Array) -> void:
	if rage_ratio >= 1.0 and auto_rage and state == State.IDLE_AUTO:
		rage_ratio = 0.0
		rage_remaining_s = RAGE_DURATION_S
		state = State.RAGE_BERSERK
		events_out.append({"type": "rage_started"})


func step(dt: float, now_utc_ms: int, events_out: Array) -> void:
	if dt <= 0.0 or is_nan(dt) or is_inf(dt):
		return
	if now_utc_ms > int(economy["last_seen_utc_ms"]):
		economy["last_seen_utc_ms"] = now_utc_ms

	if state != State.IDLE_AUTO and state != State.RAGE_BERSERK:
		return

	if state == State.RAGE_BERSERK:
		rage_remaining_s -= dt
		if rage_remaining_s <= 0.0:
			rage_remaining_s = 0.0
			state = State.IDLE_AUTO
			events_out.append({"type": "rage_ended"})

	_try_activate_rage(events_out)

	var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, cfg_raw, now_utc_ms)
	var atk_spd: float = maxf(0.1, float(stats["attack_speed"]))
	var atk_interval: float = 1.0 / atk_spd
	attack_accum_s += dt
	var hits_count: int = int(floor(attack_accum_s / atk_interval))

	if hits_count > 0:
		attack_accum_s -= float(hits_count) * atk_interval
		var is_rage: bool = (state == State.RAGE_BERSERK)
		var rage_mult: float = 2.0 if is_rage else 1.0
		var total_dmg: RefCounted = BigNumScript.zero()

		if hits_count <= 4 and rng != null:
			var crit_p: float = float(stats["crit_rate"])
			for _h in range(hits_count):
				var is_crit: bool = rng.roll_chance(crit_p)
				total_dmg = total_dmg.add(IdleEconomyScript.compute_hit_damage(stats, enemy_armor, is_crit, rage_mult))
		else:
			var crit_ev: float = 1.0 + float(stats["crit_rate"]) * (float(stats["crit_damage"]) - 1.0)
			total_dmg = IdleEconomyScript.compute_hit_damage(stats, enemy_armor, false, float(hits_count) * crit_ev * rage_mult)

		enemy_hp = (enemy_hp as RefCounted).sub_clamped(total_dmg)
		economy["ki_energy"] = float(economy["ki_energy"]) + (1.2 * float(hits_count))
		pow_charge = minf(1.0, pow_charge + 0.05 * float(hits_count))
		if not is_rage:
			rage_ratio = minf(1.0, rage_ratio + 0.04 * float(hits_count))

		_try_activate_rage(events_out)

		if (enemy_hp as RefCounted).is_zero():
			_handle_enemy_defeated(now_utc_ms, events_out)
			return

	if is_boss_active:
		boss_elapsed_s += dt
		if state != State.RAGE_BERSERK:
			player_hp_ratio = maxf(0.0, player_hp_ratio - (dt / maxf(1.0, boss_enrage_s)))
		if player_hp_ratio <= 0.0 or boss_elapsed_s >= boss_enrage_s:
			state = State.DEFEAT_REVIVE_OFFER
			events_out.append({"type": "defeat_revive_offered", "stage": economy["current_stage"]})
