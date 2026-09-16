# axm-character-design

Source-owned character form studies for the AXM 3D Studio constellation.

Current bounded lane:

- `character-neutral-a-001`: stylized human-like biped A-rest form study with explicit bilateral landmarks, local mass hierarchy and deformation handoff zones.
- Truth state: `FORM_STUDY_NOT_RIGGED_NOT_ANIMATED`.
- No claim of anatomical/biological correctness, production topology, rigging, animation, materials, runtime readiness, gameplay suitability, CANON or domain mastery.

Build the retained evidence locally:

```bash
PYTHONPATH=src python tools/build_character_baseline.py --out evidence/character-neutral-a-001
python -m unittest discover -s tests -v
```

Generated source, mesh, OBJ and front/side/top SVG evidence are derived from the same exact source function and retained by CI.
