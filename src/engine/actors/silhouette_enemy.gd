extends Node2D
## Silhuetas Dark Fantasy dos inimigos e Chefes Titanicos com telegrafos claros e status elementais.

const CoreScript = preload("res://src/core/action_combat_core.gd")

var enemy_data: Dictionary = {}
var anim_t: float = 0.0


func update_from_core(e: Dictionary, floor_y: float, dt: float) -> void:
	anim_t += dt
	enemy_data = e
	var ai: int = int(e.get("ai_state", 0))
	visible = (ai != CoreScript.EnemyAi.DEAD)
	if not visible:
		return
	position = Vector2(float(e.get("x", 0.0)), floor_y - float(e.get("y", 0.0)))
	queue_redraw()


func _draw() -> void:
	if enemy_data.is_empty():
		return
	var arch: String = String(enemy_data.get("archetype", "shade_stalker"))
	var is_boss: bool = bool(enemy_data.get("is_boss", false))
	var facing: int = int(enemy_data.get("facing", -1))
	var ai: int = int(enemy_data.get("ai_state", 0))

	var sil: Color = Color(0.05, 0.04, 0.07)
	var eye_col: Color = Color(1.0, 0.25, 0.22)
	var scale_h: float = 195.0 if is_boss else (130.0 if arch == "bone_sentinel" else 102.0)
	var body_w: float = 48.0 if is_boss else (28.0 if arch == "bone_sentinel" else 20.0)

	# Tinta visual de status elemental
	if float(enemy_data.get("freeze_s", 0.0)) > 0.0:
		sil = Color(0.10, 0.25, 0.36)
		eye_col = Color(0.45, 0.95, 1.0)
	elif float(enemy_data.get("burn_s", 0.0)) > 0.0:
		eye_col = Color(1.0, 0.62, 0.12)
	elif float(enemy_data.get("shock_s", 0.0)) > 0.0:
		eye_col = Color(1.0, 0.95, 0.30)

	# Telegrago inequivoco de ataque (WINDUP) ou QTE vulneravel
	if ai == CoreScript.EnemyAi.WINDUP:
		var pulse: float = 0.7 + 0.3 * sin(anim_t * 28.0)
		draw_circle(Vector2(0.0, -scale_h * 0.6), body_w * 1.9, Color(1.0, 0.18, 0.14, 0.25 * pulse))
		draw_line(Vector2(0.0, -scale_h - 46.0), Vector2(0.0, -scale_h - 22.0), Color(1.0, 0.25, 0.15), 5.0)
		draw_circle(Vector2(0.0, -scale_h - 14.0), 3.5, Color(1.0, 0.25, 0.15))
	elif ai == CoreScript.EnemyAi.QTE_VULNERABLE or ai == CoreScript.EnemyAi.STAGGERED:
		draw_circle(Vector2(0.0, -scale_h * 0.55), body_w * 2.1, Color(1.0, 0.85, 0.20, 0.22))

	if arch == "hex_acolyte":
		var hover: float = sin(anim_t * 4.5) * 9.0
		var robe := PackedVector2Array([
			Vector2(-24.0, -14.0 + hover),
			Vector2(0.0, -108.0 + hover),
			Vector2(24.0, -14.0 + hover),
		])
		draw_colored_polygon(robe, sil)
		draw_circle(Vector2(float(facing) * 6.0, -82.0 + hover), 4.0, Color(0.76, 0.32, 1.0))
		draw_circle(Vector2(float(facing) * 32.0, -64.0 + hover), 9.0, Color(0.82, 0.25, 1.0, 0.85))
	else:
		# Corpo musculoso/armadura + chifres se Chefe Titanico
		var leg_off: float = sin(anim_t * 10.0) * (10.0 if ai == CoreScript.EnemyAi.CHASE else 0.0)
		draw_line(Vector2(-body_w * 0.45, -scale_h * 0.35), Vector2(-body_w * 0.55 + leg_off, 0.0), sil, 14.0 if is_boss else 8.0)
		draw_line(Vector2(body_w * 0.45, -scale_h * 0.35), Vector2(body_w * 0.55 - leg_off, 0.0), sil, 14.0 if is_boss else 8.0)

		var torso := PackedVector2Array([
			Vector2(-body_w * 0.75, -scale_h * 0.34),
			Vector2(-body_w, -scale_h * 0.82),
			Vector2(body_w, -scale_h * 0.82),
			Vector2(body_w * 0.75, -scale_h * 0.34),
		])
		draw_colored_polygon(torso, sil)
		draw_circle(Vector2(0.0, -scale_h * 0.90), body_w * 0.45, sil)
		draw_circle(Vector2(float(facing) * body_w * 0.22, -scale_h * 0.91), 5.0 if is_boss else 3.5, eye_col)

		if is_boss:
			var horn_col: Color = Color(1.0, 0.45, 0.14) if arch == "abyss_colossus_w2" else Color(0.75, 0.78, 0.85)
			draw_line(Vector2(-16.0, -scale_h * 0.98), Vector2(-34.0, -scale_h * 1.15), horn_col, 6.0)
			draw_line(Vector2(16.0, -scale_h * 0.98), Vector2(34.0, -scale_h * 1.15), horn_col, 6.0)

		# Arma pesada + golpe visivel em STRIKE
		var weap_col: Color = Color(1.0, 0.24, 0.14) if ai == CoreScript.EnemyAi.WINDUP or ai == CoreScript.EnemyAi.STRIKE else Color(0.55, 0.58, 0.68)
		var weap_start := Vector2(float(facing) * body_w * 0.5, -scale_h * 0.65)
		var weap_end := Vector2(float(facing) * (body_w + 55.0), -scale_h * 0.35)
		if ai == CoreScript.EnemyAi.WINDUP:
			weap_end = Vector2(-float(facing) * 32.0, -scale_h * 1.18)
		elif ai == CoreScript.EnemyAi.STRIKE:
			weap_end = Vector2(float(facing) * (body_w + 115.0), -scale_h * 0.25)
			draw_arc(Vector2(0.0, -scale_h * 0.5), body_w + 95.0, -0.55 if facing > 0 else PI - 0.55, 0.55 if facing > 0 else PI + 0.55, 12, Color(1.0, 0.25, 0.18, 0.8), 10.0)
		draw_line(weap_start, weap_end, weap_col, 9.0 if is_boss else 5.0)

	# Mini barra HP e Postura acima de inimigos comuns (Chefe usa HUD topo)
	if not is_boss:
		var hp_val: float = (enemy_data["hp"] as RefCounted).to_approx_float()
		var hp_max: float = maxf(1.0, (enemy_data["max_hp"] as RefCounted).to_approx_float())
		var ratio: float = clampf(hp_val / hp_max, 0.0, 1.0)
		var pos_r: float = clampf(float(enemy_data.get("posture", 0.0)) / maxf(1.0, float(enemy_data.get("posture_max", 1.0))), 0.0, 1.0)
		var bar_y: float = -scale_h - 18.0
		draw_rect(Rect2(-32.0, bar_y, 64.0, 6.0), Color(0.08, 0.08, 0.10, 0.9))
		draw_rect(Rect2(-32.0, bar_y, 64.0 * ratio, 6.0), Color(0.92, 0.18, 0.22))
		draw_rect(Rect2(-32.0, bar_y + 7.0, 64.0 * pos_r, 3.0), Color(0.98, 0.78, 0.22))
