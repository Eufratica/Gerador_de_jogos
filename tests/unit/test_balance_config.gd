extends RefCounted
## Testes unitarios puros e negativos (fail-closed) do BalanceConfig JSON.

const ConfigScript = preload("res://src/core/balance_config.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func _load_raw_balance_json() -> String:
	var f := FileAccess.open("res://config/balance_v1.json", FileAccess.READ)
	if f == null:
		return ""
	return f.get_as_text()


static func run() -> RefCounted:
	var t := HarnessScript.new("BalanceConfig")
	var valid_json: String = _load_raw_balance_json()
	t.assert_false(valid_json.is_empty(), "balance_v1.json readable")

	# 1. Config oficial valida
	var cfg := ConfigScript.parse_and_validate(valid_json)
	t.assert_true(cfg.is_valid(), "official balance_v1.json passes validation: %s" % cfg.error_message)
	var bal: Dictionary = cfg.get_ballistics_config()
	t.assert_eq(String(bal["orientation"]), "LANDSCAPE_16_9", "orientation is LANDSCAPE_16_9")
	t.assert_near(float(bal["head_core_multiplier"]), 10.0, 1e-9, "head_core_multiplier == 10.0")
	t.assert_near(float(bal["v_max"]), 1650.0, 1e-9, "v_max recalibrated to 1650.0")
	t.assert_eq(int(cfg.raw["offline_rewards_config"]["max_offline_seconds"]), 28800, "8h offline cap")

	# 2. Testes negativos fail-closed
	t.assert_false(ConfigScript.parse_and_validate("").is_valid(), "empty string rejected")
	t.assert_false(ConfigScript.parse_and_validate("{not_json").is_valid(), "broken JSON rejected")

	# 2a. Gacha probability sum != 1.0
	var bad_gacha: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_gacha["gacha_banners"][0]["probabilities"]["MYTHIC"] = 0.05
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_gacha)).is_valid(), "gacha sum != 1.0 rejected")

	# 2b. Offline cap > 8h (28800s)
	var bad_offline: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_offline["offline_rewards_config"]["max_offline_seconds"] = 36000
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_offline)).is_valid(), "offline cap > 8h rejected")

	# 2c. Ki tiers out of order
	var bad_ki: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_ki["ki_transformations"][2]["tier"] = 1
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_ki)).is_valid(), "non-ascending Ki tiers rejected")

	# 2d. Missing top-level key
	var bad_missing: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_missing.erase("prestige_config")
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_missing)).is_valid(), "missing prestige_config rejected")

	# 2e. Wrong head_core_multiplier
	var bad_bal: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_bal["ddtank_ballistics_config"]["head_core_multiplier"] = 5.0
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_bal)).is_valid(), "head_core_multiplier != 10 rejected")

	# 2f. Efficiency > 1.0 and base_cost <= 0
	var bad_eff: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_eff["offline_rewards_config"]["efficiency_ratio"] = 1.5
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_eff)).is_valid(), "efficiency_ratio > 1.0 rejected")

	var bad_cost: Dictionary = (cfg.get("raw") as Dictionary).duplicate(true)
	bad_cost["upgrade_curves"]["attack"]["base_cost"] = 0.0
	t.assert_false(ConfigScript.parse_and_validate(JSON.stringify(bad_cost)).is_valid(), "base_cost <= 0 rejected")

	return t
