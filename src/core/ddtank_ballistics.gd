class_name DDTankBallistics
extends RefCounted
## Motor puro de balistica parabolica DDTank com vento dinamico,
## deteccao continua segmento-circulo (zero tunneling) e guia laser Zero-GC.
## Sistema cartesiano puro (+x para direita, +y para cima).

const TerrainHeightmap = preload("res://src/core/terrain_heightmap.gd")

const SOLVE_CANDIDATE_ANGLES: PackedFloat64Array = [
	50.0, 45.0, 55.0, 40.0, 60.0, 35.0, 65.0, 30.0, 70.0, 25.0, 75.0, 20.0, 80.0, 15.0, 84.0, 10.0,
	48.0, 52.0, 58.0, 62.0, 68.0, 72.0, 78.0, 38.0, 32.0, 28.0, 22.0, 18.0, 12.0, 8.0
]

enum HitZone {
	NONE_OUT_OF_BOUNDS = 0,
	TERRAIN = 1,
	LIMB_GLANCING = 2,
	BODY = 3,
	HEAD_CORE = 4,
}


static func _is_finite(v: Variant) -> bool:
	if not (v is float or v is int):
		return false
	var f: float = float(v)
	return not is_nan(f) and not is_inf(f)


static func segment_circle_intersect(
	p0x: float, p0y: float,
	p1x: float, p1y: float,
	cx: float, cy: float, r: float
) -> float:
	if r <= 0.0:
		return -1.0
	var fx: float = p0x - cx
	var fy: float = p0y - cy
	var c: float = (fx * fx) + (fy * fy) - (r * r)
	if c <= 0.0:
		return 0.0

	var dx: float = p1x - p0x
	var dy: float = p1y - p0y
	var a: float = (dx * dx) + (dy * dy)
	if a <= 1e-12:
		return -1.0

	var b: float = 2.0 * ((fx * dx) + (fy * dy))
	var disc: float = (b * b) - (4.0 * a * c)
	if disc < 0.0:
		return -1.0

	var t: float = (-b - sqrt(disc)) / (2.0 * a)
	if t >= 0.0 and t <= 1.0:
		return t
	return -1.0


static func _set_invalid(out_result: Dictionary, msg: String) -> void:
	out_result["valid"] = false
	out_result["error"] = msg
	out_result["zone"] = HitZone.NONE_OUT_OF_BOUNDS
	out_result["impact_x"] = 0.0
	out_result["impact_y"] = 0.0
	out_result["flight_time"] = 0.0
	out_result["damage_multiplier"] = 0.0
	out_result["posture_damage_ratio"] = 0.0
	out_result["is_nuclear_pow"] = false
	out_result["carve_terrain"] = false


static func _set_oob(out_result: Dictionary, ix: float, iy: float, ft: float) -> void:
	out_result["valid"] = true
	out_result["error"] = ""
	out_result["zone"] = HitZone.NONE_OUT_OF_BOUNDS
	out_result["impact_x"] = ix
	out_result["impact_y"] = iy
	out_result["flight_time"] = ft
	out_result["damage_multiplier"] = 0.0
	out_result["posture_damage_ratio"] = 0.0
	out_result["is_nuclear_pow"] = false
	out_result["carve_terrain"] = false


static func _validate_shot_and_boss(shot: Dictionary, boss: Dictionary, cfg: Dictionary) -> String:
	for sk in ["origin_x", "origin_y", "angle_deg", "power_norm", "wind"]:
		if not shot.has(sk) or not _is_finite(shot[sk]):
			return "Invalid shot field: %s" % sk
	for bk in ["head_x", "head_y", "head_radius", "body_x", "body_y", "body_radius"]:
		if not boss.has(bk) or not _is_finite(boss[bk]):
			return "Invalid boss field: %s" % bk
	var angle_deg: float = float(shot["angle_deg"])
	var power_norm: float = float(shot["power_norm"])
	var wind: float = float(shot["wind"])
	if angle_deg < float(cfg["angle_min_deg"]) - 1e-6 or angle_deg > float(cfg["angle_max_deg"]) + 1e-6:
		return "Launch angle out of configured bounds"
	if power_norm < -1e-6 or power_norm > 1.0 + 1e-6:
		return "Power norm must be in [0, 1]"
	if wind < float(cfg["wind_min"]) - 1e-6 or wind > float(cfg["wind_max"]) + 1e-6:
		return "Wind out of configured bounds"
	return ""


static func _terrain_segment_hit(
	p0x: float, p0y: float, p1x: float, p1y: float,
	terrain: TerrainHeightmap, arena_w: float
) -> float:
	if p1x < 0.0 or p1x > arena_w:
		return -1.0
	var h0: float = terrain.sample_height(p0x)
	var h1: float = terrain.sample_height(p1x)
	if p1y <= h1:
		var denom: float = (p0y - h0) - (p1y - h1)
		if abs(denom) <= 1e-9:
			return 1.0
		return clampf((p0y - h0) / denom, 0.0, 1.0)
	var mid_x: float = 0.5 * (p0x + p1x)
	var mid_y: float = 0.5 * (p0y + p1y)
	var hm: float = terrain.sample_height(mid_x)
	if mid_y <= hm:
		return 0.5
	return -1.0


static func simulate_shot_into(
	shot: Dictionary,
	boss: Dictionary,
	terrain: TerrainHeightmap,
	cfg: Dictionary,
	out_result: Dictionary
) -> void:
	if terrain == null or cfg.is_empty():
		_set_invalid(out_result, "Missing terrain or ballistics config")
		return

	var err_msg: String = _validate_shot_and_boss(shot, boss, cfg)
	if not err_msg.is_empty():
		_set_invalid(out_result, err_msg)
		return

	var angle_deg: float = float(shot["angle_deg"])
	var power_norm: float = float(shot["power_norm"])
	var wind: float = float(shot["wind"])
	var angle_min: float = float(cfg["angle_min_deg"])
	var angle_max: float = float(cfg["angle_max_deg"])
	var wind_min: float = float(cfg["wind_min"])
	var wind_max: float = float(cfg["wind_max"])

	var x0: float = float(shot["origin_x"])
	var y0: float = float(shot["origin_y"])
	var v0: float = lerpf(float(cfg["v_min"]), float(cfg["v_max"]), clampf(power_norm, 0.0, 1.0))
	var theta: float = deg_to_rad(clampf(angle_deg, angle_min, angle_max))
	var vx: float = v0 * cos(theta)
	var vy: float = v0 * sin(theta)
	var ax: float = clampf(wind, wind_min, wind_max) * float(cfg["wind_accel_factor"])
	var g: float = float(cfg["gravity"])
	var dt: float = float(cfg["fixed_dt"])
	var max_steps: int = int(ceil(float(cfg["max_flight_seconds"]) / dt))
	var arena_w: float = float(cfg["arena_logical_width"])

	var hx: float = float(boss["head_x"])
	var hy: float = float(boss["head_y"])
	var hr: float = float(boss["head_radius"])
	var bx: float = float(boss["body_x"])
	var by: float = float(boss["body_y"])
	var br: float = float(boss["body_radius"])
	var lx: float = float(boss.get("limb_x", 0.0))
	var ly: float = float(boss.get("limb_y", 0.0))
	var lr: float = float(boss.get("limb_radius", 0.0))

	var boss_min_x: float = minf(hx - hr, bx - br)
	var boss_max_x: float = maxf(hx + hr, bx + br)
	var boss_min_y: float = minf(hy - hr, by - br)
	var boss_max_y: float = maxf(hy + hr, by + br)
	if lr > 0.0:
		boss_min_x = minf(boss_min_x, lx - lr)
		boss_max_x = maxf(boss_max_x, lx + lr)
		boss_min_y = minf(boss_min_y, ly - lr)
		boss_max_y = maxf(boss_max_y, ly + lr)

	var terr_max_h: float = terrain.max_height
	var half_ax: float = 0.5 * ax
	var half_g: float = 0.5 * g

	var p0x: float = x0
	var p0y: float = y0

	for step in range(max_steps):
		var t1: float = float(step + 1) * dt
		var t1_sq: float = t1 * t1
		var p1x: float = x0 + (vx * t1) + (half_ax * t1_sq)
		var p1y: float = y0 + (vy * t1) - (half_g * t1_sq)

		var seg_min_x: float = minf(p0x, p1x)
		var seg_max_x: float = maxf(p0x, p1x)
		var seg_min_y: float = minf(p0y, p1y)
		var seg_max_y: float = maxf(p0y, p1y)

		var in_boss_aabb: bool = (seg_max_x >= boss_min_x and seg_min_x <= boss_max_x and seg_max_y >= boss_min_y and seg_min_y <= boss_max_y)
		var in_terr_aabb: bool = (seg_min_y <= terr_max_h + 0.5)

		var t_head: float = -1.0
		var t_body: float = -1.0
		var t_limb: float = -1.0
		var t_terr: float = -1.0

		if in_boss_aabb:
			t_head = segment_circle_intersect(p0x, p0y, p1x, p1y, hx, hy, hr)
			t_body = segment_circle_intersect(p0x, p0y, p1x, p1y, bx, by, br)
			if lr > 0.0:
				t_limb = segment_circle_intersect(p0x, p0y, p1x, p1y, lx, ly, lr)
		if in_terr_aabb:
			t_terr = _terrain_segment_hit(p0x, p0y, p1x, p1y, terrain, arena_w)

		var best_t: float = 2.0
		var best_zone: int = HitZone.NONE_OUT_OF_BOUNDS

		if t_terr >= 0.0:
			best_t = t_terr
			best_zone = HitZone.TERRAIN
		if t_limb >= 0.0 and t_limb <= best_t + 1e-4:
			if t_limb < best_t - 1e-4 or best_zone == HitZone.TERRAIN:
				best_t = t_limb
				best_zone = HitZone.LIMB_GLANCING
		if t_body >= 0.0 and t_body <= best_t + 1e-4:
			if t_body < best_t - 1e-4 or best_zone < HitZone.BODY:
				best_t = t_body
				best_zone = HitZone.BODY
		if t_head >= 0.0 and t_head <= best_t + 1e-4:
			best_t = t_head
			best_zone = HitZone.HEAD_CORE

		if best_zone != HitZone.NONE_OUT_OF_BOUNDS:
			var t0: float = float(step) * dt
			var hit_t: float = t0 + (best_t * dt)
			var hit_x: float = lerpf(p0x, p1x, best_t)
			var hit_y: float = lerpf(p0y, p1y, best_t)
			out_result["valid"] = true
			out_result["error"] = ""
			out_result["zone"] = best_zone
			out_result["impact_x"] = hit_x
			out_result["impact_y"] = hit_y
			out_result["flight_time"] = hit_t
			out_result["is_nuclear_pow"] = (best_zone == HitZone.HEAD_CORE)
			out_result["carve_terrain"] = (best_zone == HitZone.TERRAIN)
			match best_zone:
				HitZone.HEAD_CORE:
					out_result["damage_multiplier"] = float(cfg["head_core_multiplier"])
					out_result["posture_damage_ratio"] = 0.60
				HitZone.BODY:
					out_result["damage_multiplier"] = float(cfg["body_multiplier"])
					out_result["posture_damage_ratio"] = 0.20
				HitZone.LIMB_GLANCING:
					out_result["damage_multiplier"] = float(cfg["limb_glancing_multiplier"])
					out_result["posture_damage_ratio"] = 0.10
				_:
					out_result["damage_multiplier"] = 0.0
					out_result["posture_damage_ratio"] = 0.0
			return

		if p1x < 0.0 or p1x > arena_w or p1y < 0.0:
			_set_oob(out_result, p1x, p1y, t1)
			return

		p0x = p1x
		p0y = p1y

	_set_oob(out_result, p0x, p0y, float(max_steps) * dt)


static func evaluate_shot(
	shot: Dictionary,
	boss: Dictionary,
	terrain: TerrainHeightmap,
	cfg: Dictionary
) -> Dictionary:
	var out: Dictionary = {}
	simulate_shot_into(shot, boss, terrain, cfg, out)
	return out


static func compute_laser_guide_into(
	shot: Dictionary,
	boss: Dictionary,
	terrain: TerrainHeightmap,
	cfg: Dictionary,
	out_x: PackedFloat64Array,
	out_y: PackedFloat64Array
) -> int:
	if terrain == null or cfg.is_empty():
		return 0
	if not _validate_shot_and_boss(shot, boss, cfg).is_empty():
		return 0
	var max_pts: int = mini(int(cfg["laser_guide_points"]), mini(out_x.size(), out_y.size()))
	if max_pts <= 1:
		return 0

	var x0: float = float(shot["origin_x"])
	var y0: float = float(shot["origin_y"])
	var angle_deg: float = clampf(float(shot["angle_deg"]), float(cfg["angle_min_deg"]), float(cfg["angle_max_deg"]))
	var power_norm: float = clampf(float(shot["power_norm"]), 0.0, 1.0)
	var wind: float = clampf(float(shot["wind"]), float(cfg["wind_min"]), float(cfg["wind_max"]))

	var v0: float = lerpf(float(cfg["v_min"]), float(cfg["v_max"]), power_norm)
	var theta: float = deg_to_rad(angle_deg)
	var vx: float = v0 * cos(theta)
	var vy: float = v0 * sin(theta)
	var ax: float = wind * float(cfg["wind_accel_factor"])
	var g: float = float(cfg["gravity"])
	var guide_dt: float = float(cfg["laser_guide_dt"])
	var arena_w: float = float(cfg["arena_logical_width"])

	var hx: float = float(boss["head_x"])
	var hy: float = float(boss["head_y"])
	var hr: float = float(boss["head_radius"])
	var bx: float = float(boss["body_x"])
	var by: float = float(boss["body_y"])
	var br: float = float(boss["body_radius"])
	var lx: float = float(boss.get("limb_x", 0.0))
	var ly: float = float(boss.get("limb_y", 0.0))
	var lr: float = float(boss.get("limb_radius", 0.0))

	out_x[0] = x0
	out_y[0] = y0
	var count: int = 1
	var p0x: float = x0
	var p0y: float = y0

	for i in range(1, max_pts):
		var t: float = float(i) * guide_dt
		var t_sq_half: float = 0.5 * t * t
		var p1x: float = x0 + (vx * t) + (ax * t_sq_half)
		var p1y: float = y0 + (vy * t) - (g * t_sq_half)

		var t_head: float = segment_circle_intersect(p0x, p0y, p1x, p1y, hx, hy, hr)
		var t_body: float = segment_circle_intersect(p0x, p0y, p1x, p1y, bx, by, br)
		var t_limb: float = segment_circle_intersect(p0x, p0y, p1x, p1y, lx, ly, lr) if lr > 0.0 else -1.0
		var t_terr: float = _terrain_segment_hit(p0x, p0y, p1x, p1y, terrain, arena_w)

		var hit_t: float = 2.0
		if t_terr >= 0.0:
			hit_t = minf(hit_t, t_terr)
		if t_limb >= 0.0:
			hit_t = minf(hit_t, t_limb)
		if t_body >= 0.0:
			hit_t = minf(hit_t, t_body)
		if t_head >= 0.0:
			hit_t = minf(hit_t, t_head)

		if hit_t <= 1.0:
			out_x[count] = lerpf(p0x, p1x, hit_t)
			out_y[count] = lerpf(p0y, p1y, hit_t)
			count += 1
			break

		if p1x < 0.0 or p1x > arena_w or p1y < 0.0:
			break

		out_x[count] = p1x
		out_y[count] = p1y
		count += 1
		p0x = p1x
		p0y = p1y

	return count


static func solve_aim_for_head(
	origin_x: float,
	origin_y: float,
	boss: Dictionary,
	terrain: TerrainHeightmap,
	wind: float,
	cfg: Dictionary
) -> Dictionary:
	var tx: float = float(boss["head_x"])
	var ty: float = float(boss["head_y"])
	var dx_target: float = tx - origin_x
	var dy_target: float = ty - origin_y
	var g: float = float(cfg["gravity"])
	var ax: float = wind * float(cfg["wind_accel_factor"])
	var v_min: float = float(cfg["v_min"])
	var v_max: float = float(cfg["v_max"])
	var a_min: float = float(cfg["angle_min_deg"])
	var a_max: float = float(cfg["angle_max_deg"])

	var shot_buf: Dictionary = {
		"origin_x": origin_x,
		"origin_y": origin_y,
		"angle_deg": 45.0,
		"power_norm": 0.5,
		"wind": wind,
	}
	var res_buf: Dictionary = {}

	for i in range(SOLVE_CANDIDATE_ANGLES.size()):
		var angle_deg: float = SOLVE_CANDIDATE_ANGLES[i]
		if angle_deg < a_min or angle_deg > a_max:
			continue
		var theta: float = deg_to_rad(angle_deg)
		var cos_t: float = cos(theta)
		var sin_t: float = sin(theta)
		var denom: float = (g * cos_t) + (ax * sin_t)
		var numer: float = (dx_target * sin_t) - (dy_target * cos_t)
		if denom <= 1e-6 or numer <= 1e-6:
			continue
		var t_flight: float = sqrt((2.0 * numer) / denom)
		if t_flight <= 1e-4 or t_flight > float(cfg["max_flight_seconds"]):
			continue
		var v0: float = (dx_target - (0.5 * ax * t_flight * t_flight)) / (t_flight * cos_t)
		if v0 < v_min or v0 > v_max:
			continue
		var p_norm: float = (v0 - v_min) / (v_max - v_min)
		shot_buf["angle_deg"] = angle_deg
		shot_buf["power_norm"] = p_norm
		simulate_shot_into(shot_buf, boss, terrain, cfg, res_buf)
		if bool(res_buf.get("valid", false)) and int(res_buf.get("zone", 0)) == HitZone.HEAD_CORE:
			return {
				"found": true,
				"angle_deg": angle_deg,
				"power_norm": p_norm,
				"v0": v0,
				"flight_time": t_flight,
				"outcome": res_buf.duplicate(),
			}

	return {"found": false}
