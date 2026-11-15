class_name ActionWorldConfig
extends RefCounted
## Validador hermético (fail-closed) do schema de mundos, salas, altares, combos e magias.
## Camada pura: recebe json_text em memoria; zero FileAccess, Node ou env global.

const REQUIRED_ROOT_KEYS: PackedStringArray = [
	"schema_version",
	"player_combat",
	"enemy_archetypes",
	"worlds",
]

const VALID_DELIVERIES: PackedStringArray = [
	"AOE_SELF",
	"CONE_FRONT",
	"HOMING_STRIKE",
	"AOE_SHIELD",
]


class ValidationResult:
	extends RefCounted
	var ok: bool = false
	var errors: PackedStringArray = PackedStringArray()
	var raw: Dictionary = {}

	func is_valid() -> bool:
		return ok and errors.is_empty()

	func get_world_def(world_id: String) -> Dictionary:
		for w in raw.get("worlds", []):
			if String(w.get("id", "")) == world_id:
				return w
		return {}

	func get_room_def(world_id: String, room_id: String) -> Dictionary:
		var w: Dictionary = get_world_def(world_id)
		for r in w.get("rooms", []):
			if String(r.get("id", "")) == room_id:
				return r
		return {}


static func _fail(res: ValidationResult, msg: String) -> ValidationResult:
	res.errors.append(msg)
	res.ok = false
	return res


static func _require_positive_float(d: Dictionary, key: String, ctx: String, res: ValidationResult) -> float:
	if not d.has(key) or (not (d[key] is float or d[key] is int)):
		_fail(res, "%s.%s missing numeric value" % [ctx, key])
		return 0.0
	var v: float = float(d[key])
	if is_nan(v) or is_inf(v) or v <= 0.0:
		_fail(res, "%s.%s must be > 0 (got %s)" % [ctx, key, str(d[key])])
		return 0.0
	return v


static func _validate_player_combat(pc: Dictionary, res: ValidationResult) -> void:
	for k in [
		"move_speed", "jump_velocity", "gravity", "player_half_width", "player_height",
		"dash_speed", "dash_duration_s", "dash_iframe_s", "dash_cooldown_s",
		"base_max_hp", "base_max_mana", "mana_regen_per_s", "mana_on_hit",
		"rage_on_hit", "rage_on_dodge", "rage_duration_s", "rage_dmg_mult",
		"rage_spd_mult", "qte_window_ms", "qte_finisher_mult"
	]:
		_require_positive_float(pc, k, "player_combat", res)

	var combos = pc.get("combo_steps", [])
	if not (combos is Array) or combos.size() < 3:
		_fail(res, "player_combat.combo_steps must contain at least 3 hits")
	else:
		for idx in range(combos.size()):
			var c = combos[idx]
			if not (c is Dictionary):
				_fail(res, "combo_steps[%d] must be Dictionary" % idx)
				continue
			for ck in ["damage_mult", "posture_dmg", "reach_x", "reach_y", "windup_s", "active_s", "recovery_s"]:
				_require_positive_float(c, ck, "combo_steps[%d]" % idx, res)

	var magics = pc.get("magic_powers", [])
	if not (magics is Array) or magics.size() != 4:
		_fail(res, "player_combat.magic_powers must define exactly 4 active magic skills")
	else:
		var seen_ids: Dictionary = {}
		for idx in range(magics.size()):
			var m = magics[idx]
			if not (m is Dictionary):
				_fail(res, "magic_powers[%d] must be Dictionary" % idx)
				continue
			var mid: String = String(m.get("id", ""))
			if mid.is_empty() or seen_ids.has(mid):
				_fail(res, "magic_powers[%d] duplicate or empty id" % idx)
			seen_ids[mid] = true
			for mk in ["mana_cost", "cooldown_s", "damage_mult", "posture_dmg", "radius"]:
				_require_positive_float(m, mk, "magic_powers[%s]" % mid, res)
			var delivery: String = String(m.get("delivery", ""))
			if not VALID_DELIVERIES.has(delivery):
				_fail(res, "magic_powers[%s].delivery invalid: %s" % [mid, delivery])


static func _validate_archetypes(arch: Dictionary, res: ValidationResult) -> void:
	if arch.is_empty():
		_fail(res, "enemy_archetypes cannot be empty")
		return
	for a_id in arch.keys():
		var a = arch[a_id]
		if not (a is Dictionary):
			_fail(res, "enemy_archetypes[%s] must be Dictionary" % String(a_id))
			continue
		for ak in ["hp", "dmg", "posture_max", "speed", "attack_range", "windup_s", "strike_s", "recovery_s", "gold"]:
			_require_positive_float(a, ak, "enemy_archetypes[%s]" % String(a_id), res)
		if bool(a.get("is_ranged", false)):
			_require_positive_float(a, "projectile_speed", "enemy_archetypes[%s]" % String(a_id), res)


static func _validate_worlds(worlds: Array, arch: Dictionary, res: ValidationResult) -> void:
	if worlds.is_empty():
		_fail(res, "worlds cannot be empty")
		return

	var room_lookup: Dictionary = {}
	var world_ids: Dictionary = {}

	# Passo 1: indexa mundos e salas validando estrutura local
	for w in worlds:
		if not (w is Dictionary):
			_fail(res, "world entry must be Dictionary")
			continue
		var wid: String = String(w.get("id", ""))
		if wid.is_empty() or world_ids.has(wid):
			_fail(res, "duplicate or empty world id: %s" % wid)
			continue
		world_ids[wid] = true

		var rooms = w.get("rooms", [])
		if not (rooms is Array) or rooms.is_empty():
			_fail(res, "world %s must have rooms" % wid)
			continue

		var altar_count: int = 0
		var boss_count: int = 0
		var local_rooms: Dictionary = {}

		for r in rooms:
			if not (r is Dictionary):
				_fail(res, "room in world %s must be Dictionary" % wid)
				continue
			var rid: String = String(r.get("id", ""))
			if rid.is_empty() or local_rooms.has(rid):
				_fail(res, "duplicate or empty room id %s in %s" % [rid, wid])
				continue
			local_rooms[rid] = r
			room_lookup["%s::%s" % [wid, rid]] = r

			_require_positive_float(r, "width", "room[%s]" % rid, res)
			_require_positive_float(r, "height", "room[%s]" % rid, res)
			_require_positive_float(r, "power_scale", "room[%s]" % rid, res)

			altar_count += (r.get("altars", []) as Array).size()
			for enc in r.get("encounters", []):
				var etype: String = String(enc.get("archetype", ""))
				if not arch.has(etype):
					_fail(res, "room[%s] references unknown archetype: %s" % [rid, etype])
				elif bool(arch[etype].get("is_boss", false)):
					boss_count += 1

		var entry_rid: String = String(w.get("entry_room_id", ""))
		if not local_rooms.has(entry_rid):
			_fail(res, "world %s entry_room_id not found: %s" % [wid, entry_rid])
		if altar_count < 1:
			_fail(res, "world %s must contain at least 1 Save Altar" % wid)
		if boss_count < 1:
			_fail(res, "world %s must contain at least 1 Boss encounter" % wid)

	# Passo 2: valida integridade de todos os portais e spawn_x dentro da sala destino
	for w in worlds:
		if not (w is Dictionary):
			continue
		var wid: String = String(w.get("id", ""))
		var unlock_prev: String = String(w.get("unlock_after_world_id", ""))
		if not unlock_prev.is_empty() and not world_ids.has(unlock_prev):
			_fail(res, "world %s references missing unlock_after_world_id: %s" % [wid, unlock_prev])

		for r in w.get("rooms", []):
			var rid: String = String(r.get("id", ""))
			var rw: float = float(r.get("width", 0.0))
			for p in r.get("portals", []):
				var px: float = float(p.get("x", -1.0))
				if px < 0.0 or px > rw:
					_fail(res, "portal %s outside room %s width" % [String(p.get("id", "")), rid])
				var twid: String = String(p.get("target_world_id", ""))
				var trid: String = String(p.get("target_room_id", ""))
				var tkey: String = "%s::%s" % [twid, trid]
				if not room_lookup.has(tkey):
					_fail(res, "portal %s points to missing room %s" % [String(p.get("id", "")), tkey])
					continue
				var target_room: Dictionary = room_lookup[tkey]
				var sx: float = float(p.get("target_spawn_x", -1.0))
				if sx < 0.0 or sx > float(target_room.get("width", 0.0)):
					_fail(res, "portal %s spawn_x out of bounds for %s" % [String(p.get("id", "")), tkey])


static func parse_and_validate(json_text: String) -> ValidationResult:
	var res := ValidationResult.new()
	if json_text.strip_edges().is_empty():
		return _fail(res, "Action world JSON text is empty")

	var json := JSON.new()
	if json.parse(json_text) != OK or not (json.data is Dictionary):
		return _fail(res, "Invalid JSON syntax or non-Dictionary root")

	var raw: Dictionary = json.data
	for req in REQUIRED_ROOT_KEYS:
		if not raw.has(req):
			return _fail(res, "Missing root key: %s" % req)

	if not (raw["player_combat"] is Dictionary):
		return _fail(res, "player_combat must be Dictionary")
	if not (raw["enemy_archetypes"] is Dictionary):
		return _fail(res, "enemy_archetypes must be Dictionary")
	if not (raw["worlds"] is Array):
		return _fail(res, "worlds must be Array")

	_validate_player_combat(raw["player_combat"], res)
	_validate_archetypes(raw["enemy_archetypes"], res)
	_validate_worlds(raw["worlds"], raw["enemy_archetypes"], res)

	if res.errors.is_empty():
		res.ok = true
		res.raw = raw
	return res
