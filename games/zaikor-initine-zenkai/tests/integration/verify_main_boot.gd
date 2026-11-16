extends SceneTree
## Teste de integracao real da cena principal (boot, perfis, input map e 0 nos orfaos).


func _initialize() -> void:
	var orphan_before := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
	var t_boot0 := Time.get_ticks_usec()

	var renderer_cfg := String(ProjectSettings.get_setting("rendering/renderer/rendering_method", ""))
	if renderer_cfg != "gl_compatibility":
		printerr("BOOT_FAIL: renderer esperado gl_compatibility, encontrado=%s" % renderer_cfg)
		quit(1)
		return

	var required_actions := [
		"move_forward", "move_back", "move_left", "move_right",
		"sprint", "jump", "dodge", "attack_light", "attack_heavy",
		"guard", "zenkai_activate", "interact", "pause"
	]
	for act in required_actions:
		if not InputMap.has_action(act):
			printerr("BOOT_FAIL: acao ausente no InputMap: %s" % act)
			quit(1)
			return

	var packed := ResourceLoader.load("res://scenes/main/main.tscn")
	if packed == null or not (packed is PackedScene):
		printerr("BOOT_FAIL: falha ao carregar res://scenes/main/main.tscn")
		quit(1)
		return

	var inst := (packed as PackedScene).instantiate()
	if inst == null:
		printerr("BOOT_FAIL: main.tscn retornou instancia nula")
		quit(1)
		return

	root.add_child(inst)
	await process_frame
	var boot_ms := float(Time.get_ticks_usec() - t_boot0) / 1000.0

	if not bool(inst.call("is_boot_valid")):
		printerr("BOOT_FAIL: is_boot_valid() retornou false")
		quit(1)
		return

	var t_frames0 := Time.get_ticks_usec()
	for _i in range(15):
		await process_frame
	var frames_ms := float(Time.get_ticks_usec() - t_frames0) / 1000.0

	var metrics: Dictionary = inst.call("get_runtime_metrics")
	var med_ok := bool(inst.call("apply_graphics_profile", "medium"))
	var low_ok := bool(inst.call("apply_graphics_profile", "low"))
	var invalid_ok := bool(inst.call("apply_graphics_profile", "ultra_fake"))

	inst.queue_free()
	await process_frame
	await process_frame
	var orphan_after := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
	var orphan_delta := maxi(0, orphan_after - orphan_before)

	var summary := {
		"boot_valid": true,
		"rendering_method": renderer_cfg,
		"boot_ms": snappedf(boot_ms, 0.01),
		"avg_step_ms": snappedf(frames_ms / 15.0, 0.01),
		"static_memory_mb": metrics.get("static_memory_mb", 0.0),
		"profile_switch_medium": med_ok,
		"profile_restore_low": low_ok,
		"invalid_profile_blocked": not invalid_ok,
		"orphan_nodes_after_free": orphan_after,
		"orphan_nodes_delta": orphan_delta,
		"input_actions_verified": required_actions.size(),
	}
	print("=== ZAIKOR: INITINE ZENKAI MAIN SCENE BOOT & BASELINE ===")
	print(JSON.stringify(summary))

	var ok := med_ok and low_ok and (not invalid_ok) and orphan_delta == 0 and orphan_after == 0
	quit(0 if ok else 1)
