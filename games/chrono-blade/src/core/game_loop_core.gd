class_name GameLoopCore
extends RefCounted
## Nucleo puro e deterministico generico de Action RPG 2D (Template PlayForge).
## Zero dependencias de Node, SceneTree, FileAccess ou rede.

const BigNumScript = preload("res://src/core/big_num.gd")
const SeededRngScript = preload("res://src/core/seeded_rng.gd")

var valid: bool = false
var error_message: String = ""

var game_id: String = ""
var hero_hp: RefCounted = null
var hero_max_hp: RefCounted = null
var hero_attack: RefCounted = null
var hero_x: float = 160.0
var move_speed: float = 260.0
var gold: RefCounted = null

var worlds: Array = []
var current_world_index: int = 0
var current_room_index: int = 0
var enemy_name: String = ""
var enemy_hp: RefCounted = null
var enemy_attack: RefCounted = null
var current_reward_gold: RefCounted = null

var campaign_cleared: bool = false
var defeated: bool = false
var rng: RefCounted = null


static func parse_and_create(json_text: String, seed_val: int = 12345) -> RefCounted:
	var inst = new()
	var parser := JSON.new()
	if parser.parse(json_text) != OK or not (parser.data is Dictionary):
		inst.valid = false
		inst.error_message = "JSON invalido na configuracao do template."
		return inst
	inst.boot_from_dict(parser.data, seed_val)
	return inst


func boot_from_dict(cfg: Dictionary, seed_val: int = 12345) -> bool:
	valid = false
	error_message = ""
	rng = SeededRngScript.new(seed_val)

	if not (cfg.has("game_id") and cfg.has("hero") and cfg.has("worlds")):
		error_message = "Chaves obrigatorias ausentes (game_id, hero, worlds)."
		return false

	game_id = String(cfg.get("game_id", "")).strip_edges()
	if game_id.is_empty():
		error_message = "game_id vazio."
		return false

	var hero_val = cfg.get("hero")
	if not (hero_val is Dictionary):
		error_message = "Bloco hero deve ser Dictionary."
		return false
	var hero: Dictionary = hero_val
	var base_hp: float = float(hero.get("base_hp", 0.0))
	var base_atk: float = float(hero.get("base_attack", 0.0))
	move_speed = float(hero.get("move_speed", 260.0))
	if base_hp <= 0.0 or base_atk <= 0.0 or move_speed <= 0.0:
		error_message = "Atributos do heroi devem ser > 0."
		return false

	hero_max_hp = BigNumScript.from_float(base_hp)
	hero_hp = hero_max_hp.duplicate_num()
	hero_attack = BigNumScript.from_float(base_atk)
	gold = BigNumScript.zero()
	hero_x = 160.0
	campaign_cleared = false
	defeated = false

	var worlds_val = cfg.get("worlds")
	if not (worlds_val is Array) or (worlds_val as Array).is_empty():
		error_message = "Lista worlds deve conter ao menos um mundo."
		return false
	worlds = worlds_val
	for w in worlds:
		if not (w is Dictionary) or not (w.get("rooms") is Array) or (w.get("rooms") as Array).is_empty():
			error_message = "Cada mundo deve conter lista nao vazia de salas."
			return false

	current_world_index = 0
	current_room_index = 0
	if not _load_room(0, 0):
		return false

	valid = true
	return true


func _load_room(w_idx: int, r_idx: int) -> bool:
	var w: Dictionary = worlds[w_idx]
	var rooms: Array = w["rooms"]
	if r_idx < 0 or r_idx >= rooms.size():
		error_message = "Indice de sala invalido."
		return false
	var room: Dictionary = rooms[r_idx]
	var e_hp: float = float(room.get("enemy_hp", 0.0))
	var e_atk: float = float(room.get("enemy_attack", 0.0))
	var rew: float = float(room.get("reward_gold", 0.0))
	if e_hp <= 0.0 or e_atk < 0.0 or rew < 0.0:
		error_message = "Parametros de sala invalidos."
		return false
	enemy_name = String(room.get("enemy_name", "Enemy"))
	enemy_hp = BigNumScript.from_float(e_hp)
	enemy_attack = BigNumScript.from_float(e_atk)
	current_reward_gold = BigNumScript.from_float(rew)
	return true


func step(dt_s: float, move_dir: float, attack_pressed: bool) -> Dictionary:
	var events: Array[String] = []
	if not valid or defeated or campaign_cleared or dt_s <= 0.0:
		return {"events": events}

	hero_x = clampf(hero_x + (move_dir * move_speed * dt_s), 40.0, 1880.0)

	if attack_pressed and not enemy_hp.is_zero():
		var crit_roll: bool = rng.roll_chance(0.20)
		var dmg: RefCounted = hero_attack.mul_float(1.5 if crit_roll else 1.0)
		enemy_hp = enemy_hp.sub_clamped(dmg)
		events.append("hero_crit" if crit_roll else "hero_hit")

		if enemy_hp.is_zero():
			gold = gold.add(current_reward_gold)
			events.append("room_cleared")
			_advance_room_or_clear(events)
		elif not enemy_attack.is_zero():
			hero_hp = hero_hp.sub_clamped(enemy_attack)
			events.append("hero_damaged")
			if hero_hp.is_zero():
				defeated = true
				events.append("hero_defeated")

	return {"events": events}


func _advance_room_or_clear(events: Array[String]) -> void:
	var rooms: Array = worlds[current_world_index]["rooms"]
	if current_room_index + 1 < rooms.size():
		current_room_index += 1
		_load_room(current_world_index, current_room_index)
		events.append("room_entered")
	elif current_world_index + 1 < worlds.size():
		current_world_index += 1
		current_room_index = 0
		_load_room(current_world_index, current_room_index)
		events.append("world_entered")
	else:
		campaign_cleared = true
		events.append("campaign_cleared")


func export_checkpoint_snapshot() -> Dictionary:
	return {
		"schema_version": 1,
		"game_id": game_id,
		"world_index": current_world_index,
		"room_index": current_room_index,
		"gold_m": float(gold.get("mantissa")),
		"gold_e": int(gold.get("exponent")),
		"hero_hp_m": float(hero_hp.get("mantissa")),
		"hero_hp_e": int(hero_hp.get("exponent")),
		"campaign_cleared": campaign_cleared,
	}
