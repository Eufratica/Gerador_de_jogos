extends RefCounted
## Testes unitarios puros da maquina de estados CombatFSM.

const ConfigScript = preload("res://src/core/balance_config.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const RngScript = preload("res://src/core/seeded_rng.gd")
const FsmScript = preload("res://src/core/combat_fsm.gd")
const BallisticsScript = preload("res://src/core/ddtank_ballistics.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func run() -> RefCounted:
	var t := HarnessScript.new("CombatFsm")
	var f := FileAccess.open("res://config/balance_v1.json", FileAccess.READ)
	var cfg := ConfigScript.parse_and_validate(f.get_as_text() if f != null else "")
	t.assert_true(cfg.is_valid(), "config valid")
	var raw: Dictionary = cfg.get("raw")

	var now_ms: int = 1_700_000_000_000
	var rng := RngScript.new(99)
	var fsm := FsmScript.new(raw, rng, now_ms)
	var events: Array = []

	t.assert_eq(fsm.state, FsmScript.State.IDLE_AUTO, "initial state IDLE_AUTO")

	# 1. Rage Berserk ciclo completo
	fsm.rage_ratio = 1.0
	fsm.step(0.1, now_ms + 100, events)
	t.assert_eq(fsm.state, FsmScript.State.RAGE_BERSERK, "full rage enters RAGE_BERSERK")
	fsm.step(10.1, now_ms + 10_200, events)
	t.assert_eq(fsm.state, FsmScript.State.IDLE_AUTO, "rage expires back to IDLE_AUTO")

	# 2. Chefe Titanico no estagio 5 abre DDTANK_AIM -> POW 10x -> BOSS_QTE -> avanco
	fsm.economy["current_stage"] = 5
	fsm.economy["max_stage_reached"] = 5
	fsm.economy["levels"]["attack"] = 25
	fsm.challenge_boss(events)
	t.assert_true(fsm.is_titanic_boss, "stage 5 boss is Titanic")
	t.assert_eq(fsm.state, FsmScript.State.DDTANK_AIM, "Titanic Boss auto-opens DDTANK_AIM")

	var bcfg: Dictionary = raw["ddtank_ballistics_config"]
	var px: float = float(bcfg["player_anchor_x"])
	var py: float = fsm.terrain.sample_height(px) + 32.0
	var sol := BallisticsScript.solve_aim_for_head(px, py, fsm.boss_hitbox, fsm.terrain, fsm.current_wind, bcfg)
	t.assert_true(bool(sol["found"]), "head aim found for Titanic boss")

	# Ajusta HP para sobreviver ao POW e entrar na janela de QTE
	fsm.enemy_hp = BigNumScript.from_parts(1.0, 20)
	var shot_res := fsm.release_ddtank_shot(float(sol["angle_deg"]), float(sol["power_norm"]), now_ms + 11_000, events)
	t.assert_true(bool(shot_res["ok"]), "ddtank shot executed")
	t.assert_eq(fsm.state, FsmScript.State.BOSS_QTE, "HEAD_CORE POW triggers BOSS_QTE")

	var qte_res := fsm.complete_boss_qte(true, now_ms + 12_000, events)
	t.assert_true(bool(qte_res["ok"]) and bool(qte_res["finisher_applied"]), "QTE finisher succeeds within 2500ms")
	t.assert_eq(fsm.state, FsmScript.State.IDLE_AUTO, "QTE returns to IDLE_AUTO")

	# 3. Derrota no Boss + Revive fail-closed + recuo para mesmo estagio (Decisao 1A)
	fsm.state = FsmScript.State.IDLE_AUTO
	fsm.is_boss_active = true
	fsm.is_titanic_boss = false
	fsm.enemy_hp = BigNumScript.from_parts(1.0, 30)
	fsm.boss_elapsed_s = 44.5
	fsm.step(1.0, now_ms + 15_000, events)
	t.assert_eq(fsm.state, FsmScript.State.DEFEAT_REVIVE_OFFER, "boss timeout triggers DEFEAT_REVIVE_OFFER")

	t.assert_false(bool(fsm.resolve_defeat_revive(true, false, events)["ok"]), "reject unverified revive ad")
	t.assert_eq(fsm.state, FsmScript.State.DEFEAT_REVIVE_OFFER, "stays in offer when unverified")

	var decline_res := fsm.resolve_defeat_revive(false, false, events)
	t.assert_true(bool(decline_res["ok"]) and not bool(decline_res["revived"]), "decline revive ok")
	t.assert_eq(fsm.state, FsmScript.State.IDLE_AUTO, "decline returns to IDLE_AUTO")
	t.assert_true(fsm.farming_same_stage_waves, "farms normal waves on same stage (Decision 1A)")
	t.assert_eq(int(fsm.economy["current_stage"]), 5, "stays on stage 5 when declining revive")

	# Revive verificado entra em RAGE_BERSERK com HP e POW cheios
	fsm.state = FsmScript.State.DEFEAT_REVIVE_OFFER
	var acc_res := fsm.resolve_defeat_revive(true, true, events)
	t.assert_true(bool(acc_res["ok"]) and bool(acc_res["revived"]), "verified revive accepted")
	t.assert_eq(fsm.state, FsmScript.State.RAGE_BERSERK, "revive enters RAGE_BERSERK")
	t.assert_near(fsm.pow_charge, 1.0, 1e-6, "revive fills POW bar")

	return t
