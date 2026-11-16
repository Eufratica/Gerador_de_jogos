"""Validadores tecnicos binarios e de licenca/proveniencia para Assets e Audio (Fase 7)."""
from __future__ import annotations

import hashlib
import io
import math
import re
import struct
import wave
import zlib
from typing import Any

from factory.playforge.registry import validate_project_id
from factory.playforge.spec_engine.validator import parse_semver

from .schemas import (
    APPROVED_ASSET_LICENSES,
    ASSET_ID_RE,
    ASSET_REGISTRY_REQUIRED_FIELDS,
    ASSET_TYPES,
    DISALLOWED_LICENSE_TOKENS,
    LICENSES_REQUIRING_ATTRIBUTION,
    ORIGIN_TYPES,
    AssetLicenseError,
    AssetValidationError,
)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NO_RESTRICTION_PLACEHOLDERS = frozenset({"", "none", "n/a", "na", "nenhuma", "sem restricoes"})


def compute_sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def inspect_png(raw_bytes: bytes) -> dict[str, Any]:
    """Valida assinatura PNG, chunk IHDR/CRC32 e encerramento IEND sem libs externas."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 33:
        raise AssetValidationError("Arquivo PNG vazio ou truncado.")
    data = bytes(raw_bytes)
    if not data.startswith(_PNG_SIGNATURE):
        raise AssetValidationError("Assinatura magica PNG invalida.")

    offset = 8
    ihdr_info: dict[str, int] | None = None
    saw_iend = False

    while offset + 12 <= len(data):
        length, chunk_type = struct.unpack(">I4s", data[offset : offset + 8])
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + length
        crc_end = chunk_data_end + 4
        if crc_end > len(data):
            raise AssetValidationError("Chunk PNG truncado.")

        chunk_data = data[chunk_data_start:chunk_data_end]
        expected_crc = struct.unpack(">I", data[chunk_data_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise AssetValidationError(f"CRC32 invalido no chunk PNG '{chunk_type.decode('latin1')}'.")

        if offset == 8:
            if chunk_type != b"IHDR" or length != 13:
                raise AssetValidationError("Primeiro chunk PNG deve ser IHDR valido de 13 bytes.")
            width, height, bit_depth, color_type, compression, filter_m, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if width <= 0 or height <= 0 or width > 4096 or height > 4096:
                raise AssetValidationError(f"Dimensoes PNG fora dos limites (1..4096): {width}x{height}.")
            ihdr_info = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "compression": compression,
                "filter_method": filter_m,
                "interlace": interlace,
            }
        if chunk_type == b"IEND":
            saw_iend = True
            offset = crc_end
            break
        offset = crc_end

    if ihdr_info is None or not saw_iend:
        raise AssetValidationError("Estrutura PNG incompleta (IHDR ou IEND ausente).")

    return {
        "format": "png",
        "width": ihdr_info["width"],
        "height": ihdr_info["height"],
        "dimensions": {"width": ihdr_info["width"], "height": ihdr_info["height"]},
        "resolution": f"{ihdr_info['width']}x{ihdr_info['height']}",
        "bit_depth": ihdr_info["bit_depth"],
        "color_type": ihdr_info["color_type"],
        "byte_size": len(data),
    }


def inspect_wav(raw_bytes: bytes, *, reject_clipping: bool = True) -> dict[str, Any]:
    """Valida WAV PCM e mede duracao, taxa de amostragem, dBFS e clipping."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 44:
        raise AssetValidationError("Arquivo WAV vazio ou truncado.")
    data = bytes(raw_bytes)
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            num_frames = wf.getnframes()
            pcm_bytes = wf.readframes(num_frames)
    except (wave.Error, EOFError, struct.error) as exc:
        raise AssetValidationError(f"Cabecalho ou frames WAV corrompidos: {exc}") from exc

    if channels not in (1, 2):
        raise AssetValidationError(f"Numero de canais WAV nao suportado: {channels}.")
    if sample_width != 2:
        raise AssetValidationError(f"Apenas PCM 16-bit (2 bytes) suportado em WAV, recebido {sample_width}.")
    if sample_rate < 8000 or sample_rate > 96000:
        raise AssetValidationError(f"Sample rate WAV fora do intervalo (8000..96000 Hz): {sample_rate}.")
    if num_frames <= 0 or len(pcm_bytes) < num_frames * channels * sample_width:
        raise AssetValidationError("WAV sem frames de audio validos.")

    total_samples = num_frames * channels
    samples = struct.unpack(f"<{total_samples}h", pcm_bytes[: total_samples * 2])
    max_abs = max(abs(s) for s in samples)
    clipped_samples = sum(1 for s in samples if abs(s) >= 32767)
    peak_amp = round(max_abs / 32767.0, 4)
    peak_dbfs = round(20.0 * math.log10(max(max_abs, 1) / 32767.0), 2)
    duration_s = round(num_frames / float(sample_rate), 4)

    if reject_clipping and clipped_samples > 0:
        raise AssetValidationError(
            f"Clipping detectado no audio WAV: {clipped_samples} amostra(s) saturada(s) (>= 0 dBFS)."
        )

    return {
        "format": "wav",
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "num_frames": num_frames,
        "duration_s": duration_s,
        "peak_amplitude": peak_amp,
        "peak_dbfs": peak_dbfs,
        "clipped_samples": clipped_samples,
        "dimensions": {"channels": channels, "sample_rate": sample_rate, "duration_s": duration_s},
        "resolution": f"{sample_rate}Hz/{channels}ch",
        "byte_size": len(data),
    }


def inspect_ogg(raw_bytes: bytes) -> dict[str, Any]:
    """Valida cabecalho basico Ogg Vorbis/Opus."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 64:
        raise AssetValidationError("Arquivo OGG vazio ou truncado.")
    data = bytes(raw_bytes)
    if not data.startswith(b"OggS"):
        raise AssetValidationError("Assinatura magica OggS invalida.")
    if b"\x01vorbis" not in data[:128] and b"OpusHead" not in data[:128]:
        raise AssetValidationError("Cabecalho codec Vorbis/Opus ausente no stream OGG.")
    return {
        "format": "ogg",
        "dimensions": {"stream": "ogg"},
        "resolution": "stream-ogg",
        "byte_size": len(data),
    }


def inspect_jpeg(raw_bytes: bytes) -> dict[str, Any]:
    """Valida estrutura JPEG (SOI/EOI) e extrai dimensoes do marcador SOF."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 125:
        raise AssetValidationError("Arquivo JPEG vazio ou truncado.")
    data = bytes(raw_bytes)
    if not data.startswith(b"\xff\xd8"):
        raise AssetValidationError("Assinatura JPEG (SOI) invalida.")
    if not data.rstrip(b"\x00").endswith(b"\xff\xd9"):
        raise AssetValidationError("Marcador JPEG EOI ausente.")
    offset = 2
    width = height = None
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            raise AssetValidationError("Estrutura de segmentos JPEG corrompida.")
        marker = data[offset + 1]
        if marker == 0xFF:
            offset += 1
            continue
        if marker in (0x01,) or 0xD0 <= marker <= 0xD8:
            offset += 2
            continue
        seg_len = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
        if seg_len < 2 or offset + 2 + seg_len > len(data):
            raise AssetValidationError("Segmento JPEG com tamanho invalido.")
        if marker in (0xC0, 0xC1, 0xC2):
            if seg_len < 8:
                raise AssetValidationError("Segmento SOF JPEG truncado.")
            height, width = struct.unpack(">HH", data[offset + 5 : offset + 9])
            break
        if marker == 0xDA:
            break
        offset += 2 + seg_len
    if not width or not height:
        raise AssetValidationError("Dimensoes JPEG (SOF) nao encontradas.")
    return {
        "format": "jpg",
        "width": width,
        "height": height,
        "dimensions": {"width": width, "height": height},
        "resolution": f"{width}x{height}",
        "byte_size": len(data),
    }


def inspect_mp3(raw_bytes: bytes) -> dict[str, Any]:
    """Valida cabecalho MP3 (ID3v2 ou frame sync MPEG)."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 128:
        raise AssetValidationError("Arquivo MP3 vazio ou truncado.")
    data = bytes(raw_bytes)
    offset = 0
    if data.startswith(b"ID3"):
        if data[3] > 4:
            raise AssetValidationError("Versao ID3v2 nao suportada.")
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        offset = 10 + size
    if offset + 4 > len(data):
        raise AssetValidationError("MP3 sem frames de audio apos tag ID3.")
    b1, b2 = data[offset], data[offset + 1]
    if b1 != 0xFF or (b2 & 0xE0) != 0xE0 or ((b2 >> 3) & 0x03) == 1 or ((b2 >> 1) & 0x03) == 0:
        raise AssetValidationError("Frame sync MPEG invalido no MP3.")
    return {
        "format": "mp3",
        "dimensions": {"stream": "mp3"},
        "resolution": "stream-mp3",
        "byte_size": len(data),
    }


def _summarize_gltf_json(doc: Any) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise AssetValidationError("Documento glTF deve ser objeto JSON.")
    asset = doc.get("asset")
    if not isinstance(asset, dict) or str(asset.get("version")) != "2.0":
        raise AssetValidationError("glTF exige asset.version == '2.0'.")
    meshes = doc.get("meshes", [])
    if not isinstance(meshes, list) or not meshes:
        raise AssetValidationError("glTF sem meshes.")
    for key in ("materials", "skins", "animations"):
        if key in doc and not isinstance(doc[key], list):
            raise AssetValidationError(f"glTF campo '{key}' deve ser lista.")
    materials = doc.get("materials", [])
    skins = doc.get("skins", [])
    animations = doc.get("animations", [])
    return {
        "mesh_count": len(meshes),
        "material_count": len(materials),
        "skin_count": len(skins),
        "animation_count": len(animations),
        "has_materials": len(materials) > 0,
        "has_rig": len(skins) > 0,
    }


def _model_info(fmt: str, summary: dict[str, Any], size: int) -> dict[str, Any]:
    return {
        "format": fmt,
        **summary,
        "dimensions": {k: v for k, v in summary.items() if k.endswith("_count")},
        "resolution": "mesh-" + fmt,
        "byte_size": size,
    }


def inspect_gltf(raw_bytes: bytes) -> dict[str, Any]:
    """Valida glTF 2.0 em JSON e resume malhas, materiais, rig e animacoes."""
    import json

    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 20:
        raise AssetValidationError("Arquivo glTF vazio ou truncado.")
    try:
        doc = json.loads(bytes(raw_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetValidationError(f"glTF JSON invalido: {exc}") from exc
    return _model_info("gltf", _summarize_gltf_json(doc), len(raw_bytes))


def inspect_glb(raw_bytes: bytes) -> dict[str, Any]:
    """Valida container GLB (magic, versao, tamanho, chunk JSON)."""
    import json

    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 28:
        raise AssetValidationError("Arquivo GLB vazio ou truncado.")
    data = bytes(raw_bytes)
    magic, version, total = struct.unpack("<4sII", data[:12])
    if magic != b"glTF":
        raise AssetValidationError("Assinatura GLB 'glTF' invalida.")
    if version != 2:
        raise AssetValidationError(f"Versao GLB nao suportada: {version}.")
    if total != len(data):
        raise AssetValidationError(f"Tamanho GLB divergente: cabecalho={total}, real={len(data)}.")
    chunk_len, chunk_type = struct.unpack("<II", data[12:20])
    if chunk_type != 0x4E4F534A or 20 + chunk_len > len(data):
        raise AssetValidationError("Primeiro chunk GLB deve ser JSON valido.")
    try:
        doc = json.loads(data[20 : 20 + chunk_len].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetValidationError(f"Chunk JSON do GLB invalido: {exc}") from exc
    return _model_info("glb", _summarize_gltf_json(doc), len(data))


def inspect_obj(raw_bytes: bytes) -> dict[str, Any]:
    """Valida Wavefront OBJ textual com vertices e faces coerentes."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 20:
        raise AssetValidationError("Arquivo OBJ vazio ou truncado.")
    try:
        text = bytes(raw_bytes).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssetValidationError(f"OBJ nao e texto UTF-8: {exc}") from exc
    verts = faces = 0
    has_mat = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("v "):
            if len(s.split()) < 4:
                raise AssetValidationError("Vertice OBJ malformado.")
            verts += 1
        elif s.startswith("f "):
            for tok in s.split()[1:]:
                idx = int(tok.split("/")[0]) if tok.split("/")[0].lstrip("-").isdigit() else 0
                if idx == 0 or idx > verts:
                    raise AssetValidationError("Face OBJ referencia vertice inexistente.")
            faces += 1
        elif s.startswith(("mtllib ", "usemtl ")):
            has_mat = True
    if verts == 0 or faces == 0:
        raise AssetValidationError("OBJ sem vertices ou faces.")
    return _model_info(
        "obj",
        {"vertex_count": verts, "face_count": faces, "has_materials": has_mat, "has_rig": False},
        len(raw_bytes),
    )


def inspect_fbx(raw_bytes: bytes) -> dict[str, Any]:
    """Valida assinatura FBX (binario Kaydara ou ASCII). Nao interpreta o conteudo."""
    if not isinstance(raw_bytes, (bytes, bytearray)) or len(raw_bytes) < 27:
        raise AssetValidationError("Arquivo FBX vazio ou truncado.")
    data = bytes(raw_bytes)
    if data.startswith(b"Kaydara FBX Binary  \x00"):
        kind = "binary"
    elif data.lstrip().startswith(b"; FBX"):
        kind = "ascii"
    else:
        raise AssetValidationError("Assinatura FBX invalida.")
    return {
        "format": "fbx",
        "fbx_encoding": kind,
        "dimensions": {"fbx_encoding": kind},
        "resolution": "mesh-fbx",
        "byte_size": len(data),
    }


def inspect_media_bytes(fmt: str, raw_bytes: bytes, *, reject_clipping: bool = True) -> dict[str, Any]:
    """Despacha inspecao binaria por formato suportado."""
    norm = fmt.strip().lower().lstrip(".")
    if norm == "png":
        return inspect_png(raw_bytes)
    if norm == "wav":
        return inspect_wav(raw_bytes, reject_clipping=reject_clipping)
    if norm == "ogg":
        return inspect_ogg(raw_bytes)
    if norm in ("jpg", "jpeg"):
        return inspect_jpeg(raw_bytes)
    if norm == "mp3":
        return inspect_mp3(raw_bytes)
    if norm == "gltf":
        return inspect_gltf(raw_bytes)
    if norm == "glb":
        return inspect_glb(raw_bytes)
    if norm == "obj":
        return inspect_obj(raw_bytes)
    if norm == "fbx":
        return inspect_fbx(raw_bytes)
    raise AssetValidationError(f"Formato de midia nao suportado para inspecao binaria: '{fmt}'.")


def validate_license_and_provenance(entry: dict[str, Any]) -> None:
    """Valida fail-closed a licenca comercial e os campos obrigatorios de proveniencia."""
    origin = entry.get("origin")
    if not isinstance(origin, str) or origin not in ORIGIN_TYPES:
        raise AssetLicenseError(
            f"Origem de asset invalida '{origin}'. Permitidas: {ORIGIN_TYPES}."
        )

    for key in ("author_or_provider", "tool_used", "restrictions"):
        val = entry.get(key)
        if not isinstance(val, str) or not val.strip():
            raise AssetLicenseError(f"Campo de proveniencia obrigatorio ausente ou vazio: '{key}'.")

    lic = entry.get("license")
    if not isinstance(lic, str) or not lic.strip():
        raise AssetLicenseError("Licenca do asset nao informada.")
    lic_clean = lic.strip()
    lic_tokens = set(re.split(r"[^A-Z0-9]+", lic_clean.upper()))
    if any(tok in lic_tokens for tok in DISALLOWED_LICENSE_TOKENS) or "ALL_RIGHTS_RESERVED" in lic_clean.upper():
        raise AssetLicenseError(
            f"Licenca proibida pela politica comercial/Zero Cost: '{lic_clean}'."
        )
    if lic_clean not in APPROVED_ASSET_LICENSES:
        raise AssetLicenseError(
            f"Licenca '{lic_clean}' nao consta na lista aprovada: {APPROVED_ASSET_LICENSES}."
        )

    restrictions_norm = entry["restrictions"].strip().lower()
    if lic_clean in LICENSES_REQUIRING_ATTRIBUTION and restrictions_norm in _NO_RESTRICTION_PLACEHOLDERS:
        raise AssetLicenseError(
            f"Licenca '{lic_clean}' exige registro explicito de atribuicao em 'restrictions'."
        )

    if origin == "local_ai_verified":
        model_used = entry.get("model_used")
        prompt_or_seed = entry.get("prompt_or_seed")
        if not isinstance(model_used, str) or model_used.strip().lower() in _NO_RESTRICTION_PLACEHOLDERS:
            raise AssetLicenseError("Asset de origem IA local exige 'model_used' documentado.")
        if not isinstance(prompt_or_seed, str) or prompt_or_seed.strip().lower() in _NO_RESTRICTION_PLACEHOLDERS:
            raise AssetLicenseError("Asset de origem IA local exige 'prompt_or_seed' documentado.")


def validate_asset_record(
    entry: dict[str, Any],
    *,
    raw_bytes: bytes | None = None,
    reject_clipping: bool = True,
) -> dict[str, Any]:
    """Valida integralmente um registro do AssetRegistry."""
    if not isinstance(entry, dict):
        raise AssetValidationError("Registro de asset deve ser objeto JSON.")

    missing = [field for field in ASSET_REGISTRY_REQUIRED_FIELDS if field not in entry]
    if missing:
        raise AssetValidationError(
            f"Campos obrigatorios ausentes no registro de asset: {', '.join(missing)}."
        )

    asset_id = entry["asset_id"]
    if not isinstance(asset_id, str) or not ASSET_ID_RE.match(asset_id):
        raise AssetValidationError(f"asset_id invalido: '{asset_id}'.")

    if not isinstance(entry["name"], str) or not entry["name"].strip():
        raise AssetValidationError("Campo 'name' do asset nao pode ser vazio.")

    asset_type = entry["asset_type"]
    if asset_type not in ASSET_TYPES:
        raise AssetValidationError(f"asset_type invalido '{asset_type}'. Permitidos: {ASSET_TYPES}.")

    validate_project_id(entry["project_id"])
    validate_project_id(entry["game_id"])
    parse_semver(entry["version"])

    sha = entry["sha256_hash"]
    if not isinstance(sha, str) or not _SHA256_RE.match(sha):
        raise AssetValidationError(f"sha256_hash invalido para asset '{asset_id}'.")

    byte_size = entry["byte_size"]
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size <= 0:
        raise AssetValidationError(f"byte_size invalido para asset '{asset_id}'.")

    validate_license_and_provenance(entry)

    if raw_bytes is not None:
        actual_sha = compute_sha256_bytes(raw_bytes)
        if actual_sha != sha:
            raise AssetValidationError(
                f"Divergencia de SHA-256 em '{asset_id}': esperado {sha}, atual {actual_sha}."
            )
        if len(raw_bytes) != byte_size:
            raise AssetValidationError(
                f"Divergencia de tamanho em '{asset_id}': esperado {byte_size}, atual {len(raw_bytes)}."
            )
        fmt = str(entry["format"]).strip().lower()
        if fmt in ("png", "wav", "ogg", "jpg", "jpeg", "mp3", "gltf", "glb", "obj", "fbx"):
            inspect_media_bytes(fmt, raw_bytes, reject_clipping=reject_clipping)

    _validate_extended_fields(entry)
    return dict(entry)


def _validate_extended_fields(entry: dict[str, Any]) -> None:
    """Valida campos opcionais de assets 3D/PBR quando presentes."""
    if "compatible_engines" in entry:
        engines = entry["compatible_engines"]
        if not isinstance(engines, list) or not engines or any(not isinstance(e, str) or not e.strip() for e in engines):
            raise AssetValidationError("'compatible_engines' deve ser lista nao vazia de strings.")
    if "lod_level" in entry:
        lod = entry["lod_level"]
        if isinstance(lod, bool) or not isinstance(lod, int) or lod < 0:
            raise AssetValidationError("'lod_level' deve ser inteiro >= 0.")
    if "pbr_maps" in entry:
        maps = entry["pbr_maps"]
        if not isinstance(maps, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in maps.items()):
            raise AssetValidationError("'pbr_maps' deve ser objeto {mapa: asset_id}.")
    for key in ("has_rig", "has_materials"):
        if key in entry and not isinstance(entry[key], bool):
            raise AssetValidationError(f"'{key}' deve ser booleano.")
