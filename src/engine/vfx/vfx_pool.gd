extends Node2D
## Pools Zero-GC de VFX das 4 magias, projéteis e numeros flutuantes de dano.

const MAX_BURSTS: int = 36
const MAX_TEXTS: int = 48
const MAX_SPARKS: int = 64

var floor_screen_y: float = 860.0
var _bursts: Array[Dictionary] = []
var _texts: Array[Dictionary] = []
var _sparks: Array[Dictionary] = []
var _burst_cur: int = 0
var _text_cur: int = 0
var _spark_cur: int = 0
var _projectiles_ref: Array = []
var _font: Font = null
var _pools_ready: bool = false


func _ready() -> void:
	_ensure_pools()


func _ensure_pools() -> void:
	if _pools_ready:
		return
	_pools_ready = true
	_font = ThemeDB.fallback_font
	for _i in range(MAX_BURSTS):
		_bursts.append({"active": false, "kind": "", "x": 0.0, "y": 0.0, "t": 0.0, "dur": 0.4, "dir": 1, "col": Color.WHITE})
	for _i in range(MAX_TEXTS):
		_texts.append({"active": false, "text": "", "x": 0.0, "y": 0.0, "vy": -70.0, "t": 0.0, "dur": 0.75, "scale": 1.0, "col": Color.WHITE})
	for _i in range(MAX_SPARKS):
		_sparks.append({"active": false, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "t": 0.0, "dur": 0.35, "col": Color.ORANGE})


func spawn_magic(skill_id: String, world_x: float, world_y: float, dir: int) -> void:
	_ensure_pools()
	var b: Dictionary = _bursts[_burst_cur]
	_burst_cur = (_burst_cur + 1) % MAX_BURSTS
	b["active"] = true
	b["kind"] = skill_id
	b["x"] = world_x
	b["y"] = floor_screen_y - world_y - 48.0
	b["t"] = 0.0
	b["dur"] = 0.55
	b["dir"] = dir
	var spark_col := Color(1.0, 0.45, 0.12)
	if skill_id == "glacial_tempest":
		spark_col = Color(0.35, 0.92, 1.0)
	elif skill_id == "sky_lightning":
		spark_col = Color(1.0, 0.95, 0.35)
	elif skill_id == "titan_aegis":
		spark_col = Color(0.35, 0.85, 1.0)
	b["col"] = spark_col
	spawn_sparks(world_x, floor_screen_y - world_y - 45.0, spark_col, 10)


func spawn_text(text: String, world_x: float, world_y: float, col: Color, scale_mult: float = 1.0) -> void:
	_ensure_pools()
	var d: Dictionary = _texts[_text_cur]
	_text_cur = (_text_cur + 1) % MAX_TEXTS
	d["active"] = true
	d["text"] = text
	d["x"] = world_x + float((_text_cur % 5) - 2) * 14.0
	d["y"] = floor_screen_y - world_y - 110.0
	d["vy"] = -85.0
	d["t"] = 0.0
	d["dur"] = 0.78
	d["scale"] = scale_mult
	d["col"] = col


func spawn_sparks(screen_x: float, screen_y: float, col: Color, count: int) -> void:
	_ensure_pools()
	for i in range(count):
		var s: Dictionary = _sparks[_spark_cur]
		_spark_cur = (_spark_cur + 1) % MAX_SPARKS
		var ang: float = (TAU / float(maxi(1, count))) * float(i) + float(_spark_cur) * 0.25
		var spd: float = 160.0 + float((i * 53) % 180)
		s["active"] = true
		s["x"] = screen_x
		s["y"] = screen_y
		s["vx"] = cos(ang) * spd
		s["vy"] = sin(ang) * spd - 60.0
		s["t"] = 0.0
		s["dur"] = 0.36
		s["col"] = col


func set_projectiles(projs: Array) -> void:
	_projectiles_ref = projs


func tick(dt: float) -> void:
	var any_active: bool = not _projectiles_ref.is_empty()
	for b in _bursts:
		if bool(b["active"]):
			any_active = true
			b["t"] = float(b["t"]) + dt
			if float(b["t"]) >= float(b["dur"]):
				b["active"] = false
	for d in _texts:
		if bool(d["active"]):
			any_active = true
			d["t"] = float(d["t"]) + dt
			d["y"] = float(d["y"]) + float(d["vy"]) * dt
			d["vy"] = float(d["vy"]) * 0.96
			if float(d["t"]) >= float(d["dur"]):
				d["active"] = false
	for s in _sparks:
		if bool(s["active"]):
			any_active = true
			s["t"] = float(s["t"]) + dt
			s["x"] = float(s["x"]) + float(s["vx"]) * dt
			s["y"] = float(s["y"]) + float(s["vy"]) * dt
			s["vy"] = float(s["vy"]) + 420.0 * dt
			if float(s["t"]) >= float(s["dur"]):
				s["active"] = false
	if any_active:
		queue_redraw()


func _draw() -> void:
	# Projeteis sombrios
	for p in _projectiles_ref:
		if not bool(p.get("active", false)):
			continue
		var pos := Vector2(float(p["x"]), floor_screen_y - float(p["y"]))
		draw_circle(pos, float(p.get("radius", 24.0)), Color(0.75, 0.22, 0.95, 0.78))
		draw_circle(pos, 10.0, Color(1.0, 0.85, 1.0))

	# Bursts das 4 Magias
	for b in _bursts:
		if not bool(b["active"]):
			continue
		var p: float = float(b["t"]) / maxf(0.01, float(b["dur"]))
		var a: float = clampf(1.0 - p, 0.0, 1.0)
		var pos := Vector2(float(b["x"]), float(b["y"]))
		var col: Color = b["col"]
		var kind: String = String(b["kind"])

		if kind == "chaos_flames":
			var r: float = lerpf(40.0, 270.0, p)
			draw_circle(pos, r, Color(1.0, 0.35, 0.08, 0.26 * a))
			draw_arc(pos, r, 0.0, TAU, 32, Color(1.0, 0.78, 0.18, a), 8.0)
		elif kind == "glacial_tempest":
			var dir_x: float = float(b["dir"])
			var reach: float = lerpf(80.0, 350.0, p)
			var tri := PackedVector2Array([
				pos,
				pos + Vector2(dir_x * reach, -125.0 * (0.4 + p)),
				pos + Vector2(dir_x * reach, 65.0),
			])
			draw_colored_polygon(tri, Color(0.30, 0.88, 1.0, 0.35 * a))
			draw_polyline(tri, Color(0.85, 0.98, 1.0, a), 3.0)
		elif kind == "sky_lightning":
			var top_pt := Vector2(pos.x, pos.y - 680.0)
			var mid1 := Vector2(pos.x - 28.0, pos.y - 430.0)
			var mid2 := Vector2(pos.x + 26.0, pos.y - 210.0)
			draw_line(top_pt, mid1, Color(1.0, 0.95, 0.35, a), 14.0 * a + 2.0)
			draw_line(mid1, mid2, Color(1.0, 0.98, 0.75, a), 12.0 * a + 2.0)
			draw_line(mid2, pos + Vector2(0.0, 42.0), Color(1.0, 1.0, 1.0, a), 10.0 * a + 2.0)
			draw_arc(pos + Vector2(0.0, 38.0), lerpf(20.0, 165.0, p), 0.0, TAU, 24, Color(1.0, 0.92, 0.35, a), 5.0)
		elif kind == "titan_aegis":
			var r_a: float = lerpf(50.0, 300.0, p)
			draw_circle(pos, 110.0, Color(0.25, 0.85, 1.0, 0.24 * a))
			draw_arc(pos, r_a, 0.0, TAU, 36, Color(0.55, 0.95, 1.0, a), 7.0)
		elif kind == "altar_heal":
			draw_rect(Rect2(pos.x - 36.0, pos.y - 360.0, 72.0, 400.0), Color(0.25, 0.98, 0.88, 0.35 * a))
		else:
			draw_arc(pos, lerpf(18.0, 90.0, p), 0.0, TAU, 16, Color(col.r, col.g, col.b, a), 4.0)

	# Sparks
	for s in _sparks:
		if not bool(s["active"]):
			continue
		var a_s: float = clampf(1.0 - float(s["t"]) / maxf(0.01, float(s["dur"])), 0.0, 1.0)
		var col_s: Color = s["col"]
		draw_circle(Vector2(float(s["x"]), float(s["y"])), 3.8 * a_s + 1.0, Color(col_s.r, col_s.g, col_s.b, a_s))

	# Numeros flutuantes de dano
	if _font != null:
		for d in _texts:
			if not bool(d["active"]):
				continue
			var a_t: float = clampf(1.0 - float(d["t"]) / maxf(0.01, float(d["dur"])), 0.0, 1.0)
			var c_t: Color = d["col"]
			var fsz: int = int(26.0 * float(d["scale"]))
			draw_string(_font, Vector2(float(d["x"]), float(d["y"])), String(d["text"]), HORIZONTAL_ALIGNMENT_CENTER, -1, fsz, Color(c_t.r, c_t.g, c_t.b, a_t))
