class_name IdleEconomy
extends RefCounted
## Motor puro de economia Idle, upgrades exponenciais, transformacoes de Ki,
## Gacha com hard pity, Prestigio e recompensa offline anti-tamper.

const BigNumScript = preload("res://src/core/big_num.gd")

const RARITY_ORDER: PackedStringArray = ["MYTHIC", "LEGENDARY", "EPIC", "RARE", "COMMON"]
const RARITY_MULTS: Dictionary = {
	"COMMON": 1.25,
	"RARE": 1.85,
	"EPIC": 3.40,
	"LEGENDARY": 7.50,
	"MYTHIC": 18.00,
}


static func create_initial_state(now_utc_ms: int = 0) -> Dictionary:
	var day_utc: int = int(floor(float(maxi(0, now_utc_ms)) / 86400000.0))
	return {
		"gold": BigNumScript.zero(),
		"gems": 0,
		"soul_orbs": BigNumScript.zero(),
		"ki_energy": 0.0,
		"active_ki_tier": 1,
		"levels": {
			"attack": 0,
			"crit_rate": 0,
			"crit_damage": 0,
			"attack_speed": 0,
			"penetration": 0,
		},
		"equipped_weapon_mult": 1.0,
		"equipped_aura_mult": 1.0,
		"equipped_spirit_mult": 1.0,
		"pity_counter": 0,
		"daily_ad_pulls_used": 0,
		"last_ad_day_utc": day_utc,
		"current_stage": 1,
		"max_stage_reached": 1,
		"best_stage_lifetime": 1,
		"last_seen_utc_ms": maxi(0, now_utc_ms),
		"fury_boost_until_ms": 0,
		"has_no_ads_pass": false,
	}


static func get_ki_stage_def(tier: int, cfg_raw: Dictionary) -> Dictionary:
	var list: Array = cfg_raw.get("ki_transformations", [])
	for item in list:
		if int(item["tier"]) == tier:
			return item
	return list[0] if not list.is_empty() else {"tier": 1, "atk_mult": 1.0, "spd_mult": 1.0, "crit_dmg_bonus": 0.0, "unlock_stage": 1, "ki_cost": 0.0}


static func compute_upgrade_value_bignum(curve: Dictionary, level: int) -> RefCounted:
	var lv: int = maxi(0, level)
	var base_part: RefCounted = BigNumScript.from_float(float(curve["base_value"]) + float(curve["growth_linear"]) * float(lv))
	var exp_part: RefCounted = BigNumScript.from_float(float(curve["growth_exp"])).pow_int(lv)
	return base_part.mul(exp_part)


static func compute_raw_upgrade_float(curve: Dictionary, level: int) -> float:
	var lv: int = maxi(0, level)
	return (float(curve["base_value"]) + float(curve["growth_linear"]) * float(lv)) * pow(float(curve["growth_exp"]), float(lv))


static func compute_upgrade_cost(curve: Dictionary, current_level: int, count: int) -> RefCounted:
	return BigNumScript.geometric_series_sum(
		BigNumScript.from_float(float(curve["base_cost"])),
		float(curve["cost_ratio"]),
		maxi(0, current_level),
		maxi(0, count)
	)


static func compute_max_affordable(curve: Dictionary, current_level: int, available_gold: RefCounted, max_batch: int = 1000) -> int:
	if available_gold == null or not bool(available_gold.get("valid")):
		return 0
	var lo: int = 0
	var hi: int = maxi(0, max_batch)
	while lo < hi:
		var mid: int = int(ceil(float(lo + hi + 1) * 0.5))
		var c: RefCounted = compute_upgrade_cost(curve, current_level, mid)
		if bool(c.get("valid")) and c.cmp(available_gold) <= 0:
			lo = mid
		else:
			hi = mid - 1
	return lo


static func buy_upgrade(state: Dictionary, stat_key: String, count: int, cfg_raw: Dictionary) -> Dictionary:
	var curves: Dictionary = cfg_raw.get("upgrade_curves", {})
	var levels: Dictionary = state.get("levels", {})
	if count <= 0 or not curves.has(stat_key) or not levels.has(stat_key):
		return {"ok": false, "error": "Invalid stat_key or count"}

	var curve: Dictionary = curves[stat_key]
	var cur_lv: int = int(levels[stat_key])
	if curve.has("hard_cap_level") and curve["hard_cap_level"] != null:
		if cur_lv + count > int(curve["hard_cap_level"]):
			return {"ok": false, "error": "Upgrade exceeds hard_cap_level"}

	if stat_key == "attack_speed" and curve.has("hard_cap_value") and curve["hard_cap_value"] != null:
		var cur_val: float = compute_raw_upgrade_float(curve, cur_lv)
		if cur_val >= float(curve["hard_cap_value"]) - 1e-9:
			return {"ok": false, "error": "attack_speed already at hard_cap_value"}

	var cost: RefCounted = compute_upgrade_cost(curve, cur_lv, count)
	var gold: RefCounted = state["gold"]
	if not bool(cost.get("valid")) or gold.cmp(cost) < 0:
		return {"ok": false, "error": "Insufficient gold", "cost": cost}

	state["gold"] = gold.sub_clamped(cost)
	levels[stat_key] = cur_lv + count
	return {"ok": true, "cost": cost, "new_level": levels[stat_key]}


static func can_activate_ki_tier(state: Dictionary, target_tier: int, cfg_raw: Dictionary) -> bool:
	var list: Array = cfg_raw.get("ki_transformations", [])
	for item in list:
		if int(item["tier"]) == target_tier:
			return int(state["max_stage_reached"]) >= int(item["unlock_stage"]) and float(state["ki_energy"]) >= float(item["ki_cost"])
	return false


static func activate_ki_tier(state: Dictionary, target_tier: int, cfg_raw: Dictionary) -> Dictionary:
	if not can_activate_ki_tier(state, target_tier, cfg_raw):
		return {"ok": false, "error": "Ki stage or energy requirements not met"}
	var ki_def: Dictionary = get_ki_stage_def(target_tier, cfg_raw)
	state["ki_energy"] = maxf(0.0, float(state["ki_energy"]) - float(ki_def["ki_cost"]))
	state["active_ki_tier"] = target_tier
	return {"ok": true, "tier": target_tier, "ki_def": ki_def}


static func compute_player_stats(state: Dictionary, cfg_raw: Dictionary, now_utc_ms: int) -> Dictionary:
	var curves: Dictionary = cfg_raw["upgrade_curves"]
	var levels: Dictionary = state["levels"]
	var ki_def: Dictionary = get_ki_stage_def(int(state["active_ki_tier"]), cfg_raw)
	var prestige_cfg: Dictionary = cfg_raw["prestige_config"]

	var atk_upgrade: RefCounted = compute_upgrade_value_bignum(curves["attack"], int(levels["attack"]))
	var pen_upgrade: RefCounted = compute_upgrade_value_bignum(curves["penetration"], int(levels["penetration"]))

	var raw_crit_rate: float = compute_raw_upgrade_float(curves["crit_rate"], int(levels["crit_rate"]))
	var crit_cap: float = float(curves["crit_rate"].get("hard_cap_value", 1.0))
	var overflow_ratio: float = float(curves["crit_rate"].get("overflow_to_crit_dmg_ratio", 2.0))
	var eff_crit_rate: float = minf(crit_cap, raw_crit_rate)
	var crit_overflow_bonus: float = maxf(0.0, raw_crit_rate - crit_cap) * overflow_ratio

	var base_crit_dmg: float = compute_raw_upgrade_float(curves["crit_damage"], int(levels["crit_damage"]))
	var eff_crit_dmg: float = base_crit_dmg + crit_overflow_bonus + float(ki_def.get("crit_dmg_bonus", 0.0))

	var raw_spd: float = compute_raw_upgrade_float(curves["attack_speed"], int(levels["attack_speed"]))
	var spd_cap: float = float(curves["attack_speed"].get("hard_cap_value", 4.0))
	var fury_active: bool = now_utc_ms < int(state["fury_boost_until_ms"])
	var eff_spd: float = minf(spd_cap, raw_spd) * float(ki_def["spd_mult"]) * (2.0 if fury_active else 1.0)

	var orbs: RefCounted = state["soul_orbs"]
	var prestige_atk_mult: RefCounted = BigNumScript.one().add(orbs.mul_float(float(prestige_cfg["per_orb_atk_bonus"])))
	var prestige_gold_mult: RefCounted = BigNumScript.one().add(orbs.mul_float(float(prestige_cfg["per_orb_gold_bonus"])))

	var gear_and_ki_mult: float = (
		float(state["equipped_weapon_mult"])
		* float(state["equipped_aura_mult"])
		* float(state["equipped_spirit_mult"])
		* float(ki_def["atk_mult"])
	)
	var atk_total: RefCounted = atk_upgrade.mul_float(gear_and_ki_mult).mul(prestige_atk_mult)
	var crit_ev: float = 1.0 + eff_crit_rate * (eff_crit_dmg - 1.0)
	var expected_dps: RefCounted = atk_total.mul_float(eff_spd * crit_ev)
	var gold_mult: RefCounted = prestige_gold_mult.mul_float(2.0 if fury_active else 1.0)

	return {
		"atk_total": atk_total,
		"penetration": pen_upgrade,
		"crit_rate": eff_crit_rate,
		"crit_damage": eff_crit_dmg,
		"attack_speed": eff_spd,
		"expected_dps": expected_dps,
		"gold_multiplier": gold_mult,
		"fury_boost_active": fury_active,
	}


static func compute_enemy_params(stage: int, wave_in_stage: int, cfg_raw: Dictionary) -> Dictionary:
	var ec: Dictionary = cfg_raw["enemy_stage_config"]
	var s: int = maxi(1, stage)
	var w: int = maxi(1, wave_in_stage)
	var waves_per_stage: int = int(ec["waves_per_stage"])
	var is_boss: bool = (w >= waves_per_stage)
	var titanic_every: int = maxi(1, int(ec.get("titanic_boss_every_n_stages", 5)))
	var is_titanic: bool = is_boss and (s % titanic_every == 0)

	var hp: RefCounted = BigNumScript.from_float(float(ec["hp_base"])).mul(
		BigNumScript.from_float(float(ec["hp_stage_ratio"])).pow_int(s - 1)
	)
	if is_boss:
		hp = hp.mul_float(float(ec["boss_hp_multiplier"]))

	var armor: RefCounted = BigNumScript.from_float(float(ec["armor_base"])).mul(
		BigNumScript.from_float(float(ec["armor_stage_ratio"])).pow_int(s - 1)
	)
	var gold_drop: RefCounted = BigNumScript.from_float(float(ec["gold_base"])).mul(
		BigNumScript.from_float(float(ec["gold_stage_ratio"])).pow_int(s - 1)
	).mul_float(3.0 if is_boss else 1.0)

	return {
		"stage": s,
		"wave": w,
		"is_boss": is_boss,
		"is_titanic": is_titanic,
		"hp": hp,
		"armor": armor,
		"gold_drop": gold_drop,
		"posture_max": float(ec["titanic_posture_max"]) if is_titanic else 0.0,
		"enrage_seconds": float(ec.get("boss_enrage_seconds", 45.0)),
	}


static func compute_hit_damage(stats: Dictionary, enemy_armor: RefCounted, is_crit: bool, special_mult: float = 1.0) -> RefCounted:
	var excess_armor: RefCounted = enemy_armor.sub_clamped(stats["penetration"])
	var ratio: float = excess_armor.div(BigNumScript.from_float(100.0)).to_approx_float()
	var mitigation: float = 0.05 if is_inf(ratio) or is_nan(ratio) else maxf(0.05, 1.0 / (1.0 + ratio))
	var crit_mult: float = float(stats["crit_damage"]) if is_crit else 1.0
	return stats["atk_total"].mul_float(mitigation * crit_mult * maxf(0.0, special_mult))


static func compute_offline_reward(
	state: Dictionary,
	gold_per_sec: RefCounted,
	cfg_raw: Dictionary,
	now_utc_ms: int,
	request_3x: bool,
	reward_verified: bool
) -> Dictionary:
	var last_seen: int = int(state["last_seen_utc_ms"])
	if now_utc_ms < last_seen:
		return {
			"ok": false,
			"tamper_detected": true,
			"error": "Clock rollback detected",
			"effective_seconds": 0,
			"multiplier": 1.0,
			"gold": BigNumScript.zero(),
		}

	if request_3x and not (reward_verified or bool(state["has_no_ads_pass"])):
		return {
			"ok": false,
			"tamper_detected": false,
			"error": "Unverified Rewarded Ad or No-Ads Pass for 3x Dragon Chest",
			"effective_seconds": 0,
			"multiplier": 1.0,
			"gold": BigNumScript.zero(),
		}

	var off_cfg: Dictionary = cfg_raw["offline_rewards_config"]
	var raw_delta_s: int = int(floor(float(now_utc_ms - last_seen) / 1000.0))
	var eff_s: int = mini(raw_delta_s, int(off_cfg["max_offline_seconds"]))
	if eff_s < int(off_cfg["min_claim_seconds"]):
		return {
			"ok": true,
			"tamper_detected": false,
			"effective_seconds": eff_s,
			"multiplier": 1.0,
			"gold": BigNumScript.zero(),
		}

	var mult: float = float(off_cfg["dragon_chest_ad_multiplier"]) if request_3x else 1.0
	var base_loot: RefCounted = gold_per_sec.mul_float(float(eff_s) * float(off_cfg["efficiency_ratio"]) * mult)
	return {
		"ok": true,
		"tamper_detected": false,
		"effective_seconds": eff_s,
		"multiplier": mult,
		"gold": base_loot,
	}


static func _find_banner(banner_id: String, cfg_raw: Dictionary) -> Dictionary:
	for b in cfg_raw.get("gacha_banners", []):
		if String(b["banner_id"]) == banner_id:
			return b
	return {}


static func _roll_rarity_once(probs: Dictionary, rng: RefCounted) -> String:
	var roll: float = rng.next_float()
	var acc: float = 0.0
	for r_name in RARITY_ORDER:
		if probs.has(r_name):
			acc += float(probs[r_name])
			if roll < acc:
				return String(r_name)
	return "COMMON"


static func execute_gacha_pull(
	state: Dictionary,
	banner_id: String,
	pull_count: int,
	via_ad: bool,
	reward_verified: bool,
	rng: RefCounted,
	cfg_raw: Dictionary,
	now_utc_ms: int
) -> Dictionary:
	if rng == null or (pull_count != 1 and pull_count != 10):
		return {"ok": false, "error": "Invalid RNG or pull_count (must be 1 or 10)"}
	var banner: Dictionary = _find_banner(banner_id, cfg_raw)
	if banner.is_empty():
		return {"ok": false, "error": "Unknown banner_id"}

	var cur_day: int = int(floor(float(maxi(0, now_utc_ms)) / 86400000.0))
	if cur_day > int(state["last_ad_day_utc"]):
		state["last_ad_day_utc"] = cur_day
		state["daily_ad_pulls_used"] = 0

	if via_ad:
		if pull_count != 10:
			return {"ok": false, "error": "Ad free pull only supports 10x"}
		if not (reward_verified or bool(state["has_no_ads_pass"])):
			return {"ok": false, "error": "Unverified Rewarded Ad or No-Ads Pass"}
		if int(state["daily_ad_pulls_used"]) >= int(banner["daily_ad_ten_pull_cap"]):
			return {"ok": false, "error": "Daily ad 10x pull cap reached"}
		state["daily_ad_pulls_used"] = int(state["daily_ad_pulls_used"]) + 1
	else:
		var cost: int = int(banner["single_cost_gems"]) if pull_count == 1 else int(banner["ten_pull_cost_gems"])
		if int(state["gems"]) < cost:
			return {"ok": false, "error": "Insufficient gems"}
		state["gems"] = int(state["gems"]) - cost

	var pity_limit: int = int(banner["pity_hard_threshold"])
	var pity_rarity: String = String(banner["pity_guaranteed_min_rarity"])
	var probs: Dictionary = banner["probabilities"]
	var results: Array[String] = []
	var pity_triggered: bool = false

	for _i in range(pull_count):
		var pity: int = int(state["pity_counter"]) + 1
		var rarity: String
		if pity >= pity_limit:
			rarity = pity_rarity
			state["pity_counter"] = 0
			pity_triggered = true
		else:
			rarity = _roll_rarity_once(probs, rng)
			if rarity == pity_rarity:
				state["pity_counter"] = 0
			else:
				state["pity_counter"] = pity
		results.append(rarity)

		var target_mult: float = float(RARITY_MULTS.get(rarity, 1.0))
		var equip_key: String = "equipped_weapon_mult"
		if String(banner.get("category", "WEAPON")) == "AURA":
			equip_key = "equipped_aura_mult"
		elif String(banner.get("category", "WEAPON")) == "SPIRIT":
			equip_key = "equipped_spirit_mult"

		if target_mult > float(state[equip_key]):
			state[equip_key] = target_mult
		else:
			# Duplicatas dao pequeno ganho cumulativo de fusao/refino.
			state[equip_key] = float(state[equip_key]) + (target_mult * 0.02)

	return {
		"ok": true,
		"results": results,
		"pity_triggered": pity_triggered,
		"pity_counter": int(state["pity_counter"]),
	}


static func compute_prestige_preview(state: Dictionary, cfg_raw: Dictionary) -> Dictionary:
	var pcfg: Dictionary = cfg_raw["prestige_config"]
	var max_s: int = int(state["max_stage_reached"])
	var min_req: int = int(pcfg["min_stage_required"])
	if max_s < min_req:
		return {"eligible": false, "gained_orbs": BigNumScript.zero(), "min_stage_required": min_req}

	var ratio: float = float(max_s) / float(pcfg["base_divisor"])
	var raw_orbs: float = floor(float(pcfg["soul_orb_scale"]) * pow(ratio, float(pcfg["stage_exponent"])))
	return {
		"eligible": true,
		"gained_orbs": BigNumScript.from_float(maxf(1.0, raw_orbs)),
		"min_stage_required": min_req,
	}


static func execute_prestige(state: Dictionary, cfg_raw: Dictionary) -> Dictionary:
	var preview: Dictionary = compute_prestige_preview(state, cfg_raw)
	if not bool(preview["eligible"]):
		return {"ok": false, "error": "Minimum stage not reached for Prestige"}

	var gained: RefCounted = preview["gained_orbs"]
	state["soul_orbs"] = (state["soul_orbs"] as RefCounted).add(gained)
	state["best_stage_lifetime"] = maxi(int(state.get("best_stage_lifetime", 1)), int(state["max_stage_reached"]))
	state["gold"] = BigNumScript.zero()
	state["ki_energy"] = 0.0
	state["active_ki_tier"] = 1
	state["current_stage"] = 1
	state["max_stage_reached"] = 1
	var levels: Dictionary = state["levels"]
	for k in levels.keys():
		levels[k] = 0

	return {"ok": true, "gained_orbs": gained, "total_orbs": state["soul_orbs"]}
