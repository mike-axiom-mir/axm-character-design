"""Runtime-owned bounded cache for review-006 posed smooth normals.

This module does not own Character source form, topology, Rigging, Animation, or
Materials meaning.  It implements one narrow runtime/preparation candidate for
an exact deforming receiver: cache face-normal work whose vertices are proven
static for the bound motion, while replaying dynamic and cached face
contributions in the original face order.

The intended reference is the Materials review method
``AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL``.  Exact equivalence to that
external owner is an evidence requirement; this module alone does not claim it.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

Vec3 = tuple[float, float, float]
Face = tuple[int, int, int]

_DEGENERATE_EPS = 1e-15


def _vec3(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("expected 3D vector")
    return (float(value[0]), float(value[1]), float(value[2]))


def _sub(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (
        float(a[0]) - float(b[0]),
        float(a[1]) - float(b[1]),
        float(a[2]) - float(b[2]),
    )


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(a[index]) * float(b[index]) for index in range(3))


def _length(value: Sequence[float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: Sequence[float]) -> Vec3:
    magnitude = _length(value)
    if magnitude <= _DEGENERATE_EPS:
        raise ValueError("zero-length accumulated normal")
    return tuple(float(component) / magnitude for component in value)  # type: ignore[return-value]


def _face_normal(vertices: Sequence[Sequence[float]], face: Face) -> Vec3:
    a, b, c = face
    first = _sub(vertices[b], vertices[a])
    second = _sub(vertices[c], vertices[a])
    normal = _cross(first, second)
    if _length(normal) <= _DEGENERATE_EPS:
        raise ValueError("degenerate face in normal receiver")
    return normal


def _full_smooth_normals(vertices: Sequence[Sequence[float]], faces: Sequence[Face]) -> tuple[Vec3, ...]:
    """Internal neutral precompute using the same arithmetic/order as the reference method."""
    accum = [[0.0, 0.0, 0.0] for _ in vertices]
    for face in faces:
        normal = _face_normal(vertices, face)
        for index in face:
            accum[index][0] += normal[0]
            accum[index][1] += normal[1]
            accum[index][2] += normal[2]
    return tuple(_normalize(value) for value in accum)


@dataclass(frozen=True)
class PosedNormalCachePlan:
    """Immutable cache plan for one exact topology + proven static-vertex set."""

    vertex_count: int
    faces: tuple[Face, ...]
    static_vertex_indices: frozenset[int]
    cached_face_normals: tuple[Vec3 | None, ...]
    cached_output_normals: tuple[Vec3 | None, ...]
    static_face_count: int
    dynamic_face_count: int
    static_output_vertex_count: int
    dynamic_output_vertex_count: int

    @property
    def face_count(self) -> int:
        return len(self.faces)


def build_posed_normal_cache_plan(
    neutral_vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    static_vertex_indices: Iterable[int],
) -> PosedNormalCachePlan:
    """Build a cache without changing topology or normal semantics.

    A face can reuse its neutral cross product only when every source vertex of
    that face belongs to the externally proven static set.  A final output
    normal can be reused only when none of its incident faces are dynamic.
    """
    vertices = tuple(_vec3(value) for value in neutral_vertices)
    normalized_faces: tuple[Face, ...] = tuple(
        (int(face[0]), int(face[1]), int(face[2])) for face in faces
    )
    if not vertices:
        raise ValueError("normal cache requires vertices")
    if not normalized_faces:
        raise ValueError("normal cache requires faces")
    for face in normalized_faces:
        if any(index < 0 or index >= len(vertices) for index in face):
            raise ValueError("face index outside vertex domain")

    static_vertices = frozenset(int(index) for index in static_vertex_indices)
    if any(index < 0 or index >= len(vertices) for index in static_vertices):
        raise ValueError("static vertex index outside vertex domain")

    cached_faces: list[Vec3 | None] = []
    incident_dynamic = [False] * len(vertices)
    for face in normalized_faces:
        if all(index in static_vertices for index in face):
            cached_faces.append(_face_normal(vertices, face))
        else:
            cached_faces.append(None)
            for index in face:
                incident_dynamic[index] = True

    neutral_normals = _full_smooth_normals(vertices, normalized_faces)
    cached_outputs: list[Vec3 | None] = []
    for index, normal in enumerate(neutral_normals):
        if not incident_dynamic[index]:
            if index not in static_vertices:
                raise ValueError("static output vertex was not declared static")
            cached_outputs.append(normal)
        else:
            cached_outputs.append(None)

    static_face_count = sum(value is not None for value in cached_faces)
    static_output_vertex_count = sum(value is not None for value in cached_outputs)
    return PosedNormalCachePlan(
        vertex_count=len(vertices),
        faces=normalized_faces,
        static_vertex_indices=static_vertices,
        cached_face_normals=tuple(cached_faces),
        cached_output_normals=tuple(cached_outputs),
        static_face_count=static_face_count,
        dynamic_face_count=len(normalized_faces) - static_face_count,
        static_output_vertex_count=static_output_vertex_count,
        dynamic_output_vertex_count=len(vertices) - static_output_vertex_count,
    )


def assert_static_vertices_unchanged(
    plan: PosedNormalCachePlan,
    neutral_vertices: Sequence[Sequence[float]],
    posed_vertices: Sequence[Sequence[float]],
) -> None:
    """Fail closed if a pose violates the static-set prerequisite."""
    if len(neutral_vertices) != plan.vertex_count or len(posed_vertices) != plan.vertex_count:
        raise ValueError("vertex count drift against normal cache plan")
    for index in plan.static_vertex_indices:
        if _vec3(neutral_vertices[index]) != _vec3(posed_vertices[index]):
            raise ValueError(f"static vertex moved at index {index}")


def evaluate_cached_smooth_normals(
    posed_vertices: Sequence[Sequence[float]],
    plan: PosedNormalCachePlan,
) -> tuple[Vec3, ...]:
    """Evaluate the exact smooth-normal field with cached static work.

    Face contributions are still accumulated in the exact original face order.
    Cached faces substitute only the cross product already proven invariant.
    Dynamic-output vertices therefore see the same ordered contribution stream
    as the uncached method.
    """
    if len(posed_vertices) != plan.vertex_count:
        raise ValueError("vertex count drift against normal cache plan")
    vertices = tuple(_vec3(value) for value in posed_vertices)
    accum = [[0.0, 0.0, 0.0] for _ in range(plan.vertex_count)]

    for face_index, face in enumerate(plan.faces):
        normal = plan.cached_face_normals[face_index]
        if normal is None:
            normal = _face_normal(vertices, face)
        for index in face:
            if plan.cached_output_normals[index] is None:
                accum[index][0] += normal[0]
                accum[index][1] += normal[1]
                accum[index][2] += normal[2]

    output: list[Vec3] = []
    for index, cached in enumerate(plan.cached_output_normals):
        output.append(cached if cached is not None else _normalize(accum[index]))
    return tuple(output)


def operation_budget(plan: PosedNormalCachePlan, pose_count: int) -> dict[str, int]:
    """Return deterministic expensive-operation counts for before/after evidence."""
    if pose_count < 1:
        raise ValueError("pose_count must be positive")
    control_face_crosses = plan.face_count * pose_count
    candidate_face_crosses = plan.dynamic_face_count * pose_count
    control_vertex_normalizations = plan.vertex_count * pose_count
    candidate_vertex_normalizations = plan.dynamic_output_vertex_count * pose_count
    return {
        "pose_count": pose_count,
        "control_face_crosses": control_face_crosses,
        "candidate_face_crosses": candidate_face_crosses,
        "saved_face_crosses": control_face_crosses - candidate_face_crosses,
        "control_vertex_normalizations": control_vertex_normalizations,
        "candidate_vertex_normalizations": candidate_vertex_normalizations,
        "saved_vertex_normalizations": control_vertex_normalizations - candidate_vertex_normalizations,
    }
