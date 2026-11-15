extends SceneTree
## Runner CLI headless oficial de testes unitarios puros (Etapa 3).
## Executa offline em < 1s e aplica politica fail-closed (exit != 0 se houver erro).

const TestBigNum = preload("res://tests/unit/test_big_num.gd")
const TestBalanceConfig = preload("res://tests/unit/test_balance_config.gd")
const TestDDTankBallistics = preload("res://tests/unit/test_ddtank_ballistics.gd")
const TestIdleEconomy = preload("res://tests/unit/test_idle_economy.gd")
const TestCombatFsm = preload("res://tests/unit/test_combat_fsm.gd")
const TestActionWorldCore = preload("res://tests/unit/test_action_world_core.gd")


func _init() -> void:
	var t0_usec: int = Time.get_ticks_usec()
	var suites: Array = []
	var suite_times_ms: Array[float] = []

	var s0 := Time.get_ticks_usec()
	suites.append(TestBigNum.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s0) / 1000.0)

	var s1 := Time.get_ticks_usec()
	suites.append(TestBalanceConfig.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s1) / 1000.0)

	var s2 := Time.get_ticks_usec()
	suites.append(TestDDTankBallistics.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s2) / 1000.0)

	var s3 := Time.get_ticks_usec()
	suites.append(TestIdleEconomy.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s3) / 1000.0)

	var s4 := Time.get_ticks_usec()
	suites.append(TestCombatFsm.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s4) / 1000.0)

	var s5 := Time.get_ticks_usec()
	suites.append(TestActionWorldCore.run())
	suite_times_ms.append(float(Time.get_ticks_usec() - s5) / 1000.0)

	var elapsed_ms: float = float(Time.get_ticks_usec() - t0_usec) / 1000.0

	var total_checks: int = 0
	var total_fails: int = 0

	print("=== PLAYFORGE UNIT TEST RUNNER (HEADLESS / OFFLINE) ===")
	for idx in range(suites.size()):
		var s = suites[idx]
		total_checks += int(s.total_assertions)
		total_fails += int(s.failed_assertions)
		print(" - Suite %-18s : %d assertions, %d failed (%.2f ms)" % [s.suite_name, s.total_assertions, s.failed_assertions, suite_times_ms[idx]])
		for err in s.failures:
			printerr(err)

	print("Total: %d assertions | Failed: %d | Elapsed: %.2f ms" % [total_checks, total_fails, elapsed_ms])

	if total_fails > 0:
		printerr("QUALITY GATE FAILED (fail-closed).")
		quit(1)
		return

	if elapsed_ms >= 1000.0:
		printerr("QUALITY GATE FAILED: core tests exceeded 1000 ms budget (%.2f ms)." % elapsed_ms)
		quit(1)
		return

	print("QUALITY GATE PASSED (< 1s deterministic pure core).")
	quit(0)
