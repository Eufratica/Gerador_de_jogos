class_name TerrainHeightmap
extends RefCounted
## Terreno logico 1D pre-alocado para deformacao por crateras DDTank.
## Coordenadas cartesianas puras (+x para direita, +y para cima).
## Zero GC Alloc apos inicializacao.

const SAMPLE_COUNT: int = 256

var arena_width: float = 1920.0
var bedrock_y: float = 40.0
var max_height: float = 180.0
var dx: float = 1920.0 / float(SAMPLE_COUNT - 1)
var _heights: PackedFloat64Array = PackedFloat64Array()


func _init(p_arena_width: float = 1920.0, p_base_ground_y: float = 180.0, p_bedrock_y: float = 40.0) -> void:
	arena_width = max(1.0, p_arena_width)
	bedrock_y = p_bedrock_y
	dx = arena_width / float(SAMPLE_COUNT - 1)
	_heights.resize(SAMPLE_COUNT)
	reset_flat(p_base_ground_y)


func reset_flat(ground_y: float) -> void:
	var clamped_y: float = max(bedrock_y, ground_y)
	max_height = clamped_y
	for i in range(SAMPLE_COUNT):
		_heights[i] = clamped_y


func set_profile_slope(start_y: float, end_y: float) -> void:
	max_height = max(bedrock_y, max(start_y, end_y))
	for i in range(SAMPLE_COUNT):
		var t: float = float(i) / float(SAMPLE_COUNT - 1)
		_heights[i] = max(bedrock_y, lerpf(start_y, end_y, t))


func sample_height(x: float) -> float:
	var clamped_x: float = clampf(x, 0.0, arena_width)
	var f_idx: float = clamped_x / dx
	var idx0: int = clampi(int(floor(f_idx)), 0, SAMPLE_COUNT - 1)
	var idx1: int = mini(idx0 + 1, SAMPLE_COUNT - 1)
	var frac: float = f_idx - float(idx0)
	return lerpf(_heights[idx0], _heights[idx1], frac)


func carve_crater(impact_x: float, impact_y: float, radius: float) -> int:
	if is_nan(impact_x) or is_nan(impact_y) or is_nan(radius) or radius <= 0.0:
		return 0

	var min_x: float = max(0.0, impact_x - radius)
	var max_x: float = min(arena_width, impact_x + radius)
	var idx_min: int = clampi(int(floor(min_x / dx)), 0, SAMPLE_COUNT - 1)
	var idx_max: int = clampi(int(ceil(max_x / dx)), 0, SAMPLE_COUNT - 1)
	var r_sq: float = radius * radius
	var modified: int = 0

	for i in range(idx_min, idx_max + 1):
		var col_x: float = float(i) * dx
		var offset_x: float = col_x - impact_x
		var inside_sq: float = r_sq - (offset_x * offset_x)
		if inside_sq >= 0.0:
			var crater_floor: float = impact_y - sqrt(inside_sq)
			var next_h: float = max(bedrock_y, min(_heights[i], crater_floor))
			if next_h < _heights[i]:
				_heights[i] = next_h
				modified += 1

	return modified


func copy_from(other: RefCounted) -> void:
	if other == null:
		return
	arena_width = float(other.get("arena_width"))
	bedrock_y = float(other.get("bedrock_y"))
	max_height = float(other.get("max_height"))
	dx = float(other.get("dx"))
	var other_h: PackedFloat64Array = other.get("_heights")
	for i in range(SAMPLE_COUNT):
		_heights[i] = other_h[i]
