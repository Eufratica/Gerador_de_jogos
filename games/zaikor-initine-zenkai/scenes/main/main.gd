extends Node3D
## Cena raiz base da Etapa 1 (Compatibility Renderer, 1280x720, perfil Baixo padrao).

const BootstrapScript = preload("res://scripts/core/game_bootstrap.gd")
const GraphicsConfigScript = preload("res://scripts/core/graphics_config.gd")

var current_profile_id: String = GraphicsConfigScript.DEFAULT_PROFILE_ID
var boot_descriptor: Dictionary = {}
var _boot_valid: bool = false
var _benchmark_target_frames: int = 0
var _benchmark_frames_seen: int = 0
var _benchmark_start_usec: int = 0

@onready var _sun_light: DirectionalLight3D = $SunLight
@onready var _world_env: WorldEnvironment = $WorldEnvironment
@onready var _hud_label: Label = $OverlayHUD/StatsLabel


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--benchmark-frames="):
			_benchmark_target_frames = clampi(int(arg.split("=")[1]), 10, 600)
			_benchmark_start_usec = Time.get_ticks_usec()
	apply_graphics_profile(current_profile_id)


func apply_graphics_profile(profile_id: String) -> bool:
	var desc := BootstrapScript.build_boot_descriptor(profile_id)
	if not bool(desc.get("valid", false)):
		_boot_valid = false
		boot_descriptor = desc
		_update_hud()
		return false

	boot_descriptor = desc
	current_profile_id = String(desc["profile"]["profile_id"])
	var prof: Dictionary = desc["profile"]

	Engine.max_fps = int(prof["fps_cap"])
	var vp := get_viewport()
	if vp != null:
		vp.scaling_3d_scale = float(prof["render_scale"])
		vp.msaa_3d = int(prof["msaa_3d"]) as Viewport.MSAA

	if _sun_light != null:
		_sun_light.shadow_enabled = bool(prof["directional_shadows_enabled"])
		_sun_light.directional_shadow_mode = int(prof["directional_shadow_mode"]) as DirectionalLight3D.ShadowMode

	if _world_env != null and _world_env.environment != null:
		_world_env.environment.glow_enabled = bool(prof["glow_enabled"])
		_world_env.environment.fog_enabled = bool(prof["fog_enabled"])

	_boot_valid = true
	_update_hud()
	return true


func is_boot_valid() -> bool:
	return _boot_valid


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F1:
			apply_graphics_profile(GraphicsConfigScript.PROFILE_LOW)
		elif event.keycode == KEY_F2:
			apply_graphics_profile(GraphicsConfigScript.PROFILE_MEDIUM)
		elif event.keycode == KEY_F3:
			apply_graphics_profile(GraphicsConfigScript.PROFILE_HIGH)


func _process(_delta: float) -> void:
	_update_hud()
	if _benchmark_target_frames > 0:
		_benchmark_frames_seen += 1
		if _benchmark_frames_seen >= _benchmark_target_frames:
			var elapsed_ms := float(Time.get_ticks_usec() - _benchmark_start_usec) / 1000.0
			var avg_ms := elapsed_ms / float(_benchmark_frames_seen)
			var payload := get_runtime_metrics()
			payload["benchmark_frames"] = _benchmark_frames_seen
			payload["wall_elapsed_ms"] = snappedf(elapsed_ms, 0.01)
			payload["wall_avg_frame_ms"] = snappedf(avg_ms, 0.01)
			payload["wall_avg_fps"] = snappedf(1000.0 / avg_ms, 0.1) if avg_ms > 0.0 else 0.0
			payload["video_adapter"] = RenderingServer.get_video_adapter_name()
			payload["video_vendor"] = RenderingServer.get_video_adapter_vendor()
			print("ZIZ_BENCHMARK:" + JSON.stringify(payload))
			_benchmark_target_frames = 0
			get_tree().quit(0)


func get_runtime_metrics() -> Dictionary:
	var fps := float(Engine.get_frames_per_second())
	var frame_ms := (1000.0 / fps) if fps > 0.0 else 0.0
	var mem_mb := float(Performance.get_monitor(Performance.MEMORY_STATIC)) / (1024.0 * 1024.0)
	var active_nodes := int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))
	var orphan_nodes := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
	return {
		"profile_id": current_profile_id,
		"fps": snappedf(fps, 0.1),
		"frame_ms": snappedf(frame_ms, 0.01),
		"static_memory_mb": snappedf(mem_mb, 0.01),
		"active_nodes": active_nodes,
		"orphan_nodes": orphan_nodes,
		"rendering_method": String(ProjectSettings.get_setting("rendering/renderer/rendering_method", "")),
	}


func _update_hud() -> void:
	if _hud_label == null:
		return
	if not _boot_valid:
		_hud_label.text = "BOOT ERROR: Perfil grafico invalido"
		return
	var prof: Dictionary = boot_descriptor.get("profile", {})
	var m := get_runtime_metrics()
	_hud_label.text = (
		"%s (%s)\n" % [BootstrapScript.GAME_TITLE, BootstrapScript.STAGE_VERSION]
		+ "Renderizador: %s | Perfil: %s [F1 Baixo | F2 Medio | F3 Alto]\n" % [m["rendering_method"], String(prof.get("label", current_profile_id))]
		+ "FPS: %.1f (Meta cap: %d) | Frame: %.2f ms | Mem Estatica: %.2f MB" % [m["fps"], int(prof.get("fps_cap", 30)), m["frame_ms"], m["static_memory_mb"]]
	)
