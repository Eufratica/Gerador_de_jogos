class_name SeededRng
extends RefCounted
## PRNG deterministico XorShift32 com mascara explicita para execucao portatil.
## Camada pura: zero dependencia de Node ou entropia global do SO.

const DEFAULT_SEED: int = 0x6D2B79F5
const U32_MASK: int = 0xFFFFFFFF

var _state: int = DEFAULT_SEED


func _init(p_seed: int = DEFAULT_SEED) -> void:
	reseed(p_seed)


func reseed(p_seed: int) -> void:
	var s: int = p_seed & U32_MASK
	_state = s if s != 0 else DEFAULT_SEED
	# Warm-up para descorrelacionar sementes sequenciais (1, 2, 3...).
	for _i in range(4):
		next_u32()


func next_u32() -> int:
	var x: int = _state
	x = (x ^ ((x << 13) & U32_MASK)) & U32_MASK
	x = (x ^ ((x >> 17) & U32_MASK)) & U32_MASK
	x = (x ^ ((x << 5) & U32_MASK)) & U32_MASK
	_state = x if x != 0 else DEFAULT_SEED
	return _state


func next_float() -> float:
	return float(next_u32()) / 4294967296.0


func range_float(min_val: float, max_val: float) -> float:
	if max_val <= min_val:
		return min_val
	return min_val + (next_float() * (max_val - min_val))


func range_int(min_incl: int, max_excl: int) -> int:
	if max_excl <= min_incl:
		return min_incl
	return min_incl + (next_u32() % (max_excl - min_incl))


func roll_chance(probability: float) -> bool:
	if is_nan(probability) or probability <= 0.0:
		return false
	if probability >= 1.0:
		return true
	return next_float() < probability
