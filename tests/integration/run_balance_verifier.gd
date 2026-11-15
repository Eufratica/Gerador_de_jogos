extends SceneTree
## Runner CLI headless oficial do BalanceVerifier (72h offline, fail-closed).

const BalanceConfigScript = preload("res://src/core/balance_config.gd")
const BalanceVerifierScript = preload("res://src/factory/balance_verifier.gd")


func _init() -> void:
	var config_path: String = "res://config/balance_v1.json"
	if not FileAccess.file_exists(config_path):
		printerr("BALANCE VERIFIER FAILED: missing config file: %s" % config_path)
		quit(1)
		return

	var json_text: String = FileAccess.get_file_as_string(config_path)
	if json_text.is_empty():
		printerr("BALANCE VERIFIER FAILED: empty or unreadable config file: %s" % config_path)
		quit(1)
		return

	var cfg: RefCounted = BalanceConfigScript.parse_and_validate(json_text)
	if cfg == null or not cfg.is_valid():
		printerr("BALANCE VERIFIER FAILED: invalid balance config schema.")
		if cfg != null and cfg.get("errors") != null:
			for err in cfg.get("errors"):
				printerr(" - %s" % str(err))
		quit(1)
		return

	var suffixes: PackedStringArray = cfg.get_bignum_suffixes()
	var decimals: int = cfg.get_bignum_decimals()
	var cfg_raw: Dictionary = cfg.get("raw")

	var t0_usec: int = Time.get_ticks_usec()
	var audit: Dictionary = BalanceVerifierScript.run_full_audit(cfg_raw)
	var elapsed_ms: float = float(Time.get_ticks_usec() - t0_usec) / 1000.0

	print("=== PLAYFORGE BALANCE VERIFIER (72H HEADLESS / FAIL-CLOSED) ===")
	print("Config: %s | Elapsed: %.2f ms" % [config_path, elapsed_ms])

	var reports: Array = audit.get("reports", [])
	for rep in reports:
		var prof: String = str(rep.get("profile", "UNKNOWN"))
		var ok: bool = bool(rep.get("ok", false))
		var best_stage: int = int(rep.get("best_stage", 0))
		var prestige_count: int = int(rep.get("prestige_count", 0))
		var max_stall_s: float = float(rep.get("max_stall_s", 0.0))
		var max_wave_s: float = float(rep.get("max_wave_s", 0.0))
		var max_recovery_s: float = float(rep.get("max_recovery_s", 0.0))
		var final_gold = rep.get("final_gold")
		var soul_orbs = rep.get("soul_orbs")
		var gold_str: String = final_gold.format(suffixes, decimals) if final_gold != null else "N/A"
		var orbs_str: String = soul_orbs.format(suffixes, decimals) if soul_orbs != null else "N/A"
		print(
			" - Profile %-13s [%s] | best_stage=%d | prestiges=%d | max_stall=%.1fs | max_wave=%.1fs | max_recovery=%.1fs | gold=%s | orbs=%s"
			% [
				prof,
				"PASS" if ok else "FAIL",
				best_stage,
				prestige_count,
				max_stall_s,
				max_wave_s,
				max_recovery_s,
				gold_str,
				orbs_str,
			]
		)

	var passed: bool = bool(audit.get("passed", false))
	if not passed:
		var errors: PackedStringArray = audit.get("errors", PackedStringArray())
		for err in errors:
			printerr("FAIL: %s" % err)
		printerr("BALANCE GATE FAILED (fail-closed).")
		quit(1)
		return

	print("BALANCE GATE PASSED (0 progress walls / 0 soft-locks across 72h).")
	quit(0)
