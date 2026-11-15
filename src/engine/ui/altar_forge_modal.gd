extends CanvasLayer
## Modal Dark Fantasy do Altar: Forja de Upgrades, Gacha Transparente e Bau Offline / Ascensao.

const IdleEconomyScript = preload("res://src/core/idle_economy.gd")

signal upgrade_requested(stat_key: String, count: int)
signal gacha_pull_requested(count: int)
signal offline_claim_requested(use_3x: bool)
signal closed

const STAT_META: Array[Array] = [
	["attack", "Laminas / Ataque"],
	["crit_rate", "Chance Critica"],
	["crit_damage", "Dano Critico"],
	["attack_speed", "Vel. de Ataque"],
	["penetration", "Penetracao Armadura"],
]

var _panel: PanelContainer = null
var _gold_lbl: Label = null
var _gems_lbl: Label = null
var _stats_summary_lbl: Label = null
var _stat_rows: Dictionary = {}
var _pity_lbl: Label = null
var _gacha_res_lbl: Label = null
var _gacha_1_btn: Button = null
var _gacha_10_btn: Button = null
var _offline_lbl: Label = null
var _offline_btn: Button = null
var _built: bool = false


func _ready() -> void:
	_ensure_built()


func _ensure_built() -> void:
	if _built:
		return
	_built = true
	layer = 30
	visible = false
	_build_ui()


func _build_ui() -> void:
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.02, 0.02, 0.04, 0.82)
	add_child(dim)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	_panel = PanelContainer.new()
	_panel.custom_minimum_size = Vector2(1180.0, 680.0)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.07, 0.07, 0.10, 0.96)
	style.border_width_left = 2
	style.border_width_top = 2
	style.border_width_right = 2
	style.border_width_bottom = 2
	style.border_color = Color(0.88, 0.56, 0.20)
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_left = 10
	style.corner_radius_bottom_right = 10
	style.content_margin_left = 24
	style.content_margin_right = 24
	style.content_margin_top = 20
	style.content_margin_bottom = 20
	_panel.add_theme_stylebox_override("panel", style)
	center.add_child(_panel)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 14)
	_panel.add_child(root)

	# Cabecalho
	var header := HBoxContainer.new()
	root.add_child(header)
	var title := Label.new()
	title.text = "ALTAR DA FORJA & RUNAS"
	title.add_theme_font_size_override("font_size", 28)
	title.add_theme_color_override("font_color", Color(1.0, 0.78, 0.35))
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(title)

	_gold_lbl = Label.new()
	_gold_lbl.add_theme_font_size_override("font_size", 20)
	_gold_lbl.add_theme_color_override("font_color", Color(1.0, 0.85, 0.30))
	header.add_child(_gold_lbl)

	var sep := Control.new()
	sep.custom_minimum_size = Vector2(24.0, 0.0)
	header.add_child(sep)

	_gems_lbl = Label.new()
	_gems_lbl.add_theme_font_size_override("font_size", 20)
	_gems_lbl.add_theme_color_override("font_color", Color(0.45, 0.92, 1.0))
	header.add_child(_gems_lbl)

	var sep2 := Control.new()
	sep2.custom_minimum_size = Vector2(24.0, 0.0)
	header.add_child(sep2)

	var close_btn := Button.new()
	close_btn.text = "FECHAR [ESC]"
	close_btn.custom_minimum_size = Vector2(150.0, 44.0)
	close_btn.pressed.connect(func() -> void: emit_signal("closed"))
	header.add_child(close_btn)

	_stats_summary_lbl = Label.new()
	_stats_summary_lbl.add_theme_font_size_override("font_size", 16)
	_stats_summary_lbl.add_theme_color_override("font_color", Color(0.78, 0.82, 0.90))
	root.add_child(_stats_summary_lbl)

	# Corpo em 2 colunas: Forja (esq) + Gacha & Offline (dir)
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 24)
	cols.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(cols)

	var forge_box := VBoxContainer.new()
	forge_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	forge_box.add_theme_constant_override("separation", 10)
	cols.add_child(forge_box)

	var f_head := Label.new()
	f_head.text = "FORJA DE PODER (UPGRADES)"
	f_head.add_theme_font_size_override("font_size", 20)
	f_head.add_theme_color_override("font_color", Color(0.95, 0.55, 0.25))
	forge_box.add_child(f_head)

	for meta in STAT_META:
		var key: String = String(meta[0])
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		forge_box.add_child(row)

		var lbl := Label.new()
		lbl.text = String(meta[1])
		lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		lbl.add_theme_font_size_override("font_size", 17)
		row.add_child(lbl)

		var b1 := Button.new()
		b1.custom_minimum_size = Vector2(165.0, 44.0)
		b1.pressed.connect(func() -> void: emit_signal("upgrade_requested", key, 1))
		row.add_child(b1)

		var b5 := Button.new()
		b5.text = "+5"
		b5.custom_minimum_size = Vector2(72.0, 44.0)
		b5.pressed.connect(func() -> void: emit_signal("upgrade_requested", key, 5))
		row.add_child(b5)

		_stat_rows[key] = {"lbl": lbl, "b1": b1, "b5": b5, "title": String(meta[1])}

	var right_box := VBoxContainer.new()
	right_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right_box.add_theme_constant_override("separation", 12)
	cols.add_child(right_box)

	var g_head := Label.new()
	g_head.text = "INVOCACAO DE RUNAS & ARMAS (GACHA)"
	g_head.add_theme_font_size_override("font_size", 20)
	g_head.add_theme_color_override("font_color", Color(0.45, 0.88, 1.0))
	right_box.add_child(g_head)

	var prob_lbl := Label.new()
	prob_lbl.text = "Taxas oficiais: Comum 55% | Raro 28% | Epico 12% | Lendario 4% | Mitico 1%"
	prob_lbl.add_theme_font_size_override("font_size", 14)
	prob_lbl.add_theme_color_override("font_color", Color(0.70, 0.76, 0.85))
	prob_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right_box.add_child(prob_lbl)

	_pity_lbl = Label.new()
	_pity_lbl.add_theme_font_size_override("font_size", 16)
	right_box.add_child(_pity_lbl)

	var g_btns := HBoxContainer.new()
	g_btns.add_theme_constant_override("separation", 12)
	right_box.add_child(g_btns)

	_gacha_1_btn = Button.new()
	_gacha_1_btn.text = "INVOCAR 1x (50 Gemas)"
	_gacha_1_btn.custom_minimum_size = Vector2(230.0, 48.0)
	_gacha_1_btn.pressed.connect(func() -> void: emit_signal("gacha_pull_requested", 1))
	g_btns.add_child(_gacha_1_btn)

	_gacha_10_btn = Button.new()
	_gacha_10_btn.text = "INVOCAR 10x (450 Gemas)"
	_gacha_10_btn.custom_minimum_size = Vector2(240.0, 48.0)
	_gacha_10_btn.pressed.connect(func() -> void: emit_signal("gacha_pull_requested", 10))
	g_btns.add_child(_gacha_10_btn)

	_gacha_res_lbl = Label.new()
	_gacha_res_lbl.text = "Nenhuma invocacao realizada nesta sessao."
	_gacha_res_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_gacha_res_lbl.custom_minimum_size = Vector2(0.0, 72.0)
	_gacha_res_lbl.add_theme_font_size_override("font_size", 15)
	_gacha_res_lbl.add_theme_color_override("font_color", Color(1.0, 0.90, 0.55))
	right_box.add_child(_gacha_res_lbl)

	var off_head := Label.new()
	off_head.text = "BAU DO DRAGAO (GANHO OFFLINE / TETO 8H)"
	off_head.add_theme_font_size_override("font_size", 18)
	off_head.add_theme_color_override("font_color", Color(1.0, 0.72, 0.30))
	right_box.add_child(off_head)

	_offline_lbl = Label.new()
	_offline_lbl.add_theme_font_size_override("font_size", 15)
	_offline_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right_box.add_child(_offline_lbl)

	_offline_btn = Button.new()
	_offline_btn.text = "RESGATAR BAU OFFLINE (1x)"
	_offline_btn.custom_minimum_size = Vector2(280.0, 46.0)
	_offline_btn.pressed.connect(func() -> void: emit_signal("offline_claim_requested", false))
	right_box.add_child(_offline_btn)


func set_gacha_feedback(msg: String) -> void:
	if _gacha_res_lbl != null:
		_gacha_res_lbl.text = msg


func refresh(eco: Dictionary, stats: Dictionary, balance_cfg: Dictionary, suffixes: PackedStringArray, decimals: int, offline_preview: Dictionary) -> void:
	var gold_bn: RefCounted = eco["gold"]
	var gems: int = int(eco["gems"])
	_gold_lbl.text = "Ouro: %s" % gold_bn.format(suffixes, decimals)
	_gems_lbl.text = "Gemas: %d" % gems

	var atk_bn: RefCounted = stats["atk_total"]
	_stats_summary_lbl.text = (
		"ATK Total: %s  |  Crit: %.1f%% (x%.2f)  |  Vel: %.2fx  |  Arma x%.2f  |  Aura x%.2f"
		% [
			atk_bn.format(suffixes, decimals),
			float(stats["crit_rate"]) * 100.0,
			float(stats["crit_damage"]),
			float(stats["attack_speed"]),
			float(eco.get("equipped_weapon_mult", 1.0)),
			float(eco.get("equipped_aura_mult", 1.0)),
		]
	)

	var curves: Dictionary = balance_cfg["upgrade_curves"]
	var levels: Dictionary = eco["levels"]
	for meta in STAT_META:
		var key: String = String(meta[0])
		var row: Dictionary = _stat_rows[key]
		var lv: int = int(levels.get(key, 0))
		var cost1: RefCounted = IdleEconomyScript.compute_upgrade_cost(curves[key], lv, 1)
		var cost5: RefCounted = IdleEconomyScript.compute_upgrade_cost(curves[key], lv, 5)
		(row["lbl"] as Label).text = "%s [Nv %d]" % [String(row["title"]), lv]
		var b1: Button = row["b1"]
		var b5: Button = row["b5"]
		b1.text = "+1 (%s)" % cost1.format(suffixes, decimals)
		b1.disabled = gold_bn.cmp(cost1) < 0
		b5.disabled = gold_bn.cmp(cost5) < 0

	var pity: int = int(eco.get("pity_counter", 0))
	_pity_lbl.text = "Hard Pity Mitico Garantido: %d / 50" % pity
	_gacha_1_btn.disabled = gems < 50
	_gacha_10_btn.disabled = gems < 450

	var eff_s: int = int(offline_preview.get("effective_seconds", 0))
	var off_gold: RefCounted = offline_preview.get("gold")
	if bool(offline_preview.get("tamper_detected", false)):
		_offline_lbl.text = "Anomalia de relogio detectada (fail-closed)."
		_offline_btn.disabled = true
	elif eff_s < 60 or off_gold == null or off_gold.is_zero():
		_offline_lbl.text = "Acumule >= 60s fora de combate para liberar recompensa offline."
		_offline_btn.disabled = true
	else:
		_offline_lbl.text = "Tempo acumulado: %ds (teto 8h) -> %s Ouro" % [eff_s, off_gold.format(suffixes, decimals)]
		_offline_btn.disabled = false
