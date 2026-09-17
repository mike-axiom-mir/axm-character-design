"""Small Technical-Art bridge for receiver-local triangle winding observations.

This module is deliberately policy-free. It does not claim a universal Godot rule,
change source topology, or choose production geometry. It only provides exact,
fail-closed helpers for comparing triangle index order across an import boundary.
"""
from __future__ import annotations

from typing import Iterable, Sequence

SCHEMA = "axm.target-host-triangle-winding-bridge/v0.1"
EXACT_OWNER_ORDER = "EXACT_OWNER_ORDER"
EXACT_REVERSED_WINDING = "EXACT_REVERSED_WINDING"
OTHER_INDEX_RELATION = "OTHER_INDEX_RELATION"


def _validated_faces(faces: Iterable[Sequence[int]]) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    for face_index, face in enumerate(faces):
        if not isinstance(face, (list, tuple)) or len(face) != 3:
            raise ValueError(f"face {face_index} must contain exactly three indices")
        row = tuple(int(value) for value in face)
        if any(value < 0 for value in row):
            raise ValueError(f"face {face_index} contains a negative index")
        if len(set(row)) != 3:
            raise ValueError(f"face {face_index} is degenerate in index space")
        rows.append(row)
    if not rows:
        raise ValueError("at least one triangle is required")
    return rows


def flatten_faces(faces: Iterable[Sequence[int]]) -> list[int]:
    return [value for face in _validated_faces(faces) for value in face]


def reverse_triangle_winding(faces: Iterable[Sequence[int]]) -> list[list[int]]:
    """Return the exact per-triangle [a,b,c] -> [a,c,b] permutation."""
    return [[a, c, b] for a, b, c in _validated_faces(faces)]


def classify_index_relation(
    owner_faces: Iterable[Sequence[int]], imported_indices: Sequence[int]
) -> dict:
    owner = _validated_faces(owner_faces)
    imported = [int(value) for value in imported_indices]
    expected_count = len(owner) * 3
    if len(imported) != expected_count:
        raise ValueError(
            f"imported index count {len(imported)} does not match triangle payload {expected_count}"
        )
    owner_flat = [value for face in owner for value in face]
    reversed_faces = [(a, c, b) for a, b, c in owner]
    reversed_flat = [value for face in reversed_faces for value in face]
    owner_mismatches = sum(a != b for a, b in zip(imported, owner_flat))
    reversed_mismatches = sum(a != b for a, b in zip(imported, reversed_flat))
    exact_owner_triangles = 0
    exact_reversed_triangles = 0
    for triangle_index, (owner_face, reversed_face) in enumerate(zip(owner, reversed_faces)):
        row = tuple(imported[triangle_index * 3 : triangle_index * 3 + 3])
        exact_owner_triangles += row == owner_face
        exact_reversed_triangles += row == reversed_face
    if owner_mismatches == 0:
        relation = EXACT_OWNER_ORDER
    elif reversed_mismatches == 0:
        relation = EXACT_REVERSED_WINDING
    else:
        relation = OTHER_INDEX_RELATION
    return {
        "schema": SCHEMA,
        "relation": relation,
        "triangle_count": len(owner),
        "index_count": expected_count,
        "owner_order_mismatch_count": owner_mismatches,
        "reversed_winding_mismatch_count": reversed_mismatches,
        "exact_owner_triangles": exact_owner_triangles,
        "exact_reversed_triangles": exact_reversed_triangles,
    }
