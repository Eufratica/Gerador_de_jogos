extends SceneTree
## Verificacao headless gerada pela PlayForge Factory (Fase 5) para: chrono-blade

const HarnessScript = preload("res://tests/unit/test_harness.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const SeededRngScript = preload("res://src/core/seeded_rng.gd")
const CoreScript = preload("res://src/core/game_loop_core.gd")
const SaveStoreScript = preload("res://src/engine/local_checkpoint_store.gd")
const MainScene = preload("res://src/engine/main.tscn")

const EXPECTED_GAME_ID: String = "chrono-blade"
const EXPECTED_GAME_NAME: String = "Chrono Blade"
const EXPECTED_WORLDS: int = 1
const EXPECTED_TOTAL_ROOMS: int = 2
const EXPECTED_MIN_GOLD: float = 82.5


func _initialize() -> void:
	var t0_usec: int = Time.get_ticks_usec()
	var t := HarnessScript.new("GeneratedGame:" + EXPECTED_GAME_ID)

	# 1. Invariantes puros herdados (BigNum, SeededRng e fail-closed JSON)
	var a: RefCounted = BigNumScript.from_float(100.0)
	var b: RefCounted = BigNumScript.from_float(50.0)
	t.assert_eq(int(round(a.add(b).to_approx_float())), 150, "BigNum add deterministic")
	var rng1 := SeededRngScript.new(42)
	var rng2 := SeededRngScript.new(42)
	t.assert_eq(rng1.next_u32(), rng2.next_u32(), "SeededRng deterministic")
	var bad_core: RefCounted = CoreScript.parse_and_create("{invalid json")
	t.assert_false(bool(bad_core.get("valid")), "Invalid JSON rejected fail-closed")

	# 2. Config parametrizada da GameSpecification
	var cfg_exists: bool = FileAccess.file_exists("res://config/template_defaults.json")
	t.assert_true(cfg_exists, "Config template_defaults.json exists")
	var cfg_text: String = FileAccess.get_file_as_string("res://config/template_defaults.json")

	var parsed = JSON.parse_string(cfg_text)
	t.assert_true(parsed is Dictionary, "Config parses as Dictionary")
	if parsed is Dictionary:
		t.assert_eq(String(parsed.get("game_id", "")), EXPECTED_GAME_ID, "Config game_id matches project_id")
		t.assert_eq(String(parsed.get("game_name", "")), EXPECTED_GAME_NAME, "Config game_name matches spec")
		var ws: Array = parsed.get("worlds", [])
		t.assert_eq(ws.size(), EXPECTED_WORLDS, "Config world count matches spec")
		var room_sum: int = 0
		for w in ws:
			room_sum += (w.get("rooms", []) as Array).size()
		t.assert_eq(room_sum, EXPECTED_TOTAL_ROOMS, "Config room count matches spec")

	# 3. Simulacao deterministica completa de campanha
	var core: RefCounted = CoreScript.parse_and_create(cfg_text, 202605)
	t.assert_true(bool(core.get("valid")), "GameLoopCore boots generated config")

	var steps: int = 0
	while not bool(core.get("campaign_cleared")) and not bool(core.get("defeated")) and steps < 500:
		core.step(0.1, 1.0, true)
		steps += 1
	t.assert_true(bool(core.get("campaign_cleared")), "Generated campaign clears without softlock")
	t.assert_false(bool(core.get("defeated")), "Hero survives generated campaign")
	t.assert_true(core.get("gold").to_approx_float() + 0.01 >= EXPECTED_MIN_GOLD, "Economy reward matches rooms")

	# 4. Persistencia fail-closed + roundtrip
	t.assert_true(SaveStoreScript.load_snapshot("res://config/nonexistent.json").is_empty(), "Missing save returns empty")
	var snap: Dictionary = core.export_checkpoint_snapshot()
	var save_path: String = "user://generated_verify_" + EXPECTED_GAME_ID + ".json"
	t.assert_true(SaveStoreScript.save_snapshot(snap, save_path), "Checkpoint save succeeds")
	var loaded: Dictionary = SaveStoreScript.load_snapshot(save_path)
	t.assert_eq(String(loaded.get("game_id", "")), EXPECTED_GAME_ID, "Checkpoint load preserves game_id")
	SaveStoreScript.clear_save(save_path)

	# 5. Boot real da cena Main.tscn
	var main_inst: Control = MainScene.instantiate()
	t.assert_true(main_inst != null, "MainScene instantiates cleanly")
	root.add_child(main_inst)
	await process_frame
	t.assert_true(main_inst.is_boot_valid(), "MainScene boot gate valid")
	main_inst.queue_free()
	await process_frame

	var elapsed_ms: float = float(Time.get_ticks_usec() - t0_usec) / 1000.0
	print("=== PLAYFORGE GENERATED GAME VERIFICATION (%s) ===" % EXPECTED_GAME_ID)
	print("Assertions: %d | Failed: %d | Elapsed: %.2f ms" % [t.total_assertions, t.failed_assertions, elapsed_ms])
	for err in t.failures:
		printerr(err)

	if t.failed_assertions > 0 or elapsed_ms >= 1000.0:
		quit(1)
		return
	quit(0)
