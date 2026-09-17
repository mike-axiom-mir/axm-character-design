extends "res://character_review006_target_host_playback_observe.gd"

# The exact Technical Art transport is sampled at 160 Hz / 321 endpoint-inclusive keys.
# GLTFDocument.generate_scene() otherwise rebakes at its default 30 Hz, which produced
# 61 imported keys over this 2 s clip and invalidated the exact-density witness.
const EXACT_TRANSPORT_BAKE_FPS := 160.0

func import_target() -> Node3D:
    var document := GLTFDocument.new()
    var state := GLTFState.new()
    var error := document.append_from_file(GLB_PATH, state)
    if error != OK:
        fail("GLTFDocument append_from_file failed: " + str(error))
        return null
    var generated = document.generate_scene(state, EXACT_TRANSPORT_BAKE_FPS, false, true)
    if generated == null or not (generated is Node3D):
        fail("GLTFDocument generate_scene returned no Node3D at exact 160 Hz transport bake")
        return null
    return generated as Node3D
