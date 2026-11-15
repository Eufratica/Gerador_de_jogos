extends SceneTree
## Runner CLI headless do ActionBalanceVerifier (Mundos 1 -> 2, combos, magias, QTE e Altares).

const BalanceConfigScript = preload("res://src/core/balance_config.gd")
const WorldConfigScript = preload("res://src/core/action_world_config.gd")
const ActionVerifierScript = preload("res://src/factory/action_balance_verifier.gd")


func _init() -> void:
	var b_path: String = "res://config/balance_v1.json"
	var w_path: String = "res://config/action_world_v1.json"
	if not FileAccess.file_exists(b_path) or not FileAccess.file_exists(w_path):
		printerr("ACTION VERIFIER FAILED: missing config file.")
		quit(1)
		return

	var bcfg: RefCounted = BalanceConfigScript.parse_and_validate(FileAccess.get_file_as_string(b_path))
	var wcfg: RefCounted = WorldConfigScript.parse_and_validate(FileAccess.get_file_as_string(w_path))
	if not bcfg.is_valid() or not wcfg.is_valid():
		printerr("ACTION VERIFIER FAILED: invalid config schema.")
		if wcfg != null and wcfg.get("errors") != null:
			for err in wcfg.get("errors"):
				printerr(" - %s" % str(err))
		quit(1)
		return

	var suffixes: PackedStringArray = bcfg.get_bignum_suffixes()
	var decimals: int = bcfg.get_bignum_decimals()

	var t0_usec: int = Time.get_ticks_usec()
	var audit: Dictionary = ActionVerifierScript.run_full_audit(bcfg.get("raw"), wcfg.get("raw"))
	var elapsed_ms: float = float(Time.get_ticks_usec() - t0_usec) / 1000.0

	print("=== PLAYFORGE ACTION BALANCE VERIFIER (2D DARK FANTASY / FAIL-CLOSED) ===")
	print("Elapsed: %.2f ms" % elapsed_ms)

	for rep in audit.get("reports", []):
		var gold_str: String = rep["final_gold"].format(suffixes, decimals) if rep.get("final_gold") != null else "N/A"
		print(
			" - Profile %-12s [%s] | clear_t=%.1fs | worlds=%d | rooms=%d | altars=%d | magics=%d | qtes=%d | dodges=%d | deaths=%d | atk_lv=%d | gold=%s"
			% [
				String(rep["profile"]),
				"PASS" if bool(rep["ok"]) else "FAIL",
				float(rep["elapsed_sim_s"]),
				int(rep["worlds_cleared"]),
				int(rep["rooms_visited"]),
				int(rep["altars_used"]),
				int(rep["skills_cast"]),
				int(rep["qte_successes"]),
				int(rep["dodges"]),
				int(rep["deaths"]),
				int(rep["attack_lv"]),
				gold_str,
			]
		)

	if not bool(audit.get("passed", false)):
		for err in audit.get("errors", []):
			printerr("FAIL: %s" % String(err))
		printerr("ACTION BALANCE GATE FAILED (fail-closed).")
		quit(1)
		return

	print("ACTION BALANCE GATE PASSED (World 1 -> World 2 clear, 0 soft-locks).")
	quit(0)
