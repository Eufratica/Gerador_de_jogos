extends CanvasLayer
## HUD de Combate 16:9 com barras de HP/Mana/Furia, Boss, 4 Magias, QTE e Controles Touch/PC.

signal open_forge_clicked
signal back_to_title_clicked
signal interact_clicked
signal qte_clicked
signal revive_clicked(accepted: bool)

var _hp_bar: ProgressBar = null
var _hp_lbl: Label = null
var _mana_bar: ProgressBar = null
var _rage_bar: ProgressBar = null
var _res_lbl: Label = null
var _loc_lbl: Label = null
var _status_toast: Label = null

var _boss_box: VBoxContainer = null
var _boss_name_lbl: Label = null
var _boss_hp_bar: ProgressBar = null
var _boss_posture_bar: ProgressBar = null

var _touch_root: Control = null
var _touch_visible: bool = true
var _touch_toggle_btn: Button = null
var _interact_btn: Button = null
var _rage_btn: Button = null

var _skill_btns: Array[Button] = []
var _qte_overlay: Control = null
var _qte_bar: ProgressBar = null
var _defeat_overlay: Control = null
var _defeat_revive_btn: Button = null
var _victory_overlay: Control = null

# Estado de toque em hold/pulse
var touch_left_held: bool = false
var touch_right_held: bool = false
var touch_jump_pulse: bool = false
var touch_dash_pulse: bool = false
var touch_attack_pulse: bool = false
var touch_rage_pulse: bool = false
var touch_skill_pulse: int = -1
var _toast_timer_s: float = 0.0
var _built: bool = false


func _ready() -> void:
	_ensure_built()


func _ensure_built() -> void:
	if _built:
		return
	_built = true
	layer = 10
	_build_hud()


func _make_bar(w: float, h: float, fill_col: Color, bg_col: Color) -> ProgressBar:
	var pb := ProgressBar.new()
	pb.custom_minimum_size = Vector2(w, h)
	pb.max_value = 1.0
	pb.value = 1.0
	pb.show_percentage = false
	var sb_bg := StyleBoxFlat.new()
	sb_bg.bg_color = bg_col
	sb_bg.corner_radius_top_left = 4
	sb_bg.corner_radius_top_right = 4
	sb_bg.corner_radius_bottom_left = 4
	sb_bg.corner_radius_bottom_right = 4
	var sb_fg := StyleBoxFlat.new()
	sb_fg.bg_color = fill_col
	sb_fg.corner_radius_top_left = 4
	sb_fg.corner_radius_top_right = 4
	sb_fg.corner_radius_bottom_left = 4
	sb_fg.corner_radius_bottom_right = 4
	pb.add_theme_stylebox_override("background", sb_bg)
	pb.add_theme_stylebox_override("fill", sb_fg)
	return pb


func _make_action_btn(lbl_text: String, size_v: Vector2, accent: Color) -> Button:
	var btn := Button.new()
	btn.text = lbl_text
	btn.custom_minimum_size = size_v
	btn.focus_mode = Control.FOCUS_NONE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.08, 0.08, 0.12, 0.85)
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


func _build_hud() -> void:
	# Topo Esquerdo: Guerreiro
	var tl := VBoxContainer.new()
	tl.position = Vector2(28.0, 22.0)
	tl.add_theme_constant_override("separation", 6)
	add_child(tl)

	_loc_lbl = Label.new()
	_loc_lbl.add_theme_font_size_override("font_size", 18)
	_loc_lbl.add_theme_color_override("font_color", Color(0.95, 0.78, 0.42))
	tl.add_child(_loc_lbl)

	_hp_bar = _make_bar(360.0, 22.0, Color(0.88, 0.18, 0.22), Color(0.12, 0.05, 0.06, 0.9))
	tl.add_child(_hp_bar)
	_hp_lbl = Label.new()
	_hp_lbl.add_theme_font_size_override("font_size", 13)
	_hp_lbl.position = Vector2(10.0, 2.0)
	_hp_bar.add_child(_hp_lbl)

	_mana_bar = _make_bar(320.0, 14.0, Color(0.22, 0.65, 1.0), Color(0.06, 0.09, 0.14, 0.9))
	tl.add_child(_mana_bar)

	_rage_bar = _make_bar(280.0, 12.0, Color(1.0, 0.56, 0.14), Color(0.14, 0.08, 0.04, 0.9))
	tl.add_child(_rage_bar)

	_res_lbl = Label.new()
	_res_lbl.add_theme_font_size_override("font_size", 18)
	_res_lbl.add_theme_color_override("font_color", Color(0.92, 0.94, 0.98))
	tl.add_child(_res_lbl)

	# Topo Centro: Chefe Titanico
	_boss_box = VBoxContainer.new()
	_boss_box.position = Vector2(610.0, 22.0)
	_boss_box.custom_minimum_size = Vector2(700.0, 0.0)
	_boss_box.add_theme_constant_override("separation", 5)
	_boss_box.visible = false
	add_child(_boss_box)

	_boss_name_lbl = Label.new()
	_boss_name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_boss_name_lbl.add_theme_font_size_override("font_size", 22)
	_boss_name_lbl.add_theme_color_override("font_color", Color(1.0, 0.35, 0.25))
	_boss_box.add_child(_boss_name_lbl)

	_boss_hp_bar = _make_bar(700.0, 22.0, Color(0.85, 0.14, 0.18), Color(0.12, 0.04, 0.05, 0.9))
	_boss_box.add_child(_boss_hp_bar)

	_boss_posture_bar = _make_bar(700.0, 10.0, Color(0.98, 0.78, 0.20), Color(0.12, 0.10, 0.04, 0.9))
	_boss_box.add_child(_boss_posture_bar)

	# Topo Direito: Utilitarios
	var tr := HBoxContainer.new()
	tr.position = Vector2(1420.0, 22.0)
	tr.add_theme_constant_override("separation", 10)
	add_child(tr)

	_touch_toggle_btn = _make_action_btn("Touch: ON", Vector2(140.0, 44.0), Color(0.4, 0.75, 0.95))
	_touch_toggle_btn.pressed.connect(func() -> void:
		_touch_visible = not _touch_visible
		_touch_root.visible = _touch_visible
		_touch_toggle_btn.text = "Touch: ON" if _touch_visible else "Touch: OFF"
	)
	tr.add_child(_touch_toggle_btn)

	var forge_btn := _make_action_btn("Forja / Runas [F]", Vector2(175.0, 44.0), Color(0.95, 0.68, 0.24))
	forge_btn.pressed.connect(func() -> void: emit_signal("open_forge_clicked"))
	tr.add_child(forge_btn)

	var title_btn := _make_action_btn("Titulo", Vector2(120.0, 44.0), Color(0.65, 0.65, 0.72))
	title_btn.pressed.connect(func() -> void: emit_signal("back_to_title_clicked"))
	tr.add_child(title_btn)

	# Toast informativo no topo medio
	_status_toast = Label.new()
	_status_toast.position = Vector2(610.0, 108.0)
	_status_toast.custom_minimum_size = Vector2(700.0, 36.0)
	_status_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status_toast.add_theme_font_size_override("font_size", 22)
	_status_toast.add_theme_color_override("font_color", Color(0.35, 0.98, 0.90))
	_status_toast.visible = false
	add_child(_status_toast)

	# Botoes Touch / PC Hints
	_touch_root = Control.new()
	_touch_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_touch_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_touch_root)

	var left_btn := _make_action_btn("< [A]", Vector2(115.0, 100.0), Color(0.55, 0.65, 0.80))
	left_btn.position = Vector2(36.0, 940.0)
	left_btn.button_down.connect(func() -> void: touch_left_held = true)
	left_btn.button_up.connect(func() -> void: touch_left_held = false)
	_touch_root.add_child(left_btn)

	var right_btn := _make_action_btn("> [D]", Vector2(115.0, 100.0), Color(0.55, 0.65, 0.80))
	right_btn.position = Vector2(170.0, 940.0)
	right_btn.button_down.connect(func() -> void: touch_right_held = true)
	right_btn.button_up.connect(func() -> void: touch_right_held = false)
	_touch_root.add_child(right_btn)

	# 4 Magias Ativas
	var magic_labels: Array[String] = ["[1] Chamas", "[2] Gelo", "[3] Raio", "[4] Egide"]
	var magic_cols: Array[Color] = [
		Color(1.0, 0.42, 0.16),
		Color(0.35, 0.90, 1.0),
		Color(1.0, 0.92, 0.30),
		Color(0.42, 0.88, 0.82),
	]
	for i in range(4):
		var sb := _make_action_btn(magic_labels[i], Vector2(126.0, 74.0), magic_cols[i])
		sb.position = Vector2(1130.0 + float(i) * 136.0, 976.0)
		var idx_copy: int = i
		sb.pressed.connect(func() -> void: touch_skill_pulse = idx_copy)
		_touch_root.add_child(sb)
		_skill_btns.append(sb)

	_rage_btn = _make_action_btn("FURIA [R]", Vector2(138.0, 62.0), Color(1.0, 0.62, 0.15))
	_rage_btn.position = Vector2(1130.0, 898.0)
	_rage_btn.pressed.connect(func() -> void: touch_rage_pulse = true)
	_touch_root.add_child(_rage_btn)

	_interact_btn = _make_action_btn("INTERAGIR [E]", Vector2(260.0, 62.0), Color(0.35, 0.95, 0.88))
	_interact_btn.position = Vector2(1284.0, 898.0)
	_interact_btn.visible = false
	_interact_btn.pressed.connect(func() -> void: emit_signal("interact_clicked"))
	_touch_root.add_child(_interact_btn)

	var dash_btn := _make_action_btn("DASH [Shift]", Vector2(128.0, 76.0), Color(0.38, 0.88, 1.0))
	dash_btn.position = Vector2(1690.0, 875.0)
	dash_btn.pressed.connect(func() -> void: touch_dash_pulse = true)
	_touch_root.add_child(dash_btn)

	var jump_btn := _make_action_btn("PULO [Space]", Vector2(128.0, 76.0), Color(0.75, 0.85, 0.95))
	jump_btn.position = Vector2(1550.0, 875.0)
	jump_btn.pressed.connect(func() -> void: touch_jump_pulse = true)
	_touch_root.add_child(jump_btn)

	var atk_btn := _make_action_btn("GOLPE [J]", Vector2(200.0, 96.0), Color(1.0, 0.28, 0.22))
	atk_btn.position = Vector2(1688.0, 960.0)
	atk_btn.pressed.connect(func() -> void: touch_attack_pulse = true)
	_touch_root.add_child(atk_btn)

	# Overlay QTE do Chefe
	_qte_overlay = CenterContainer.new()
	_qte_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_qte_overlay.visible = false
	add_child(_qte_overlay)
	var qte_box := VBoxContainer.new()
	qte_box.add_theme_constant_override("separation", 12)
	_qte_overlay.add_child(qte_box)
	var qte_btn := _make_action_btn("QTE FINISHER! [ESPACO / TOQUE]", Vector2(460.0, 110.0), Color(1.0, 0.82, 0.18))
	qte_btn.add_theme_font_size_override("font_size", 24)
	qte_btn.pressed.connect(func() -> void: emit_signal("qte_clicked"))
	qte_box.add_child(qte_btn)
	_qte_bar = _make_bar(460.0, 16.0, Color(1.0, 0.82, 0.18), Color(0.15, 0.10, 0.04, 0.9))
	qte_box.add_child(_qte_bar)

	# Overlay Derrota (Fail-Closed)
	_defeat_overlay = _make_modal_overlay("VOCE CAIU EM COMBATE")
	var d_box: VBoxContainer = _defeat_overlay.get_node("Center/Panel/VBox")
	_defeat_revive_btn = _make_action_btn("Reviver c/ Furia", Vector2(360.0, 54.0), Color(1.0, 0.72, 0.22))
	_defeat_revive_btn.pressed.connect(func() -> void: emit_signal("revive_clicked", true))
	d_box.add_child(_defeat_revive_btn)
	var d_altar_btn := _make_action_btn("Voltar ao Ultimo Altar (Manter Ouro)", Vector2(360.0, 54.0), Color(0.35, 0.92, 0.88))
	d_altar_btn.pressed.connect(func() -> void: emit_signal("revive_clicked", false))
	d_box.add_child(d_altar_btn)
	add_child(_defeat_overlay)

	# Overlay Vitoria de Campanha
	_victory_overlay = _make_modal_overlay("MUNDOS CONQUISTADOS!")
	var v_box: VBoxContainer = _victory_overlay.get_node("Center/Panel/VBox")
	var v_sub := Label.new()
	v_sub.text = "Todos os Chefes Titanicos desta temporada foram derrotados!"
	v_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v_box.add_child(v_sub)
	var v_title_btn := _make_action_btn("Voltar ao Titulo", Vector2(320.0, 52.0), Color(0.95, 0.75, 0.30))
	v_title_btn.pressed.connect(func() -> void: emit_signal("back_to_title_clicked"))
	v_box.add_child(v_title_btn)
	add_child(_victory_overlay)


func _make_modal_overlay(title_txt: String) -> Control:
	var root := ColorRect.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.color = Color(0.02, 0.01, 0.02, 0.78)
	root.visible = false
	var center := CenterContainer.new()
	center.name = "Center"
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var panel := PanelContainer.new()
	panel.name = "Panel"
	panel.custom_minimum_size = Vector2(460.0, 260.0)
	center.add_child(panel)
	var vbox := VBoxContainer.new()
	vbox.name = "VBox"
	vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_theme_constant_override("separation", 16)
	panel.add_child(vbox)
	var lbl := Label.new()
	lbl.text = title_txt
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", 28)
	lbl.add_theme_color_override("font_color", Color(1.0, 0.38, 0.25))
	vbox.add_child(lbl)
	return root


func show_toast(msg: String, duration_s: float = 2.4) -> void:
	_status_toast.text = msg
	_status_toast.visible = true
	_toast_timer_s = duration_s


func consume_touch_pulses() -> Dictionary:
	var dir_x: float = 0.0
	if touch_left_held:
		dir_x -= 1.0
	if touch_right_held:
		dir_x += 1.0
	var out: Dictionary = {
		"move_x": dir_x,
		"jump_pressed": touch_jump_pulse,
		"dash_pressed": touch_dash_pulse,
		"attack_pressed": touch_attack_pulse,
		"rage_pressed": touch_rage_pulse,
		"cast_skill_idx": touch_skill_pulse,
	}
	touch_jump_pulse = false
	touch_dash_pulse = false
	touch_attack_pulse = false
	touch_rage_pulse = false
	touch_skill_pulse = -1
	return out


func update_state(dt: float, core: RefCounted, world_name: String, room_name: String, suffixes: PackedStringArray, decimals: int, interact_hint: String, now_ms: int) -> void:
	if _toast_timer_s > 0.0:
		_toast_timer_s = maxf(0.0, _toast_timer_s - dt)
		if _toast_timer_s == 0.0:
			_status_toast.visible = false

	_loc_lbl.text = "%s  —  %s" % [world_name, room_name]
	var hp_f: float = (core.hp as RefCounted).to_approx_float()
	var mhp_f: float = maxf(1.0, (core.max_hp as RefCounted).to_approx_float())
	_hp_bar.value = clampf(hp_f / mhp_f, 0.0, 1.0)
	_hp_lbl.text = "HP: %s / %s" % [(core.hp as RefCounted).format(suffixes, decimals), (core.max_hp as RefCounted).format(suffixes, decimals)]
	_mana_bar.value = clampf(core.mana / maxf(1.0, core.max_mana), 0.0, 1.0)
	_rage_bar.value = 1.0 if core.is_rage_active() else clampf(core.rage_ratio, 0.0, 1.0)
	_rage_btn.disabled = (core.rage_ratio < 1.0 and not core.is_rage_active())

	var gold_str: String = (core.economy["gold"] as RefCounted).format(suffixes, decimals)
	_res_lbl.text = "Ouro: %s   |   Gemas: %d" % [gold_str, int(core.economy["gems"])]

	var magics: Array = core.world_cfg["player_combat"]["magic_powers"]
	for i in range(4):
		var cd: float = core.skill_cooldowns[i]
		var cost: float = float(magics[i]["mana_cost"])
		var btn: Button = _skill_btns[i]
		var short_names: Array[String] = ["Chamas", "Gelo", "Raio", "Egide"]
		if cd > 0.05:
			btn.text = "[%d] %.1fs" % [i + 1, cd]
			btn.disabled = true
		else:
			btn.text = "[%d] %s\n(%d MP)" % [i + 1, short_names[i], int(cost)]
			btn.disabled = core.mana < cost

	if interact_hint.is_empty():
		_interact_btn.visible = false
	else:
		_interact_btn.visible = true
		_interact_btn.text = "%s [E]" % interact_hint

	# Barra do Boss se houver chefe vivo na sala
	var boss_dict: Dictionary = {}
	for e in core.enemies:
		if bool(e["is_boss"]) and int(e["ai_state"]) != 7:
			boss_dict = e
			break
	if boss_dict.is_empty():
		_boss_box.visible = false
	else:
		_boss_box.visible = true
		var arch_id: String = String(boss_dict["archetype"])
		_boss_name_lbl.text = String(core.world_cfg["enemy_archetypes"][arch_id]["display_name"]).to_upper()
		var bhp: float = (boss_dict["hp"] as RefCounted).to_approx_float()
		var bmhp: float = maxf(1.0, (boss_dict["max_hp"] as RefCounted).to_approx_float())
		_boss_hp_bar.value = clampf(bhp / bmhp, 0.0, 1.0)
		_boss_posture_bar.value = clampf(float(boss_dict["posture"]) / maxf(1.0, float(boss_dict["posture_max"])), 0.0, 1.0)

	# Overlays QTE / Derrota / Vitoria
	var phase: int = int(core.game_phase)
	_qte_overlay.visible = (phase == 1)
	if phase == 1:
		var win_ms: float = maxf(1.0, float(core.world_cfg["player_combat"]["qte_window_ms"]))
		_qte_bar.value = clampf(1.0 - float(now_ms - int(core.qte_started_ms)) / win_ms, 0.0, 1.0)

	_defeat_overlay.visible = (phase == 2)
	if phase == 2:
		var has_pass: bool = bool(core.economy.get("has_no_ads_pass", false))
		_defeat_revive_btn.disabled = not has_pass
		_defeat_revive_btn.text = "Reviver c/ Furia (No-Ads Pass)" if has_pass else "Reviver c/ Anuncio (Sprint 4C)"

	_victory_overlay.visible = (phase == 3)
	if phase == 2 or phase == 3:
		touch_left_held = false
		touch_right_held = false
