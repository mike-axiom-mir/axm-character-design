# axm-character-design

Source-owned character form studies for the AXM 3D Studio constellation.

Current bounded lane:

- `character-neutral-a-001`: stylized human-like biped A-rest baseline with explicit bilateral landmarks, local mass hierarchy and deformation handoff zones.
- `character-neutral-a-shoulder-transition-feathered-003`: retained review candidate that removed the prior complete mechanical-collar shoulder read under independent QA + Art Direction review.
- `character-neutral-a-shoulder-source-004`: exact source-lineage adoption of the accepted E transition semantics. It preserves the E proof mesh exactly while creating a distinct source/provenance identity for downstream Geometry.
- Truth state remains bounded: source/form direction only; connected production topology, rigging, deformation, materials, runtime and gameplay are not accepted.
- No claim of anatomical/biological correctness, CANON, production readiness or domain mastery.

Build the retained evidence locally:

```bash
PYTHONPATH=src python tools/build_character_baseline.py --out evidence/character-neutral-a-001
PYTHONPATH=src python tools/build_shoulder_source_lineage.py --out evidence/character-neutral-a-001
PYTHONPATH=src python -m unittest discover -s tests -v
```

The source-lineage adoption fails closed unless the exact accepted E source digest and exact E mesh digest are reproduced first. Its adopted source identity is intentionally new, while its proof mesh digest remains exactly equal to E so migration cannot silently reshape the accepted form. Generated evidence is retained by CI.
