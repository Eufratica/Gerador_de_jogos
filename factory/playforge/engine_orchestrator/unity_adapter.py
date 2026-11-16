"""Adaptador estrutural Unity Engine com deteccao real de host e bloqueio fail-closed (P1)."""
from __future__ import annotations

import glob
import json
import os
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


def _find_unity_executable() -> tuple[str | None, str | None]:
    which_unity = shutil.which("Unity") or shutil.which("unity-editor")
    if which_unity:
        return which_unity, "detected-in-path"
    patterns = (
        "C:/Program Files/Unity/Hub/Editor/*/Editor/Unity.exe",
        "C:/Program Files/Unity/Editor/Unity.exe",
        "/opt/unity/Editor/Unity",
        str(Path.home() / "Unity/Hub/Editor/*/Editor/Unity"),
    )
    for pat in patterns:
        matches = sorted(glob.glob(pat), reverse=True)
        for cand in matches:
            if os.path.isfile(cand):
                ver = Path(cand).parts[-3] if "Hub" in cand else "detected"
                return cand, ver
    return None, None


class UnityEngineAdapter(EngineAdapter):
    """Adaptador Unity (C#, GameObjects/Prefabs, URP/HDRP, multiplataforma)."""

    engine_id = "unity"
    display_name = "Unity Engine"
    supported_dimensions = ("2d", "2.5d", "3d-indie", "3d-aaa-large")
    supported_technologies = (
        "C#",
        "GameObjects & Components",
        "Prefabs",
        "Animator",
        "Unity Physics",
        "URP",
        "HDRP",
    )
    license_summary = "Proprietaria (Unity Personal gratuita ate limite vigente; exige Unity Hub + conta)"

    def probe_toolchain(self) -> ToolchainProbeResult:
        exe, ver = _find_unity_executable()
        return ToolchainProbeResult(
            engine_id=self.engine_id,
            display_name=self.display_name,
            available=exe is not None,
            executable_path=exe,
            version=ver,
            license_type="Proprietary-Personal-Free-Tier",
            recommended_min_ram_gb=8.0,
            requires_dedicated_gpu=False,
            headless_supported=True,
            notes=(
                f"Editor Unity detectado em {exe}."
                if exe
                else "Unity Editor/Hub nao instalado no host; scaffold estrutural habilitado e build/teste bloqueados."
            ),
        )

    def scaffold_project(self, project_dir: Path, spec: dict[str, Any]) -> EngineScaffoldResult:
        project_dir.mkdir(parents=True, exist_ok=True)
        game_name = str(spec.get("name") or project_dir.name)
        packages = {
            "dependencies": {
                "com.unity.render-pipelines.universal": "14.0.11",
                "com.unity.textmeshpro": "3.0.9",
                "com.unity.inputsystem": "1.7.0",
            }
        }
        core_cs = (
            "// PlayForge Factory Unity Core Configuration (puro C# sem MonoBehaviour)\n"
            "namespace PlayForge.Core\n{\n"
            "    public sealed class GameSpecConfig\n    {\n"
            f'        public string GameName => "{game_name}";\n'
            f'        public string SpecId => "{spec.get("spec_id", "manual")}";\n'
            "    }\n}\n"
        )
        bootstrap_cs = (
            "using UnityEngine;\n"
            "using PlayForge.Core;\n\n"
            "namespace PlayForge.Engine\n{\n"
            "    public sealed class GameBootstrap : MonoBehaviour\n    {\n"
            "        private void Awake()\n        {\n"
            "            var cfg = new GameSpecConfig();\n"
            "            Debug.Log(cfg.GameName);\n"
            "        }\n    }\n}\n"
        )
        written = (
            "ProjectSettings/ProjectVersion.txt",
            "Packages/manifest.json",
            "Assets/Scripts/Core/GameSpecConfig.cs",
            "Assets/Scripts/Engine/GameBootstrap.cs",
            "Assets/Scenes/.gitkeep",
        )
        _atomic_write_text(project_dir / "ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 2022.3.45f1\n")
        _atomic_write_json(project_dir / "Packages/manifest.json", packages)
        _atomic_write_text(project_dir / "Assets/Scripts/Core/GameSpecConfig.cs", core_cs)
        _atomic_write_text(project_dir / "Assets/Scripts/Engine/GameBootstrap.cs", bootstrap_cs)
        _atomic_write_text(project_dir / "Assets/Scenes/.gitkeep", "")
        probe = self.probe_toolchain()
        warnings = () if probe.available else ("Unity Editor ausente no host; compilacao/testes bloqueados ate instalacao.",)
        return EngineScaffoldResult(
            engine_id=self.engine_id,
            project_dir=str(project_dir),
            files_written=written,
            executable_ready=probe.available,
            warnings=warnings,
        )

    def validate_project(self, project_dir: Path) -> EngineValidationResult:
        required = (
            "ProjectSettings/ProjectVersion.txt",
            "Packages/manifest.json",
            "Assets/Scripts/Core/GameSpecConfig.cs",
        )
        issues: list[str] = []
        for rel in required:
            if not (project_dir / rel).is_file():
                issues.append(f"Arquivo obrigatorio Unity ausente: '{rel}'.")
        manifest_path = project_dir / "Packages/manifest.json"
        if manifest_path.is_file():
            try:
                parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
                if "dependencies" not in parsed:
                    issues.append("Packages/manifest.json sem chave 'dependencies'.")
            except json.JSONDecodeError as exc:
                issues.append(f"Packages/manifest.json invalido: {exc}")
        return EngineValidationResult(
            engine_id=self.engine_id,
            passed=len(issues) == 0,
            checked_files=required,
            issues=tuple(issues),
        )

    def run_tests(self, project_dir: Path) -> EngineTestResult:
        probe = self.probe_toolchain()
        if not probe.available:
            raise EngineToolchainUnavailableError(
                "Unity Editor nao detectado no host; impossivel executar Unity Test Runner sem simulacao falsa."
            )
        return EngineTestResult(
            engine_id=self.engine_id,
            passed=False,
            executed=False,
            elapsed_ms=0.0,
            summary="Unity detectado, porem execucao automatizada em batchmode requer projeto importado em -runTests.",
        )

    def score_profile(
        self,
        request: EngineProfileRequest,
        hardware_profile: dict[str, Any],
        probe: ToolchainProbeResult,
    ) -> tuple[dict[str, float], dict[str, str]]:
        ram_gb = float(hardware_profile.get("total_ram_gb") or 8.0)
        has_gpu = bool(hardware_profile.get("has_dedicated_gpu", False))
        dim_map = {"2d": 8.5, "2.5d": 9.2, "3d-indie": 9.4, "3d-aaa-large": 7.5}
        cam_map = {
            "side-scroller": 8.5,
            "top-down": 9.0,
            "isometric": 9.2,
            "first-person": 9.0,
            "third-person-cinematic": 8.5,
        }
        gfx_map = {
            "pixel-vector-2d": 8.2,
            "stylized-3d": 9.5,
            "pbr-standard": 9.3,
            "photorealistic-lumen-nanite": 6.5,
        }
        anim_map = {
            "basic-2d": 8.0,
            "skeletal-2d": 8.8,
            "standard-3d": 9.2,
            "advanced-mocap-cinematic": 8.0,
        }
        phys_map = {
            "none": 8.0,
            "arcade-2d": 8.5,
            "deterministic-2d": 7.5,
            "rigidbody-3d": 9.3,
            "advanced-destruction-cloth": 7.5,
        }
        perf_map = {
            "mobile-60fps-low-spec": 7.8,
            "desktop-60fps": 8.8,
            "high-end-gpu-60fps": 8.0,
        }
        dev_map = {"low-mvp": 7.2, "medium": 9.3, "high": 9.0, "aaa-scale": 7.0}
        if request.require_csharp:
            dev_map["medium"] = 10.0

        genre_score = 9.8 if request.require_csharp else 8.8
        if request.require_csharp:
            for key in dev_map:
                dev_map[key] = 10.0
        hw_score = 8.2 if ram_gb >= 8.0 else 4.5
        if request.graphic_quality == "photorealistic-lumen-nanite" and not has_gpu:
            hw_score = 5.0
        lic_score = 4.5 if request.licensing_preference == "open-source-mit" else 8.8

        scores = {
            "genre": genre_score,
            "world_dimension": dim_map[request.world_dimension],
            "camera_type": cam_map[request.camera_type],
            "character_count": 9.0 if request.character_count <= 50 else 8.2,
            "animation_complexity": anim_map[request.animation_complexity],
            "physics_needs": phys_map[request.physics_needs],
            "graphic_quality": gfx_map[request.graphic_quality],
            "target_platforms": 9.8,
            "expected_performance": perf_map[request.expected_performance],
            "development_complexity": dev_map[request.development_complexity],
            "free_tools_availability": 7.5,
            "hardware_requirements": hw_score if probe.available else max(hw_score - 1.5, 4.0),
            "licensing": lic_score,
            "automation_possibility": 7.2,
        }
        reasons = {
            "genre": f"Ecossistema amplo de pacotes/prefabs Unity adequado para '{request.genre}'.",
            "world_dimension": f"URP/HDRP e 2D Tilemap maduros para '{request.world_dimension}'.",
            "camera_type": "Cinemachine e componentes modulares atendem multiplos estilos de camera.",
            "character_count": f"Prefabs e LODs escalam bem para {request.character_count} personagens.",
            "animation_complexity": f"Animator Controller + Avatar retargeting atendem '{request.animation_complexity}'.",
            "physics_needs": f"PhysX/Box2D nativo com bom equilibrio para '{request.physics_needs}'.",
            "graphic_quality": f"URP/Shader Graph forte em '{request.graphic_quality}'.",
            "target_platforms": f"Cobertura multiplataforma completa (incluindo consoles) para {list(request.target_platforms)}.",
            "expected_performance": "IL2CPP e Burst/Jobs entregam bom throughput multiplataforma.",
            "development_complexity": "Modularidade C# forte (preferencial quando C# e requisito).",
            "free_tools_availability": "Alguns recursos avancados dependem de Asset Store paga ou Unity Pro.",
            "hardware_requirements": (
                f"Host ({ram_gb:.2f} GB RAM): Unity Editor {'instalado' if probe.available else 'ausente no host; requer ~10-25 GB em disco'}."
            ),
            "licensing": "Unity Personal e gratuita sob limite de receita, porem proprietaria e requer conta Unity.",
            "automation_possibility": "Batchmode mais lento que CLI headless do Godot e exige ativacao de licenca.",
        }
        return scores, reasons
