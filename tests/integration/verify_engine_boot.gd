extends SceneTree
## Teste de integracao headless do cliente visual Sprint 4B (main.tscn + battle_arena.tscn).
## Verifica instanciacao completa sem erros de parse, simulacao de frames e cleanup limpo.

const HarnessScript = preload("res://tests/unit/test_harness.gd")
const MainScene = preload("res://src/engine/main.tscn")
const ArenaScene = preload("res://src/engine/scenes/battle_arena.tscn")
const SaveStoreScript = preload("res://src/engine/services/local_checkpoint_store.gd")


func _initialize() -> void:
	var t := HarnessScript.new("EngineBoot4B")

	var custom_save_path: String = ""
	for arg in OS.get_cmdline_user_args():
		if String(arg).begins_with("--save-path="):
			custom_save_path = String(arg).substr("--save-path=".length())

	# 1. Testa LocalCheckpointStore fail-closed contra caminho inexistente
	var bad_load: Dictionary = SaveStoreScript.load_snapshot("res://config/does_not_exist.json")
	t.assert_true(bad_load.is_empty(), "missing checkpoint returns empty safely")

	# 2. Instancia MainScene (Tela Titulo) dentro da SceneTree (sem chamar _ready manual!)
	var main_inst: Control = MainScene.instantiate()
	main_inst.save_path = custom_save_path
	t.assert_true(main_inst != null, "MainScene instantiated")
	root.add_child(main_inst)
	await process_frame
	t.assert_true(main_inst.get("_title_layer") != null, "Title screen layer built cleanly by SceneTree")

	# Dispara Novo Jogo -> instancia BattleArena com ActionCombatCore completo
	main_inst._on_new_game_pressed()
	await process_frame
	var arena: Node2D = main_inst.get("_active_arena")
	t.assert_true(arena != null, "BattleArena instantiated via Main")
	if arena == null:
		printerr("FATAL: BattleArena null after _on_new_game_pressed")
		quit(1)
		return
	t.assert_true(arena.is_boot_valid(), "BattleArena booted fail-closed JSONs cleanly")

	# 3. Executa 10 frames reais + abre e fecha Altar/Forja + casta magia 0 via core
	for _i in range(10):
		await process_frame

	arena._pulse_skill = 0
	await process_frame
	t.assert_true(arena.core.skill_cooldowns[0] > 0.0, "engine frame forwards magic skill input to core")

	arena._on_open_forge()
	t.assert_true(arena.get("_forge").visible, "Forge modal opens")
	arena._on_close_forge()
	t.assert_false(arena.get("_forge").visible, "Forge modal closes")

	# 4. Salva snapshot (se custom_save_path fornecido via CLI) + retorna ao titulo + valida Continuar + Offline
	var snap: Dictionary = arena.core.export_checkpoint_snapshot(int(Time.get_unix_time_from_system() * 1000.0) - 120_000)
	if not custom_save_path.is_empty():
		t.assert_true(SaveStoreScript.save_snapshot(snap, custom_save_path), "custom save snapshot wrote cleanly")
	main_inst._on_exited_to_title()
	await process_frame
	t.assert_true(main_inst.get("_active_arena") == null, "Arena freed on exit to title")
	if not custom_save_path.is_empty():
		t.assert_true(not main_inst.get("_continue_btn").disabled, "Continue button enabled when save exists")
		main_inst._on_continue_pressed()
		await process_frame
		var arena_cont: Node2D = main_inst.get("_active_arena")
		t.assert_true(arena_cont != null and arena_cont.is_boot_valid(), "Continue from Altar restored BattleArena")
		main_inst._on_exited_to_title()
		await process_frame
		SaveStoreScript.clear_save(custom_save_path)

	# 5. Boot direto de ArenaScene restaurando snapshot com 120s de offline pendente
	var arena2: Node2D = ArenaScene.instantiate()
	arena2.configure_boot(snap, custom_save_path)
	root.add_child(arena2)
	await process_frame
	t.assert_true(arena2.is_boot_valid(), "ArenaScene restored checkpoint cleanly")
	var pend: Dictionary = arena2.get("_pending_offline_res")
	t.assert_true(bool(pend.get("ok", false)) and int(pend.get("effective_seconds", 0)) >= 119, "Offline chest pending time preserved across restore")

	# Limpeza para nao deixar leaked nodes no SceneTree headless
	main_inst.queue_free()
	arena2.queue_free()
	await process_frame

	print("=== PLAYFORGE ENGINE BOOT & WIRING TEST (HEADLESS) ===")
	print("Assertions: %d | Failed: %d" % [t.total_assertions, t.failed_assertions])
	for err in t.failures:
		printerr(err)

	if t.failed_assertions > 0:
		quit(1)
		return
	print("ENGINE BOOT GATE PASSED.")
	quit(0)
