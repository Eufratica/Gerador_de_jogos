class_name ZizTestHarness
extends RefCounted
## Harness minimo e deterministico para testes unitarios headless em scripts/core/.

var assertions: int = 0
var failures: Array[String] = []


func assert_true(cond: bool, msg: String) -> void:
	assertions += 1
	if not cond:
		failures.append("FAIL [assert_true]: %s" % msg)


func assert_false(cond: bool, msg: String) -> void:
	assertions += 1
	if cond:
		failures.append("FAIL [assert_false]: %s" % msg)


func assert_eq(actual: Variant, expected: Variant, msg: String) -> void:
	assertions += 1
	if actual != expected:
		failures.append("FAIL [assert_eq]: %s (esperado=%s, obtido=%s)" % [msg, str(expected), str(actual)])


func passed() -> bool:
	return failures.is_empty()
