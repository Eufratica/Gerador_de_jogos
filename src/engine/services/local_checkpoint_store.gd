class_name LocalCheckpointStore
extends RefCounted
## Persistencia local fail-closed de checkpoints do Altar (Sprint 4B).
## Em Sprint 4C sera espelhada no Supabase via CloudSavePort com assinatura HMAC.

const DEFAULT_SAVE_PATH: String = "user://checkpoint_v1.json"


static func save_snapshot(snap: Dictionary, path: String = DEFAULT_SAVE_PATH) -> bool:
	if snap.is_empty() or not (snap.has("checkpoint") and snap.has("gold") and snap.has("levels")):
		return false
	var f: FileAccess = FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(snap))
	f.close()
	return true


static func load_snapshot(path: String = DEFAULT_SAVE_PATH) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var txt: String = FileAccess.get_file_as_string(path)
	if txt.strip_edges().is_empty():
		return {}
	var j := JSON.new()
	if j.parse(txt) != OK or not (j.data is Dictionary):
		return {}
	var data: Dictionary = j.data
	if not (data.has("schema_version") and data.has("checkpoint") and data.has("gold") and data.has("levels")):
		return {}
	return data


static func has_valid_save(path: String = DEFAULT_SAVE_PATH) -> bool:
	return not load_snapshot(path).is_empty()


static func clear_save(path: String = DEFAULT_SAVE_PATH) -> void:
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
