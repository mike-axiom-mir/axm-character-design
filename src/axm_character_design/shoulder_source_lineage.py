from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .organic_form import canonical_digest, mesh_checks, neutral_character_study, validate_study, write_obj
from .shoulder_transition_feathered import (
    BLEND_WEIGHTS,
    ROOT_RING_INDICES,
    TARGET_AXIS_SCALE,
    audit_feathered_shoulder,
    build_feathered_shoulder_mesh,
    feathered_shoulder_candidate,
)

SCHEMA = "axm.character-shoulder-source-lineage/v0.1"
SOURCE_ID = "character-neutral-a-shoulder-source-004"
STATUS = "PASS_EXACT_E_FORM_MIGRATED_TO_SOURCE_LINEAGE"

# Repository-owned E identities come from the exact retained Character workflow
# (head 4fb82dc97cbdb487a1cde407b503f50565b40c05, run 35090245742).
EXPECTED_REVIEW_SOURCE_DIGEST = "3fe07d029bf701c1455eef9c651285b2ec2a638628d9f57a4f2648f4acfd6e9b"
EXPECTED_REVIEW_MESH_DIGEST = "30a4612212f2e8252b6f813912ce76c655763e6d3abb4650c04ad1af72baea7f"

# Independent Visual QA reconstructed the same proof mesh but serialized its
# review source differently. Keep that separate instead of silently treating a
# reconstruction digest as the repository's canonical source identity.
QA_RECONSTRUCTION_SOURCE_DIGEST = "846b841724121ee104536ca0e7d4fd22a2005bfd04e25e90b75a9b399b756043"
QA_RECONSTRUCTION_MESH_DIGEST = EXPECTED_REVIEW_MESH_DIGEST

ART_DIRECTION_PACKET = {
    "repository": "mike-axiom-mir/axm-create-me",
    "path": "studio/direction/CHARACTER_FEATHERED_SHOULDER_ADOPTION_DIRECTION_003.md",
    "commit": "3c3c481d0360f604ff2b625c9a3ba2594c1284bb",
    "decision": "PASS_ART_DIRECTION_CHARACTER_FEATHERED_SHOULDER_E",
}
VISUAL_QA_DECISION = "PASS_CHARACTER_FEATHERED_SHOULDER_LOCAL_VISUAL_DEFECT_GATE"


def _review_candidate():
    baseline = neutral_character_study()
    review = feathered_shoulder_candidate(baseline)
    review_mesh = build_feathered_shoulder_mesh(review)
    if canonical_digest(review) != EXPECTED_REVIEW_SOURCE_DIGEST:
        raise ValueError("accepted E repository review source identity drift")
    if canonical_digest(review_mesh) != EXPECTED_REVIEW_MESH_DIGEST:
        raise ValueError("accepted E repository review mesh identity drift")
    return review, review_mesh


def adopted_character_source():
    review, _ = _review_candidate()
    adopted = deepcopy(review)
    adopted["study_id"] = SOURCE_ID
    adopted["intent"] = "stylized_biped_form_study_with_adopted_feathered_shoulder_transition"
    adopted["shoulder_transition_repair"]["status"] = (
        "SOURCE_LINEAGE_ADOPTED_FORM_DIRECTION_NOT_CONNECTED_TOPOLOGY"
    )
    adopted["source_lineage_adoption"] = {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "accepted_review_variant_id": review["shoulder_transition_repair"]["variant_id"],
        "repository_review_source_digest": EXPECTED_REVIEW_SOURCE_DIGEST,
        "repository_review_mesh_digest": EXPECTED_REVIEW_MESH_DIGEST,
        "visual_qa_reconstruction_source_digest": QA_RECONSTRUCTION_SOURCE_DIGEST,
        "visual_qa_reconstruction_mesh_digest": QA_RECONSTRUCTION_MESH_DIGEST,
        "reconstruction_identity_note": "QA source serialization is retained as independent evidence; repository exact-head source digest remains source authority while both paths agree on the proof mesh digest",
        "art_direction": ART_DIRECTION_PACKET,
        "visual_qa_decision": VISUAL_QA_DECISION,
        "migration_policy": "EXACT_FORM_SEMANTICS_NEW_SOURCE_IDENTITY_NO_GEOMETRY_DRIFT",
        "downstream_state": "CONNECTED_TOPOLOGY_AND_DEFORMATION_NOT_ACCEPTED",
    }
    validate_study(adopted)
    return adopted


def build_adopted_character_mesh(source=None):
    source = source or adopted_character_source()
    validate_study(source)
    return build_feathered_shoulder_mesh(source)


def _normalized_back_to_review(adopted):
    normalized = deepcopy(adopted)
    normalized.pop("source_lineage_adoption")
    normalized["study_id"] = normalized["shoulder_transition_repair"]["variant_id"]
    normalized["intent"] = "stylized_biped_form_study_with_feathered_open_shoulder_transitions"
    normalized["shoulder_transition_repair"]["status"] = "DERIVED_REVIEW_VARIANT_NOT_ACCEPTED_SOURCE"
    return normalized


def audit_source_lineage_adoption(source=None):
    review, review_mesh = _review_candidate()
    source = source or adopted_character_source()
    validate_study(source)

    normalized = _normalized_back_to_review(source)
    if canonical_digest(normalized) != EXPECTED_REVIEW_SOURCE_DIGEST:
        raise ValueError("source migration changed accepted E form semantics")

    adoption = source["source_lineage_adoption"]
    if adoption["repository_review_source_digest"] != EXPECTED_REVIEW_SOURCE_DIGEST:
        raise ValueError("source adoption repository review source provenance drift")
    if adoption["repository_review_mesh_digest"] != EXPECTED_REVIEW_MESH_DIGEST:
        raise ValueError("source adoption repository review mesh provenance drift")
    if adoption["visual_qa_reconstruction_source_digest"] != QA_RECONSTRUCTION_SOURCE_DIGEST:
        raise ValueError("source adoption QA reconstruction source provenance drift")
    if adoption["visual_qa_reconstruction_mesh_digest"] != QA_RECONSTRUCTION_MESH_DIGEST:
        raise ValueError("source adoption QA reconstruction mesh provenance drift")
    if adoption["art_direction"] != ART_DIRECTION_PACKET:
        raise ValueError("source adoption art-direction provenance drift")
    if adoption["visual_qa_decision"] != VISUAL_QA_DECISION:
        raise ValueError("source adoption visual-QA provenance drift")

    review_audit = audit_feathered_shoulder(review)
    if review_audit["status"] != "PASS_BOUNDED_FEATHERED_SHOULDER_TRANSITION_CANDIDATE":
        raise ValueError("accepted E prerequisite no longer passes its bounded structural audit")

    adopted_mesh = build_adopted_character_mesh(source)
    review_checks = mesh_checks(review_mesh)
    adopted_checks = mesh_checks(adopted_mesh)
    review_mesh_digest = canonical_digest(review_mesh)
    adopted_mesh_digest = canonical_digest(adopted_mesh)
    if review_mesh_digest != EXPECTED_REVIEW_MESH_DIGEST:
        raise ValueError("accepted E review mesh changed during adoption audit")
    if adopted_mesh_digest != review_mesh_digest:
        raise ValueError("source migration changed accepted E proof geometry")
    if adopted_checks != review_checks:
        raise ValueError("source migration changed accepted E mesh checks")

    source_digest = canonical_digest(source)
    if source_digest == EXPECTED_REVIEW_SOURCE_DIGEST:
        raise ValueError("source migration failed to create a distinct source identity")

    transition = source["shoulder_transition_repair"]
    if transition["root_ring_indices"] != list(ROOT_RING_INDICES):
        raise ValueError("adopted root-ring selection drift")
    if transition["blend_weights"] != list(BLEND_WEIGHTS):
        raise ValueError("adopted feather weights drift")
    if transition["target_axis_scale"] != list(TARGET_AXIS_SCALE):
        raise ValueError("adopted target-axis scale drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_id": SOURCE_ID,
        "accepted_review_variant_id": review["shoulder_transition_repair"]["variant_id"],
        "repository_review_source_digest": EXPECTED_REVIEW_SOURCE_DIGEST,
        "repository_review_mesh_digest": EXPECTED_REVIEW_MESH_DIGEST,
        "visual_qa_reconstruction_source_digest": QA_RECONSTRUCTION_SOURCE_DIGEST,
        "visual_qa_reconstruction_mesh_digest": QA_RECONSTRUCTION_MESH_DIGEST,
        "adopted_source_digest": source_digest,
        "adopted_mesh_digest": adopted_mesh_digest,
        "form_metrics": adopted_checks,
        "preserved_transition_semantics": {
            "root_ring_indices": list(ROOT_RING_INDICES),
            "blend_weights": list(BLEND_WEIGHTS),
            "target_axis_scale": list(TARGET_AXIS_SCALE),
            "anchor_radius_reference_m": transition["anchor_radius_reference_m"],
            "upper_arm_root_radius_reference_m": transition["upper_arm_root_radius_reference_m"],
        },
        "gates": {
            "repository-review-source-identity-pinned": "PASS",
            "repository-review-mesh-identity-pinned": "PASS",
            "QA-reconstruction-provenance-kept-distinct": "PASS",
            "repository-and-QA-review-mesh-agree": "PASS",
            "art-direction-provenance-pinned": "PASS",
            "visual-qa-decision-pinned": "PASS",
            "accepted-E-structural-audit-replayed": "PASS",
            "adopted-source-identity-distinct": "PASS",
            "accepted-E-form-semantics-preserved": "PASS",
            "accepted-E-proof-mesh-byte-semantics-preserved": "PASS",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
            "target-host-or-runtime-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "this migrates the already accepted E shoulder form direction into a distinct Character source-lineage identity without changing the accepted proof geometry",
            "repository exact-head source identity and independent QA reconstruction source identity are deliberately kept distinct; they agree on the accepted E proof mesh identity",
            "the retained 0.085 m anchor-radius reference, 0.075 m upper-arm-root reference, eight-sample open saddle, feather weights and target-axis scale are preserved exactly",
            "the migrated proof mesh remains disconnected low-resolution evidence and is not connected production topology",
            "no anatomy/biology, rigging, weighting, deformation, materials, target-engine, Armor/Unit fit, runtime, gameplay, CANON, production readiness, or Organic Form mastery claim",
        ],
    }


def build_source_lineage_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = adopted_character_source()
    mesh = build_adopted_character_mesh(source)
    receipt = audit_source_lineage_adoption(source)

    (out / "shoulder-source-lineage.source.json").write_text(
        json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-source-lineage.mesh.json").write_text(
        json.dumps(mesh, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8"
    )
    write_obj(mesh, out / "shoulder-source-lineage.obj")
    (out / "shoulder-source-lineage-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
