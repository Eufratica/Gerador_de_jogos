class_name BalanceConfig
extends RefCounted
## Parser e validador estrito (fail-closed) do schema GameBalanceConfig.
## Camada pura: recebe json_text em memoria, sem FileAccess ou env global.

var valid: bool = false
var error_message: String = "Uninitialized config"
var raw: Dictionary = {}


static func _fail(msg: String) -> RefCounted:
	var cfg := new()
	cfg.valid = false
	cfg.error_message = msg
	return cfg


static func _is_num(v: Variant) -> bool:
	if not (v is float or v is int):
		return false
	var f: float = float(v)
	return not is_nan(f) and not is_inf(f)


static func _require_num(d: Dictionary, key: String, ctx: String) -> Dictionary:
	if not d.has(key) or not _is_num(d[key]):
		return {"ok": false, "err": "%s.%s must be a finite number" % [ctx, key]}
	return {"ok": true, "val": float(d[key])}


static func _require_dict(d: Dictionary, key: String, ctx: String) -> Dictionary:
	if not d.has(key) or not (d[key] is Dictionary):
		return {"ok": false, "err": "%s.%s must be an object" % [ctx, key]}
	return {"ok": true, "val": d[key]}


static func parse_and_validate(json_text: String) -> RefCounted:
	if json_text.strip_edges().is_empty():
		return _fail("JSON text is empty")

	var parser := JSON.new()
	var parse_err: int = parser.parse(json_text)
	if parse_err != OK or not (parser.data is Dictionary):
		return _fail("Invalid JSON syntax or root is not an object: %s" % parser.get_error_message())

	var root: Dictionary = parser.data
	var required_top: Array[String] = [
		"schema_version", "bignum_format", "upgrade_curves",
		"ki_transformations", "gacha_banners", "prestige_config",
		"offline_rewards_config", "ddtank_ballistics_config",
		"enemy_stage_config", "monetization_placements"
	]
	for k in required_top:
		if not root.has(k):
			return _fail("Missing top-level key: %s" % k)

	if not (root["schema_version"] is String) or String(root["schema_version"]).is_empty():
		return _fail("schema_version must be a non-empty string")

	var err: String = _validate_bignum(root["bignum_format"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_upgrades(root["upgrade_curves"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_ki(root["ki_transformations"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_gacha(root["gacha_banners"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_prestige(root["prestige_config"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_offline(root["offline_rewards_config"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_ballistics(root["ddtank_ballistics_config"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_enemy(root["enemy_stage_config"])
	if not err.is_empty():
		return _fail(err)

	err = _validate_monetization(root["monetization_placements"])
	if not err.is_empty():
		return _fail(err)

	var cfg := new()
	cfg.raw = root
	cfg.valid = true
	cfg.error_message = ""
	return cfg


static func _validate_bignum(v: Variant) -> String:
	if not (v is Dictionary):
		return "bignum_format must be an object"
	var d: Dictionary = v
	if not d.has("decimal_places") or not _is_num(d["decimal_places"]) or int(d["decimal_places"]) < 0:
		return "bignum_format.decimal_places must be >= 0"
	if not d.has("suffixes") or not (d["suffixes"] is Array):
		return "bignum_format.suffixes must be an array"
	var suffixes: Array = d["suffixes"]
	if suffixes.size() < 2 or String(suffixes[0]) != "":
		return "bignum_format.suffixes must start with empty string and have >= 2 entries"
	return ""


static func _validate_upgrades(v: Variant) -> String:
	if not (v is Dictionary):
		return "upgrade_curves must be an object"
	var d: Dictionary = v
	var keys: Array[String] = ["attack", "crit_rate", "crit_damage", "attack_speed", "penetration"]
	for k in keys:
		if not d.has(k) or not (d[k] is Dictionary):
			return "upgrade_curves.%s must be an object" % k
		var c: Dictionary = d[k]
		for req_f in ["base_value", "growth_linear", "growth_exp", "base_cost", "cost_ratio"]:
			if not c.has(req_f) or not _is_num(c[req_f]):
				return "upgrade_curves.%s.%s must be finite number" % [k, req_f]
		if float(c["base_cost"]) <= 0.0:
			return "upgrade_curves.%s.base_cost must be > 0" % k
		if float(c["cost_ratio"]) < 1.0:
			return "upgrade_curves.%s.cost_ratio must be >= 1.0" % k
		if float(c["growth_exp"]) < 1.0:
			return "upgrade_curves.%s.growth_exp must be >= 1.0" % k
	return ""


static func _validate_ki(v: Variant) -> String:
	if not (v is Array):
		return "ki_transformations must be an array"
	var arr: Array = v
	if arr.size() < 5:
		return "ki_transformations must contain at least 5 stages"
	var prev_tier: int = 0
	for item in arr:
		if not (item is Dictionary):
			return "ki_transformations entries must be objects"
		var t: Dictionary = item
		for req_k in ["id", "tier", "unlock_stage", "ki_cost", "atk_mult", "spd_mult"]:
			if not t.has(req_k):
				return "ki_transformations missing key: %s" % req_k
		if not _is_num(t["tier"]) or int(t["tier"]) <= prev_tier:
			return "ki_transformations tier must be strictly ascending"
		prev_tier = int(t["tier"])
		if float(t["atk_mult"]) < 1.0 or float(t["spd_mult"]) < 1.0:
			return "ki_transformations multipliers must be >= 1.0"
		if int(t["unlock_stage"]) < 1 or float(t["ki_cost"]) < 0.0:
			return "ki_transformations unlock_stage/ki_cost out of range"
	return ""


static func _validate_gacha(v: Variant) -> String:
	if not (v is Array):
		return "gacha_banners must be an array"
	var arr: Array = v
	if arr.is_empty():
		return "gacha_banners cannot be empty"
	for item in arr:
		if not (item is Dictionary):
			return "gacha_banners entry must be an object"
		var b: Dictionary = item
		if not b.has("pity_hard_threshold") or not _is_num(b["pity_hard_threshold"]) or int(b["pity_hard_threshold"]) < 1:
			return "gacha banner pity_hard_threshold must be >= 1"
		if not b.has("daily_ad_ten_pull_cap") or not _is_num(b["daily_ad_ten_pull_cap"]) or int(b["daily_ad_ten_pull_cap"]) < 0:
			return "gacha banner daily_ad_ten_pull_cap must be >= 0"
		if not b.has("probabilities") or not (b["probabilities"] is Dictionary):
			return "gacha banner missing probabilities object"
		var probs: Dictionary = b["probabilities"]
		var sum_p: float = 0.0
		for rk in probs.keys():
			if not _is_num(probs[rk]) or float(probs[rk]) < 0.0:
				return "gacha probability must be >= 0"
			sum_p += float(probs[rk])
		if abs(sum_p - 1.0) > 1e-9:
			return "gacha probabilities must sum to 1.0 (got %.12f)" % sum_p
	return ""


static func _validate_prestige(v: Variant) -> String:
	if not (v is Dictionary):
		return "prestige_config must be an object"
	var d: Dictionary = v
	for rk in ["min_stage_required", "base_divisor", "stage_exponent", "soul_orb_scale", "per_orb_atk_bonus", "per_orb_gold_bonus"]:
		if not d.has(rk) or not _is_num(d[rk]):
			return "prestige_config.%s must be finite number" % rk
	if int(d["min_stage_required"]) < 1 or float(d["base_divisor"]) <= 0.0 or float(d["soul_orb_scale"]) <= 0.0:
		return "prestige_config invalid positive bounds"
	return ""


static func _validate_offline(v: Variant) -> String:
	if not (v is Dictionary):
		return "offline_rewards_config must be an object"
	var d: Dictionary = v
	for rk in ["min_claim_seconds", "max_offline_seconds", "efficiency_ratio", "dragon_chest_ad_multiplier"]:
		if not d.has(rk) or not _is_num(d[rk]):
			return "offline_rewards_config.%s must be finite number" % rk
	var max_s: int = int(d["max_offline_seconds"])
	var min_s: int = int(d["min_claim_seconds"])
	var eff: float = float(d["efficiency_ratio"])
	var mult: float = float(d["dragon_chest_ad_multiplier"])
	if min_s < 0 or max_s <= 0 or max_s > 28800 or min_s > max_s:
		return "offline_rewards_config seconds bounds violate 8h cap"
	if eff <= 0.0 or eff > 1.0 or mult < 1.0:
		return "offline_rewards_config efficiency/multiplier out of bounds"
	return ""


static func _validate_ballistics(v: Variant) -> String:
	if not (v is Dictionary):
		return "ddtank_ballistics_config must be an object"
	var d: Dictionary = v
	if not d.has("orientation") or String(d["orientation"]) != "LANDSCAPE_16_9":
		return "ddtank_ballistics_config.orientation must be LANDSCAPE_16_9"
	var req_nums: Array[String] = [
		"arena_logical_width", "arena_logical_height", "player_anchor_x",
		"boss_anchor_x_min", "boss_anchor_x_max", "gravity", "v_min", "v_max",
		"angle_min_deg", "angle_max_deg", "wind_min", "wind_max", "wind_accel_factor",
		"fixed_dt", "max_flight_seconds", "crater_radius_px",
		"head_core_multiplier", "body_multiplier", "limb_glancing_multiplier",
		"laser_guide_points", "laser_guide_dt"
	]
	for k in req_nums:
		if not d.has(k) or not _is_num(d[k]):
			return "ddtank_ballistics_config.%s must be finite number" % k
	if float(d["gravity"]) <= 0.0 or float(d["v_min"]) <= 0.0 or float(d["v_min"]) >= float(d["v_max"]):
		return "ddtank_ballistics_config invalid gravity or velocity bounds"
	if float(d["angle_min_deg"]) < 0.0 or float(d["angle_min_deg"]) >= float(d["angle_max_deg"]) or float(d["angle_max_deg"]) > 90.0:
		return "ddtank_ballistics_config invalid angle bounds"
	if float(d["wind_min"]) >= 0.0 or float(d["wind_max"]) <= 0.0 or float(d["wind_accel_factor"]) < 0.0:
		return "ddtank_ballistics_config invalid wind bounds"
	if float(d["fixed_dt"]) <= 0.0 or float(d["fixed_dt"]) > 0.02 or float(d["max_flight_seconds"]) <= 0.0:
		return "ddtank_ballistics_config invalid timestep bounds"
	if float(d["crater_radius_px"]) <= 0.0 or not is_equal_approx(float(d["head_core_multiplier"]), 10.0):
		return "ddtank_ballistics_config invalid crater or head_core_multiplier != 10.0"
	var w: float = float(d["arena_logical_width"])
	var px: float = float(d["player_anchor_x"])
	var bmin: float = float(d["boss_anchor_x_min"])
	var bmax: float = float(d["boss_anchor_x_max"])
	if px <= 0.0 or px >= bmin or bmin > bmax or bmax >= w:
		return "ddtank_ballistics_config invalid arena anchor positions"
	return ""


static func _validate_enemy(v: Variant) -> String:
	if not (v is Dictionary):
		return "enemy_stage_config must be an object"
	var d: Dictionary = v
	for rk in ["waves_per_stage", "hp_base", "hp_stage_ratio", "gold_base", "gold_stage_ratio", "boss_hp_multiplier", "titanic_posture_max", "qte_window_ms"]:
		if not d.has(rk) or not _is_num(d[rk]) or float(d[rk]) <= 0.0:
			return "enemy_stage_config.%s must be > 0" % rk
	return ""


static func _validate_monetization(v: Variant) -> String:
	if not (v is Dictionary):
		return "monetization_placements must be an object"
	var d: Dictionary = v
	if not d.has("no_ads_sku") or String(d["no_ads_sku"]).is_empty():
		return "monetization_placements.no_ads_sku required"
	if not d.has("rewarded_placements") or not (d["rewarded_placements"] is Array) or (d["rewarded_placements"] as Array).size() < 5:
		return "monetization_placements.rewarded_placements must contain 5 placements"
	return ""


func is_valid() -> bool:
	return valid


func get_bignum_suffixes() -> PackedStringArray:
	var out := PackedStringArray()
	if not valid:
		return out
	for s in raw["bignum_format"]["suffixes"]:
		out.append(String(s))
	return out


func get_bignum_decimals() -> int:
	return int(raw["bignum_format"]["decimal_places"]) if valid else 2


func get_ballistics_config() -> Dictionary:
	return raw["ddtank_ballistics_config"] if valid else {}
