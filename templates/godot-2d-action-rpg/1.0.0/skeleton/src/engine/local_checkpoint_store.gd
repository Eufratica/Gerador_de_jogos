class_name LocalCheckpointStore
extends RefCounted
## Persistencia local fail-closed de checkpoints versionados (Template PlayForge).

const DEFAULT_SAVE_PATH: String = "user://checkpoint_v1.json"


static func save_snapshot(snap: Dictionary, path: String = DEFAULT_SAVE_PATH) -> bool:
	if snap.is_empty() or not (snap.has("schema_version") and snap.has("game_id") and snap.has("world_index")):
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
	var parser := JSON.new()
	if parser.parse(txt) != OK or not (parser.data is Dictionary):
		return {}
	var data: Dictionary = parser.data
	if not (data.has("schema_version") and data.has("game_id") and data.has("world_index")):
		return {}
	return data


static func clear_save(path: String = DEFAULT_SAVE_PATH) -> void:
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
