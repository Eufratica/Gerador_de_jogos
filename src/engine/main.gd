extends Control
## Tela Titulo Dark Fantasy e gerenciador raiz do cliente Godot 4.4 (Zaikor: Zenkai Infinite).

const ArenaScene = preload("res://src/engine/scenes/battle_arena.tscn")
const SaveStoreScript = preload("res://src/engine/services/local_checkpoint_store.gd")

var _title_layer: Control = null
var _continue_btn: Button = null
var _new_btn: Button = null
var _active_arena: Node = null
var save_path: String = SaveStoreScript.DEFAULT_SAVE_PATH
var _built: bool = false


func _ready() -> void:
	if _built:
		_refresh_save_button()
		return
	_built = true
	_build_title_screen()
	_refresh_save_button()


func _build_title_screen() -> void:
	_title_layer = Control.new()
	_title_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_title_layer)

	var bg := ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.05, 0.04, 0.07)
	_title_layer.add_child(bg)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_title_layer.add_child(center)

	var vbox := VBoxContainer.new()
	vbox.custom_minimum_size = Vector2(720.0, 0.0)
	vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_theme_constant_override("separation", 18)
	center.add_child(vbox)

	var k_lbl := Label.new()
	k_lbl.text = "DARK FANTASY 2D ACTION RPG"
	k_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	k_lbl.add_theme_font_size_override("font_size", 18)
	k_lbl.add_theme_color_override("font_color", Color(0.95, 0.45, 0.20))
	vbox.add_child(k_lbl)

	var title_lbl := Label.new()
	title_lbl.text = "ZAIKOR: ZENKAI INFINITE"
	title_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title_lbl.add_theme_font_size_override("font_size", 58)
	title_lbl.add_theme_color_override("font_color", Color(0.98, 0.96, 0.92))
	vbox.add_child(title_lbl)

	var sub_lbl := Label.new()
	sub_lbl.text = "Laminas, 4 Poderes Magicos, Mundos Interconectados & Altares de Salvamento"
	sub_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub_lbl.add_theme_font_size_override("font_size", 20)
	sub_lbl.add_theme_color_override("font_color", Color(0.72, 0.78, 0.88))
	vbox.add_child(sub_lbl)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0.0, 18.0)
	vbox.add_child(spacer)

	_continue_btn = _styled_btn("CONTINUAR DO ALTAR", Color(0.28, 0.92, 0.85))
	_continue_btn.pressed.connect(_on_continue_pressed)
	vbox.add_child(_continue_btn)

	_new_btn = _styled_btn("NOVO JOGO", Color(1.0, 0.38, 0.22))
	_new_btn.pressed.connect(_on_new_game_pressed)
	vbox.add_child(_new_btn)

	var controls_lbl := Label.new()
	controls_lbl.text = "PC: [A/D] Mover  |  [W/Space] Pular  |  [Shift] Dash (i-frames)  |  [J] Combo  |  [1-4] Magias  |  [R] Furia  |  [E] Altar/Portal  |  [F] Forja\nMobile: Botoes Touch na tela (alternavel no topo direito)"
	controls_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	controls_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	controls_lbl.add_theme_font_size_override("font_size", 15)
	controls_lbl.add_theme_color_override("font_color", Color(0.60, 0.65, 0.74))
	vbox.add_child(controls_lbl)

	var ver_lbl := Label.new()
	ver_lbl.text = "PlayForge Engine Core v0.4.0-playable-slice | 1920x1080"
	ver_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ver_lbl.add_theme_font_size_override("font_size", 13)
	ver_lbl.add_theme_color_override("font_color", Color(0.45, 0.48, 0.55))
	vbox.add_child(ver_lbl)


func _styled_btn(txt: String, accent: Color) -> Button:
	var btn := Button.new()
	btn.text = txt
	btn.custom_minimum_size = Vector2(440.0, 66.0)
	btn.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	btn.add_theme_font_size_override("font_size", 24)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.09, 0.09, 0.13, 0.95)
	sb.border_width_left = 2
	sb.border_width_top = 2
	sb.border_width_right = 2
	sb.border_width_bottom = 2
	sb.border_color = accent
	sb.corner_radius_top_left = 10
	sb.corner_radius_top_right = 10
	sb.corner_radius_bottom_left = 10
	sb.corner_radius_bottom_right = 10
	btn.add_theme_stylebox_override("normal", sb)
	return btn


func _refresh_save_button() -> void:
	var has_save: bool = (not save_path.is_empty()) and SaveStoreScript.has_valid_save(save_path)
	_continue_btn.disabled = not has_save
	_continue_btn.text = "CONTINUAR DO ALTAR" if has_save else "CONTINUAR DO ALTAR (SEM SAVE)"


func _on_continue_pressed() -> void:
	var snap: Dictionary = {} if save_path.is_empty() else SaveStoreScript.load_snapshot(save_path)
	start_arena(snap)


func _on_new_game_pressed() -> void:
	start_arena({})


func start_arena(snapshot_to_restore: Dictionary) -> void:
	if _active_arena != null:
		_active_arena.queue_free()
		_active_arena = null
	_title_layer.visible = false
	_active_arena = ArenaScene.instantiate()
	_active_arena.configure_boot(snapshot_to_restore, save_path)
	_active_arena.exited_to_title.connect(_on_exited_to_title)
	add_child(_active_arena)


func _on_exited_to_title() -> void:
	if _active_arena != null:
		_active_arena.queue_free()
		_active_arena = null
	_refresh_save_button()
	_title_layer.visible = true
