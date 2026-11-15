extends Node2D
## Controlador da Arena Jogavel Dark Fantasy (Godot 4.4 16:9).
## Camada de borda: zero logica de negocio aqui; tudo delega para src/core/.

signal exited_to_title

const FLOOR_SCREEN_Y: float = 860.0

const BalanceConfigScript = preload("res://src/core/balance_config.gd")
const WorldConfigScript = preload("res://src/core/action_world_config.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const RngScript = preload("res://src/core/seeded_rng.gd")
const IdleEconomyScript = preload("res://src/core/idle_economy.gd")
const ActionCoreScript = preload("res://src/core/action_combat_core.gd")

const BackdropScript = preload("res://src/engine/world/world_backdrop.gd")
const WarriorScript = preload("res://src/engine/actors/silhouette_warrior.gd")
const EnemyVisScript = preload("res://src/engine/actors/silhouette_enemy.gd")
const VfxPoolScript = preload("res://src/engine/vfx/vfx_pool.gd")
const SfxScript = preload("res://src/engine/audio/procedural_sfx.gd")
const HudScript = preload("res://src/engine/ui/game_hud.gd")
const ForgeModalScript = preload("res://src/engine/ui/altar_forge_modal.gd")
const SaveStoreScript = preload("res://src/engine/services/local_checkpoint_store.gd")

var core: RefCounted = null
var _balance_raw: Dictionary = {}
var _world_raw: Dictionary = {}
var _rng: RefCounted = null
var _suffixes: PackedStringArray = PackedStringArray()
var _decimals: int = 2
var _boot_ok: bool = false

var _backdrop: Node2D = null
var _warrior: Node2D = null
var _enemies_layer: Node2D = null
var _enemy_nodes: Array[Node2D] = []
var _vfx: Node2D = null
var _cam: Camera2D = null
var _sfx: Node = null
var _hud: CanvasLayer = null
var _forge: CanvasLayer = null

var _events_buf: Array = []
var _hitstop_s: float = 0.0
var _shake_trauma: float = 0.0
var _paused: bool = false

var _pulse_jump: bool = false
var _pulse_dash: bool = false
var _pulse_attack: bool = false
var _pulse_rage: bool = false
var _pulse_interact: bool = false
var _pulse_qte: bool = false
var _pulse_skill: int = -1
var _initial_snap: Dictionary = {}
var _pending_offline_res: Dictionary = {}
var _save_path: String = SaveStoreScript.DEFAULT_SAVE_PATH


func configure_boot(snapshot_to_restore: Dictionary = {}, save_path_override: String = SaveStoreScript.DEFAULT_SAVE_PATH) -> void:
	_initial_snap = snapshot_to_restore
	_save_path = save_path_override


func _ready() -> void:
	_build_scene_tree()
	_boot_core()


func _build_scene_tree() -> void:
	_backdrop = BackdropScript.new()
	_backdrop.floor_screen_y = FLOOR_SCREEN_Y
	add_child(_backdrop)

	_enemies_layer = Node2D.new()
	add_child(_enemies_layer)

	_warrior = WarriorScript.new()
	add_child(_warrior)

	_vfx = VfxPoolScript.new()
	_vfx.floor_screen_y = FLOOR_SCREEN_Y
	add_child(_vfx)

	_cam = Camera2D.new()
	_cam.position = Vector2(960.0, 540.0)
	_cam.enabled = true
	add_child(_cam)

	_sfx = SfxScript.new()
	add_child(_sfx)

	_hud = HudScript.new()
	add_child(_hud)
	_hud.open_forge_clicked.connect(_on_open_forge)
	_hud.back_to_title_clicked.connect(func() -> void: emit_signal("exited_to_title"))
	_hud.interact_clicked.connect(func() -> void: _pulse_interact = true)
	_hud.qte_clicked.connect(func() -> void: _pulse_qte = true)
	_hud.revive_clicked.connect(_on_revive_choice)

	_forge = ForgeModalScript.new()
	add_child(_forge)
	_forge.closed.connect(_on_close_forge)
	_forge.upgrade_requested.connect(_on_upgrade_requested)
	_forge.gacha_pull_requested.connect(_on_gacha_requested)
	_forge.offline_claim_requested.connect(_on_offline_claim_requested)


func _boot_core() -> void:
	var b_path: String = "res://config/balance_v1.json"
	var w_path: String = "res://config/action_world_v1.json"
	if not FileAccess.file_exists(b_path) or not FileAccess.file_exists(w_path):
		push_error("FAIL-CLOSED: Missing JSON configs in res://config/")
		return

	var bcfg: RefCounted = BalanceConfigScript.parse_and_validate(FileAccess.get_file_as_string(b_path))
	var wcfg: RefCounted = WorldConfigScript.parse_and_validate(FileAccess.get_file_as_string(w_path))
	if bcfg == null or not bcfg.is_valid() or wcfg == null or not wcfg.is_valid():
		push_error("FAIL-CLOSED: Invalid config schema on engine boot.")
		return

	_balance_raw = bcfg.get("raw")
	_world_raw = wcfg.get("raw")
	_suffixes = bcfg.get_bignum_suffixes()
	_decimals = bcfg.get_bignum_decimals()

	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	_rng = RngScript.new(now_ms ^ 0x5A1C0)
	core = ActionCoreScript.new(_balance_raw, _world_raw, _rng, now_ms)

	if not _initial_snap.is_empty():
		var evs: Array = []
		if core.restore_from_checkpoint(_initial_snap, now_ms, evs):
			var stats: Dictionary = IdleEconomyScript.compute_player_stats(core.economy, _balance_raw, now_ms)
			var gps: RefCounted = BigNumScript.from_float(12.0).mul(stats["gold_multiplier"])
			_pending_offline_res = IdleEconomyScript.compute_offline_reward(core.economy, gps, _balance_raw, now_ms, false, false)
			_hud.show_toast("Checkpoint restaurado do Altar!", 2.5)
		else:
			_hud.show_toast("Save corrompido: iniciando nova jornada.", 2.5)

	_sync_room_visuals()
	_boot_ok = true


func is_boot_valid() -> bool:
	return _boot_ok and core != null


func _sync_room_visuals() -> void:
	var p_map: Dictionary = {}
	for p in core.current_room_def.get("portals", []):
		p_map[String(p["id"])] = bool(core.get_portal_state(p)["unlocked"])

	var alt_id: String = String(core.checkpoint.get("altar_id", ""))
	_backdrop.set_room_state(core.current_world_id, core.current_room_def, p_map, core.opened_chests, alt_id)

	while _enemy_nodes.size() < core.enemies.size():
		var en := EnemyVisScript.new()
		_enemies_layer.add_child(en)
		_enemy_nodes.append(en)
	for i in range(_enemy_nodes.size()):
		if i < core.enemies.size():
			_enemy_nodes[i].update_from_core(core.enemies[i], FLOOR_SCREEN_Y, 0.0)
		else:
			_enemy_nodes[i].visible = false

	_vfx.set_projectiles(core.projectiles)


func _unhandled_input(event: InputEvent) -> void:
	if not _boot_ok:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if not _paused:
			if core.game_phase == ActionCoreScript.GamePhase.BOSS_QTE:
				_pulse_qte = true
			else:
				_pulse_attack = true
		return
	if event is InputEventKey and event.pressed and not event.echo:
		var kc: Key = event.keycode
		if kc == KEY_ESCAPE or kc == KEY_F:
			if _forge.visible:
				_on_close_forge()
			else:
				_on_open_forge()
			return
		if _paused:
			return
		if core.game_phase == ActionCoreScript.GamePhase.BOSS_QTE:
			if kc == KEY_SPACE or kc == KEY_E or kc == KEY_Q or kc == KEY_J:
				_pulse_qte = true
			return
		if kc == KEY_W or kc == KEY_UP or kc == KEY_SPACE:
			_pulse_jump = true
		elif kc == KEY_SHIFT or kc == KEY_K or kc == KEY_L:
			_pulse_dash = true
		elif kc == KEY_J or kc == KEY_Z:
			_pulse_attack = true
		elif kc == KEY_1 or kc == KEY_U:
			_pulse_skill = 0
		elif kc == KEY_2 or kc == KEY_I:
			_pulse_skill = 1
		elif kc == KEY_3 or kc == KEY_O:
			_pulse_skill = 2
		elif kc == KEY_4 or kc == KEY_P:
			_pulse_skill = 3
		elif kc == KEY_R:
			_pulse_rage = true
		elif kc == KEY_E:
			_pulse_interact = true


func _process(delta: float) -> void:
	if not _boot_ok:
		return
	var dt: float = minf(delta, 0.05)

	if _hitstop_s > 0.0:
		_hitstop_s = maxf(0.0, _hitstop_s - dt)
		_update_camera_and_fx(dt)
		return

	if not _paused:
		var cmd: Dictionary = _gather_input_command()
		var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
		_events_buf.clear()
		core.step(dt, cmd, now_ms, _events_buf)
		_process_core_events(_events_buf)

	_update_visual_frame(dt)
	_update_camera_and_fx(dt)


func _gather_input_command() -> Dictionary:
	var touch_cmd: Dictionary = _hud.consume_touch_pulses()
	var move_x: float = float(touch_cmd["move_x"])
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		move_x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		move_x += 1.0
	move_x = clampf(move_x, -1.0, 1.0)

	var skill_idx: int = _pulse_skill if _pulse_skill >= 0 else int(touch_cmd["cast_skill_idx"])
	var cmd: Dictionary = {
		"move_x": move_x,
		"jump_pressed": _pulse_jump or bool(touch_cmd["jump_pressed"]),
		"dash_pressed": _pulse_dash or bool(touch_cmd["dash_pressed"]),
		"attack_pressed": _pulse_attack or bool(touch_cmd["attack_pressed"]),
		"rage_pressed": _pulse_rage or bool(touch_cmd["rage_pressed"]),
		"interact_pressed": _pulse_interact,
		"qte_pressed": _pulse_qte,
		"cast_skill_idx": skill_idx,
	}
	_pulse_jump = false
	_pulse_dash = false
	_pulse_attack = false
	_pulse_rage = false
	_pulse_interact = false
	_pulse_qte = false
	_pulse_skill = -1
	return cmd


func _process_core_events(events: Array) -> void:
	var refresh_room: bool = false
	for ev in events:
		var et: String = String(ev.get("type", ""))
		if et == "room_entered" or et == "room_cleared":
			refresh_room = true
		if et == "room_cleared":
			_hud.show_toast("Area limpa! Portais liberados.", 2.2)
		elif et == "attack_started":
			var cstep: int = int(ev.get("combo_step", 0))
			_sfx.play("slash_%d" % clampi(cstep + 1, 1, 3), 0.95 + float(cstep) * 0.08)
		elif et == "player_dashed":
			_sfx.play("dash")
		elif et == "magic_cast":
			var sid: String = String(ev.get("skill_id", ""))
			_vfx.spawn_magic(sid, float(ev["x"]), float(ev["y"]), core.facing)
			_shake_trauma = maxf(_shake_trauma, 0.45)
			if sid == "chaos_flames":
				_sfx.play("fire")
			elif sid == "glacial_tempest":
				_sfx.play("ice")
			elif sid == "sky_lightning":
				_sfx.play("lightning")
			elif sid == "titan_aegis":
				_sfx.play("aegis")
		elif et == "enemy_hit":
			var dmg_bn: RefCounted = ev["damage"]
			var is_crit: bool = bool(ev.get("crit", false))
			var tgt_pos: Vector2 = _find_enemy_world_pos(String(ev["enemy_id"]))
			var txt: String = ("%s!" if is_crit else "%s") % dmg_bn.format(_suffixes, _decimals)
			var col: Color = Color(1.0, 0.86, 0.22) if is_crit else Color(0.98, 0.96, 0.95)
			_vfx.spawn_text(txt, tgt_pos.x, tgt_pos.y + 40.0, col, 1.35 if is_crit else 1.0)
			_vfx.spawn_sparks(tgt_pos.x, FLOOR_SCREEN_Y - tgt_pos.y - 55.0, col, 6)
			_sfx.play("hit", 1.15 if is_crit else 0.95)
		elif et == "enemy_defeated":
			_shake_trauma = maxf(_shake_trauma, 0.55 if bool(ev.get("is_boss", false)) else 0.25)
			if bool(ev.get("is_boss", false)):
				refresh_room = true
				_hitstop_s = 0.09
				_hud.show_toast("CHEFE TITANICO DERROTADO!", 3.0)
		elif et == "boss_qte_started":
			_shake_trauma = 0.65
			_sfx.play("rage")
		elif et == "boss_qte_finisher":
			_hitstop_s = 0.12
			_shake_trauma = 1.0
			_sfx.play("qte")
			var qdmg: RefCounted = ev["damage"]
			_vfx.spawn_text("EXECUCAO! %s" % qdmg.format(_suffixes, _decimals), core.px + float(core.facing) * 80.0, core.py + 90.0, Color(1.0, 0.35, 0.18), 1.65)
		elif et == "player_dodged":
			_sfx.play("dodge")
			_vfx.spawn_text("ESQUIVA!", core.px, core.py + 50.0, Color(0.35, 0.95, 1.0), 1.15)
		elif et == "player_hit":
			_shake_trauma = maxf(_shake_trauma, 0.50)
			var pdmg: RefCounted = ev["damage"]
			_vfx.spawn_text("-%s" % pdmg.format(_suffixes, _decimals), core.px, core.py + 45.0, Color(1.0, 0.22, 0.24), 1.1)
		elif et == "rage_started":
			_sfx.play("rage")
			_hud.show_toast("FURIA ESPARTANA ATIVADA!", 2.0)
		elif et == "altar_activated":
			_sfx.play("altar")
			_vfx.spawn_magic("altar_heal", core.px, core.py, 1)
			_vfx.spawn_text("CURA + CHECKPOINT", core.px, core.py + 80.0, Color(0.35, 0.98, 0.88), 1.25)
			if not _save_path.is_empty():
				SaveStoreScript.save_snapshot(ev["snapshot"], _save_path)
			_hud.show_toast("Progresso salvo no Altar! Abrindo Forja...", 2.4)
			refresh_room = true
			_on_open_forge()
		elif et == "chest_opened":
			_sfx.play("chest")
			var cg: RefCounted = ev["gold"]
			_vfx.spawn_text("+%s Ouro | +%d Gemas" % [cg.format(_suffixes, _decimals), int(ev["gems"])], core.px, core.py + 60.0, Color(1.0, 0.88, 0.32), 1.25)
			refresh_room = true
		elif et == "portal_locked":
			_hud.show_toast("Portal selado: %s" % String(ev.get("reason", "derrote os inimigos")), 2.0)

	if refresh_room:
		_sync_room_visuals()


func _find_enemy_world_pos(eid: String) -> Vector2:
	for e in core.enemies:
		if String(e["id"]) == eid:
			return Vector2(float(e["x"]), float(e["y"]))
	return Vector2(core.px + float(core.facing) * 90.0, core.py)


func _compute_interact_hint() -> String:
	for a in core.current_room_def.get("altars", []):
		if absf(core.px - float(a["x"])) <= float(a.get("radius", 110.0)):
			return "Altar: Curar, Salvar & Forja"
	for c in core.current_room_def.get("chests", []):
		if not core.opened_chests.has(String(c["id"])) and absf(core.px - float(c["x"])) <= 95.0 and absf(core.py - float(c.get("y", 0.0))) <= 120.0:
			return "Abrir Bau do Tesouro"
	for p in core.current_room_def.get("portals", []):
		if absf(core.px - float(p["x"])) <= float(p.get("radius", 95.0)):
			var st: Dictionary = core.get_portal_state(p)
			return "Atravessar Portal" if bool(st["unlocked"]) else "Portal Selado"
	return ""


func _update_visual_frame(dt: float) -> void:
	_warrior.update_visual(dt, core.px, core.py, FLOOR_SCREEN_Y, {
		"action": core.player_action,
		"facing": core.facing,
		"combo_index": core.combo_index,
		"rage": core.is_rage_active(),
		"invuln": core.is_invulnerable(),
		"vx": core.vx,
		"vy": core.vy,
	})

	for i in range(core.enemies.size()):
		if i < _enemy_nodes.size():
			_enemy_nodes[i].update_from_core(core.enemies[i], FLOOR_SCREEN_Y, dt)

	_vfx.set_projectiles(core.projectiles)
	_vfx.tick(dt)
	_backdrop.tick(dt, _cam.position.x)

	var wdef: Dictionary = _find_world_def(core.current_world_id)
	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	_hud.update_state(
		dt,
		core,
		String(wdef.get("display_name", core.current_world_id)),
		String(core.current_room_def.get("display_name", core.current_room_id)),
		_suffixes,
		_decimals,
		_compute_interact_hint(),
		now_ms
	)


func _update_camera_and_fx(dt: float) -> void:
	var rw: float = float(core.current_room_def.get("width", 2200.0))
	var target_x: float = clampf(core.px + float(core.facing) * 110.0, 960.0, maxf(960.0, rw - 960.0))
	_cam.position.x = lerpf(_cam.position.x, target_x, clampf(dt * 8.0, 0.0, 1.0))
	_shake_trauma = maxf(0.0, _shake_trauma - dt * 2.4)
	var mag: float = _shake_trauma * _shake_trauma * 22.0
	_cam.offset = Vector2(sin(Time.get_ticks_msec() * 0.09) * mag, cos(Time.get_ticks_msec() * 0.13) * mag)


func _find_world_def(wid: String) -> Dictionary:
	for w in _world_raw.get("worlds", []):
		if String(w.get("id", "")) == wid:
			return w
	return {}


func _refresh_forge_modal() -> void:
	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	var stats: Dictionary = IdleEconomyScript.compute_player_stats(core.economy, _balance_raw, now_ms)
	_forge.refresh(core.economy, stats, _balance_raw, _suffixes, _decimals, _pending_offline_res)


func _on_open_forge() -> void:
	_sfx.play("ui")
	_paused = true
	_refresh_forge_modal()
	_forge.visible = true


func _on_close_forge() -> void:
	_sfx.play("ui")
	_forge.visible = false
	_paused = false


func _on_upgrade_requested(stat_key: String, count: int) -> void:
	var evs: Array = []
	var res: Dictionary = core.buy_forge_upgrade(stat_key, count, evs)
	if bool(res.get("ok", false)):
		_sfx.play("ui", 1.15)
		if not _save_path.is_empty():
			SaveStoreScript.save_snapshot(core.export_checkpoint_snapshot(int(Time.get_unix_time_from_system() * 1000.0)), _save_path)
	_refresh_forge_modal()


func _on_gacha_requested(count: int) -> void:
	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	var res: Dictionary = IdleEconomyScript.execute_gacha_pull(core.economy, "weapons_mythic_v1", count, false, false, _rng, _balance_raw, now_ms)
	if bool(res.get("ok", false)):
		_sfx.play("chest")
		var items: Array = res["results"]
		_forge.set_gacha_feedback("Invocado (%dx): %s" % [count, ", ".join(items)])
		if not _save_path.is_empty():
			SaveStoreScript.save_snapshot(core.export_checkpoint_snapshot(now_ms), _save_path)
	else:
		_forge.set_gacha_feedback("Falhou: %s" % String(res.get("error", "Erro")))
	_refresh_forge_modal()


func _on_offline_claim_requested(use_3x: bool) -> void:
	if _pending_offline_res.is_empty():
		return
	if use_3x and not bool(core.economy.get("has_no_ads_pass", false)):
		_hud.show_toast("Bau 3x exige Rewarded Ad (Sprint 4C) ou No-Ads Pass.", 2.2)
		return
	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	var mult_factor: float = 3.0 if (use_3x and bool(core.economy.get("has_no_ads_pass", false))) else 1.0
	if bool(_pending_offline_res.get("ok", false)) and not (_pending_offline_res["gold"] as RefCounted).is_zero():
		var final_gold: RefCounted = (_pending_offline_res["gold"] as RefCounted).mul_float(mult_factor)
		core.economy["gold"] = (core.economy["gold"] as RefCounted).add(final_gold)
		core.economy["last_seen_utc_ms"] = now_ms
		_pending_offline_res = {}
		_sfx.play("chest")
		if not _save_path.is_empty():
			SaveStoreScript.save_snapshot(core.export_checkpoint_snapshot(now_ms), _save_path)
	_refresh_forge_modal()


func _on_revive_choice(accepted: bool) -> void:
	var evs: Array = []
	var res: Dictionary = core.resolve_defeat_revive(accepted, false, evs)
	if bool(res.get("ok", false)):
		_process_core_events(evs)
		_sync_room_visuals()
	else:
		_hud.show_toast(String(res.get("error", "Revive indisponivel")), 2.0)
