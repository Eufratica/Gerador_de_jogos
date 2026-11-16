extends SceneTree
## Runner unitario headless offline de scripts/core/ (meta < 1s).

const HarnessScript = preload("res://tests/unit/test_harness.gd")
const GraphicsTestsScript = preload("res://tests/unit/test_graphics_config.gd")


func _initialize() -> void:
	var t0 := Time.get_ticks_usec()
	var t := HarnessScript.new()

	var suite: RefCounted = GraphicsTestsScript.new()
	suite.call("run", t)

	var elapsed_ms := float(Time.get_ticks_usec() - t0) / 1000.0
	print("=== ZAIKOR: INITINE ZENKAI UNIT TESTS (HEADLESS) ===")
	print("Assertions: %d | Failed: %d | Elapsed: %.2f ms" % [t.assertions, t.failures.size(), elapsed_ms])
	for f in t.failures:
		printerr(f)

	quit(0 if t.passed() else 1)
