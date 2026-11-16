class_name BigNum
extends RefCounted
## Matematica deterministica de escala cosmica para Idle RPG.
## Camada pura (zero dependencia de Node/SceneTree/rede/env).
## Representacao canonica: V = mantissa * 10^exponent, com zero = (0.0, 0)
## e 1.0 <= mantissa < 10.0 para valores positivos finitos.

const MAX_EXPONENT: int = 1_000_000_000_000_000
const LOG10_E: float = 2.302585092994046
const EPS_ZERO: float = 1e-15

var mantissa: float = 0.0
var exponent: int = 0
var valid: bool = true
var error_message: String = ""


func _init(p_m: float = 0.0, p_e: int = 0, p_valid: bool = true, p_err: String = "") -> void:
	mantissa = p_m
	exponent = p_e
	valid = p_valid
	error_message = p_err


static func invalid(err: String) -> RefCounted:
	return new(0.0, 0, false, err)


static func zero() -> RefCounted:
	return new(0.0, 0, true, "")


static func one() -> RefCounted:
	return new(1.0, 0, true, "")


static func from_float(value: float) -> RefCounted:
	if is_nan(value) or is_inf(value):
		return invalid("NaN or Inf is not allowed in BigNum")
	if value < 0.0:
		return invalid("Negative value is not allowed in unsigned BigNum")
	if value <= EPS_ZERO:
		return zero()
	return _normalize(value, 0)


static func from_parts(p_mantissa: float, p_exponent: int) -> RefCounted:
	if is_nan(p_mantissa) or is_inf(p_mantissa):
		return invalid("NaN or Inf mantissa in BigNum")
	if p_mantissa < 0.0:
		return invalid("Negative mantissa is not allowed in unsigned BigNum")
	if p_mantissa <= EPS_ZERO:
		return zero()
	return _normalize(p_mantissa, p_exponent)


static func _normalize(p_m: float, p_e: int) -> RefCounted:
	if is_nan(p_m) or is_inf(p_m) or p_m < 0.0:
		return invalid("Invalid state during BigNum normalization")
	if p_m <= EPS_ZERO:
		return zero()

	var m: float = p_m
	var e: int = p_e

	# Escalonamento seguro antes do log para extremos subnormais/altos de float64.
	while m >= 1e150:
		m *= 1e-100
		e += 100
	while m > 0.0 and m < 1e-150:
		m *= 1e100
		e -= 100

	var shift: int = int(floor(log(m) / LOG10_E))
	if shift != 0:
		m /= pow(10.0, float(shift))
		e += shift

	var guard: int = 0
	while m >= 10.0 and guard < 16:
		m *= 0.1
		e += 1
		guard += 1
	while m > 0.0 and m < 1.0 and guard < 32:
		m *= 10.0
		e -= 1
		guard += 1

	if is_nan(m) or is_inf(m) or abs(e) > MAX_EXPONENT:
		return invalid("BigNum exponent overflow or non-finite mantissa")

	return new(m, e, true, "")


func duplicate_num() -> RefCounted:
	return get_script().new(mantissa, exponent, valid, error_message)


func is_zero() -> bool:
	return valid and mantissa == 0.0


func cmp(other: RefCounted) -> int:
	if not valid or other == null or not bool(other.get("valid")):
		return -2
	var om: float = float(other.get("mantissa"))
	var oe: int = int(other.get("exponent"))
	if mantissa == 0.0 and om == 0.0:
		return 0
	if mantissa == 0.0:
		return -1
	if om == 0.0:
		return 1
	if exponent < oe:
		return -1
	if exponent > oe:
		return 1
	if abs(mantissa - om) <= 1e-12:
		return 0
	return -1 if mantissa < om else 1


func add(other: RefCounted) -> RefCounted:
	if not valid:
		return duplicate_num()
	if other == null or not bool(other.get("valid")):
		return invalid(String(other.get("error_message")) if other != null else "Null operand in add")
	if is_zero():
		return other.duplicate_num()
	if other.is_zero():
		return duplicate_num()

	var oe: int = int(other.get("exponent"))
	var hi: RefCounted = self if exponent >= oe else other
	var lo: RefCounted = other if exponent >= oe else self
	var hi_e: int = int(hi.get("exponent"))
	var lo_e: int = int(lo.get("exponent"))
	var diff: int = hi_e - lo_e
	if diff > 15:
		return hi.duplicate_num()

	var scaled_lo: float = float(lo.get("mantissa")) / pow(10.0, float(diff))
	return _normalize(float(hi.get("mantissa")) + scaled_lo, hi_e)


func sub_clamped(other: RefCounted) -> RefCounted:
	if not valid:
		return duplicate_num()
	if other == null or not bool(other.get("valid")):
		return invalid(String(other.get("error_message")) if other != null else "Null operand in sub_clamped")
	if cmp(other) <= 0:
		return zero()

	var diff: int = exponent - int(other.get("exponent"))
	if diff > 15:
		return duplicate_num()

	var scaled_other: float = float(other.get("mantissa")) / pow(10.0, float(diff))
	var rem: float = mantissa - scaled_other
	if rem <= EPS_ZERO:
		return zero()
	return _normalize(rem, exponent)


func mul(other: RefCounted) -> RefCounted:
	if not valid:
		return duplicate_num()
	if other == null or not bool(other.get("valid")):
		return invalid(String(other.get("error_message")) if other != null else "Null operand in mul")
	if is_zero() or other.is_zero():
		return zero()
	var oe: int = int(other.get("exponent"))
	if abs(exponent + oe) > MAX_EXPONENT:
		return invalid("Exponent overflow in BigNum.mul")
	return _normalize(mantissa * float(other.get("mantissa")), exponent + oe)


func mul_float(factor: float) -> RefCounted:
	return mul(from_float(factor))


func div(other: RefCounted) -> RefCounted:
	if not valid:
		return duplicate_num()
	if other == null or not bool(other.get("valid")):
		return invalid(String(other.get("error_message")) if other != null else "Null operand in div")
	if other.is_zero():
		return invalid("Division by zero in BigNum.div")
	if is_zero():
		return zero()
	return _normalize(mantissa / float(other.get("mantissa")), exponent - int(other.get("exponent")))


func pow_int(power: int) -> RefCounted:
	if not valid:
		return duplicate_num()
	if power < 0:
		return invalid("Negative exponent unsupported in BigNum.pow_int")
	if power == 0:
		return one()
	if is_zero():
		return zero()

	var res: RefCounted = one()
	var base: RefCounted = duplicate_num()
	var p: int = power
	while p > 0:
		if (p & 1) == 1:
			res = res.mul(base)
			if not bool(res.get("valid")):
				return res
		p >>= 1
		if p > 0:
			base = base.mul(base)
			if not bool(base.get("valid")):
				return base
	return res


static func geometric_series_sum(base_cost: RefCounted, ratio: float, current_level: int, count: int) -> RefCounted:
	if base_cost == null or not bool(base_cost.get("valid")):
		return invalid("Invalid base_cost in geometric_series_sum")
	if is_nan(ratio) or is_inf(ratio) or ratio <= 0.0:
		return invalid("Ratio must be finite and > 0 in geometric_series_sum")
	if current_level < 0 or count < 0:
		return invalid("Level and count must be >= 0")
	if count == 0:
		return zero()

	var r_bn: RefCounted = from_float(ratio)
	var first_term: RefCounted = base_cost.mul(r_bn.pow_int(current_level))
	if not bool(first_term.get("valid")):
		return first_term

	if abs(ratio - 1.0) <= 1e-12:
		return first_term.mul_float(float(count))

	var r_pow_n: RefCounted = r_bn.pow_int(count)
	if not bool(r_pow_n.get("valid")):
		return r_pow_n

	if ratio > 1.0:
		return first_term.mul(r_pow_n.sub_clamped(one())).div(from_float(ratio - 1.0))
	return first_term.mul(one().sub_clamped(r_pow_n)).div(from_float(1.0 - ratio))


func to_approx_float() -> float:
	if not valid:
		return NAN
	if is_zero():
		return 0.0
	if exponent > 308:
		return INF
	if exponent < -308:
		return 0.0
	return mantissa * pow(10.0, float(exponent))


func format(suffixes: PackedStringArray, decimal_places: int = 2) -> String:
	if not valid:
		return "ERR"
	if is_zero():
		return "0"

	if exponent < 0:
		var small_val: float = to_approx_float()
		var fmt_small: String = "%." + str(maxi(0, decimal_places)) + "f"
		return fmt_small % small_val

	if exponent < 3:
		var val: float = mantissa * pow(10.0, float(exponent))
		if abs(val - round(val)) < 1e-6:
			return str(int(round(val)))
		var fmt_mid: String = "%." + str(maxi(0, decimal_places)) + "f"
		return fmt_mid % val

	var group: int = int(exponent / 3)
	var rem: int = exponent % 3
	var scaled: float = mantissa * pow(10.0, float(rem))
	var scale_pow: float = pow(10.0, float(maxi(0, decimal_places)))
	var rounded_scaled: float = round(scaled * scale_pow) / scale_pow
	if rounded_scaled >= 1000.0:
		scaled *= 0.001
		group += 1

	var fmt_str: String = "%." + str(maxi(0, decimal_places)) + "f"
	if group < suffixes.size():
		return (fmt_str % scaled) + suffixes[group]
	return (fmt_str % mantissa) + "e" + str(exponent)
