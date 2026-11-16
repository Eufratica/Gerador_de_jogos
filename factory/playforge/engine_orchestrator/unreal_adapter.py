"""Adaptador estrutural Unreal Engine 5 com checagem rigorosa de host e GPU (P1)."""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from factory.playforge.registry import _atomic_write_json, _atomic_write_text

from .adapter import EngineAdapter
from .schemas import (
    EngineProfileRequest,
    EngineScaffoldResult,
    EngineTestResult,
    EngineToolchainUnavailableError,
    EngineValidationResult,
    ToolchainProbeResult,
)


def _find_unreal_executable() -> tuple[str | None, str | None]:
    which_ue = shutil.which("UnrealEditor-Cmd") or shutil.which("UE4Editor-Cmd")
    if which_ue:
        return which_ue, "detected-in-path"
    patterns = (
        "C:/Program Files/Epic Games/UE_5.*/Engine/Binaries/Win64/UnrealEditor-Cmd.exe",
        "C:/Program Files/Epic Games/UE_5.*/Engine/Binaries/Linux/UnrealEditor-Cmd",
        "/opt/unreal*/Engine/Binaries/Linux/UnrealEditor-Cmd",
    )
    for pat in patterns:
        matches = sorted(glob.glob(pat), reverse=True)
        for cand in matches:
            if os.path.isfile(cand):
                ver = next((part for part in Path(cand).parts if part.startswith("UE_")), "5.x")
                return cand, ver
    return None, None


class UnrealEngineAdapter(EngineAdapter):
    """Adaptador Unreal Engine 5 (C++, Blueprints, Niagara, Lumen, Nanite)."""

    engine_id = "unreal"
    display_name = "Unreal Engine 5"
    supported_dimensions = ("3d-indie", "3d-aaa-large")
    supported_technologies = (
        "C++",
        "Blueprints",
        "Gameplay Framework",
        "Enhanced Input",
        "Animation Blueprints",
        "Niagara",
        "Lumen",
        "Nanite",
    )
    license_summary = "EULA Epic ($0 ate US$ 1M; 5% royalty > US$ 1M em jogos; nao open source)"

    def probe_toolchain(self) -> ToolchainProbeResult:
        exe, ver = _find_unreal_executable()
        return ToolchainProbeResult(
            engine_id=self.engine_id,
            display_name=self.display_name,
            available=exe is not None,
            executable_path=exe,
            version=ver,
            license_type="Proprietary-Epic-EULA-5pct-Royalty-Above-1M",
            recommended_min_ram_gb=32.0,
            requires_dedicated_gpu=True,
            headless_supported=True,
            notes=(
                f"UnrealEditor-Cmd detectado em {exe}."
                if exe
                else "Unreal Engine 5 nao instalada no host (recomendado Epic: 32 GB RAM + GPU DX12 >= 8 GB VRAM)."
            ),
        )

    def scaffold_project(self, project_dir: Path, spec: dict[str, Any]) -> EngineScaffoldResult:
        project_dir.mkdir(parents=True, exist_ok=True)
        raw_slug = str(spec.get("game_id") or project_dir.name)
        module_name = re.sub(r"[^A-Za-z0-9]", "", raw_slug.title()) or "PlayForgeGame"
        uproject_rel = f"{module_name}.uproject"

        uproject = {
            "FileVersion": 3,
            "EngineAssociation": "5.4",
            "Category": "",
            "Description": str(spec.get("value_proposition") or "Projeto gerado pela PlayForge Factory."),
            "Modules": [
                {
                    "Name": module_name,
                    "Type": "Runtime",
                    "LoadingPhase": "Default",
                }
            ],
            "Plugins": [
                {"Name": "EnhancedInput", "Enabled": True},
                {"Name": "Niagara", "Enabled": True},
            ],
        }
        default_engine_ini = (
            "[/Script/EngineSettings.GameMapsSettings]\n"
            f"GameDefaultMap=/Game/Maps/MainMap\n"
            "[/Script/Engine.RendererSettings]\n"
            "r.DynamicGlobalIlluminationMethod=0\n"
            "r.Lumen.HardwareRayTracing=False\n"
        )
        build_cs = (
            "using UnrealBuildTool;\n\n"
            f"public class {module_name} : ModuleRules\n{{\n"
            f"    public {module_name}(ReadOnlyTargetRules Target) : base(Target)\n    {{\n"
            "        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;\n"
            '        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput" });\n'
            "    }\n}\n"
        )
        written = (
            uproject_rel,
            "Config/DefaultEngine.ini",
            f"Source/{module_name}/{module_name}.Build.cs",
            "Content/.gitkeep",
        )
        _atomic_write_json(project_dir / uproject_rel, uproject)
        _atomic_write_text(project_dir / "Config/DefaultEngine.ini", default_engine_ini)
        _atomic_write_text(project_dir / f"Source/{module_name}/{module_name}.Build.cs", build_cs)
        _atomic_write_text(project_dir / "Content/.gitkeep", "")
        probe = self.probe_toolchain()
        warnings = () if probe.available else (
            "Unreal Engine 5 ausente no host; compilacao C++/AutomationTests bloqueada fail-closed.",
        )
        return EngineScaffoldResult(
            engine_id=self.engine_id,
            project_dir=str(project_dir),
            files_written=written,
            executable_ready=probe.available,
            warnings=warnings,
        )

    def validate_project(self, project_dir: Path) -> EngineValidationResult:
        uprojects = list(project_dir.glob("*.uproject"))
        checked = ["Config/DefaultEngine.ini"]
        issues: list[str] = []
        if not uprojects:
            issues.append("Arquivo *.uproject obrigatorio ausente.")
        else:
            checked.insert(0, uprojects[0].name)
            try:
                parsed = json.loads(uprojects[0].read_text(encoding="utf-8"))
                if parsed.get("FileVersion") != 3 or not parsed.get("Modules"):
                    issues.append("*.uproject sem FileVersion=3 ou Modules validos.")
            except json.JSONDecodeError as exc:
                issues.append(f"*.uproject invalido: {exc}")
        if not (project_dir / "Config/DefaultEngine.ini").is_file():
            issues.append("Config/DefaultEngine.ini ausente.")
        if not list(project_dir.glob("Source/*/*.Build.cs")):
            issues.append("Modulo C++ *.Build.cs ausente em Source/.")
        return EngineValidationResult(
            engine_id=self.engine_id,
            passed=len(issues) == 0,
            checked_files=tuple(checked),
            issues=tuple(issues),
        )

    def run_tests(self, project_dir: Path) -> EngineTestResult:
        probe = self.probe_toolchain()
        if not probe.available:
            raise EngineToolchainUnavailableError(
                "Unreal Engine 5 / UnrealEditor-Cmd nao encontrado no host; "
                "impossivel compilar C++ ou executar Unreal Automation Tests."
            )
        return EngineTestResult(
            engine_id=self.engine_id,
            passed=False,
            executed=False,
            elapsed_ms=0.0,
            summary="Unreal detectado, mas projeto requer UnrealBuildTool + Visual Studio antes de NullRHI Automation.",
        )

    def score_profile(
        self,
        request: EngineProfileRequest,
        hardware_profile: dict[str, Any],
        probe: ToolchainProbeResult,
    ) -> tuple[dict[str, float], dict[str, str]]:
        ram_gb = float(hardware_profile.get("total_ram_gb") or 8.0)
        has_gpu = bool(hardware_profile.get("has_dedicated_gpu", False))

        dim_map = {"2d": 2.0, "2.5d": 5.5, "3d-indie": 8.4, "3d-aaa-large": 10.0}
        cam_map = {
            "side-scroller": 4.5,
            "top-down": 6.0,
            "isometric": 7.0,
            "first-person": 9.8,
            "third-person-cinematic": 10.0,
        }
        gfx_map = {
            "pixel-vector-2d": 2.0,
            "stylized-3d": 8.5,
            "pbr-standard": 9.6,
            "photorealistic-lumen-nanite": 10.0,
        }
        anim_map = {
            "basic-2d": 2.0,
            "skeletal-2d": 3.0,
            "standard-3d": 9.2,
            "advanced-mocap-cinematic": 10.0,
        }
        phys_map = {
            "none": 6.0,
            "arcade-2d": 3.5,
            "deterministic-2d": 2.5,
            "rigidbody-3d": 9.5,
            "advanced-destruction-cloth": 10.0,
        }
        perf_map = {
            "mobile-60fps-low-spec": 3.0,
            "desktop-60fps": 8.0,
            "high-end-gpu-60fps": 10.0,
        }
        dev_map = {"low-mvp": 2.5, "medium": 6.0, "high": 9.2, "aaa-scale": 10.0}
        genre_lower = request.genre.lower()
        genre_score = 9.5 if any(k in genre_lower for k in ("3d", "adventure", "shooter", "open-world", "action")) else 6.0
        plat_score = 6.5 if ("web" in request.target_platforms or request.expected_performance == "mobile-60fps-low-spec") else 9.2

        # Hardware real da maquina atual (11.74 GB / Iris Xe) penaliza fortemente UE5 localmente
        hw_score = 9.5 if (ram_gb >= 24.0 and has_gpu and probe.available) else (4.0 if ram_gb >= 16.0 and has_gpu else 1.5)
        lic_score = 3.5 if request.licensing_preference == "open-source-mit" else 8.2
        auto_score = 5.5 if probe.available else 2.5

        scores = {
            "genre": genre_score,
            "world_dimension": dim_map[request.world_dimension],
            "camera_type": cam_map[request.camera_type],
            "character_count": 9.5 if request.character_count > 10 else 8.0,
            "animation_complexity": anim_map[request.animation_complexity],
            "physics_needs": phys_map[request.physics_needs],
            "graphic_quality": gfx_map[request.graphic_quality],
            "target_platforms": plat_score,
            "expected_performance": perf_map[request.expected_performance],
            "development_complexity": dev_map[request.development_complexity],
            "free_tools_availability": 8.0,
            "hardware_requirements": hw_score,
            "licensing": lic_score,
            "automation_possibility": auto_score,
        }
        reasons = {
            "genre": f"Unreal destaca-se em acao 3D terceira pessoa, combate cinematografico e mundos extensos ({request.genre}).",
            "world_dimension": f"Dimensao '{request.world_dimension}' ({'ideal para mundo 3D grande' if '3d' in request.world_dimension else 'subutilizada/pesada para 2D'}).",
            "camera_type": f"Gameplay Framework + SpringArm nativo para '{request.camera_type}'.",
            "character_count": f"Animation Blueprints e Niagara escalam bem para {request.character_count} personagem(ns).",
            "animation_complexity": f"Control Rig, IK e Motion Matching nativos para '{request.animation_complexity}'.",
            "physics_needs": f"Chaos Physics / Cloth nativo para '{request.physics_needs}'.",
            "graphic_quality": f"Lumen e Nanite lideram em '{request.graphic_quality}'.",
            "target_platforms": f"Forte em PC/Consoles; pesado para Web/Mobile low-spec ({list(request.target_platforms)}).",
            "expected_performance": f"Otimizado para hardware dedicado ({request.expected_performance}).",
            "development_complexity": f"Compilacao C++/shaders mais pesada em projetos simples ('{request.development_complexity}').",
            "free_tools_availability": "Ferramentas nativas integradas (Niagara/Sequencer/MetaSounds) gratis no editor.",
            "hardware_requirements": (
                f"Host atual: {ram_gb:.2f} GB RAM, GPU dedicada={has_gpu}, UE5 instalada={probe.available} "
                "(Epic recomenda 32 GB RAM + GPU DX12 >= 8 GB VRAM)."
            ),
            "licensing": "$0 inicial ate US$ 1M; 5% royalty > US$ 1M e EULA proprietario (nao open source).",
            "automation_possibility": "Automation Tests exigem compilacao C++ e UE5 instalada localmente.",
        }
        return scores, reasons
