class_name TestZizGraphicsConfig
extends RefCounted
## Testes unitarios puros para perfis graficos e bootstrap de Zaikor: Initine Zenkai.

const GraphicsConfigScript = preload("res://scripts/core/graphics_config.gd")
const BootstrapScript = preload("res://scripts/core/game_bootstrap.gd")


func run(t: RefCounted) -> void:
	var ids: Array[String] = GraphicsConfigScript.list_profile_ids()
	t.assert_eq(ids.size(), 3, "Devem existir exatamente 3 perfis (low, medium, high)")

	var low := GraphicsConfigScript.get_profile("low")
	var low_val := GraphicsConfigScript.validate_profile(low)
	t.assert_true(bool(low_val.get("valid", false)), "Perfil low padrao deve ser valido")
	t.assert_eq(String(low.get("renderer", "")), "gl_compatibility", "Perfil low obrigatoriamente usa gl_compatibility")
	t.assert_eq(int(low.get("viewport_width", 0)), 1280, "Resolucao largura padrao 1280")
	t.assert_eq(int(low.get("viewport_height", 0)), 720, "Resolucao altura padrao 720")
	t.assert_eq(int(low.get("fps_cap", 0)), 30, "Meta inicial de FPS no perfil Baixo = 30")
	t.assert_false(bool(low.get("experimental", true)), "Perfil Baixo nao e experimental")

	var high := GraphicsConfigScript.get_profile("high")
	t.assert_true(bool(GraphicsConfigScript.validate_profile(high).get("valid", false)), "Perfil high deve validar sob Compatibility")
	t.assert_true(bool(high.get("experimental", false)), "Perfil Alto deve ser marcado como experimental")

	# Fail-closed contra recursos pesados vedados (Secao 7.2) e renderizadores nao autorizados
	var bad_renderer := low.duplicate()
	bad_renderer["renderer"] = "forward_plus"
	t.assert_false(bool(GraphicsConfigScript.validate_profile(bad_renderer).get("valid", true)), "Deve rejeitar forward_plus por fail-closed")

	var bad_lumen := low.duplicate()
	bad_lumen["lumen"] = true
	t.assert_false(bool(GraphicsConfigScript.validate_profile(bad_lumen).get("valid", true)), "Deve bloquear Lumen por padrao")

	var bad_res := low.duplicate()
	bad_res["viewport_width"] = 320
	t.assert_false(bool(GraphicsConfigScript.validate_profile(bad_res).get("valid", true)), "Deve bloquear resolucao invalida")

	var bad_boot := BootstrapScript.build_boot_descriptor("inexistente")
	t.assert_false(bool(bad_boot.get("valid", true)), "Bootstrap deve falhar fechado para perfil desconhecido")

	var ok_boot := BootstrapScript.build_boot_descriptor("low")
	t.assert_true(bool(ok_boot.get("valid", false)), "Bootstrap low deve aprovar")
	t.assert_eq(String(ok_boot.get("project_id", "")), "zaikor-initine-zenkai", "project_id consistente no bootstrap")
	t.assert_eq(String(ok_boot.get("renderer", "")), "gl_compatibility", "renderer consistente no bootstrap")
