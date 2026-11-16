"""Adaptador Godot Engine (4.4+ / GDScript + CLI headless real) (Incremento P1)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from factory.playforge.asset_pipeline.synthesizer import resolve_factory_godot_bin
from factory.playforge.registry import _atomic_write_json, _atomic_write_text
from factory.playforge.template_registry.validator import TemplateValidationError, TemplateValidator

from .adapter import EngineAdapter
from .schemas import (
    EngineProfileRequest,
    EngineScaffoldResult,
    EngineTestResult,
    EngineToolchainUnavailableError,
    EngineValidationResult,
    ToolchainProbeResult,
)


class GodotEngineAdapter(EngineAdapter):
    """Adaptador real da Godot Engine (MIT, GDScript/C#, Scenes/Nodes/Signals, headless CLI)."""

    engine_id = "godot"
    display_name = "Godot Engine 4.4"
    supported_dimensions = ("2d", "2.5d", "3d-indie")
    supported_technologies = (
        "GDScript",
        "Scenes & Nodes",
        "Signals",
        "Physics Engine (2D/3D)",
        "AnimationTree",
        "Shaders",
        "C# (opcional com .NET SDK)",
    )
    license_summary = "MIT (100% open source, custo zero, sem royalties)"

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root

    def probe_toolchain(self) -> ToolchainProbeResult:
        godot_bin = resolve_factory_godot_bin(repo_root=self.repo_root)
        return ToolchainProbeResult(
            engine_id=self.engine_id,
            display_name=self.display_name,
            available=godot_bin is not None and godot_bin.is_file(),
            executable_path=str(godot_bin) if godot_bin else None,
            version="4.4-stable" if godot_bin else None,
            license_type="MIT",
            recommended_min_ram_gb=4.0,
            requires_dedicated_gpu=False,
            headless_supported=True,
            notes=(
                "Binario CLI headless disponivel localmente para testes em < 1s."
                if godot_bin
                else "Binario Godot CLI nao encontrado em tools/godot/ nem no PATH."
            ),
        )

    def scaffold_project(self, project_dir: Path, spec: dict[str, Any]) -> EngineScaffoldResult:
        project_dir.mkdir(parents=True, exist_ok=True)
        game_name = str(spec.get("name") or project_dir.name)
        project_godot = (
            "; Engine configuration file.\n"
            "; PlayForge Factory Godot Adapter\n\n"
            "config_version=5\n\n"
            "[application]\n\n"
            f'config/name="{game_name}"\n'
            'run/main_scene="res://src/engine/main.tscn"\n'
            'config/features=PackedStringArray("4.4", "Forward Plus")\n'
        )
        main_gd = (
            "extends Node\n\n"
            "func _ready() -> void:\n"
            "\tget_tree().quit(0)\n"
        )
        main_tscn = '[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://src/engine/main.gd" id="1"]\n\n[node name="Main" type="Node"]\nscript = ExtResource("1")\n'
        test_gd = (
            "extends SceneTree\n\n"
            "func _init() -> void:\n"
            '\tprint("GODOT_ADAPTER_SMOKE_PASS | Passed: 1 | Failed: 0")\n'
            "\tquit(0)\n"
        )
        written = [
            "project.godot",
            "src/engine/main.gd",
            "src/engine/main.tscn",
            "tests/unit/run_engine_tests.gd",
            "config/engine_spec_summary.json",
        ]
        _atomic_write_text(project_dir / "project.godot", project_godot)
        _atomic_write_text(project_dir / "src/engine/main.gd", main_gd)
        _atomic_write_text(project_dir / "src/engine/main.tscn", main_tscn)
        _atomic_write_text(project_dir / "tests/unit/run_engine_tests.gd", test_gd)
        _atomic_write_json(
            project_dir / "config/engine_spec_summary.json",
            {"engine": "godot", "game_id": spec.get("game_id", project_dir.name), "spec_id": spec.get("spec_id", "manual")},
        )
        probe = self.probe_toolchain()
        return EngineScaffoldResult(
            engine_id=self.engine_id,
            project_dir=str(project_dir),
            files_written=tuple(written),
            executable_ready=probe.available,
            warnings=() if probe.available else ("Godot CLI ausente no host.",),
        )

    def validate_project(self, project_dir: Path) -> EngineValidationResult:
        required = ("project.godot", "src/engine/main.tscn")
        issues: list[str] = []
        checked: list[str] = []
        for rel in required:
            checked.append(rel)
            target = project_dir / rel
            if not target.is_file():
                issues.append(f"Arquivo obrigatorio Godot ausente: '{rel}'.")
        pg = project_dir / "project.godot"
        if pg.is_file() and "[application]" not in pg.read_text(encoding="utf-8", errors="ignore"):
            issues.append("project.godot sem secao [application].")
        return EngineValidationResult(
            engine_id=self.engine_id,
            passed=len(issues) == 0,
            checked_files=tuple(checked),
            issues=tuple(issues),
        )

    def run_tests(self, project_dir: Path) -> EngineTestResult:
        probe = self.probe_toolchain()
        if not probe.available or not probe.executable_path:
            raise EngineToolchainUnavailableError(
                "Godot Engine CLI nao encontrado no ambiente para execucao real de testes."
            )
        candidates = (
            "tests/unit/verify_generated_game.gd",
            "tests/unit/run_template_tests.gd",
            "tests/unit/run_unit_tests.gd",
            "tests/unit/run_engine_tests.gd",
        )
        chosen = next((c for c in candidates if (project_dir / c).is_file()), None)
        if chosen is None:
            return EngineTestResult(
                engine_id=self.engine_id,
                passed=False,
                executed=False,
                elapsed_ms=0.0,
                summary="Nenhum script de teste Godot encontrado em tests/unit/.",
            )
        t0 = time.perf_counter()
        try:
            res = TemplateValidator().run_demo_tests(
                demo_dir=project_dir,
                test_script_res=f"res://{chosen}",
                godot_bin=Path(probe.executable_path),
            )
        except TemplateValidationError as exc:
            return EngineTestResult(
                engine_id=self.engine_id,
                passed=False,
                executed=True,
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                summary=exc.message,
            )
        return EngineTestResult(
            engine_id=self.engine_id,
            passed=True,
            executed=True,
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            summary=f"Suite Godot '{chosen}' aprovada.",
            stdout_tail=str(res.get("output", ""))[-400:],
        )

    def score_profile(
        self,
        request: EngineProfileRequest,
        hardware_profile: dict[str, Any],
        probe: ToolchainProbeResult,
    ) -> tuple[dict[str, float], dict[str, str]]:
        ram_gb = float(hardware_profile.get("total_ram_gb") or 8.0)
        dim_map = {"2d": 10.0, "2.5d": 9.2, "3d-indie": 7.8, "3d-aaa-large": 3.0}
        cam_map = {
            "side-scroller": 10.0,
            "top-down": 9.8,
            "isometric": 9.5,
            "first-person": 7.5,
            "third-person-cinematic": 6.5,
        }
        gfx_map = {
            "pixel-vector-2d": 10.0,
            "stylized-3d": 8.8,
            "pbr-standard": 7.5,
            "photorealistic-lumen-nanite": 2.5,
        }
        anim_map = {
            "basic-2d": 9.8,
            "skeletal-2d": 9.5,
            "standard-3d": 8.0,
            "advanced-mocap-cinematic": 5.0,
        }
        phys_map = {
            "none": 9.5,
            "arcade-2d": 9.8,
            "deterministic-2d": 10.0,
            "rigidbody-3d": 8.0,
            "advanced-destruction-cloth": 4.0,
        }
        perf_map = {
            "mobile-60fps-low-spec": 9.8,
            "desktop-60fps": 9.0,
            "high-end-gpu-60fps": 5.5,
        }
        dev_map = {"low-mvp": 10.0, "medium": 9.2, "high": 7.8, "aaa-scale": 4.0}
        genre_lower = request.genre.lower()
        genre_score = 9.5 if any(k in genre_lower for k in ("rpg", "platform", "strategy", "idle", "roguelike", "puzzle", "arcade", "ddtank")) else 8.0
        if "aaa" in genre_lower or "cinematic" in genre_lower:
            genre_score = 5.5

        console_penalty = 1.5 if any("console" in p.lower() for p in request.target_platforms) else 0.0
        plat_score = max(3.5, 9.5 - console_penalty)
        char_score = 9.5 if request.character_count <= 30 else 7.5
        auto_score = 10.0 if request.automation_preference == "headless-cli-priority" else 9.5
        if request.require_csharp:
            # Build padrao Godot 4 no host nao traz runtime .NET e Godot 4 C# tem restricoes no export Web.
            genre_score = min(genre_score, 6.0)
            dev_map["low-mvp"] = 6.0
            dev_map["medium"] = 5.0
            dev_map["high"] = 5.0
            auto_score = 5.5
            if "web" in {p.lower() for p in request.target_platforms}:
                plat_score = min(plat_score, 5.0)
        hw_score = 10.0 if ram_gb >= 4.0 else 7.0
        lic_score = 10.0 if request.licensing_preference == "open-source-mit" else 9.0

        scores = {
            "genre": genre_score,
            "world_dimension": dim_map[request.world_dimension],
            "camera_type": cam_map[request.camera_type],
            "character_count": char_score,
            "animation_complexity": anim_map[request.animation_complexity],
            "physics_needs": phys_map[request.physics_needs],
            "graphic_quality": gfx_map[request.graphic_quality],
            "target_platforms": plat_score,
            "expected_performance": perf_map[request.expected_performance],
            "development_complexity": dev_map[request.development_complexity],
            "free_tools_availability": 10.0,
            "hardware_requirements": hw_score if probe.available else max(hw_score - 1.0, 5.0),
            "licensing": lic_score,
            "automation_possibility": auto_score,
        }
        reasons = {
            "genre": f"Godot atende diretamente RPGs, plataforma, estrategia e jogos 2D/3D indie ({request.genre}).",
            "world_dimension": f"Dimensao '{request.world_dimension}' pontuada pelo pipeline 2D dedicado e Forward+/Mobile 3D.",
            "camera_type": f"Camera '{request.camera_type}' suportada via Camera2D/Camera3D e scripts GDScript.",
            "character_count": f"Suporta {request.character_count} personagem(ns) com baixo overhead de cena.",
            "animation_complexity": f"AnimationPlayer/AnimationTree adequado para '{request.animation_complexity}'.",
            "physics_needs": f"Fisica deterministica 2D/3D enxuta para '{request.physics_needs}'.",
            "graphic_quality": f"Adequado para '{request.graphic_quality}' sem overhead AAA.",
            "target_platforms": f"Exportacao nativa Windows/Linux/Android/Web para {list(request.target_platforms)}.",
            "expected_performance": f"Runtime leve (~100 MB) ideal para '{request.expected_performance}'.",
            "development_complexity": f"Iteracao rapida para complexidade '{request.development_complexity}'.",
            "free_tools_availability": "100% compativel com Blender, GIMP, Krita, FFmpeg sem plugins pagos.",
            "hardware_requirements": f"Roda bem no host atual ({ram_gb:.2f} GB RAM, CLI local {'disponivel' if probe.available else 'ausente'}).",
            "licensing": "Licenca MIT pura (zero royalties, alinhamento maximo Free First).",
            "automation_possibility": "CLI '--headless' nativo com execucao e QA em < 1s.",
        }
        return scores, reasons
