extends SceneTree
## Runner CLI headless de validacao do template godot-2d-action-rpg.

const HarnessScript = preload("res://tests/unit/test_harness.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const SeededRngScript = preload("res://src/core/seeded_rng.gd")
const CoreScript = preload("res://src/core/game_loop_core.gd")
const SaveStoreScript = preload("res://src/engine/local_checkpoint_store.gd")
const MainScene = preload("res://src/engine/main.tscn")


func _initialize() -> void:
	var t0_usec: int = Time.get_ticks_usec()
	var t := HarnessScript.new("TemplateAction2D")

	# 1. BigNum & SeededRng determinismo basico
	var a: RefCounted = BigNumScript.from_float(100.0)
	var b: RefCounted = BigNumScript.from_float(50.0)
	t.assert_eq(int(round(a.add(b).to_approx_float())), 150, "BigNum add works")

	var rng1 := SeededRngScript.new(42)
	var rng2 := SeededRngScript.new(42)
	t.assert_eq(rng1.next_u32(), rng2.next_u32(), "SeededRng is deterministic")

	# 2. Fail-closed em config invalida
	var bad_core: RefCounted = CoreScript.parse_and_create("{invalid json")
	t.assert_false(bool(bad_core.get("valid")), "Invalid JSON rejected fail-closed")

	# 3. Boot real a partir de res://config/template_defaults.json + loop de combate
	var cfg_text: String = FileAccess.get_file_as_string("res://config/template_defaults.json")
	var core: RefCounted = CoreScript.parse_and_create(cfg_text, 777)
	t.assert_true(bool(core.get("valid")), "Valid template_defaults.json boots cleanly")

	# Simula combate ate limpar mundo 1
	var steps: int = 0
	while not bool(core.get("campaign_cleared")) and not bool(core.get("defeated")) and steps < 50:
		core.step(0.1, 1.0, true)
		steps += 1
	t.assert_true(bool(core.get("campaign_cleared")), "Demo campaign clears cleanly without softlock")
	t.assert_true(core.get("gold").to_approx_float() >= 125.0, "Gold reward accumulated")

	# 4. Persistencia fail-closed
	t.assert_true(SaveStoreScript.load_snapshot("res://config/nonexistent.json").is_empty(), "Missing save returns empty")
	var snap: Dictionary = core.export_checkpoint_snapshot()
	t.assert_true(snap.get("schema_version", 0) == 1, "Snapshot schema_version == 1")

	# 5. Instanciacao da cena principal
	var main_inst: Control = MainScene.instantiate()
	t.assert_true(main_inst != null, "MainScene instantiated")
	root.add_child(main_inst)
	await process_frame
	t.assert_true(main_inst.is_boot_valid(), "MainScene booted fail-closed cleanly")
	main_inst.queue_free()
	await process_frame

	var elapsed_ms: float = float(Time.get_ticks_usec() - t0_usec) / 1000.0
	print("=== PLAYFORGE TEMPLATE TEST RUNNER (godot-2d-action-rpg) ===")
	print("Assertions: %d | Failed: %d | Elapsed: %.2f ms" % [t.total_assertions, t.failed_assertions, elapsed_ms])
	for err in t.failures:
		printerr(err)

	if t.failed_assertions > 0 or elapsed_ms >= 1000.0:
		quit(1)
		return
	quit(0)
