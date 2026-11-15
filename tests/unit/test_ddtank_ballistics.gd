extends RefCounted
## Testes unitarios puros de TerrainHeightmap, colisao continua,
## Guia Laser Zero-GC e varredura de 1.320 combinacoes balisticas DDTank.

const ConfigScript = preload("res://src/core/balance_config.gd")
const TerrainScript = preload("res://src/core/terrain_heightmap.gd")
const BallisticsScript = preload("res://src/core/ddtank_ballistics.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func run() -> RefCounted:
	var t := HarnessScript.new("DDTankBallistics")

	var f := FileAccess.open("res://config/balance_v1.json", FileAccess.READ)
	var cfg := ConfigScript.parse_and_validate(f.get_as_text() if f != null else "")
	t.assert_true(cfg.is_valid(), "config valid for ballistics suite")
	var bcfg: Dictionary = cfg.get_ballistics_config()

	# 1. TerrainHeightmap: perfil, cratera e bedrock
	var terrain := TerrainScript.new(1920.0, 180.0, 40.0)
	t.assert_near(terrain.sample_height(500.0), 180.0, 1e-6, "flat terrain initial height")
	var cols_mod: int = terrain.carve_crater(600.0, 180.0, 56.0)
	t.assert_true(cols_mod > 0, "crater modified columns")
	t.assert_near(terrain.sample_height(600.0), 124.0, 2.0, "crater center lowered by radius 56")
	t.assert_near(terrain.sample_height(800.0), 180.0, 1e-6, "outside crater untouched")

	# Escavar repetidamente ate bedrock nao pode descer abaixo de 40.0
	for _k in range(10):
		terrain.carve_crater(600.0, 50.0, 80.0)
	t.assert_true(terrain.sample_height(600.0) >= 40.0 - 1e-6, "crater clamped at bedrock_y")

	# 2. Anti-tunneling segment_circle_intersect (segmento longo atravessando alvo pequeno)
	var t_hit: float = BallisticsScript.segment_circle_intersect(0.0, 100.0, 1000.0, 100.0, 500.0, 100.0, 5.0)
	t.assert_true(t_hit > 0.45 and t_hit < 0.55, "continuous segment intersection catches tiny target")
	t.assert_near(BallisticsScript.segment_circle_intersect(0.0, 100.0, 1000.0, 100.0, 500.0, 200.0, 5.0), -1.0, 1e-6, "segment miss returns -1")

	# 3. Zonas de acerto e fail-closed em entradas invalidas
	var flat_terrain := TerrainScript.new(1920.0, 180.0, 40.0)
	var boss := {
		"head_x": 1480.0,
		"head_y": 420.0,
		"head_radius": 42.0,
		"body_x": 1480.0,
		"body_y": 275.0,
		"body_radius": 92.0,
		"limb_x": 1390.0,
		"limb_y": 270.0,
		"limb_radius": 38.0,
	}

	var invalid_shot := BallisticsScript.evaluate_shot(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": 95.0, "power_norm": 0.5, "wind": 0.0},
		boss, flat_terrain, bcfg
	)
	t.assert_false(bool(invalid_shot["valid"]), "reject out-of-bounds angle 95 deg")

	var nan_shot := BallisticsScript.evaluate_shot(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": NAN, "power_norm": 0.5, "wind": 0.0},
		boss, flat_terrain, bcfg
	)
	t.assert_false(bool(nan_shot["valid"]), "reject NaN launch angle")

	# Tiro baixo que cai no chao, escava cratera e altera o ponto de impacto do tiro seguinte
	var crater_terrain := TerrainScript.new(1920.0, 180.0, 40.0)
	var low_params := {"origin_x": 220.0, "origin_y": 210.0, "angle_deg": 20.0, "power_norm": 0.15, "wind": 0.0}
	var low_shot := BallisticsScript.evaluate_shot(low_params, boss, crater_terrain, bcfg)
	t.assert_true(bool(low_shot["valid"]), "low shot valid")
	t.assert_eq(int(low_shot["zone"]), BallisticsScript.HitZone.TERRAIN, "low shot hits TERRAIN")
	t.assert_true(bool(low_shot["carve_terrain"]), "terrain hit flags carve_terrain")
	crater_terrain.carve_crater(float(low_shot["impact_x"]), float(low_shot["impact_y"]), float(bcfg["crater_radius_px"]))
	var second_low := BallisticsScript.evaluate_shot(low_params, boss, crater_terrain, bcfg)
	t.assert_true(float(second_low["impact_y"]) < float(low_shot["impact_y"]) - 5.0, "crater deepens subsequent shot impact")

	# Zonas BODY (1x), LIMB_GLANCING (0.5x) e NONE_OUT_OF_BOUNDS
	var body_sol := BallisticsScript.solve_aim_for_head(
		220.0, 210.0,
		{"head_x": boss["body_x"], "head_y": boss["body_y"], "head_radius": 20.0, "body_x": boss["body_x"], "body_y": boss["body_y"], "body_radius": 10.0},
		flat_terrain, 0.0, bcfg
	)
	t.assert_true(bool(body_sol["found"]), "body solver found")
	var body_hit := BallisticsScript.evaluate_shot(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": body_sol.get("angle_deg", 45.0), "power_norm": body_sol.get("power_norm", 0.5), "wind": 0.0},
		boss, flat_terrain, bcfg
	)
	t.assert_eq(int(body_hit["zone"]), BallisticsScript.HitZone.BODY, "body hit zone detected")
	t.assert_near(float(body_hit["damage_multiplier"]), 1.0, 1e-6, "body multiplier is 1.0x")

	var limb_sol := BallisticsScript.solve_aim_for_head(
		220.0, 210.0,
		{"head_x": boss["limb_x"], "head_y": boss["limb_y"], "head_radius": 15.0, "body_x": 1800.0, "body_y": 900.0, "body_radius": 10.0},
		flat_terrain, 0.0, bcfg
	)
	t.assert_true(bool(limb_sol["found"]), "limb solver found")
	var limb_hit := BallisticsScript.evaluate_shot(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": limb_sol.get("angle_deg", 45.0), "power_norm": limb_sol.get("power_norm", 0.5), "wind": 0.0},
		boss, flat_terrain, bcfg
	)
	t.assert_eq(int(limb_hit["zone"]), BallisticsScript.HitZone.LIMB_GLANCING, "limb hit zone detected")
	t.assert_near(float(limb_hit["damage_multiplier"]), 0.5, 1e-6, "limb multiplier is 0.5x")

	var oob_shot := BallisticsScript.evaluate_shot(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": 45.0, "power_norm": 1.0, "wind": 100.0},
		boss, flat_terrain, bcfg
	)
	t.assert_eq(int(oob_shot["zone"]), BallisticsScript.HitZone.NONE_OUT_OF_BOUNDS, "max power + tailwind overshoots arena")

	# 4. Guia Laser Atomico Zero-GC usando buffers pre-alocados
	var solved := BallisticsScript.solve_aim_for_head(220.0, 210.0, boss, flat_terrain, -60.0, bcfg)
	t.assert_true(bool(solved["found"]), "solver finds head solution with wind=-60")
	var guide_x := PackedFloat64Array()
	var guide_y := PackedFloat64Array()
	guide_x.resize(int(bcfg["laser_guide_points"]))
	guide_y.resize(int(bcfg["laser_guide_points"]))
	var pt_count: int = BallisticsScript.compute_laser_guide_into(
		{"origin_x": 220.0, "origin_y": 210.0, "angle_deg": solved["angle_deg"], "power_norm": solved["power_norm"], "wind": -60.0},
		boss, flat_terrain, bcfg, guide_x, guide_y
	)
	t.assert_true(pt_count >= 5 and pt_count <= int(bcfg["laser_guide_points"]), "laser guide points within buffer")
	var last_dx: float = guide_x[pt_count - 1] - float(boss["head_x"])
	var last_dy: float = guide_y[pt_count - 1] - float(boss["head_y"])
	t.assert_true(sqrt((last_dx * last_dx) + (last_dy * last_dy)) <= float(boss["head_radius"]) + 5.0, "laser guide ends at HEAD_CORE")

	# 5. Varredura massiva: 11 ventos x 10 distancias x 4 elevacoes x 3 perfis de terreno = 1.320 combinacoes!
	var winds: Array[float] = [-100.0, -80.0, -60.0, -40.0, -20.0, 0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
	var total_scenarios: int = 0
	var head_hits: int = 0
	var sweep_terrain := TerrainScript.new(1920.0, 180.0, 40.0)
	var test_boss := boss.duplicate()

	for preset_idx in range(3):
		if preset_idx == 0:
			sweep_terrain.reset_flat(180.0)
		elif preset_idx == 1:
			sweep_terrain.set_profile_slope(150.0, 260.0)
		else:
			sweep_terrain.reset_flat(180.0)
			sweep_terrain.carve_crater(220.0, 180.0, 48.0)
			sweep_terrain.carve_crater(850.0, 180.0, 56.0)
			sweep_terrain.carve_crater(1220.0, 180.0, 56.0)

		var player_y: float = sweep_terrain.sample_height(220.0) + 32.0

		for d_idx in range(10):
			var boss_x: float = lerpf(1320.0, 1580.0, float(d_idx) / 9.0)
			var base_boss_ground: float = sweep_terrain.sample_height(boss_x)

			for elev_idx in range(4):
				var head_offset_y: float = 200.0 + float(elev_idx) * 65.0
				test_boss["head_x"] = boss_x
				test_boss["head_y"] = base_boss_ground + head_offset_y
				test_boss["body_x"] = boss_x
				test_boss["body_y"] = base_boss_ground + head_offset_y - 140.0
				test_boss["limb_x"] = boss_x - 85.0
				test_boss["limb_y"] = base_boss_ground + head_offset_y - 145.0

				for w in winds:
					total_scenarios += 1
					var sol := BallisticsScript.solve_aim_for_head(220.0, player_y, test_boss, sweep_terrain, w, bcfg)
					if bool(sol["found"]):
						var out: Dictionary = sol["outcome"]
						if bool(out["is_nuclear_pow"]) and is_equal_approx(float(out["damage_multiplier"]), 10.0):
							head_hits += 1

	t.assert_true(total_scenarios >= 1000, "ran >= 1000 ballistic scenarios (actual=%d)" % total_scenarios)
	t.assert_eq(head_hits, total_scenarios, "all %d ballistic combinations hit HEAD_CORE (10x POW!)" % total_scenarios)

	return t
