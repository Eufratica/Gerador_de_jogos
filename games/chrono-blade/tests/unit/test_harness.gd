class_name TestHarness
extends RefCounted
## Auxiliar minimo e deterministico para testes unitarios puros headless.

var suite_name: String = ""
var total_assertions: int = 0
var failed_assertions: int = 0
var failures: PackedStringArray = PackedStringArray()


func _init(p_name: String) -> void:
	suite_name = p_name


func assert_true(cond: bool, msg: String) -> void:
	total_assertions += 1
	if not cond:
		failed_assertions += 1
		failures.append("[%s] FAIL assert_true: %s" % [suite_name, msg])


func assert_false(cond: bool, msg: String) -> void:
	assert_true(not cond, msg)


func assert_eq(actual: Variant, expected: Variant, msg: String) -> void:
	total_assertions += 1
	if actual != expected:
		failed_assertions += 1
		failures.append("[%s] FAIL assert_eq (%s): expected=%s actual=%s" % [suite_name, msg, str(expected), str(actual)])


func assert_near(actual: float, expected: float, tol: float, msg: String) -> void:
	total_assertions += 1
	if is_nan(actual) or is_nan(expected) or abs(actual - expected) > tol:
		failed_assertions += 1
		failures.append("[%s] FAIL assert_near (%s): expected=%.9f actual=%.9f tol=%.9f" % [suite_name, msg, expected, actual, tol])
