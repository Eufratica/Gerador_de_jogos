class_name ZizGraphicsConfig
extends RefCounted
## Configuracao pura e deterministica dos perfis graficos (Secao 7.1-7.5).
## Zero dependencias de Node, SceneTree, arquivos ou rede.

const PROFILE_LOW := "low"
const PROFILE_MEDIUM := "medium"
const PROFILE_HIGH := "high"

const ALLOWED_RENDERER := "gl_compatibility"
const FORBIDDEN_DEFAULT_FEATURES: Array[String] = [
	"ray_tracing",
	"lumen",
	"nanite",
	"virtual_shadow_maps",
	"heavy_volumetrics",
]

const REFERENCE_WIDTH := 1280
const REFERENCE_HEIGHT := 720
const DEFAULT_PROFILE_ID := PROFILE_LOW


static func list_profile_ids() -> Array[String]:
	return [PROFILE_LOW, PROFILE_MEDIUM, PROFILE_HIGH]


static func get_profile(profile_id: String = DEFAULT_PROFILE_ID) -> Dictionary:
	var key := profile_id.strip_edges().to_lower()
	match key:
		PROFILE_LOW:
			return {
				"profile_id": PROFILE_LOW,
				"label": "Baixo (Referencia Iris Xe)",
				"experimental": false,
				"renderer": ALLOWED_RENDERER,
				"viewport_width": REFERENCE_WIDTH,
				"viewport_height": REFERENCE_HEIGHT,
				"fps_cap": 30,
				"render_scale": 1.0,
				"shadow_atlas_size": 1024,
				"directional_shadows_enabled": true,
				"directional_shadow_mode": 0,
				"msaa_3d": 0,
				"glow_enabled": false,
				"fog_enabled": false,
				"lod_bias": 0.5,
			}
		PROFILE_MEDIUM:
			return {
				"profile_id": PROFILE_MEDIUM,
				"label": "Medio",
				"experimental": false,
				"renderer": ALLOWED_RENDERER,
				"viewport_width": REFERENCE_WIDTH,
				"viewport_height": REFERENCE_HEIGHT,
				"fps_cap": 30,
				"render_scale": 1.0,
				"shadow_atlas_size": 2048,
				"directional_shadows_enabled": true,
				"directional_shadow_mode": 1,
				"msaa_3d": 0,
				"glow_enabled": false,
				"fog_enabled": true,
				"lod_bias": 1.0,
			}
		PROFILE_HIGH:
			return {
				"profile_id": PROFILE_HIGH,
				"label": "Alto (Experimental - Sujeito a Benchmark)",
				"experimental": true,
				"renderer": ALLOWED_RENDERER,
				"viewport_width": REFERENCE_WIDTH,
				"viewport_height": REFERENCE_HEIGHT,
				"fps_cap": 60,
				"render_scale": 1.0,
				"shadow_atlas_size": 2048,
				"directional_shadows_enabled": true,
				"directional_shadow_mode": 2,
				"msaa_3d": 1,
				"glow_enabled": true,
				"fog_enabled": true,
				"lod_bias": 1.5,
			}
		_:
			return {}


static func validate_profile(profile: Dictionary) -> Dictionary:
	var errors: Array[String] = []
	if profile.is_empty():
		errors.append("Perfil grafico vazio ou desconhecido.")
		return {"valid": false, "errors": errors}

	var renderer := String(profile.get("renderer", ""))
	if renderer != ALLOWED_RENDERER:
		errors.append("Renderizador invalido '%s'; obrigatorio '%s'." % [renderer, ALLOWED_RENDERER])

	var w := int(profile.get("viewport_width", 0))
	var h := int(profile.get("viewport_height", 0))
	if w < 640 or h < 360:
		errors.append("Resolucao abaixo do minimo permitido (%dx%d)." % [w, h])

	var fps_cap := int(profile.get("fps_cap", 0))
	if fps_cap < 15 or fps_cap > 120:
		errors.append("fps_cap fora da faixa segura (15..120): %d." % fps_cap)

	var scale := float(profile.get("render_scale", 0.0))
	if scale < 0.5 or scale > 1.0:
		errors.append("render_scale deve permanecer entre 0.5 e 1.0 (encontrado %.2f)." % scale)

	for forbidden in FORBIDDEN_DEFAULT_FEATURES:
		if bool(profile.get(forbidden, false)):
			errors.append("Recurso pesado proibido por padrao habilitado: '%s'." % forbidden)

	return {"valid": errors.is_empty(), "errors": errors}
