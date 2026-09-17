"""Exact animation-output accessor sharing for the bounded review-006 export.

This is a Technical Art export contract, not an optimization policy in Universal
Creation.  It consumes Runtime PR #23's proven mechanism at the producer
boundary: two animation channels may share one output accessor only when their
accessor semantics and encoded payload bytes are exactly identical.

The bounded implementation deliberately fails closed unless the removable
accessor/view is the final tightly-packed binary payload.  That keeps the edit
small, auditable, rollbackable, and incapable of silently rewriting unrelated
GLB storage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any

from .review006_uc_skin_transport import PackedCharacterGlb, pack_character_glb

SCHEMA = "axm.character-exact-animation-output-accessor-sharing/v0.1"
ADOPTION_STATUS = "PASS_CHARACTER_REVIEW006_TECHNICAL_ART_EXACT_RELEASE_SCALE_ACCESSOR_SHARING_CANDIDATE"
RUNTIME_DONOR_HEAD = "d95caae1df766b2e08bca50241d732ecb2208aee"
RUNTIME_DONOR_SCHEMA = "axm.character-review006-runtime-scale-accessor-dedup/v0.1"
LEFT_RELEASE_NODE = "shoulder-L-release-transport"
RIGHT_RELEASE_NODE = "shoulder-R-release-transport"
EXPECTED_DENSE_KEYS = 321
EXPECTED_DUPLICATE_PAYLOAD_BYTES = EXPECTED_DENSE_KEYS * 3 * 4


@dataclass(frozen=True)
class AccessorSharingResult:
    bytes: bytes
    document: dict[str, Any]
    receipt: dict[str, Any]


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _pad4(data: bytes, fill: bytes = b"\x00") -> bytes:
    return data + fill * ((-len(data)) % 4)


def parse_glb(body: bytes) -> tuple[dict[str, Any], bytes]:
    if len(body) < 28:
        raise ValueError("GLB too short")
    magic, version, total = struct.unpack_from("<4sII", body, 0)
    if magic != b"glTF" or version != 2 or total != len(body):
        raise ValueError("unexpected GLB header")
    json_len, json_kind = struct.unpack_from("<I4s", body, 12)
    if json_kind != b"JSON":
        raise ValueError("first GLB chunk is not JSON")
    json_start = 20
    json_end = json_start + json_len
    document = json.loads(body[json_start:json_end].decode("utf-8").rstrip(" "))
    bin_len, bin_kind = struct.unpack_from("<I4s", body, json_end)
    if bin_kind != b"BIN\x00":
        raise ValueError("second GLB chunk is not BIN")
    bin_start = json_end + 8
    binary = body[bin_start:bin_start + bin_len]
    if bin_start + bin_len != len(body):
        raise ValueError("unexpected trailing GLB bytes")
    if int(document["buffers"][0]["byteLength"]) != len(binary):
        raise ValueError("GLB buffer length/document mismatch")
    return document, binary


def build_glb(document: dict[str, Any], binary: bytes) -> bytes:
    document = copy.deepcopy(document)
    document["buffers"][0]["byteLength"] = len(binary)
    json_chunk = _pad4(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8"), b" "
    )
    bin_chunk = _pad4(binary)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(bin_chunk), b"BIN\x00")
        + bin_chunk
    )


def _accessor_semantics(accessor: dict[str, Any]) -> dict[str, Any]:
    """Return semantics that must match before encoded payload sharing is legal."""
    return {key: value for key, value in accessor.items() if key != "bufferView"}


def accessor_payload(document: dict[str, Any], binary: bytes, accessor_index: int) -> bytes:
    accessor = document["accessors"][int(accessor_index)]
    if "sparse" in accessor:
        raise ValueError("sparse animation outputs are outside exact sharing v0.1")
    if int(accessor.get("byteOffset", 0)) != 0:
        raise ValueError("non-zero accessor byteOffset is outside exact sharing v0.1")
    view = document["bufferViews"][int(accessor["bufferView"])]
    if "byteStride" in view:
        raise ValueError("strided animation outputs are outside exact sharing v0.1")
    component_size = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}.get(
        int(accessor["componentType"])
    )
    component_count = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16,
    }.get(str(accessor["type"]))
    if component_size is None or component_count is None:
        raise ValueError("unsupported accessor representation")
    expected = int(accessor["count"]) * component_size * component_count
    if int(view["byteLength"]) != expected:
        raise ValueError("animation output bufferView is not tightly packed")
    offset = int(view.get("byteOffset", 0))
    payload = binary[offset:offset + expected]
    if len(payload) != expected:
        raise ValueError("animation output payload is truncated")
    return payload


def _channel_output(document: dict[str, Any], node_name: str, path: str) -> tuple[int, int]:
    node_indexes = [i for i, row in enumerate(document.get("nodes", [])) if row.get("name") == node_name]
    if len(node_indexes) != 1:
        raise ValueError(f"expected exactly one node named {node_name!r}")
    animation_rows = document.get("animations", [])
    if len(animation_rows) != 1:
        raise ValueError("bounded sharing contract expects exactly one animation")
    animation = animation_rows[0]
    matches: list[tuple[int, int]] = []
    for channel in animation.get("channels", []):
        target = channel.get("target", {})
        if int(target.get("node", -1)) != node_indexes[0] or target.get("path") != path:
            continue
        sampler_index = int(channel["sampler"])
        sampler = animation["samplers"][sampler_index]
        matches.append((sampler_index, int(sampler["output"])))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {path!r} channel for {node_name!r}")
    return matches[0]


def share_exact_animation_output_accessor(
    control_glb: bytes,
    *,
    keeper_node_name: str,
    duplicate_node_name: str,
    path: str,
) -> AccessorSharingResult:
    """Share one exact animation output accessor or reject without guessing.

    v0.1 only removes a final accessor whose bufferView is itself the final,
    tightly-packed binary region.  This is intentionally narrower than a
    general GLB compactor.
    """
    document, binary = parse_glb(control_glb)
    keeper_sampler, keeper_accessor = _channel_output(document, keeper_node_name, path)
    duplicate_sampler, duplicate_accessor = _channel_output(document, duplicate_node_name, path)
    if keeper_accessor == duplicate_accessor:
        raise ValueError("control already shares the requested animation output accessor")

    keep_row = document["accessors"][keeper_accessor]
    duplicate_row = document["accessors"][duplicate_accessor]
    if _accessor_semantics(keep_row) != _accessor_semantics(duplicate_row):
        raise ValueError("animation output accessor semantics differ; sharing rejected")
    keeper_payload = accessor_payload(document, binary, keeper_accessor)
    duplicate_payload = accessor_payload(document, binary, duplicate_accessor)
    if keeper_payload != duplicate_payload:
        raise ValueError("animation output payloads are not byte-identical; sharing rejected")

    duplicate_view_index = int(duplicate_row["bufferView"])
    if duplicate_accessor != len(document["accessors"]) - 1:
        raise ValueError("v0.1 only removes the final accessor")
    if duplicate_view_index != len(document["bufferViews"]) - 1:
        raise ValueError("v0.1 only removes the final bufferView")
    duplicate_view = document["bufferViews"][duplicate_view_index]
    duplicate_offset = int(duplicate_view.get("byteOffset", 0))
    duplicate_length = int(duplicate_view["byteLength"])
    if duplicate_offset + duplicate_length != len(binary):
        raise ValueError("v0.1 only removes the final binary payload")

    candidate_document = copy.deepcopy(document)
    candidate_document["animations"][0]["samplers"][duplicate_sampler]["output"] = keeper_accessor
    candidate_document["accessors"].pop()
    candidate_document["bufferViews"].pop()
    candidate_binary = binary[:duplicate_offset]
    candidate_glb = build_glb(candidate_document, candidate_binary)

    reparsed, rebinary = parse_glb(candidate_glb)
    _, keeper_after = _channel_output(reparsed, keeper_node_name, path)
    _, duplicate_after = _channel_output(reparsed, duplicate_node_name, path)
    if keeper_after != duplicate_after or keeper_after != keeper_accessor:
        raise ValueError("candidate channels do not share the exact keeper accessor")
    if accessor_payload(reparsed, rebinary, keeper_after) != keeper_payload:
        raise ValueError("retained shared animation output payload changed")

    receipt = {
        "schema": SCHEMA,
        "status": "PASS_EXACT_ANIMATION_OUTPUT_ACCESSOR_SHARING",
        "runtime_donor_head": RUNTIME_DONOR_HEAD,
        "keeper": {
            "node": keeper_node_name,
            "path": path,
            "sampler": keeper_sampler,
            "control_accessor": keeper_accessor,
        },
        "duplicate": {
            "node": duplicate_node_name,
            "path": path,
            "sampler": duplicate_sampler,
            "control_accessor": duplicate_accessor,
        },
        "candidate_shared_accessor": keeper_accessor,
        "shared_payload_bytes": len(keeper_payload),
        "shared_payload_sha256": sha256_bytes(keeper_payload),
        "removed_binary_bytes": duplicate_length,
        "control_accessors": len(document["accessors"]),
        "candidate_accessors": len(reparsed["accessors"]),
        "control_buffer_views": len(document["bufferViews"]),
        "candidate_buffer_views": len(reparsed["bufferViews"]),
        "semantics_exactly_equal_before_share": True,
        "payload_bytes_exactly_equal_before_share": True,
        "domain_semantics_inferred": False,
    }
    return AccessorSharingResult(candidate_glb, reparsed, receipt)


def mutate_duplicate_output_byte(
    control_glb: bytes, *, duplicate_node_name: str, path: str
) -> bytes:
    """Verifier-only negative: change one payload byte without changing metadata."""
    document, binary = parse_glb(control_glb)
    _, accessor_index = _channel_output(document, duplicate_node_name, path)
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][int(accessor["bufferView"])]
    offset = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    mutated = bytearray(binary)
    mutated[offset] ^= 0x01
    return build_glb(document, bytes(mutated))


def pack_character_glb_with_shared_release_scale() -> tuple[PackedCharacterGlb, dict[str, Any]]:
    """Technical Art adoption candidate for the exact review-006 producer."""
    control = pack_character_glb()
    result = share_exact_animation_output_accessor(
        control.bytes,
        keeper_node_name=LEFT_RELEASE_NODE,
        duplicate_node_name=RIGHT_RELEASE_NODE,
        path="scale",
    )
    if result.receipt["shared_payload_bytes"] != EXPECTED_DUPLICATE_PAYLOAD_BYTES:
        raise ValueError("review-006 exact bilateral scale payload byte budget drift")
    adopted = PackedCharacterGlb(
        result.bytes,
        result.document,
        control.times,
        control.angles,
        control.source_vertex_counts,
        control.source_triangle_counts,
    )
    receipt = {
        "schema": "axm.character-review006-technical-art-accessor-sharing-adoption/v0.1",
        "status": ADOPTION_STATUS,
        "runtime_donor": {
            "head": RUNTIME_DONOR_HEAD,
            "schema": RUNTIME_DONOR_SCHEMA,
            "mechanism_retested_in_producer_context": True,
            "runtime_acceptance_transferred": False,
        },
        "control": {"bytes": len(control.bytes), "sha256": sha256_bytes(control.bytes)},
        "candidate": {"bytes": len(adopted.bytes), "sha256": sha256_bytes(adopted.bytes)},
        "bytes_saved": len(control.bytes) - len(adopted.bytes),
        "sharing": result.receipt,
        "truth_boundary": {
            "technical_art_export_candidate": True,
            "default_historical_packer_rewritten": False,
            "uc_modified": False,
            "runtime_policy_owned_here": False,
            "domain_semantics_centralized": False,
            "art_or_qa_acceptance": False,
            "canon": False,
            "production_readiness": False,
        },
    }
    return adopted, receipt
