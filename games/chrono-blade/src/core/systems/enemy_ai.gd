class_name EnemyAiCore
extends RefCounted
# PlayForge Modular System (enemy_ai) - logica 100% pura e offline

const SYSTEM_ID := "enemy_ai"
const CATEGORY := "ai"

static func describe() -> Dictionary:
	return {"system_id": SYSTEM_ID, "category": CATEGORY, "pure": true}
