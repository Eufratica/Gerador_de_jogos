class_name CombatActionCore
extends RefCounted
# PlayForge Modular System (combat_action) - logica 100% pura e offline

const SYSTEM_ID := "combat_action"
const CATEGORY := "combat"

static func describe() -> Dictionary:
	return {"system_id": SYSTEM_ID, "category": CATEGORY, "pure": true}
