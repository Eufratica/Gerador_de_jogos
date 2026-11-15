extends RefCounted
## Testes unitarios puros do BigNum (escala cosmica, fail-closed e serie geometrica).

const BigNumScript = preload("res://src/core/big_num.gd")
const HarnessScript = preload("res://tests/unit/test_harness.gd")


static func run() -> RefCounted:
	var t := HarnessScript.new("BigNum")
	var suffixes := PackedStringArray(["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"])

	# 1. Zero e Um canonicos
	var z := BigNumScript.zero()
	var o := BigNumScript.one()
	t.assert_true(z.valid and z.is_zero(), "zero valid")
	t.assert_true(o.valid and not o.is_zero(), "one valid")
	t.assert_eq(z.format(suffixes, 2), "0", "format zero")
	t.assert_eq(o.format(suffixes, 2), "1", "format one")
	t.assert_eq(z.cmp(o), -1, "0 < 1")
	t.assert_eq(o.cmp(z), 1, "1 > 0")

	# 2. Normalizacao de fronteiras float64 e subnormais
	var boundary := BigNumScript.from_parts(9.999999999999999, 2)
	t.assert_true(boundary.valid, "boundary valid")
	t.assert_true(boundary.mantissa >= 1.0 and boundary.mantissa < 10.0, "mantissa normalized [1, 10)")

	var large := BigNumScript.from_float(1.5e250)
	t.assert_true(large.valid and large.exponent == 250, "from_float 1e250")
	t.assert_near(large.mantissa, 1.5, 1e-12, "mantissa 1.5e250")

	var huge: RefCounted = large.mul(BigNumScript.from_float(2.0e200))
	t.assert_true(huge.valid and huge.exponent == 450, "overflow-safe mul > 1e308")
	t.assert_near(huge.mantissa, 3.0, 1e-12, "mantissa 3.0e450")
	t.assert_eq(huge.format(suffixes, 2), "3.00e450", "scientific fallback above Dc")

	# 3. Rejeicao fail-closed de NaN, Inf, negativo e divisao por zero
	t.assert_false(BigNumScript.from_float(NAN).valid, "reject NaN")
	t.assert_false(BigNumScript.from_float(INF).valid, "reject INF")
	t.assert_false(BigNumScript.from_float(-1.0).valid, "reject negative")
	t.assert_false(o.div(z).valid, "reject div by zero")
	t.assert_false(o.pow_int(-1).valid, "reject negative pow_int")

	# 4. Aritmetica basica e sub_clamped
	var a := BigNumScript.from_float(1540.0)
	var b := BigNumScript.from_float(460.0)
	var sum_ab: RefCounted = a.add(b)
	t.assert_near(sum_ab.to_approx_float(), 2000.0, 1e-6, "1540 + 460 == 2000")
	t.assert_eq(a.format(suffixes, 2), "1.54K", "1540 -> 1.54K")

	var clamped: RefCounted = b.sub_clamped(a)
	t.assert_true(clamped.valid and clamped.is_zero(), "sub_clamped floors at 0")

	var diff_ba: RefCounted = a.sub_clamped(b)
	t.assert_near(diff_ba.to_approx_float(), 1080.0, 1e-6, "1540 - 460 == 1080")
	var div_ab: RefCounted = a.div(BigNumScript.from_float(4.0))
	t.assert_near(div_ab.to_approx_float(), 385.0, 1e-6, "1540 / 4 == 385")
	t.assert_eq(a.pow_int(0).cmp(o), 0, "x^0 == 1")
	t.assert_true(BigNumScript.from_float(0.0).is_zero(), "from_float(0) == zero")
	t.assert_near(BigNumScript.geometric_series_sum(BigNumScript.from_float(10.0), 1.0, 10, 5).to_approx_float(), 50.0, 1e-6, "ratio 1.0 -> 50")
	t.assert_true(BigNumScript.geometric_series_sum(BigNumScript.from_float(10.0), 1.14, 10, 0).is_zero(), "count 0 -> zero")

	# 5. Carry-over na formatacao (999.999 -> 1.00M, nunca 1000.00K)
	var carry := BigNumScript.from_float(999_999.0)
	t.assert_eq(carry.format(suffixes, 2), "1.00M", "rounding carry 999999 -> 1.00M")
	t.assert_eq(BigNumScript.from_parts(1.25, 15).format(suffixes, 2), "1.25Qa", "Qa suffix at 10^15")
	t.assert_eq(BigNumScript.from_parts(4.5, 18).format(suffixes, 2), "4.50Qi", "Qi suffix at 10^18")

	# 6. Serie geometrica O(1) vs soma iterativa exata (100 niveis)
	var base_cost := BigNumScript.from_float(10.0)
	var ratio: float = 1.14
	var start_lvl: int = 25
	var buy_count: int = 100

	var iter_sum := BigNumScript.zero()
	var r_bn := BigNumScript.from_float(ratio)
	for i in range(buy_count):
		var term: RefCounted = base_cost.mul(r_bn.pow_int(start_lvl + i))
		iter_sum = iter_sum.add(term)

	var closed_sum := BigNumScript.geometric_series_sum(base_cost, ratio, start_lvl, buy_count)
	t.assert_true(closed_sum.valid, "closed geometric sum valid")
	t.assert_eq(closed_sum.exponent, iter_sum.exponent, "geometric sum exponent match")
	t.assert_near(closed_sum.mantissa, iter_sum.mantissa, 1e-9, "geometric sum mantissa match")

	# 7. Serie geometrica em escala extrema (nivel 5000, além de float64 se multiplicado direto)
	var extreme_sum := BigNumScript.geometric_series_sum(base_cost, 1.14, 5000, 100)
	t.assert_true(extreme_sum.valid and extreme_sum.exponent > 250, "extreme level 5000 valid without overflow")

	return t
