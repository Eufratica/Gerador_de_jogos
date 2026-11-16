class_name LocomotionCore
extends RefCounted
# PlayForge Modular System (locomotion) - logica 100% pura e offline

const SYSTEM_ID := "locomotion"
const CATEGORY := "movement"

static func describe() -> Dictionary:
	return {"system_id": SYSTEM_ID, "category": CATEGORY, "pure": true}
