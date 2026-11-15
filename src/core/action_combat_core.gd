class_name ActionCombatCore
extends RefCounted
## Motor puro e deterministico de combate 2D lateral Dark Fantasy (estilo God of War).
## Suporta plataformas 2D, combos de 3 golpes, 4 poderes magicos ativos, i-frames,
## quebra de postura + QTE em Chefes Titanicos, Altares de Salvamento e Portais.
## Camada pura: zero dependencia de Node, SceneTree, UI, FileAccess ou rede.

const BigNumScript = preload("res://src/core/big_num.gd")
const IdleEconomyScript = preload("res://src/core/idle_economy.gd")

enum GamePhase {
	EXPLORING = 0,
	BOSS_QTE = 1,
	DEFEATED_REVIVE_OFFER = 2,
	CAMPAIGN_CLEARED = 3,
}

enum PlayerAction {
	IDLE = 0,
	MOVE = 1,
	JUMP_FALL = 2,
	DASH = 3,
	ATTACK_WINDUP = 4,
	ATTACK_ACTIVE = 5,
	ATTACK_RECOVERY = 6,
	CAST_MAGIC = 7,
}

enum EnemyAi {
	IDLE = 0,
	CHASE = 1,
	WINDUP = 2,
	STRIKE = 3,
	RECOVERY = 4,
	STAGGERED = 5,
	QTE_VULNERABLE = 6,
	DEAD = 7,
}

var balance_cfg: Dictionary = {}
var world_cfg: Dictionary = {}
var rng: RefCounted = null
var economy: Dictionary = {}

var current_world_id: String = ""
var current_room_id: String = ""
var current_room_def: Dictionary = {}
var cleared_rooms: Dictionary = {}
var defeated_boss_worlds: Dictionary = {}
var opened_chests: Dictionary = {}
var checkpoint: Dictionary = {}

var px: float = 180.0
var py: float = 0.0
var vx: float = 0.0
var vy: float = 0.0
var facing: int = 1
var on_ground: bool = true

var player_action: int = PlayerAction.IDLE
var action_timer_s: float = 0.0
var combo_index: int = 0
var combo_window_s: float = 0.0
var _hit_enemies_swing: Dictionary = {}

var dash_timer_s: float = 0.0
var dash_iframe_s: float = 0.0
var dash_cooldown_s: float = 0.0
var dash_dir: int = 1

var hp: RefCounted = null
var max_hp: RefCounted = null
var shield_hp: RefCounted = null
var mana: float = 100.0
var max_mana: float = 100.0
var rage_ratio: float = 0.0
var rage_remaining_s: float = 0.0
var skill_cooldowns: Array[float] = [0.0, 0.0, 0.0, 0.0]

var enemies: Array[Dictionary] = []
var projectiles: Array[Dictionary] = []

var game_phase: int = GamePhase.EXPLORING
var qte_target_idx: int = -1
var qte_started_ms: int = 0


func _init(p_balance_cfg: Dictionary, p_world_cfg: Dictionary, p_rng: RefCounted, now_utc_ms: int = 0) -> void:
	balance_cfg = p_balance_cfg
	world_cfg = p_world_cfg
	rng = p_rng
	economy = IdleEconomyScript.create_initial_state(now_utc_ms)

	var pc: Dictionary = world_cfg["player_combat"]
	max_mana = float(pc["base_max_mana"])
	mana = max_mana
	_recompute_max_hp(true)

	var worlds: Array = world_cfg["worlds"]
	var first_world: Dictionary = worlds[0]
	var wid: String = String(first_world["id"])
	var rid: String = String(first_world["entry_room_id"])
	var rdef: Dictionary = _find_room_def(wid, rid)
	checkpoint = {
		"world_id": wid,
		"room_id": rid,
		"x": float(rdef.get("default_spawn_x", 180.0)),
		"y": float(rdef.get("default_spawn_y", 0.0)),
		"altar_id": "",
	}
	var boot_events: Array = []
	enter_room(wid, rid, float(checkpoint["x"]), float(checkpoint["y"]), boot_events)


func _room_key(wid: String, rid: String) -> String:
	return "%s::%s" % [wid, rid]


func _find_world_def(wid: String) -> Dictionary:
	for w in world_cfg.get("worlds", []):
		if String(w.get("id", "")) == wid:
			return w
	return {}


func _find_room_def(wid: String, rid: String) -> Dictionary:
	var w: Dictionary = _find_world_def(wid)
	for r in w.get("rooms", []):
		if String(r.get("id", "")) == rid:
			return r
	return {}


func _recompute_max_hp(fill_full: bool = false) -> void:
	var pc: Dictionary = world_cfg["player_combat"]
	var base_hp: float = float(pc["base_max_hp"])
	var atk_lv: int = int(economy["levels"].get("attack", 0))
	var orbs_f: float = (economy["soul_orbs"] as RefCounted).to_approx_float()
	var scale_f: float = 1.0 + (0.12 * float(atk_lv)) + (0.05 * orbs_f)
	var prev_max: RefCounted = max_hp if max_hp != null else BigNumScript.from_float(base_hp)
	max_hp = BigNumScript.from_float(base_hp * scale_f)
	if fill_full or hp == null:
		hp = max_hp.duplicate_num()
		shield_hp = BigNumScript.zero()
	elif max_hp.cmp(prev_max) > 0:
		var delta: RefCounted = max_hp.sub_clamped(prev_max)
		hp = hp.add(delta)
		if hp.cmp(max_hp) > 0:
			hp = max_hp.duplicate_num()


func is_rage_active() -> bool:
	return rage_remaining_s > 0.0


func is_invulnerable() -> bool:
	return dash_iframe_s > 0.0


func is_room_cleared() -> bool:
	for e in enemies:
		if int(e["ai_state"]) != EnemyAi.DEAD:
			return false
	return true


func get_room_enemies_alive() -> int:
	var count: int = 0
	for e in enemies:
		if int(e["ai_state"]) != EnemyAi.DEAD:
			count += 1
	return count


func get_portal_state(portal_def: Dictionary) -> Dictionary:
	var req_clear: bool = bool(portal_def.get("requires_room_cleared", false))
	var req_boss: bool = bool(portal_def.get("requires_boss_defeated", false))
	var unlocked: bool = true
	var reason: String = ""
	if req_clear and not is_room_cleared():
		unlocked = false
		reason = "Defeat room enemies first"
	elif req_boss and not defeated_boss_worlds.has(current_world_id):
		unlocked = false
		reason = "Defeat World Boss first"
	return {"unlocked": unlocked, "reason": reason}


func enter_room(wid: String, rid: String, spawn_x: float, spawn_y: float, events_out: Array) -> bool:
	var rdef: Dictionary = _find_room_def(wid, rid)
	if rdef.is_empty():
		return false

	current_world_id = wid
	current_room_id = rid
	current_room_def = rdef

	var rw: float = float(rdef["width"])
	var half_w: float = float(world_cfg["player_combat"]["player_half_width"])
	px = clampf(spawn_x, half_w, rw - half_w)
	py = maxf(0.0, spawn_y)
	vx = 0.0
	vy = 0.0
	on_ground = (py <= 0.0)
	player_action = PlayerAction.IDLE
	action_timer_s = 0.0
	combo_index = 0
	combo_window_s = 0.0
	dash_timer_s = 0.0
	dash_iframe_s = 0.0
	projectiles.clear()
	enemies.clear()
	qte_target_idx = -1

	var rkey: String = _room_key(wid, rid)
	var already_cleared: bool = cleared_rooms.has(rkey)
	if not already_cleared:
		_spawn_room_enemies(rdef)

	events_out.append({
		"type": "room_entered",
		"world_id": wid,
		"room_id": rid,
		"cleared": already_cleared,
	})
	return true


func _spawn_room_enemies(rdef: Dictionary) -> void:
	var arch_map: Dictionary = world_cfg["enemy_archetypes"]
	var scale: float = float(rdef.get("power_scale", 1.0))
	var enc_list: Array = rdef.get("encounters", [])
	for idx in range(enc_list.size()):
		var enc: Dictionary = enc_list[idx]
		var aid: String = String(enc["archetype"])
		var adef: Dictionary = arch_map[aid]
		var is_boss: bool = bool(adef.get("is_boss", false))
		var ehp: RefCounted = BigNumScript.from_float(float(adef["hp"]) * scale)
		var earm: RefCounted = BigNumScript.from_float(float(adef.get("armor", 0.0)) * scale)
		var edmg: RefCounted = BigNumScript.from_float(float(adef["dmg"]) * scale)
		var egold: RefCounted = BigNumScript.from_float(float(adef["gold"]) * scale)
		var pmax: float = float(adef["posture_max"])
		enemies.append({
			"id": "%s_%d" % [aid, idx],
			"archetype": aid,
			"x": float(enc["x"]),
			"y": float(enc.get("y", 0.0)),
			"vx": 0.0,
			"hp": ehp,
			"max_hp": ehp.duplicate_num(),
			"armor": earm,
			"dmg": edmg,
			"gold": egold,
			"gems": int(adef.get("gems", 0)),
			"posture": pmax,
			"posture_max": pmax,
			"is_boss": is_boss,
			"is_ranged": bool(adef.get("is_ranged", false)),
			"projectile_speed": float(adef.get("projectile_speed", 0.0)),
			"speed": float(adef["speed"]),
			"attack_range": float(adef["attack_range"]),
			"windup_s": float(adef["windup_s"]),
			"strike_s": float(adef["strike_s"]),
			"recovery_s": float(adef["recovery_s"]),
			"ai_state": EnemyAi.IDLE,
			"ai_timer_s": 0.0,
			"facing": -1,
			"hit_player_this_strike": false,
			"burn_s": 0.0,
			"burn_dps": BigNumScript.zero(),
			"freeze_s": 0.0,
			"shock_s": 0.0,
			"shock_dps": BigNumScript.zero(),
		})


func buy_forge_upgrade(stat_key: String, count: int, events_out: Array) -> Dictionary:
	var res: Dictionary = IdleEconomyScript.buy_upgrade(economy, stat_key, count, balance_cfg)
	if bool(res.get("ok", false)):
		_recompute_max_hp(false)
		events_out.append({
			"type": "forge_upgraded",
			"stat": stat_key,
			"new_level": res["new_level"],
		})
	return res


func try_interact(now_utc_ms: int, events_out: Array) -> Dictionary:
	# 1. Altar de Salvamento (cura, cria checkpoint de salvamento local/Supabase, sinaliza Forja)
	for a in current_room_def.get("altars", []):
		var ax: float = float(a["x"])
		var ay: float = float(a.get("y", 0.0))
		var ar: float = float(a.get("radius", 110.0))
		if absf(px - ax) <= ar and absf(py - ay) <= 130.0:
			hp = max_hp.duplicate_num()
			mana = max_mana
			shield_hp = BigNumScript.zero()
			checkpoint = {
				"world_id": current_world_id,
				"room_id": current_room_id,
				"x": ax,
				"y": ay,
				"altar_id": String(a["id"]),
			}
			var snap: Dictionary = export_checkpoint_snapshot(now_utc_ms)
			events_out.append({
				"type": "altar_activated",
				"altar_id": a["id"],
				"world_id": current_world_id,
				"room_id": current_room_id,
				"snapshot": snap,
			})
			return {"ok": true, "kind": "ALTAR", "altar_id": a["id"], "snapshot": snap}

	# 2. Baus de Tesouro
	for c in current_room_def.get("chests", []):
		var cid: String = String(c["id"])
		if opened_chests.has(cid):
			continue
		if absf(px - float(c["x"])) <= 95.0 and absf(py - float(c.get("y", 0.0))) <= 120.0:
			opened_chests[cid] = true
			var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, balance_cfg, now_utc_ms)
			var g_add: RefCounted = BigNumScript.from_float(float(c["gold"])).mul(stats["gold_multiplier"])
			economy["gold"] = (economy["gold"] as RefCounted).add(g_add)
			var gems_add: int = int(c.get("gems", 0))
			economy["gems"] = int(economy["gems"]) + gems_add
			events_out.append({"type": "chest_opened", "chest_id": cid, "gold": g_add, "gems": gems_add})
			return {"ok": true, "kind": "CHEST", "chest_id": cid, "gold": g_add, "gems": gems_add}

	# 3. Portais entre Salas / Mundos
	for p in current_room_def.get("portals", []):
		var pr: float = float(p.get("radius", 95.0))
		if absf(px - float(p["x"])) <= pr and absf(py - float(p.get("y", 0.0))) <= 140.0:
			var pstate: Dictionary = get_portal_state(p)
			if not bool(pstate["unlocked"]):
				events_out.append({"type": "portal_locked", "portal_id": p["id"], "reason": pstate["reason"]})
				return {"ok": false, "kind": "PORTAL", "error": pstate["reason"]}
			var entered: bool = enter_room(
				String(p["target_world_id"]),
				String(p["target_room_id"]),
				float(p["target_spawn_x"]),
				float(p["target_spawn_y"]),
				events_out
			)
			return {"ok": entered, "kind": "PORTAL", "portal_id": p["id"]}

	return {"ok": false, "kind": "NONE", "error": "Nothing interactable nearby"}


func step(dt: float, input_cmd: Dictionary, now_utc_ms: int, events_out: Array) -> void:
	if dt <= 0.0 or is_nan(dt) or is_inf(dt):
		return
	if now_utc_ms > int(economy["last_seen_utc_ms"]):
		economy["last_seen_utc_ms"] = now_utc_ms

	if game_phase == GamePhase.DEFEATED_REVIVE_OFFER or game_phase == GamePhase.CAMPAIGN_CLEARED:
		return

	if game_phase == GamePhase.BOSS_QTE:
		_step_qte_window(input_cmd, now_utc_ms, events_out)
		return

	_tick_player_timers(dt, events_out)
	_handle_player_commands(dt, input_cmd, now_utc_ms, events_out)
	_integrate_player_physics(dt)
	_step_enemies_and_dots(dt, now_utc_ms, events_out)
	_step_projectiles(dt, events_out)
	_check_room_completion(events_out)

	if hp.is_zero() and game_phase == GamePhase.EXPLORING:
		game_phase = GamePhase.DEFEATED_REVIVE_OFFER
		events_out.append({
			"type": "defeat_revive_offered",
			"world_id": current_world_id,
			"room_id": current_room_id,
		})


func _step_qte_window(input_cmd: Dictionary, now_utc_ms: int, events_out: Array) -> void:
	var window_ms: int = int(world_cfg["player_combat"]["qte_window_ms"])
	var elapsed_ms: int = now_utc_ms - qte_started_ms
	if bool(input_cmd.get("qte_pressed", false)) and elapsed_ms <= window_ms:
		if qte_target_idx >= 0 and qte_target_idx < enemies.size():
			var boss: Dictionary = enemies[qte_target_idx]
			var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, balance_cfg, now_utc_ms)
			var qte_mult: float = float(world_cfg["player_combat"]["qte_finisher_mult"])
			var dmg: RefCounted = IdleEconomyScript.compute_hit_damage(stats, boss["armor"], true, qte_mult)
			boss["hp"] = (boss["hp"] as RefCounted).sub_clamped(dmg)
			events_out.append({
				"type": "boss_qte_finisher",
				"success": true,
				"enemy_id": boss["id"],
				"damage": dmg,
			})
			if (boss["hp"] as RefCounted).is_zero():
				_kill_enemy(boss, now_utc_ms, events_out)
			else:
				boss["posture"] = float(boss["posture_max"]) * 0.55
				boss["ai_state"] = EnemyAi.RECOVERY
				boss["ai_timer_s"] = 0.65
		qte_target_idx = -1
		game_phase = GamePhase.EXPLORING
		_check_room_completion(events_out)
		return

	if elapsed_ms > window_ms:
		if qte_target_idx >= 0 and qte_target_idx < enemies.size():
			var boss: Dictionary = enemies[qte_target_idx]
			if int(boss["ai_state"]) != EnemyAi.DEAD:
				boss["posture"] = float(boss["posture_max"]) * 0.60
				boss["ai_state"] = EnemyAi.RECOVERY
				boss["ai_timer_s"] = 0.45
		events_out.append({"type": "boss_qte_timeout"})
		qte_target_idx = -1
		game_phase = GamePhase.EXPLORING


func _tick_player_timers(dt: float, events_out: Array) -> void:
	var pc: Dictionary = world_cfg["player_combat"]
	mana = minf(max_mana, mana + float(pc["mana_regen_per_s"]) * dt)
	dash_cooldown_s = maxf(0.0, dash_cooldown_s - dt)
	dash_iframe_s = maxf(0.0, dash_iframe_s - dt)
	if combo_window_s > 0.0:
		combo_window_s = maxf(0.0, combo_window_s - dt)
		if combo_window_s == 0.0:
			combo_index = 0

	for i in range(4):
		skill_cooldowns[i] = maxf(0.0, skill_cooldowns[i] - dt)

	if rage_remaining_s > 0.0:
		rage_remaining_s = maxf(0.0, rage_remaining_s - dt)
		if rage_remaining_s == 0.0:
			events_out.append({"type": "rage_ended"})


func _handle_player_commands(dt: float, input_cmd: Dictionary, now_utc_ms: int, events_out: Array) -> void:
	var pc: Dictionary = world_cfg["player_combat"]

	if bool(input_cmd.get("rage_pressed", false)) and rage_ratio >= 1.0 and not is_rage_active():
		rage_ratio = 0.0
		rage_remaining_s = float(pc["rage_duration_s"])
		events_out.append({"type": "rage_started"})

	if bool(input_cmd.get("interact_pressed", false)):
		try_interact(now_utc_ms, events_out)

	# Dash com cancelamento de ataque (dash cancel estilo Dead Cells / GoW)
	if bool(input_cmd.get("dash_pressed", false)) and dash_cooldown_s <= 0.0 and player_action != PlayerAction.DASH:
		var move_dir: float = float(input_cmd.get("move_x", 0.0))
		if absf(move_dir) > 0.1:
			facing = 1 if move_dir > 0.0 else -1
		dash_dir = facing
		player_action = PlayerAction.DASH
		dash_timer_s = float(pc["dash_duration_s"])
		dash_iframe_s = float(pc["dash_iframe_s"])
		dash_cooldown_s = float(pc["dash_cooldown_s"])
		vx = float(dash_dir) * float(pc["dash_speed"])
		vy = 0.0
		events_out.append({"type": "player_dashed", "dir": dash_dir})
		return

	if player_action == PlayerAction.DASH:
		dash_timer_s -= dt
		vx = float(dash_dir) * float(pc["dash_speed"])
		if dash_timer_s <= 0.0:
			player_action = PlayerAction.IDLE if on_ground else PlayerAction.JUMP_FALL
			vx = 0.0
		return

	# Poder magico (4 skills ativas)
	var skill_idx: int = int(input_cmd.get("cast_skill_idx", -1))
	if skill_idx >= 0 and skill_idx < 4 and _can_interrupt_for_skill():
		if _try_cast_magic_skill(skill_idx, now_utc_ms, events_out):
			return

	# Maquina de estados de combo / cast
	if player_action == PlayerAction.ATTACK_WINDUP or player_action == PlayerAction.ATTACK_ACTIVE or player_action == PlayerAction.ATTACK_RECOVERY or player_action == PlayerAction.CAST_MAGIC:
		_step_attack_or_cast(dt, now_utc_ms, events_out)
		return

	# Movimentacao normal e pulo
	var move_x: float = clampf(float(input_cmd.get("move_x", 0.0)), -1.0, 1.0)
	if absf(move_x) > 0.05:
		facing = 1 if move_x > 0.0 else -1
		vx = move_x * float(pc["move_speed"]) * (float(pc["rage_spd_mult"]) if is_rage_active() else 1.0)
	else:
		vx = 0.0

	if bool(input_cmd.get("jump_pressed", false)) and on_ground:
		vy = float(pc["jump_velocity"])
		on_ground = false

	if bool(input_cmd.get("attack_pressed", false)):
		_start_combo_attack(events_out)
		return

	player_action = PlayerAction.MOVE if (on_ground and absf(vx) > 1.0) else (PlayerAction.IDLE if on_ground else PlayerAction.JUMP_FALL)


func _can_interrupt_for_skill() -> bool:
	return player_action == PlayerAction.IDLE or player_action == PlayerAction.MOVE or player_action == PlayerAction.JUMP_FALL or player_action == PlayerAction.ATTACK_RECOVERY


func _start_combo_attack(events_out: Array) -> void:
	var combos: Array = world_cfg["player_combat"]["combo_steps"]
	var step_idx: int = clampi(combo_index, 0, combos.size() - 1)
	var step_def: Dictionary = combos[step_idx]
	player_action = PlayerAction.ATTACK_WINDUP
	action_timer_s = float(step_def["windup_s"]) / (1.3 if is_rage_active() else 1.0)
	_hit_enemies_swing.clear()
	vx = float(facing) * float(step_def.get("lunge_vx", 0.0))
	events_out.append({"type": "attack_started", "combo_step": step_idx, "id": step_def["id"]})


func _step_attack_or_cast(dt: float, now_utc_ms: int, events_out: Array) -> void:
	action_timer_s -= dt
	if player_action == PlayerAction.ATTACK_ACTIVE:
		_apply_melee_combo_hits(now_utc_ms, events_out)

	if action_timer_s > 0.0:
		return

	if player_action == PlayerAction.CAST_MAGIC:
		player_action = PlayerAction.IDLE if on_ground else PlayerAction.JUMP_FALL
		return

	var combos: Array = world_cfg["player_combat"]["combo_steps"]
	var step_def: Dictionary = combos[clampi(combo_index, 0, combos.size() - 1)]
	if player_action == PlayerAction.ATTACK_WINDUP:
		player_action = PlayerAction.ATTACK_ACTIVE
		action_timer_s = float(step_def["active_s"])
		_apply_melee_combo_hits(now_utc_ms, events_out)
	elif player_action == PlayerAction.ATTACK_ACTIVE:
		player_action = PlayerAction.ATTACK_RECOVERY
		vx = 0.0
		action_timer_s = float(step_def["recovery_s"]) / (1.3 if is_rage_active() else 1.0)
	else:
		combo_window_s = float(step_def.get("combo_window_s", 0.0))
		combo_index = (combo_index + 1) % combos.size() if combo_window_s > 0.0 else 0
		player_action = PlayerAction.IDLE if on_ground else PlayerAction.JUMP_FALL


func _apply_melee_combo_hits(now_utc_ms: int, events_out: Array) -> void:
	var pc: Dictionary = world_cfg["player_combat"]
	var step_def: Dictionary = pc["combo_steps"][clampi(combo_index, 0, (pc["combo_steps"] as Array).size() - 1)]
	var reach_x: float = float(step_def["reach_x"])
	var reach_y: float = float(step_def["reach_y"])
	var dmg_mult: float = float(step_def["damage_mult"]) * (float(pc["rage_dmg_mult"]) if is_rage_active() else 1.0)
	var posture_dmg: float = float(step_def["posture_dmg"]) * (1.5 if is_rage_active() else 1.0)

	for idx in range(enemies.size()):
		if _hit_enemies_swing.has(idx):
			continue
		var e: Dictionary = enemies[idx]
		if int(e["ai_state"]) == EnemyAi.DEAD:
			continue
		var dx: float = float(e["x"]) - px
		if (facing > 0 and dx < -25.0) or (facing < 0 and dx > 25.0) or absf(dx) > reach_x:
			continue
		if absf(float(e["y"]) - py) > reach_y:
			continue

		_hit_enemies_swing[idx] = true
		mana = minf(max_mana, mana + float(pc["mana_on_hit"]))
		if not is_rage_active():
			rage_ratio = minf(1.0, rage_ratio + float(pc["rage_on_hit"]))
		_damage_enemy(idx, dmg_mult, posture_dmg, "", 0.0, 0.0, now_utc_ms, events_out)


func _try_cast_magic_skill(skill_idx: int, now_utc_ms: int, events_out: Array) -> bool:
	var pc: Dictionary = world_cfg["player_combat"]
	var skill: Dictionary = pc["magic_powers"][skill_idx]
	var cost: float = float(skill["mana_cost"])
	if skill_cooldowns[skill_idx] > 0.0 or mana < cost:
		return false

	mana -= cost
	skill_cooldowns[skill_idx] = float(skill["cooldown_s"])
	player_action = PlayerAction.CAST_MAGIC
	action_timer_s = 0.22
	vx = 0.0

	var shield_r: float = float(skill.get("shield_ratio", 0.0))
	if shield_r > 0.0:
		shield_hp = max_hp.mul_float(shield_r)

	var delivery: String = String(skill["delivery"])
	var center_x: float = px
	var center_y: float = py
	var radius: float = float(skill["radius"])
	var range_x: float = float(skill.get("range_x", 0.0))
	if delivery == "HOMING_STRIKE":
		var tgt: Dictionary = _find_nearest_enemy(px, py, range_x)
		if not tgt.is_empty():
			center_x = float(tgt["x"])
			center_y = float(tgt["y"])
		else:
			center_x = px + float(facing) * minf(range_x * 0.5, 280.0)
	elif delivery == "CONE_FRONT":
		center_x = px + float(facing) * (range_x * 0.5)
		radius = maxf(radius, range_x * 0.55)

	var dmg_mult: float = float(skill["damage_mult"]) * (float(pc["rage_dmg_mult"]) if is_rage_active() else 1.0)
	var posture_dmg: float = float(skill["posture_dmg"])
	var status: String = String(skill.get("status", ""))
	var st_dur: float = float(skill.get("status_duration_s", 0.0))
	var st_dps: float = float(skill.get("status_dps_mult", 0.0))

	events_out.append({
		"type": "magic_cast",
		"skill_id": skill["id"],
		"skill_idx": skill_idx,
		"x": center_x,
		"y": center_y,
	})

	for idx in range(enemies.size()):
		var e: Dictionary = enemies[idx]
		if int(e["ai_state"]) == EnemyAi.DEAD:
			continue
		if absf(float(e["x"]) - center_x) <= radius and absf(float(e["y"]) - center_y) <= (radius + 60.0):
			_damage_enemy(idx, dmg_mult, posture_dmg, status, st_dur, st_dps, now_utc_ms, events_out)

	return true


func _find_nearest_enemy(ox: float, oy: float, max_dist: float) -> Dictionary:
	var best: Dictionary = {}
	var best_d: float = max_dist + 1.0
	for e in enemies:
		if int(e["ai_state"]) == EnemyAi.DEAD:
			continue
		var d: float = absf(float(e["x"]) - ox) + absf(float(e["y"]) - oy) * 0.5
		if d <= max_dist and d < best_d:
			best_d = d
			best = e
	return best


func _damage_enemy(
	idx: int,
	dmg_mult: float,
	posture_dmg: float,
	status: String,
	status_dur_s: float,
	status_dps_mult: float,
	now_utc_ms: int,
	events_out: Array
) -> void:
	var e: Dictionary = enemies[idx]
	if int(e["ai_state"]) == EnemyAi.DEAD:
		return

	var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, balance_cfg, now_utc_ms)
	var is_crit: bool = rng.roll_chance(float(stats["crit_rate"])) if rng != null else false
	var dmg: RefCounted = IdleEconomyScript.compute_hit_damage(stats, e["armor"], is_crit, dmg_mult)
	e["hp"] = (e["hp"] as RefCounted).sub_clamped(dmg)

	var is_boss: bool = bool(e["is_boss"])
	e["posture"] = maxf(0.0, float(e["posture"]) - posture_dmg)

	if status == "BURN" and status_dur_s > 0.0:
		e["burn_s"] = status_dur_s
		e["burn_dps"] = IdleEconomyScript.compute_hit_damage(stats, e["armor"], false, status_dps_mult)
	elif status == "FREEZE" and status_dur_s > 0.0:
		e["freeze_s"] = status_dur_s
	elif status == "SHOCK" and status_dur_s > 0.0:
		e["shock_s"] = status_dur_s
		e["shock_dps"] = IdleEconomyScript.compute_hit_damage(stats, e["armor"], false, status_dps_mult)
	elif status == "STAGGER" and not is_boss:
		e["ai_state"] = EnemyAi.STAGGERED
		e["ai_timer_s"] = maxf(float(e["ai_timer_s"]), status_dur_s)

	events_out.append({
		"type": "enemy_hit",
		"enemy_id": e["id"],
		"damage": dmg,
		"crit": is_crit,
		"status": status,
	})

	if (e["hp"] as RefCounted).is_zero():
		_kill_enemy(e, now_utc_ms, events_out)
		return

	if float(e["posture"]) <= 0.0:
		if is_boss and game_phase == GamePhase.EXPLORING:
			e["ai_state"] = EnemyAi.QTE_VULNERABLE
			game_phase = GamePhase.BOSS_QTE
			qte_target_idx = idx
			qte_started_ms = now_utc_ms
			events_out.append({
				"type": "boss_qte_started",
				"enemy_id": e["id"],
				"window_ms": int(world_cfg["player_combat"]["qte_window_ms"]),
			})
		elif not is_boss:
			e["ai_state"] = EnemyAi.STAGGERED
			e["ai_timer_s"] = 1.2
			e["posture"] = float(e["posture_max"])


func _kill_enemy(e: Dictionary, now_utc_ms: int, events_out: Array) -> void:
	e["ai_state"] = EnemyAi.DEAD
	var stats: Dictionary = IdleEconomyScript.compute_player_stats(economy, balance_cfg, now_utc_ms)
	var gained_gold: RefCounted = (e["gold"] as RefCounted).mul(stats["gold_multiplier"])
	economy["gold"] = (economy["gold"] as RefCounted).add(gained_gold)
	var gems_add: int = int(e.get("gems", 0))
	economy["gems"] = int(economy["gems"]) + gems_add
	economy["ki_energy"] = float(economy["ki_energy"]) + (15.0 if bool(e["is_boss"]) else 4.0)

	if bool(e["is_boss"]):
		defeated_boss_worlds[current_world_id] = true
		economy["current_stage"] = int(economy["current_stage"]) + 1
		economy["max_stage_reached"] = maxi(int(economy["max_stage_reached"]), int(economy["current_stage"]))

	events_out.append({
		"type": "enemy_defeated",
		"enemy_id": e["id"],
		"is_boss": e["is_boss"],
		"gold": gained_gold,
		"gems": gems_add,
	})


func _integrate_player_physics(dt: float) -> void:
	var pc: Dictionary = world_cfg["player_combat"]
	var prev_y: float = py
	var rw: float = float(current_room_def["width"])
	var half_w: float = float(pc["player_half_width"])

	if not on_ground and player_action != PlayerAction.DASH:
		vy -= float(pc["gravity"]) * dt

	px = clampf(px + vx * dt, half_w, rw - half_w)
	py += vy * dt

	if vy <= 0.0:
		for plat in current_room_def.get("platforms", []):
			var plat_x: float = float(plat["x"])
			var plat_w: float = float(plat["w"])
			var top_y: float = float(plat["y"]) + float(plat.get("h", 24.0))
			if px >= plat_x and px <= (plat_x + plat_w) and prev_y >= top_y - 2.0 and py <= top_y:
				py = top_y
				vy = 0.0
				on_ground = true
				return

	if py <= 0.0:
		py = 0.0
		vy = 0.0
		on_ground = true
	else:
		on_ground = false


func _step_enemies_and_dots(dt: float, now_utc_ms: int, events_out: Array) -> void:
	for e in enemies:
		if int(e["ai_state"]) == EnemyAi.DEAD:
			continue

		# DoTs elementais (BURN, SHOCK)
		if float(e["burn_s"]) > 0.0:
			e["burn_s"] = maxf(0.0, float(e["burn_s"]) - dt)
			e["hp"] = (e["hp"] as RefCounted).sub_clamped((e["burn_dps"] as RefCounted).mul_float(dt))
		if float(e["shock_s"]) > 0.0:
			e["shock_s"] = maxf(0.0, float(e["shock_s"]) - dt)
			e["hp"] = (e["hp"] as RefCounted).sub_clamped((e["shock_dps"] as RefCounted).mul_float(dt))
		if (e["hp"] as RefCounted).is_zero():
			_kill_enemy(e, now_utc_ms, events_out)
			continue

		var frozen: bool = float(e["freeze_s"]) > 0.0
		if frozen:
			e["freeze_s"] = maxf(0.0, float(e["freeze_s"]) - dt)
		var time_scale: float = 0.35 if frozen else 1.0

		var ai: int = int(e["ai_state"])
		var dx: float = px - float(e["x"])
		var dist: float = absf(dx)
		e["facing"] = 1 if dx >= 0.0 else -1

		if ai == EnemyAi.STAGGERED or ai == EnemyAi.RECOVERY:
			e["ai_timer_s"] = float(e["ai_timer_s"]) - dt * time_scale
			if float(e["ai_timer_s"]) <= 0.0:
				e["ai_state"] = EnemyAi.CHASE
			continue

		if ai == EnemyAi.WINDUP:
			e["ai_timer_s"] = float(e["ai_timer_s"]) - dt * time_scale
			if float(e["ai_timer_s"]) <= 0.0:
				e["ai_state"] = EnemyAi.STRIKE
				e["ai_timer_s"] = float(e["strike_s"])
				e["hit_player_this_strike"] = false
			continue

		if ai == EnemyAi.STRIKE:
			if not bool(e["hit_player_this_strike"]):
				e["hit_player_this_strike"] = true
				if bool(e["is_ranged"]):
					projectiles.append({
						"active": true,
						"x": float(e["x"]),
						"y": float(e["y"]) + 55.0,
						"vx": float(e["facing"]) * float(e["projectile_speed"]),
						"vy": 0.0,
						"radius": 24.0,
						"dmg": e["dmg"],
						"ttl_s": 2.4,
					})
				elif dist <= float(e["attack_range"]) + 20.0 and absf(py - float(e["y"])) <= 115.0:
					_apply_damage_to_player(e["dmg"], e["id"], events_out)
			e["ai_timer_s"] = float(e["ai_timer_s"]) - dt * time_scale
			if float(e["ai_timer_s"]) <= 0.0:
				e["ai_state"] = EnemyAi.RECOVERY
				e["ai_timer_s"] = float(e["recovery_s"])
			continue

		# IDLE / CHASE
		if dist <= float(e["attack_range"]) and absf(py - float(e["y"])) <= 130.0:
			e["ai_state"] = EnemyAi.WINDUP
			e["ai_timer_s"] = float(e["windup_s"])
			events_out.append({"type": "enemy_telegraph", "enemy_id": e["id"], "is_boss": e["is_boss"]})
		else:
			e["ai_state"] = EnemyAi.CHASE
			var rw: float = float(current_room_def["width"])
			e["x"] = clampf(float(e["x"]) + float(e["facing"]) * float(e["speed"]) * time_scale * dt, 40.0, rw - 40.0)


func _step_projectiles(dt: float, events_out: Array) -> void:
	var rw: float = float(current_room_def["width"])
	for p in projectiles:
		if not bool(p["active"]):
			continue
		p["ttl_s"] = float(p["ttl_s"]) - dt
		p["x"] = float(p["x"]) + float(p["vx"]) * dt
		if float(p["ttl_s"]) <= 0.0 or float(p["x"]) < 0.0 or float(p["x"]) > rw:
			p["active"] = false
			continue
		var pr: float = float(p["radius"])
		if absf(float(p["x"]) - px) <= pr + 24.0 and float(p["y"]) >= py and float(p["y"]) <= py + 110.0:
			p["active"] = false
			_apply_damage_to_player(p["dmg"], "projectile", events_out)


func _apply_damage_to_player(raw_dmg: RefCounted, source_id: String, events_out: Array) -> void:
	if is_invulnerable():
		var pc: Dictionary = world_cfg["player_combat"]
		if not is_rage_active():
			rage_ratio = minf(1.0, rage_ratio + float(pc["rage_on_dodge"]))
		events_out.append({"type": "player_dodged", "source": source_id})
		return

	var rem: RefCounted = raw_dmg
	if not shield_hp.is_zero():
		var absorbed: RefCounted = shield_hp if rem.cmp(shield_hp) >= 0 else rem
		shield_hp = shield_hp.sub_clamped(absorbed)
		rem = rem.sub_clamped(absorbed)

	if not rem.is_zero():
		hp = hp.sub_clamped(rem)
	events_out.append({"type": "player_hit", "source": source_id, "damage": raw_dmg})


func _check_room_completion(events_out: Array) -> void:
	var rkey: String = _room_key(current_world_id, current_room_id)
	if is_room_cleared() and not cleared_rooms.has(rkey):
		cleared_rooms[rkey] = true
		events_out.append({"type": "room_cleared", "world_id": current_world_id, "room_id": current_room_id})

	var all_worlds_done: bool = true
	for w in world_cfg.get("worlds", []):
		if not defeated_boss_worlds.has(String(w["id"])):
			all_worlds_done = false
			break
	if all_worlds_done and game_phase == GamePhase.EXPLORING:
		game_phase = GamePhase.CAMPAIGN_CLEARED
		events_out.append({"type": "campaign_cleared"})


func resolve_defeat_revive(accepted: bool, reward_verified: bool, events_out: Array) -> Dictionary:
	if game_phase != GamePhase.DEFEATED_REVIVE_OFFER:
		return {"ok": false, "error": "Not in DEFEATED_REVIVE_OFFER"}

	if accepted:
		if not (reward_verified or bool(economy["has_no_ads_pass"])):
			return {"ok": false, "error": "Unverified Rewarded Ad or No-Ads Pass"}
		hp = max_hp.duplicate_num()
		mana = max_mana
		for i in range(4):
			skill_cooldowns[i] = 0.0
		rage_ratio = 0.0
		rage_remaining_s = float(world_cfg["player_combat"]["rage_duration_s"])
		game_phase = GamePhase.EXPLORING
		events_out.append({"type": "player_revived_in_place"})
		return {"ok": true, "revived": true}

	# Recusa de revive: retorna ao ultimo Altar/Checkpoint mantendo ouro, gemas e upgrades
	game_phase = GamePhase.EXPLORING
	_recompute_max_hp(true)
	mana = max_mana
	rage_remaining_s = 0.0
	enter_room(
		String(checkpoint["world_id"]),
		String(checkpoint["room_id"]),
		float(checkpoint["x"]),
		float(checkpoint["y"]),
		events_out
	)
	events_out.append({"type": "respawned_at_checkpoint", "checkpoint": checkpoint.duplicate()})
	return {"ok": true, "revived": false}


static func _encode_bignum(bn: RefCounted) -> Dictionary:
	return {"m": float(bn.get("mantissa")), "e": int(bn.get("exponent"))}


static func _decode_bignum(d: Dictionary) -> RefCounted:
	if not d.has("m") or not d.has("e"):
		return BigNumScript.invalid("Missing BigNum serialization fields")
	return BigNumScript.from_parts(float(d["m"]), int(d["e"]))


func export_checkpoint_snapshot(now_utc_ms: int) -> Dictionary:
	return {
		"schema_version": "1.0.0",
		"saved_utc_ms": now_utc_ms,
		"checkpoint": checkpoint.duplicate(),
		"cleared_rooms": cleared_rooms.duplicate(),
		"defeated_boss_worlds": defeated_boss_worlds.duplicate(),
		"opened_chests": opened_chests.duplicate(),
		"gems": int(economy["gems"]),
		"gold": _encode_bignum(economy["gold"]),
		"soul_orbs": _encode_bignum(economy["soul_orbs"]),
		"levels": (economy["levels"] as Dictionary).duplicate(),
		"has_no_ads_pass": bool(economy["has_no_ads_pass"]),
	}


func restore_from_checkpoint(snap: Dictionary, now_utc_ms: int, events_out: Array) -> bool:
	if not (snap.has("checkpoint") and snap.has("gold") and snap.has("levels")):
		return false
	if not (snap["gold"] is Dictionary):
		return false
	var g: RefCounted = _decode_bignum(snap["gold"])
	var orbs_dict: Dictionary = snap.get("soul_orbs", {"m": 0.0, "e": 0})
	var orbs: RefCounted = _decode_bignum(orbs_dict)
	if not bool(g.get("valid")) or not bool(orbs.get("valid")):
		return false

	economy["gold"] = g
	economy["soul_orbs"] = orbs
	economy["gems"] = int(snap.get("gems", 0))
	economy["has_no_ads_pass"] = bool(snap.get("has_no_ads_pass", false))
	economy["last_seen_utc_ms"] = int(snap.get("saved_utc_ms", now_utc_ms))
	for k in economy["levels"].keys():
		if snap["levels"].has(k):
			economy["levels"][k] = int(snap["levels"][k])

	checkpoint = (snap["checkpoint"] as Dictionary).duplicate()
	cleared_rooms = (snap.get("cleared_rooms", {}) as Dictionary).duplicate()
	defeated_boss_worlds = (snap.get("defeated_boss_worlds", {}) as Dictionary).duplicate()
	opened_chests = (snap.get("opened_chests", {}) as Dictionary).duplicate()
	_recompute_max_hp(true)
	mana = max_mana
	game_phase = GamePhase.EXPLORING
	return enter_room(
		String(checkpoint["world_id"]),
		String(checkpoint["room_id"]),
		float(checkpoint["x"]),
		float(checkpoint["y"]),
		events_out
	)
