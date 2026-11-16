"""Sintetizadores locais Zero Cost (PNG RGBA e WAV PCM16 sem dependencias externas)."""
from __future__ import annotations

import io
import math
import shutil
import struct
import wave
import zlib
from pathlib import Path
from typing import Any

from factory.playforge.template_registry.registry import TemplateRegistry

from .schemas import AssetValidationError

RGBA = tuple[int, int, int, int]


def resolve_factory_godot_bin(repo_root: Path | None = None) -> Path | None:
    """Resolve binario Godot CLI priorizando repo_root e raiz instalada da PlayForge."""
    tpl_reg = TemplateRegistry(repo_root=repo_root)
    detected = tpl_reg.default_godot_bin()
    if detected is not None:
        return detected
    install_root = Path(__file__).resolve().parents[3]
    for rel in (
        "tools/godot/Godot_v4.4-stable_win64_console.exe",
        "tools/godot/Godot_v4.4-stable_linux.x86_64",
    ):
        cand = install_root / rel
        if cand.is_file():
            return cand
    return None


def _find_windows_tool_fallback(name: str) -> str | None:
    """Procura binarios instalados via winget/instaladores padrao quando o PATH da sessao nao foi atualizado."""
    import glob
    import os

    if os.name != "nt":
        return None
    local_app = os.environ.get("LOCALAPPDATA", "")
    patterns: list[str] = []
    if name == "ffmpeg":
        patterns += [
            os.path.join(local_app, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "**", "bin", "ffmpeg.exe"),
            "C:/Program Files/ffmpeg/bin/ffmpeg.exe",
        ]
    elif name == "blender":
        patterns += [
            "C:/Program Files/Blender Foundation/Blender*/blender.exe",
            os.path.join(local_app, "Programs", "Blender Foundation", "Blender*", "blender.exe"),
        ]
    for pat in patterns:
        if not pat:
            continue
        matches = sorted(glob.glob(pat, recursive=True), reverse=True)
        for cand in matches:
            if os.path.isfile(cand):
                return cand
    return None


def inspect_media_toolchain(repo_root: Path | None = None) -> dict[str, Any]:
    """Audita ferramentas gratuitas de midia presentes no ambiente sem inventar capacidade."""
    tools_to_probe = ("ffmpeg", "blender", "krita", "gimp", "magick", "sox")
    external_tools: dict[str, str | None] = {
        name: (shutil.which(name) or _find_windows_tool_fallback(name)) for name in tools_to_probe
    }
    godot_bin = resolve_factory_godot_bin(repo_root=repo_root)

    def _tool(name: str, *, mandatory: bool = False) -> dict[str, Any]:
        path = external_tools.get(name)
        return {"installed": bool(path), "path": path, "mandatory": mandatory}

    tool_orchestration: dict[str, Any] = {
        "modeling_sculpting": {"blender": _tool("blender"), "fallback": "stdlib-3d-mesh-v1"},
        "animation": {
            "blender": _tool("blender"),
            "engine_native_state_machine": {"installed": True, "path": "builtin", "mandatory": False},
        },
        "audio": {
            "engine_native": {"installed": True, "path": "builtin", "mandatory": True},
            "ffmpeg": _tool("ffmpeg"),
            "fmod": {"installed": False, "path": None, "mandatory": False},
            "wwise": {"installed": False, "path": None, "mandatory": False},
            "audacity_like_editor": {"installed": False, "path": None, "mandatory": False},
        },
        "texturing_pbr": {
            "blender": _tool("blender"),
            "krita": _tool("krita"),
            "stdlib-pbr-synthesizer-v1": {"installed": True, "path": "builtin", "mandatory": False},
            "substance_painter": {
                "installed": False,
                "path": None,
                "mandatory": False,
                "note": "Somente com licenca legitima do usuario; nunca requerido.",
            },
        },
        "environments_terrain": {
            "engine_native_terrain": {"installed": True, "path": "builtin", "mandatory": False},
            "stdlib-3d-mesh-v1": {"installed": True, "path": "builtin", "mandatory": False},
        },
    }
    return {
        "external_cli_tools": external_tools,
        "tool_orchestration": tool_orchestration,
        "builtin_synthesizers": [
            "stdlib-png-rgba-v1",
            "stdlib-wav-pcm16-v1",
            "stdlib-3d-mesh-v1",
            "stdlib-pbr-synthesizer-v1",
        ],
        "godot_cli_available": godot_bin is not None,
        "godot_cli_path": str(godot_bin) if godot_bin else None,
        "paid_services_enabled": False,
        "zero_cost_policy": "ENFORCED_LOCAL_ONLY",
    }


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _encode_rgba_png(width: int, height: int, rows: list[bytearray]) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw_scanlines = bytearray()
    for row in rows:
        raw_scanlines.append(0)  # Filter type 0 (None)
        raw_scanlines.extend(row)
    compressed = zlib.compress(bytes(raw_scanlines), level=6)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _set_px(rows: list[bytearray], width: int, height: int, x: int, y: int, color: RGBA) -> None:
    if 0 <= x < width and 0 <= y < height:
        idx = x * 4
        rows[y][idx : idx + 4] = bytes(color)


def _fill_rect(
    rows: list[bytearray],
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: RGBA,
) -> None:
    for y in range(max(0, y0), min(height, y1)):
        for x in range(max(0, x0), min(width, x1)):
            _set_px(rows, width, height, x, y, color)


def synthesize_png_sprite(
    *,
    width: int = 64,
    height: int = 64,
    pattern: str = "hero_silhouette",
    primary_rgba: RGBA = (64, 166, 242, 255),
    secondary_rgba: RGBA = (18, 22, 34, 255),
    accent_rgba: RGBA = (250, 204, 21, 255),
    seed: int = 2026,
) -> bytes:
    """Gera PNG RGBA 8-bit deterministico local sem bibliotecas externas."""
    if width <= 0 or height <= 0 or width > 2048 or height > 2048:
        raise AssetValidationError(f"Dimensoes invalidas para sintese PNG: {width}x{height}.")

    valid_patterns = (
        "hero_silhouette",
        "enemy_silhouette",
        "ui_panel",
        "icon_gem",
        "backdrop_gradient",
    )
    if pattern not in valid_patterns:
        raise AssetValidationError(f"Padrao de sintese PNG desconhecido '{pattern}'. Permitidos: {valid_patterns}.")

    rows = [bytearray(width * 4) for _ in range(height)]

    if pattern == "backdrop_gradient":
        rng = seed & 0x7FFFFFFF
        for y in range(height):
            t = y / float(max(1, height - 1))
            r = int(secondary_rgba[0] * (1.0 - t) + primary_rgba[0] * t * 0.45)
            g = int(secondary_rgba[1] * (1.0 - t) + primary_rgba[1] * t * 0.45)
            b = int(secondary_rgba[2] * (1.0 - t) + primary_rgba[2] * t * 0.45)
            for x in range(width):
                _set_px(rows, width, height, x, y, (r, g, b, 255))
        for _ in range(max(8, (width * height) // 180)):
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            sx = rng % width
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            sy = rng % max(1, (height * 2) // 3)
            _set_px(rows, width, height, sx, sy, accent_rgba)
        return _encode_rgba_png(width, height, rows)

    if pattern == "ui_panel":
        _fill_rect(rows, width, height, 0, 0, width, height, accent_rgba)
        border = max(2, min(width, height) // 16)
        _fill_rect(
            rows,
            width,
            height,
            border,
            border,
            width - border,
            height - border,
            secondary_rgba,
        )
        _fill_rect(rows, width, height, border * 2, border * 2, width - border * 2, border * 3, primary_rgba)
        return _encode_rgba_png(width, height, rows)

    if pattern == "icon_gem":
        cx, cy = width // 2, height // 2
        radius = max(4, min(width, height) // 3)
        for y in range(height):
            for x in range(width):
                dist = abs(x - cx) + abs(y - cy)
                if dist <= radius:
                    col = accent_rgba if dist <= radius // 2 else primary_rgba
                    _set_px(rows, width, height, x, y, col)
                elif dist == radius + 1:
                    _set_px(rows, width, height, x, y, secondary_rgba)
        return _encode_rgba_png(width, height, rows)

    # Silhouettes (hero / enemy)
    cx = width // 2
    torso_w = max(8, width // 3)
    torso_top = height // 3
    torso_bot = (height * 3) // 4
    _fill_rect(rows, width, height, cx - torso_w // 2, torso_top, cx + torso_w // 2, torso_bot, secondary_rgba)
    # Ombros / aura
    _fill_rect(
        rows,
        width,
        height,
        cx - torso_w // 2 - 2,
        torso_top,
        cx + torso_w // 2 + 2,
        torso_top + max(3, height // 10),
        primary_rgba,
    )
    # Cabeca / elmo
    head_r = max(4, min(width, height) // 7)
    _fill_rect(rows, width, height, cx - head_r, torso_top - head_r * 2, cx + head_r, torso_top, secondary_rgba)
    # Visor / nucleo
    _fill_rect(rows, width, height, cx - head_r // 2, torso_top - head_r, cx + head_r // 2, torso_top - head_r // 2, accent_rgba)
    if pattern == "enemy_silhouette":
        # Chifres / ombreiras pontudas
        _fill_rect(rows, width, height, cx - head_r - 2, torso_top - head_r * 2 - 4, cx - head_r + 1, torso_top - head_r, accent_rgba)
        _fill_rect(rows, width, height, cx + head_r - 1, torso_top - head_r * 2 - 4, cx + head_r + 2, torso_top - head_r, accent_rgba)
    else:
        # Espada lateral do heroi
        _fill_rect(rows, width, height, cx + torso_w // 2 + 2, torso_top - 4, cx + torso_w // 2 + 5, torso_bot - 4, accent_rgba)

    return _encode_rgba_png(width, height, rows)


def synthesize_wav_audio(
    *,
    preset: str = "slash",
    duration_s: float | None = None,
    sample_rate: int = 22050,
    gain: float = 0.65,
    fade_ms: int = 12,
    seed: int = 2026,
) -> bytes:
    """Gera WAV PCM16 mono deterministico com normalizacao anti-clipping."""
    default_durations = {
        "slash": 0.14,
        "hit": 0.10,
        "dash": 0.14,
        "ui_click": 0.07,
        "victory_chime": 0.42,
        "dark_ambient_loop": 1.20,
    }
    if preset not in default_durations:
        raise AssetValidationError(
            f"Preset de audio desconhecido '{preset}'. Permitidos: {tuple(default_durations)}."
        )
    if sample_rate < 8000 or sample_rate > 48000:
        raise AssetValidationError(f"Sample rate invalido: {sample_rate}.")

    dur = float(duration_s if duration_s is not None else default_durations[preset])
    if dur <= 0.01 or dur > 30.0:
        raise AssetValidationError(f"Duracao de audio fora dos limites (0.01..30s): {dur}.")

    eff_gain = max(0.05, min(0.85, float(gain)))
    n_frames = max(1, int(dur * sample_rate))
    fade_samples = min(n_frames // 3, int((max(1, fade_ms) / 1000.0) * sample_rate))

    raw_floats: list[float] = []
    phase = 0.0
    rng = seed & 0x7FFFFFFF

    for i in range(n_frames):
        t = i / float(max(1, n_frames - 1))
        if preset in ("slash", "hit", "dash"):
            f0, f1, noise_mix = {
                "slash": (540.0, 140.0, 0.35),
                "hit": (220.0, 62.0, 0.55),
                "dash": (760.0, 210.0, 0.42),
            }[preset]
            freq = f0 + (f1 - f0) * t
            phase += (2.0 * math.pi * freq) / float(sample_rate)
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            noise = (rng / 1073741824.0) - 1.0
            env = (1.0 - t) ** 2
            sig = (math.sin(phase) * (1.0 - noise_mix) + noise * noise_mix) * env
        elif preset in ("ui_click", "victory_chime"):
            freqs = (680.0,) if preset == "ui_click" else (440.0, 554.37, 659.25)
            sec_t = i / float(sample_rate)
            env = 1.0 - t
            sig = sum(math.sin(2.0 * math.pi * f * sec_t) for f in freqs) / float(len(freqs))
            sig *= env
        else:
            # Loop ambiente com frequencias inteiras por ciclo total (emenda sem clique)
            cycle_t = i / float(n_frames)
            sig = (
                0.55 * math.sin(2.0 * math.pi * round(55.0 * dur) * cycle_t)
                + 0.30 * math.sin(2.0 * math.pi * round(82.5 * dur) * cycle_t)
                + 0.15 * math.sin(2.0 * math.pi * round(110.0 * dur) * cycle_t)
            )

        if fade_samples > 0:
            if i < fade_samples:
                sig *= i / float(fade_samples)
            elif i >= n_frames - fade_samples and preset != "dark_ambient_loop":
                sig *= max(0, n_frames - 1 - i) / float(fade_samples)

        raw_floats.append(sig)

    peak = max((abs(v) for v in raw_floats), default=1.0)
    scale = (eff_gain / peak) if peak > 1e-6 else eff_gain
    # Garante teto rigoroso <= 0.85 (-1.4 dBFS) com zero clipping
    if scale * peak > 0.85:
        scale = 0.85 / peak

    pcm = bytearray(n_frames * 2)
    for i, val in enumerate(raw_floats):
        sample_i = max(-32700, min(32700, int(val * scale * 32767.0)))
        struct.pack_into("<h", pcm, i * 2, sample_i)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# P2 — Sintetizadores 3D / PBR Zero Cost (stdlib, deterministicos)
# ---------------------------------------------------------------------------

_CUBE_POSITIONS: tuple[tuple[float, float, float], ...] = (
    (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
    (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
)
_CUBE_TRIS: tuple[tuple[int, int, int], ...] = (
    (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
    (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (3, 0, 4), (3, 4, 7),
)


def _build_gltf_document(
    *, name: str, with_material: bool, with_rig: bool, buffer_uri: str | None
) -> tuple[dict[str, Any], bytes]:
    pos_bytes = b"".join(struct.pack("<3f", *p) for p in _CUBE_POSITIONS)
    idx_bytes = b"".join(struct.pack("<3H", *t) for t in _CUBE_TRIS)
    blob = pos_bytes + idx_bytes  # 96 + 72 bytes (multiplo de 4)
    views: list[dict[str, Any]] = [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
        {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(idx_bytes), "target": 34963},
    ]
    accessors: list[dict[str, Any]] = [
        {
            "bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3",
            "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5],
        },
        {"bufferView": 1, "componentType": 5123, "count": len(_CUBE_TRIS) * 3, "type": "SCALAR"},
    ]
    primitive: dict[str, Any] = {"attributes": {"POSITION": 0}, "indices": 1}
    doc: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "playforge-stdlib-gltf-v1"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0}],
        "meshes": [{"name": name, "primitives": [primitive]}],
    }
    if with_material:
        doc["materials"] = [
            {
                "name": f"{name}-mat",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.55, 0.55, 0.6, 1.0],
                    "metallicFactor": 0.2,
                    "roughnessFactor": 0.7,
                },
            }
        ]
        primitive["material"] = 0
    if with_rig:
        anim_times = struct.pack("<2f", 0.0, 1.0)
        anim_vals = struct.pack("<6f", 0.0, 0.0, 0.0, 0.0, 0.5, 0.0)
        off = len(blob)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(anim_times)})
        views.append({"buffer": 0, "byteOffset": off + len(anim_times), "byteLength": len(anim_vals)})
        blob += anim_times + anim_vals
        accessors.append(
            {"bufferView": 2, "componentType": 5126, "count": 2, "type": "SCALAR", "min": [0.0], "max": [1.0]}
        )
        accessors.append({"bufferView": 3, "componentType": 5126, "count": 2, "type": "VEC3"})
        doc["nodes"].append({"name": f"{name}-joint0"})
        doc["nodes"][0]["children"] = [1]
        doc["skins"] = [{"name": f"{name}-skin", "joints": [1]}]
        doc["animations"] = [
            {
                "name": "idle",
                "samplers": [{"input": 2, "output": 3, "interpolation": "LINEAR"}],
                "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}],
            }
        ]
    doc["bufferViews"] = views
    doc["accessors"] = accessors
    buf: dict[str, Any] = {"byteLength": len(blob)}
    if buffer_uri is not None:
        buf["uri"] = buffer_uri
    doc["buffers"] = [buf]
    return doc, blob


def synthesize_gltf_mesh(
    *, name: str = "prop-crate", with_material: bool = True, with_rig: bool = False
) -> bytes:
    """Gera glTF 2.0 (JSON, buffer base64 embutido) de um cubo; opcionalmente com material PBR e rig/animacao."""
    import base64
    import json

    placeholder, blob = _build_gltf_document(
        name=name, with_material=with_material, with_rig=with_rig, buffer_uri=None
    )
    placeholder["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(blob).decode("ascii")
    return json.dumps(placeholder, sort_keys=True, separators=(",", ":")).encode("utf-8")


def synthesize_glb_mesh(*, name: str = "prop-crate", with_material: bool = True) -> bytes:
    """Gera GLB 2.0 binario (chunks JSON + BIN) de um cubo."""
    import json

    doc, blob = _build_gltf_document(name=name, with_material=with_material, with_rig=False, buffer_uri=None)
    json_bytes = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    bin_bytes = blob + b"\x00" * ((4 - len(blob) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<II", len(json_bytes), 0x4E4F534A)
        + json_bytes
        + struct.pack("<II", len(bin_bytes), 0x004E4942)
        + bin_bytes
    )


def synthesize_obj_mesh(*, name: str = "prop_cube", with_material: bool = True) -> bytes:
    """Gera Wavefront OBJ de um cubo (material referenciado por usemtl)."""
    lines = [f"# PlayForge procedural mesh: {name}", f"o {name}"]
    for x, y, z in _CUBE_POSITIONS:
        lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
    if with_material:
        lines.append(f"usemtl {name}_material")
    for a, b, c in _CUBE_TRIS:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def synthesize_pbr_texture_set(
    *, width: int = 32, height: int = 32, surface: str = "metal"
) -> dict[str, bytes]:
    """Gera mapas PBR PNG (albedo, normal, roughness, metallic, ao) deterministicos."""
    presets: dict[str, dict[str, Any]] = {
        "metal": {"albedo": (150, 152, 158), "rough": 90, "metal": 230, "ao": 235},
        "stone": {"albedo": (110, 105, 100), "rough": 220, "metal": 10, "ao": 200},
        "wood": {"albedo": (120, 80, 45), "rough": 180, "metal": 5, "ao": 215},
        "cloth": {"albedo": (140, 40, 50), "rough": 240, "metal": 0, "ao": 225},
    }
    if surface not in presets:
        raise AssetValidationError(f"Superficie PBR desconhecida '{surface}'. Validas: {sorted(presets)}.")
    if not (1 <= width <= 1024 and 1 <= height <= 1024):
        raise AssetValidationError("Dimensoes PBR devem estar entre 1 e 1024.")
    p = presets[surface]

    def flat(rgb: tuple[int, int, int]) -> bytes:
        rows = []
        for y in range(height):
            row = bytearray()
            for x in range(width):
                # ruido deterministico leve para evitar mapas triviais identicos
                n = ((x * 7 + y * 13) % 5) - 2
                row += bytes((max(0, min(255, rgb[0] + n)), max(0, min(255, rgb[1] + n)), max(0, min(255, rgb[2] + n)), 255))
            rows.append(row)
        return _encode_rgba_png(width, height, rows)

    return {
        "albedo": flat(p["albedo"]),
        "normal": flat((128, 128, 255)),
        "roughness": flat((p["rough"],) * 3),
        "metallic": flat((p["metal"],) * 3),
        "ao": flat((p["ao"],) * 3),
    }
