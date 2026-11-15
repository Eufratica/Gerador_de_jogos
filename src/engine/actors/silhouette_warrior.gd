extends Node2D
## Guerreiro Zaikor em silhueta Dark Fantasy de alto contraste + laminas brilhantes (Zero GC).

const CoreScript = preload("res://src/core/action_combat_core.gd")
const SCARF_PTS: int = 8
const GHOST_MAX: int = 5

var action_state: int = 0
var facing: int = 1
var combo_step: int = 0
var rage_active: bool = false
var invuln_active: bool = false
var vx: float = 0.0
var vy: float = 0.0
var anim_t: float = 0.0

var _scarf: PackedVector2Array = PackedVector2Array()
var _ghost_world_x: PackedFloat64Array = PackedFloat64Array()
var _ghost_world_y: PackedFloat64Array = PackedFloat64Array()
var _ghost_alpha: PackedFloat64Array = PackedFloat64Array()
var _ghost_cursor: int = 0
var _ghost_accum: float = 0.0
var _floor_screen_y: float = 860.0
var _pools_ready: bool = false


func _ready() -> void:
	_ensure_pools()


func _ensure_pools() -> void:
	if _pools_ready:
		return
	_pools_ready = true
	_scarf.resize(SCARF_PTS)
	_ghost_world_x.resize(GHOST_MAX)
	_ghost_world_y.resize(GHOST_MAX)
	_ghost_alpha.resize(GHOST_MAX)
	for i in range(GHOST_MAX):
		_ghost_alpha[i] = 0.0


func update_visual(dt: float, world_x: float, world_y: float, floor_y: float, p_state: Dictionary) -> void:
	_ensure_pools()
	anim_t += dt
	_floor_screen_y = floor_y
	position = Vector2(world_x, floor_y - world_y)
	action_state = int(p_state.get("action", 0))
	facing = int(p_state.get("facing", 1))
	combo_step = int(p_state.get("combo_index", 0))
	rage_active = bool(p_state.get("rage", false))
	invuln_active = bool(p_state.get("invuln", false))
	vx = float(p_state.get("vx", 0.0))
	vy = float(p_state.get("vy", 0.0))

	# Cachecol fluido local
	for i in range(SCARF_PTS):
		var frac: float = float(i) / float(SCARF_PTS - 1)
		var trail_x: float = -float(facing) * (10.0 + frac * 44.0) - clampf(vx * 0.04, -22.0, 22.0) * frac
		var wave_y: float = -78.0 + sin(anim_t * 11.0 - frac * 3.0) * (5.0 + frac * 7.0) + clampf(vy * 0.02, -14.0, 14.0) * frac
		_scarf[i] = Vector2(trail_x, wave_y)

	# Rastro fantasma durante dash / rage
	for i in range(GHOST_MAX):
		_ghost_alpha[i] = maxf(0.0, _ghost_alpha[i] - dt * 4.5)
	if invuln_active or rage_active:
		_ghost_accum += dt
		if _ghost_accum >= 0.045:
			_ghost_accum = 0.0
			_ghost_world_x[_ghost_cursor] = world_x
			_ghost_world_y[_ghost_cursor] = world_y
			_ghost_alpha[_ghost_cursor] = 0.45 if invuln_active else 0.22
			_ghost_cursor = (_ghost_cursor + 1) % GHOST_MAX

	queue_redraw()


func _draw() -> void:
	# Fantasmas em coordenadas locais relativas
	for i in range(GHOST_MAX):
		var a: float = _ghost_alpha[i]
		if a <= 0.02:
			continue
		var rel: Vector2 = Vector2(_ghost_world_x[i], _floor_screen_y - _ghost_world_y[i]) - position
		var gc: Color = Color(0.25, 0.85, 1.0, a * 0.6) if invuln_active else Color(1.0, 0.35, 0.12, a * 0.5)
		draw_rect(Rect2(rel.x - 16.0, rel.y - 96.0, 32.0, 96.0), gc)

	var sil_col: Color = Color(0.04, 0.04, 0.06)
	var rim_col: Color = Color(1.0, 0.65, 0.18) if rage_active else (Color(0.35, 0.90, 1.0) if invuln_active else Color(0.30, 0.34, 0.44))
	var blade_col: Color = Color(1.0, 0.82, 0.24) if rage_active else Color(1.0, 0.26, 0.18)

	if rage_active:
		var pulse: float = 0.88 + 0.12 * sin(anim_t * 16.0)
		draw_circle(Vector2(0.0, -56.0), 58.0 * pulse, Color(1.0, 0.38, 0.08, 0.20))

	# Cachecol escarlate brilhante
	for i in range(SCARF_PTS - 1):
		var w: float = lerpf(8.0, 2.5, float(i) / float(SCARF_PTS - 1))
		draw_line(_scarf[i], _scarf[i + 1], blade_col, w)

	# Pernas articuladas
	var run_phase: float = sin(anim_t * 14.0) * (14.0 if absf(vx) > 25.0 else 0.0)
	draw_line(Vector2(-7.0, -40.0), Vector2(-10.0 + run_phase, 0.0), sil_col, 9.0)
	draw_line(Vector2(7.0, -40.0), Vector2(10.0 - run_phase, 0.0), sil_col, 9.0)

	# Tronco + ombreiras angulares (estilo guerreiro mitologico)
	var lean: float = float(facing) * (10.0 if action_state == CoreScript.PlayerAction.DASH else (6.0 if absf(vx) > 20.0 else 0.0))
	var torso := PackedVector2Array([
		Vector2(-15.0 + lean * 0.4, -40.0),
		Vector2(-21.0 + lean, -84.0),
		Vector2(21.0 + lean, -84.0),
		Vector2(15.0 + lean * 0.4, -40.0),
	])
	draw_colored_polygon(torso, sil_col)
	draw_polyline(torso, rim_col, 1.5)

	# Cabeca + elmo/crista + olhos brilhantes
	var head_c := Vector2(lean * 1.1, -99.0)
	draw_circle(head_c, 15.0, sil_col)
	var eye_x: float = head_c.x + float(facing) * 6.0
	draw_line(Vector2(eye_x - 3.0, head_c.y - 2.0), Vector2(eye_x + 5.0 * float(facing), head_c.y - 4.0), blade_col, 3.0)

	# Laminas duplas acorrentadas
	var hand := Vector2(head_c.x + float(facing) * 20.0, -60.0)
	var blade_tip := Vector2(hand.x + float(facing) * 52.0, -76.0)
	if action_state == CoreScript.PlayerAction.ATTACK_ACTIVE:
		blade_tip = Vector2(hand.x + float(facing) * 115.0, -56.0 + float(combo_step % 2) * 18.0)
		var arc_r: float = 115.0 + float(combo_step) * 24.0
		var arc_col := Color(blade_col.r, blade_col.g, blade_col.b, 0.85)
		draw_arc(Vector2(float(facing) * 18.0, -58.0), arc_r, -0.75 if facing > 0 else PI - 0.75, 0.75 if facing > 0 else PI + 0.75, 18, arc_col, 10.0 + float(combo_step) * 4.0)
		draw_arc(Vector2(float(facing) * 18.0, -58.0), arc_r - 16.0, -0.6 if facing > 0 else PI - 0.6, 0.6 if facing > 0 else PI + 0.6, 14, Color(1.0, 0.92, 0.7, 0.7), 4.0)
	elif action_state == CoreScript.PlayerAction.ATTACK_WINDUP:
		blade_tip = Vector2(hand.x - float(facing) * 34.0, -96.0)
	elif action_state == CoreScript.PlayerAction.CAST_MAGIC:
		blade_tip = Vector2(hand.x + float(facing) * 24.0, -118.0)
		draw_circle(blade_tip, 14.0, Color(0.35, 0.85, 1.0, 0.75))

	draw_line(Vector2(lean, -66.0), hand, Color(0.55, 0.55, 0.65), 2.5) # corrente
	draw_line(hand, blade_tip, blade_col, 6.0)
	draw_line(hand, blade_tip, Color(1.0, 0.95, 0.85), 2.0)
