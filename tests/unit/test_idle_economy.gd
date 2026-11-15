extends RefCounted
## Testes unitarios puros de SeededRng e IdleEconomy (upgrades, Ki, Gacha pity, Offline anti-tamper e Prestigio).

const ConfigScript = preload("res://src/core/balance_config.gd")
const BigNumScript = preload("res://src/core/big_num.gd")
const RngScript = preload("res://src/core/seeded_rng.gd")
const EcoScript = preload("res://src/core/idle_economy.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func run() -> RefCounted:
	var t := HarnessScript.new("IdleEconomy")
	var f := FileAccess.open("res://config/balance_v1.json", FileAccess.READ)
	var cfg := ConfigScript.parse_and_validate(f.get_as_text() if f != null else "")
	t.assert_true(cfg.is_valid(), "config valid")
	var raw: Dictionary = cfg.get("raw")

	# 1. SeededRng determinismo
	var r1 := RngScript.new(12345)
	var r2 := RngScript.new(12345)
	for _i in range(20):
		t.assert_eq(r1.next_u32(), r2.next_u32(), "same seed yields identical sequence")
		var fv1: float = r1.next_float()
		var fv2: float = r2.next_float()
		t.assert_near(fv1, fv2, 1e-12, "same seed yields identical float sequence")
		t.assert_true(fv1 >= 0.0 and fv1 < 1.0, "next_float in [0, 1)")

	# 2. Upgrades, saldo insuficiente fail-closed e overflow crit_rate -> crit_damage
	var now_ms: int = 1_700_000_000_000
	var st := EcoScript.create_initial_state(now_ms)
	t.assert_false(bool(EcoScript.buy_upgrade(st, "attack", 1, raw)["ok"]), "reject upgrade with 0 gold")
	st["gold"] = BigNumScript.from_float(1000.0)
	t.assert_true(bool(EcoScript.buy_upgrade(st, "attack", 5, raw)["ok"]), "buy 5 attack levels")
	t.assert_eq(int(st["levels"]["attack"]), 5, "attack level == 5")

	st["levels"]["crit_rate"] = 500 # acima de 100% (0.05 + 500*0.0025 = 1.30)
	var pstats := EcoScript.compute_player_stats(st, raw, now_ms)
	t.assert_near(float(pstats["crit_rate"]), 1.0, 1e-6, "crit_rate capped at 1.0")
	t.assert_true(float(pstats["crit_damage"]) > 2.0, "crit_rate overflow boosts crit_damage")

	# 3. Recompensa offline: monotonicidade, cap 8h e bloqueio anti-tamper / 3x sem ad
	var gps := BigNumScript.from_float(10.0)
	st["last_seen_utc_ms"] = now_ms
	var tamper := EcoScript.compute_offline_reward(st, gps, raw, now_ms - 1000, false, false)
	t.assert_false(bool(tamper["ok"]), "clock rollback rejected")
	t.assert_true(bool(tamper["tamper_detected"]), "clock rollback flags tamper")

	var unverified_3x := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 3600_000, true, false)
	t.assert_false(bool(unverified_3x["ok"]), "reject 3x dragon chest without verified ad or No-Ads Pass")

	var r_30s := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 30_000, false, false)
	var r_1h := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 3600_000, false, false)
	var r_8h := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 28800_000, false, false)
	var r_20h := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 72000_000, false, false)
	t.assert_true((r_30s["gold"] as RefCounted).is_zero(), "< 60s returns 0")
	t.assert_eq((r_1h["gold"] as RefCounted).cmp(r_8h["gold"]), -1, "1h < 8h monotonic")
	t.assert_eq((r_8h["gold"] as RefCounted).cmp(r_20h["gold"]), 0, "20h clamped strictly at 8h cap")

	st["has_no_ads_pass"] = true
	var r_noads_3x := EcoScript.compute_offline_reward(st, gps, raw, now_ms + 3600_000, true, false)
	t.assert_true(bool(r_noads_3x["ok"]), "No-Ads Pass grants 3x without ad video")
	t.assert_near(float(r_noads_3x["multiplier"]), 3.0, 1e-6, "No-Ads Pass 3x multiplier")

	# 4. Gacha Hard Pity (50) e cap diario de 3x pulls por anuncio
	var gst := EcoScript.create_initial_state(now_ms)
	gst["gems"] = 100_000
	var grng := RngScript.new(42)
	var saw_mythic: bool = false
	for _p in range(5):
		var gres := EcoScript.execute_gacha_pull(gst, "weapons_mythic_v1", 10, false, false, grng, raw, now_ms)
		t.assert_true(bool(gres["ok"]), "gacha 10x pull ok")
		for r_str in gres["results"]:
			if String(r_str) == "MYTHIC":
				saw_mythic = true
	t.assert_true(saw_mythic, "50 pulls guarantee at least 1 MYTHIC via hard pity")

	t.assert_false(bool(EcoScript.execute_gacha_pull(gst, "weapons_mythic_v1", 10, true, false, grng, raw, now_ms)["ok"]), "reject ad pull without reward_verified")
	for _a in range(3):
		t.assert_true(bool(EcoScript.execute_gacha_pull(gst, "weapons_mythic_v1", 10, true, true, grng, raw, now_ms)["ok"]), "daily ad pull within cap 3")
	t.assert_false(bool(EcoScript.execute_gacha_pull(gst, "weapons_mythic_v1", 10, true, true, grng, raw, now_ms)["ok"]), "4th daily ad pull blocked")
	t.assert_true(bool(EcoScript.execute_gacha_pull(gst, "weapons_mythic_v1", 10, true, true, grng, raw, now_ms + 86_400_000)["ok"]), "next UTC day resets daily ad pull cap")

	# 5. Prestigio fail-closed antes do stage 50 e reset limpo apos stage 50
	t.assert_false(bool(EcoScript.execute_prestige(gst, raw)["ok"]), "reject prestige below stage 50")
	gst["max_stage_reached"] = 60
	gst["gold"] = BigNumScript.from_float(99999.0)
	gst["levels"]["attack"] = 20
	var pres := EcoScript.execute_prestige(gst, raw)
	t.assert_true(bool(pres["ok"]), "prestige succeeds at stage 60")
	t.assert_true((gst["soul_orbs"] as RefCounted).cmp(BigNumScript.zero()) > 0, "soul orbs granted")
	t.assert_true((gst["gold"] as RefCounted).is_zero(), "gold reset on prestige")
	t.assert_eq(int(gst["levels"]["attack"]), 0, "attack level reset on prestige")
	t.assert_eq(int(gst["current_stage"]), 1, "stage reset to 1")
	t.assert_eq(int(gst["max_stage_reached"]), 1, "run max_stage_reached reset on prestige")
	t.assert_eq(int(gst["best_stage_lifetime"]), 60, "best_stage_lifetime preserved on prestige")
	t.assert_false(bool(EcoScript.execute_prestige(gst, raw)["ok"]), "reject back-to-back prestige exploit at stage 1")

	return t
