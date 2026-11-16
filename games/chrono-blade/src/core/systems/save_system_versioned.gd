class_name SaveSystemVersionedCore
extends RefCounted
# PlayForge Modular System (save_system_versioned) - logica 100% pura e offline

const SYSTEM_ID := "save_system_versioned"
const CATEGORY := "persistence"

static func describe() -> Dictionary:
	return {"system_id": SYSTEM_ID, "category": CATEGORY, "pure": true}
