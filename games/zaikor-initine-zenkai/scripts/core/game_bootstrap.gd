class_name ZizGameBootstrap
extends RefCounted
## Contrato puro de inicializacao e diagnostico do cliente Zaikor: Initine Zenkai.

const GraphicsConfigScript = preload("res://scripts/core/graphics_config.gd")

const PROJECT_ID := "zaikor-initine-zenkai"
const GAME_TITLE := "Zaikor: Initine Zenkai"
const STAGE_VERSION := "0.1.0-etapa1"
const REQUIRED_RENDERER := "gl_compatibility"


static func build_boot_descriptor(profile_id: String = GraphicsConfigScript.DEFAULT_PROFILE_ID) -> Dictionary:
	var profile := GraphicsConfigScript.get_profile(profile_id)
	var validation := GraphicsConfigScript.validate_profile(profile)
	if not bool(validation.get("valid", false)):
		return {
			"valid": false,
			"project_id": PROJECT_ID,
			"title": GAME_TITLE,
			"stage_version": STAGE_VERSION,
			"errors": validation.get("errors", []),
		}

	return {
		"valid": true,
		"project_id": PROJECT_ID,
		"title": GAME_TITLE,
		"stage_version": STAGE_VERSION,
		"renderer": REQUIRED_RENDERER,
		"profile": profile,
		"errors": [],
	}
