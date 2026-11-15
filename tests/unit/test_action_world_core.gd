extends RefCounted
## Testes unitarios puros do nucleo 2D Dark Fantasy (ActionWorldConfig + ActionCombatCore).

const BalanceConfigScript = preload("res://src/core/balance_config.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const RngScript = preload("res://src/core/seeded_rng.gd")
const WorldConfigScript = preload("res://src/core/action_world_config.gd")
const ActionCoreScript = preload("res://src/core/action_combat_core.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func _step_n(core: RefCounted, frames: int, dt: float, cmd: Dictionary, t0_ms: int, events: Array) -> int:
	var t_ms: int = t0_ms
	for _i in range(frames):
		t_ms += int(round(dt * 1000.0))
		core.step(dt, cmd, t_ms, events)
	return t_ms


static func run() -> RefCounted:
	var t := HarnessScript.new("ActionWorldCore")
	var fb := FileAccess.open("res://config/balance_v1.json", FileAccess.READ)
	var bcfg := BalanceConfigScript.parse_and_validate(fb.get_as_text() if fb != null else "")
	t.assert_true(bcfg.is_valid(), "balance_v1.json valid")

	var fw := FileAccess.open("res://config/action_world_v1.json", FileAccess.READ)
	var w_json: String = fw.get_as_text() if fw != null else ""
	var wcfg := WorldConfigScript.parse_and_validate(w_json)
	t.assert_true(wcfg.is_valid(), "action_world_v1.json valid")

	# 1. Fail-closed schema validation
	var bad_cfg := WorldConfigScript.parse_and_validate("{\"schema_version\":\"1.0.0\"}")
	t.assert_false(bad_cfg.is_valid(), "reject missing root keys fail-closed")

	var b_raw: Dictionary = bcfg.get("raw")
	var w_raw: Dictionary = wcfg.get("raw")
	var rng := RngScript.new(777)
	var now_ms: int = 1_700_000_000_000
	var core := ActionCoreScript.new(b_raw, w_raw, rng, now_ms)
	var events: Array = []

	t.assert_eq(core.current_world_id, "world_1_ashen_citadel", "starts in World 1")
	t.assert_eq(core.current_room_id, "w1_gate", "starts in w1_gate")

	# 2. Portal locked fail-closed while room enemies alive
	core.px = 2080.0
	var locked_portal: Dictionary = core.try_interact(now_ms, events)
	t.assert_false(bool(locked_portal["ok"]), "portal locked while room enemies alive")

	# 3. Plataforma 2D e bau elevado (pulo + aterrisagem)
	core.px = 740.0
	core.py = 0.0
	core.on_ground = true
	now_ms = _step_n(core, 1, 0.02, {"jump_pressed": true}, now_ms, events)
	now_ms = _step_n(core, 38, 0.02, {"move_x": 0.0}, now_ms, events)
	t.assert_true(core.on_ground and core.py >= 190.0, "player lands on one-way platform (~194px)")

	# 4. Combo 3 hits + 4 poderes magicos + cooldown fail-closed
	core.enter_room("world_1_ashen_citadel", "w1_gate", 820.0, 0.0, events)
	core.facing = 1
	now_ms = _step_n(core, 1, 0.02, {"attack_pressed": true}, now_ms, events)
	t.assert_eq(core.player_action, ActionCoreScript.PlayerAction.ATTACK_WINDUP, "attack enters windup")
	now_ms = _step_n(core, 20, 0.02, {}, now_ms, events)
	t.assert_eq(core.combo_index, 1, "combo_index advances after slash_1")

	# Testa cast das 4 magias (dando mana cheia para validar todas)
	for s_idx in range(4):
		core.mana = core.max_mana
		core.player_action = ActionCoreScript.PlayerAction.IDLE
		now_ms = _step_n(core, 1, 0.02, {"cast_skill_idx": s_idx}, now_ms, events)
		t.assert_true(core.skill_cooldowns[s_idx] > 0.0, "skill %d enters cooldown" % s_idx)
		if s_idx == 3:
			t.assert_false((core.shield_hp as RefCounted).is_zero(), "titan_aegis grants shield_hp")
		# Segunda tentativa imediata em cooldown falha fechado (player permanece IDLE)
		core.player_action = ActionCoreScript.PlayerAction.IDLE
		now_ms = _step_n(core, 1, 0.02, {"cast_skill_idx": s_idx}, now_ms, events)
		t.assert_eq(core.player_action, ActionCoreScript.PlayerAction.IDLE, "skill %d blocked while on cooldown" % s_idx)

	# 5. Dash i-frames bloqueiam golpe direto e geram Furia
	core.hp = (core.max_hp as RefCounted).duplicate_num()
	core.shield_hp = BigNumScript.zero()
	core.rage_ratio = 0.0
	core.dash_cooldown_s = 0.0
	now_ms = _step_n(core, 1, 0.02, {"dash_pressed": true, "move_x": 1.0}, now_ms, events)
	t.assert_true(core.is_invulnerable(), "dash grants active i-frames")
	events.clear()
	core._apply_damage_to_player(BigNumScript.from_float(50.0), "test_boss", events)
	t.assert_eq((core.hp as RefCounted).cmp(core.max_hp), 0, "i-frame prevents HP loss")
	t.assert_true(core.rage_ratio > 0.0, "dodge grants rage")

	# 6. Altar de Salvamento + Checkpoint + Boss Posture Break + QTE Finisher
	core.enter_room("world_1_ashen_citadel", "w1_sanctuary", 920.0, 0.0, events)
	core.hp = BigNumScript.from_float(10.0)
	core.mana = 5.0
	var altar_res: Dictionary = core.try_interact(now_ms, events)
	t.assert_true(bool(altar_res["ok"]) and String(altar_res["kind"]) == "ALTAR", "altar activated")
	t.assert_eq((core.hp as RefCounted).cmp(core.max_hp), 0, "altar heals HP to 100%")
	t.assert_near(core.mana, core.max_mana, 1e-6, "altar restores Mana to 100%")
	t.assert_eq(String(core.checkpoint["room_id"]), "w1_sanctuary", "checkpoint stored at sanctuary")

	# Entra no Boss Mundo 1, quebra postura com Raio Celestial / Aegis e finaliza no QTE
	core.enter_room("world_1_ashen_citadel", "w1_boss_throne", 1360.0, 0.0, events)
	core.enemies[0]["posture"] = 10.0
	core.mana = 100.0
	core.skill_cooldowns[2] = 0.0
	core.player_action = ActionCoreScript.PlayerAction.IDLE
	now_ms = _step_n(core, 1, 0.02, {"cast_skill_idx": 2}, now_ms, events)
	t.assert_eq(core.game_phase, ActionCoreScript.GamePhase.BOSS_QTE, "boss posture 0 enters BOSS_QTE")
	core.enemies[0]["hp"] = BigNumScript.from_float(10.0)
	now_ms = _step_n(core, 1, 0.05, {"qte_pressed": true}, now_ms, events)
	t.assert_eq(core.game_phase, ActionCoreScript.GamePhase.EXPLORING, "QTE finishes cleanly")
	t.assert_true(core.defeated_boss_worlds.has("world_1_ashen_citadel"), "boss defeat marks world 1 cleared")

	# Portal para Mundo 2 agora destrancado e funcional
	core.px = 1980.0
	var w2_portal: Dictionary = core.try_interact(now_ms, events)
	t.assert_true(bool(w2_portal["ok"]), "World 1 -> World 2 portal opens after boss defeat")
	t.assert_eq(core.current_world_id, "world_2_crimson_foundry", "transitioned to World 2")

	# 7. Fail-closed Defeat Revive + Respawn no Altar mantendo ouro/niveis + Snapshot round-trip
	core.economy["gold"] = BigNumScript.from_float(500.0)
	t.assert_true(bool(core.buy_forge_upgrade("attack", 2, events)["ok"]), "forge upgrade bought")
	var snap: Dictionary = core.export_checkpoint_snapshot(now_ms)

	core.hp = BigNumScript.zero()
	core.game_phase = ActionCoreScript.GamePhase.DEFEATED_REVIVE_OFFER
	t.assert_false(bool(core.resolve_defeat_revive(true, false, events)["ok"]), "reject unverified revive ad")
	var decline: Dictionary = core.resolve_defeat_revive(false, false, events)
	t.assert_true(bool(decline["ok"]) and not bool(decline["revived"]), "decline revive returns cleanly")
	t.assert_eq(core.current_room_id, "w1_sanctuary", "respawned at last Save Altar room")
	t.assert_eq(int(core.economy["levels"]["attack"]), 2, "upgrades preserved on altar respawn")

	var restored := ActionCoreScript.new(b_raw, w_raw, RngScript.new(1), now_ms)
	t.assert_true(restored.restore_from_checkpoint(snap, now_ms + 1000, events), "restore from checkpoint snapshot succeeds")
	t.assert_eq(int(restored.economy["levels"]["attack"]), 2, "restored attack upgrade level")
	t.assert_true(restored.defeated_boss_worlds.has("world_1_ashen_citadel"), "restored world boss progression")

	return t
