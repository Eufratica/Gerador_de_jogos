extends Control
## Cena raiz enxuta do template PlayForge Action 2D Base.

const CoreScript = preload("res://src/core/game_loop_core.gd")
const DEFAULT_CONFIG_PATH: String = "res://config/template_defaults.json"

var core: RefCounted = null
var _boot_ok: bool = false
var _status_label: Label = null


func _ready() -> void:
	_status_label = Label.new()
	_status_label.position = Vector2(32.0, 32.0)
	add_child(_status_label)
	boot_from_config(DEFAULT_CONFIG_PATH)


func boot_from_config(cfg_path: String = DEFAULT_CONFIG_PATH) -> bool:
	if not FileAccess.file_exists(cfg_path):
		_boot_ok = false
		_update_label("BOOT ERROR: config missing")
		return false
	var json_text: String = FileAccess.get_file_as_string(cfg_path)
	core = CoreScript.parse_and_create(json_text, 2026)
	_boot_ok = core != null and bool(core.get("valid"))
	if _boot_ok:
		_update_label("READY: %s" % String(core.get("game_id")))
	else:
		_update_label("BOOT ERROR: invalid config")
	return _boot_ok


func is_boot_valid() -> bool:
	return _boot_ok


func _update_label(msg: String) -> void:
	if _status_label != null:
		_status_label.text = msg


func _process(delta: float) -> void:
	if not _boot_ok or core == null:
		return
	var dir: float = Input.get_axis("ui_left", "ui_right")
	var atk: bool = Input.is_action_just_pressed("ui_accept")
	if dir != 0.0 or atk:
		core.step(delta, dir, atk)
		queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.06, 0.06, 0.09, 1.0))
	if core != null and bool(core.get("valid")):
		var hx: float = float(core.get("hero_x"))
		draw_rect(Rect2(Vector2(hx - 24.0, 540.0), Vector2(48.0, 96.0)), Color(0.25, 0.65, 0.95, 1.0))
		if not bool(core.get("campaign_cleared")):
			draw_rect(Rect2(Vector2(1400.0, 520.0), Vector2(64.0, 116.0)), Color(0.88, 0.24, 0.28, 1.0))
