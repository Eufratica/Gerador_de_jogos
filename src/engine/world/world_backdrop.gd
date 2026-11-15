extends Node2D
## Cenario Dark Fantasy 2D lateral em silhuetas de alto contraste (Mundos, Plataformas, Altares, Baus e Portais).

const EMBER_COUNT: int = 44

var floor_screen_y: float = 860.0
var world_id: String = "world_1_ashen_citadel"
var room_def: Dictionary = {}
var portal_unlocked: Dictionary = {}
var opened_chests: Dictionary = {}
var active_altar_id: String = ""
var camera_x: float = 960.0
var time_s: float = 0.0

var _embers_x: PackedFloat64Array = PackedFloat64Array()
var _embers_y: PackedFloat64Array = PackedFloat64Array()
var _embers_vy: PackedFloat64Array = PackedFloat64Array()
var _embers_sz: PackedFloat64Array = PackedFloat64Array()
var _pools_ready: bool = false


func _ready() -> void:
	_ensure_pools()


func _ensure_pools() -> void:
	if _pools_ready:
		return
	_pools_ready = true
	_embers_x.resize(EMBER_COUNT)
	_embers_y.resize(EMBER_COUNT)
	_embers_vy.resize(EMBER_COUNT)
	_embers_sz.resize(EMBER_COUNT)
	for i in range(EMBER_COUNT):
		_embers_x[i] = fmod(float(i * 197 + 43), 2400.0)
		_embers_y[i] = fmod(float(i * 113 + 71), 900.0)
		_embers_vy[i] = 28.0 + float(i % 5) * 14.0
		_embers_sz[i] = 2.0 + float(i % 3) * 1.4


func set_room_state(p_world_id: String, p_room_def: Dictionary, p_portal_unlocked: Dictionary, p_opened_chests: Dictionary, p_active_altar: String) -> void:
	world_id = p_world_id
	room_def = p_room_def
	portal_unlocked = p_portal_unlocked
	opened_chests = p_opened_chests
	active_altar_id = p_active_altar
	queue_redraw()


func tick(dt: float, cam_x: float) -> void:
	_ensure_pools()
	time_s += dt
	camera_x = cam_x
	var rw: float = float(room_def.get("width", 2200.0))
	for i in range(EMBER_COUNT):
		_embers_y[i] -= _embers_vy[i] * dt
		_embers_x[i] += sin(time_s * 1.4 + float(i)) * 14.0 * dt
		if _embers_y[i] < 40.0:
			_embers_y[i] = floor_screen_y - 10.0
			_embers_x[i] = fmod(_embers_x[i] + 311.0, rw)
	queue_redraw()


func _draw() -> void:
	var rw: float = float(room_def.get("width", 2200.0))
	var is_foundry: bool = (world_id == "world_2_crimson_foundry")

	var sky_top: Color = Color(0.14, 0.04, 0.05) if is_foundry else Color(0.08, 0.10, 0.14)
	var sky_mid: Color = Color(0.32, 0.08, 0.06) if is_foundry else Color(0.18, 0.21, 0.27)
	var accent_col: Color = Color(1.0, 0.36, 0.12) if is_foundry else Color(0.95, 0.56, 0.20)
	var silhouette_far: Color = Color(0.08, 0.03, 0.04) if is_foundry else Color(0.06, 0.07, 0.10)
	var silhouette_mid: Color = Color(0.04, 0.02, 0.03) if is_foundry else Color(0.035, 0.04, 0.06)

	# Fundo gradiente dramatico
	draw_rect(Rect2(-400.0, -200.0, rw + 800.0, floor_screen_y + 200.0), sky_top)
	draw_rect(Rect2(-400.0, floor_screen_y - 520.0, rw + 800.0, 520.0), sky_mid)

	# Lua / Eclipse mitologico em paralaxe distante
	var moon_x: float = camera_x * 0.72 + 460.0
	var moon_y: float = 240.0
	draw_circle(Vector2(moon_x, moon_y), 118.0, Color(accent_col.r, accent_col.g, accent_col.b, 0.18))
	draw_circle(Vector2(moon_x, moon_y), 86.0, Color(accent_col.r, accent_col.g, accent_col.b, 0.52))
	draw_circle(Vector2(moon_x - 16.0, moon_y - 8.0), 68.0, sky_top)

	# Pilares e torres goticas em paralaxe (silhuetas)
	var bg_shift: float = (camera_x - 960.0) * 0.35
	for i in range(16):
		var px: float = float(i) * 260.0 - fmod(bg_shift, 260.0)
		var h: float = 280.0 + float((i * 73) % 210)
		draw_rect(Rect2(px, floor_screen_y - h, 96.0, h), silhouette_far)
		var spire := PackedVector2Array([
			Vector2(px - 8.0, floor_screen_y - h),
			Vector2(px + 48.0, floor_screen_y - h - 75.0),
			Vector2(px + 104.0, floor_screen_y - h),
		])
		draw_colored_polygon(spire, silhouette_far)

	# Correntes penduradas no plano medio
	var mid_shift: float = (camera_x - 960.0) * 0.15
	for i in range(12):
		var cx: float = float(i) * 310.0 + 90.0 - fmod(mid_shift, 310.0)
		var ch: float = 220.0 + float((i * 53) % 180)
		draw_line(Vector2(cx, 0.0), Vector2(cx, ch), silhouette_mid, 5.0)
		draw_rect(Rect2(cx - 12.0, ch, 24.0, 28.0), silhouette_mid)

	# Churas / Cinzas subindo
	for i in range(EMBER_COUNT):
		var pulse: float = 0.45 + 0.35 * sin(time_s * 3.0 + float(i))
		draw_circle(Vector2(_embers_x[i], _embers_y[i]), _embers_sz[i], Color(accent_col.r, accent_col.g, accent_col.b, pulse))

	# Piso principal negro + rachaduras incandescentes
	draw_rect(Rect2(-400.0, floor_screen_y, rw + 800.0, 420.0), Color(0.03, 0.03, 0.04))
	draw_line(Vector2(-400.0, floor_screen_y), Vector2(rw + 400.0, floor_screen_y), Color(accent_col.r, accent_col.g, accent_col.b, 0.75), 3.0)
	for seg in range(int(rw / 180.0) + 1):
		var sx: float = float(seg) * 180.0 + 30.0
		draw_line(Vector2(sx, floor_screen_y + 12.0), Vector2(sx + 55.0, floor_screen_y + 38.0), Color(accent_col.r, accent_col.g, accent_col.b, 0.25), 2.0)

	# Plataformas unidirecionais
	for plat in room_def.get("platforms", []):
		var px: float = float(plat["x"])
		var py: float = floor_screen_y - float(plat["y"]) - float(plat.get("h", 24.0))
		var pw: float = float(plat["w"])
		var ph: float = float(plat.get("h", 24.0))
		draw_rect(Rect2(px, py, pw, ph), Color(0.06, 0.06, 0.09))
		draw_line(Vector2(px, py), Vector2(px + pw, py), Color(0.55, 0.72, 0.95, 0.85), 3.0)

	# Baus de Tesouro
	for c in room_def.get("chests", []):
		var cid: String = String(c["id"])
		var cx: float = float(c["x"])
		var cy: float = floor_screen_y - float(c.get("y", 0.0))
		var is_open: bool = opened_chests.has(cid)
		var col: Color = Color(0.32, 0.30, 0.28) if is_open else Color(0.95, 0.76, 0.22)
		draw_rect(Rect2(cx - 28.0, cy - 36.0, 56.0, 36.0), Color(0.08, 0.06, 0.05))
		draw_rect(Rect2(cx - 28.0, cy - 36.0, 56.0, 36.0), col, false, 3.0)
		if not is_open:
			var glint: float = 0.4 + 0.35 * sin(time_s * 5.0)
			draw_circle(Vector2(cx, cy - 22.0), 16.0, Color(1.0, 0.85, 0.3, glint * 0.45))

	# Altares de Salvamento
	for a in room_def.get("altars", []):
		var aid: String = String(a["id"])
		var ax: float = float(a["x"])
		var ay: float = floor_screen_y - float(a.get("y", 0.0))
		var saved_here: bool = (aid == active_altar_id)
		var glow_col: Color = Color(0.25, 0.95, 0.88) if saved_here else Color(0.22, 0.68, 1.0)
		var pulse: float = 0.75 + 0.25 * sin(time_s * 3.8)
		# Obelisco escuro + aura sagrada
		draw_circle(Vector2(ax, ay - 95.0), 75.0 * pulse, Color(glow_col.r, glow_col.g, glow_col.b, 0.14))
		draw_rect(Rect2(ax - 38.0, ay - 22.0, 76.0, 22.0), Color(0.08, 0.09, 0.12))
		var obelisk := PackedVector2Array([
			Vector2(ax - 22.0, ay - 22.0),
			Vector2(ax - 12.0, ay - 148.0),
			Vector2(ax, ay - 172.0),
			Vector2(ax + 12.0, ay - 148.0),
			Vector2(ax + 22.0, ay - 22.0),
		])
		draw_colored_polygon(obelisk, Color(0.07, 0.08, 0.11))
		draw_line(Vector2(ax, ay - 45.0), Vector2(ax, ay - 135.0), glow_col, 4.0)
		draw_circle(Vector2(ax, ay - 102.0), 14.0 * pulse, glow_col)

	# Portais
	for p in room_def.get("portals", []):
		var pid: String = String(p["id"])
		var p_x: float = float(p["x"])
		var p_y: float = floor_screen_y - float(p.get("y", 0.0))
		var open_flag: bool = bool(portal_unlocked.get(pid, false))
		var pcol: Color = Color(0.24, 0.88, 1.0) if open_flag else Color(0.92, 0.18, 0.22)
		var pulse_p: float = 0.8 + 0.2 * sin(time_s * 4.5)
		draw_rect(Rect2(p_x - 36.0, p_y - 165.0, 72.0, 165.0), Color(0.05, 0.05, 0.07))
		draw_rect(Rect2(p_x - 30.0, p_y - 155.0, 60.0, 155.0), Color(pcol.r, pcol.g, pcol.b, 0.24 * pulse_p))
		draw_rect(Rect2(p_x - 36.0, p_y - 165.0, 72.0, 165.0), pcol, false, 3.0)
		if not open_flag:
			draw_line(Vector2(p_x - 24.0, p_y - 135.0), Vector2(p_x + 24.0, p_y - 35.0), pcol, 3.5)
			draw_line(Vector2(p_x + 24.0, p_y - 135.0), Vector2(p_x - 24.0, p_y - 35.0), pcol, 3.5)
