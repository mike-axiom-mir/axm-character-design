extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_current_target_shaded_motion_reference_payload.json"
const TECHNICAL_ART_RECEIPT_PATH := "res://generated/technical-art-target-normal-proof/character-review006-target-engine-direction-frame-hypothesis-runtime-receipt.json"
const RECEIPT_PATH := "res://character-review006-current-target-shaded-motion-reference-runtime-receipt.json"
const SAMPLE_KEYS := ["80", "160", "240"]
const DEFORMED_KEYS := ["80", "240"]
const CONTEXTS := ["front", "three_quarter", "grazing"]
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.055, 0.06, 0.07, 1.0)

var payload: Dictionary = {}
var technical_art_receipt: Dictionary = {}
var captured: Dictionary = {}

func read_json(path: String) -> Dictionary:
    var f := FileAccess.open(path, FileAccess.READ)
    if f == null:
        return {}
    var parsed = JSON.parse_string(f.get_as_text())
    f.close()
    return parsed as Dictionary if parsed is Dictionary else {}

func write_receipt(data: Dictionary) -> void:
    var f := FileAccess.open(RECEIPT_PATH, FileAccess.WRITE)
    if f != null:
        f.store_string(JSON.stringify(data, "  ") + "\n")
        f.close()

func fail(message: String) -> void:
    write_receipt({
        "schema": "axm.character-review006-current-target-shaded-motion-reference-runtime/v0.3",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    })
    push_error(message)
    quit(1)

func to_v3(raw: Array) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func make_material(unshaded: bool) -> StandardMaterial3D:
    var spec: Dictionary = payload["contract"]["material"]
    var c: Array = spec["albedo_srgb"]
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(float(c[0]), float(c[1]), float(c[2]), 1.0)
    mat.metallic = float(spec["metallic"])
    mat.roughness = float(spec["roughness"])
    mat.cull_mode = BaseMaterial3D.CULL_BACK
    if unshaded:
        mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    return mat

func add_lighting(root3d: Node3D) -> void:
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = BACKGROUND
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color(0.55, 0.58, 0.62, 1.0)
    env.ambient_light_energy = 0.45
    var world_env := WorldEnvironment.new()
    world_env.environment = env
    root3d.add_child(world_env)

    var key := DirectionalLight3D.new()
    key.light_color = Color(1.0, 0.92, 0.82, 1.0)
    key.light_energy = 2.2
    key.rotation_degrees = Vector3(-42.0, -28.0, 0.0)
    key.shadow_enabled = true
    root3d.add_child(key)

    var fill := DirectionalLight3D.new()
    fill.light_color = Color(0.58, 0.70, 1.0, 1.0)
    fill.light_energy = 0.65
    fill.rotation_degrees = Vector3(-15.0, 145.0, 0.0)
    root3d.add_child(fill)

func configure_camera(camera: Camera3D, sample_key: String, context: String) -> void:
    var b: Dictionary = payload["samples"][sample_key]["camera_bounds"]
    var center := to_v3(b["center"])
    var extent := to_v3(b["extent"])
    var radius := maxf(0.22, maxf(extent.x, maxf(extent.y, extent.z)))
    var d := radius * 3.2
    if context == "front":
        camera.position = center + Vector3(0.0, radius * 0.12, d)
    elif context == "three_quarter":
        camera.position = center + Vector3(d * 0.58, radius * 0.28, d * 0.82)
    else:
        camera.position = center + Vector3(d * 0.96, radius * 0.18, d * 0.30)
    camera.fov = 34.0
    camera.near = 0.01
    camera.far = 20.0
    camera.look_at_from_position(camera.position, center, Vector3.UP)

func collect_meshes(node: Node, out: Array) -> void:
    if node is MeshInstance3D:
        out.append(node)
    for child in node.get_children():
        collect_meshes(child, out)

func find_animation_player(node: Node) -> AnimationPlayer:
    if node is AnimationPlayer:
        return node as AnimationPlayer
    for child in node.get_children():
        var found := find_animation_player(child)
        if found != null:
            return found
    return null

func instantiate_target() -> Node:
    var doc := GLTFDocument.new()
    var state := GLTFState.new()
    var err := doc.append_from_file("res://%s" % payload["target"]["glb_path"], state)
    if err != OK:
        return null
    return doc.generate_scene(state)

func seek_target(target_scene: Node, sample_key: String) -> Dictionary:
    var player := find_animation_player(target_scene)
    if player == null:
        return {"state": "FAIL_ANIMATION_PLAYER_MISSING"}
    var clip := String(payload["target"]["clip_id"])
    if not player.has_animation(clip):
        return {"state": "FAIL_CLIP_MISSING", "clips": Array(player.get_animation_list())}
    player.play(clip)
    player.seek(float(payload["samples"][sample_key]["time_s"]), true)
    player.advance(0.0)
    player.pause()
    return {"state": "PASS"}

func build_world(sample_key: String, context: String, unshaded: bool) -> Dictionary:
    var viewport := SubViewport.new()
    viewport.size = FRAME_SIZE
    viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
    viewport.transparent_bg = false
    viewport.world_3d = World3D.new()
    get_root().add_child(viewport)

    var root3d := Node3D.new()
    viewport.add_child(root3d)
    add_lighting(root3d)

    var target_scene := instantiate_target()
    if target_scene == null:
        viewport.queue_free()
        return {"state": "FAIL_GLTF_IMPORT"}
    root3d.add_child(target_scene)
    var meshes: Array = []
    collect_meshes(target_scene, meshes)
    if meshes.size() != 1:
        viewport.queue_free()
        return {"state": "FAIL_TARGET_MESH_COUNT", "mesh_count": meshes.size()}
    var mat := make_material(unshaded)
    for mesh_instance in meshes:
        mesh_instance.material_override = mat
    var seek := seek_target(target_scene, sample_key)
    if seek.get("state") != "PASS":
        viewport.queue_free()
        return seek

    var camera := Camera3D.new()
    configure_camera(camera, sample_key, context)
    root3d.add_child(camera)
    camera.current = true
    return {"state": "PASS", "viewport": viewport}

func capture(sample_key: String, context: String, variant: String) -> Dictionary:
    var unshaded := variant == "target_unshaded"
    var built := build_world(sample_key, context, unshaded)
    if built.get("state") != "PASS":
        return built
    var viewport: SubViewport = built["viewport"]
    await process_frame
    await process_frame
    await RenderingServer.frame_post_draw
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        viewport.queue_free()
        return {"state": "FAIL_EMPTY_IMAGE"}
    var path := "res://character-review006-current-target-shaded-motion-reference-%s-%s-%s.png" % [sample_key, context, variant]
    var err := image.save_png(path)
    viewport.queue_free()
    await process_frame
    return {"state": "PASS" if err == OK else "FAIL_SAVE", "image": image, "path": path}

func is_foreground(c: Color) -> bool:
    return maxf(absf(c.r - BACKGROUND.r), maxf(absf(c.g - BACKGROUND.g), absf(c.b - BACKGROUND.b))) > 0.08

func foreground_count(image: Image) -> int:
    var count := 0
    for y in range(image.get_height()):
        for x in range(image.get_width()):
            if is_foreground(image.get_pixel(x, y)):
                count += 1
    return count

func masked_diff(a: Image, b: Image) -> Dictionary:
    var changed_gt_1lsb := 0
    var max_delta := 0.0
    var sum_delta := 0.0
    var masked_pixels := 0
    for y in range(a.get_height()):
        for x in range(a.get_width()):
            var ca := a.get_pixel(x, y)
            var cb := b.get_pixel(x, y)
            if not (is_foreground(ca) or is_foreground(cb)):
                continue
            masked_pixels += 1
            var dr := absf(ca.r - cb.r)
            var dg := absf(ca.g - cb.g)
            var db := absf(ca.b - cb.b)
            var d := maxf(dr, maxf(dg, db))
            if d > (1.0 / 255.0 + 0.0000001):
                changed_gt_1lsb += 1
            max_delta = maxf(max_delta, d)
            sum_delta += (dr + dg + db) / 3.0
    return {
        "masked_pixels": masked_pixels,
        "changed_pixels_gt_1lsb": changed_gt_1lsb,
        "max_rgb_channel_delta": max_delta,
        "mean_abs_rgb_channel_delta": sum_delta / float(maxi(1, masked_pixels))
    }

func technical_art_gate() -> Dictionary:
    if technical_art_receipt.get("state") != "PASS_DIAGNOSTIC":
        return {"state": "FAIL", "reason": "Technical Art diagnostic receipt is not PASS_DIAGNOSTIC"}
    var expected := String(payload["exact_identity"]["technical_art_expected_result"])
    if technical_art_receipt.get("result") != expected:
        return {"state": "FAIL", "reason": "Technical Art direction-frame result drift"}
    if int(technical_art_receipt.get("linear_beats_inverse_count", -1)) != 6:
        return {"state": "FAIL", "reason": "Technical Art six-of-six signed ordering missing"}
    if float(technical_art_receipt.get("minimum_linear_to_nonrig_separation_ratio", 0.0)) < 100.0:
        return {"state": "FAIL", "reason": "Technical Art non-Rigging separation gate missing"}
    if bool(technical_art_receipt.get("truth_boundary", {}).get("godot_skinning_implementation_claim", true)):
        return {"state": "FAIL", "reason": "Technical Art truth boundary widened into implementation claim"}
    return {
        "state": "PASS",
        "result": technical_art_receipt["result"],
        "linear_beats_inverse_count": technical_art_receipt["linear_beats_inverse_count"],
        "minimum_linear_to_nonrig_separation_ratio": technical_art_receipt["minimum_linear_to_nonrig_separation_ratio"],
        "maximum_linear_mean_abs_rgb_channel_delta": technical_art_receipt.get("maximum_linear_mean_abs_rgb_channel_delta"),
        "implementation_claim": false
    }

func _initialize() -> void:
    payload = read_json(PAYLOAD_PATH)
    technical_art_receipt = read_json(TECHNICAL_ART_RECEIPT_PATH)
    if payload.get("schema") != "axm.character-review006-current-target-shaded-motion-reference-payload/v0.3":
        fail("missing or invalid current-target shaded-motion payload")
        return
    if technical_art_receipt.is_empty():
        fail("missing exact Technical Art target-normal receipt")
        return
    call_deferred("run_observer")

func run_observer() -> void:
    var ta_gate := technical_art_gate()
    if ta_gate.get("state") != "PASS":
        fail("Technical Art direction-frame gate failed: %s" % JSON.stringify(ta_gate))
        return

    for sample_key in SAMPLE_KEYS:
        captured[sample_key] = {}
        for context in CONTEXTS:
            captured[sample_key][context] = {}
            for variant in ["target_shaded", "target_unshaded"]:
                var row := await capture(sample_key, context, variant)
                if row.get("state") != "PASS":
                    fail("capture failed for %s/%s/%s: %s" % [sample_key, context, variant, JSON.stringify(row)])
                    return
                captured[sample_key][context][variant] = row["image"]

    var classification: Dictionary = payload["contract"]["classification"]
    var min_foreground := int(classification["minimum_foreground_pixels_per_frame"])
    var min_light_delta := int(classification["minimum_shaded_vs_unshaded_changed_pixels_gt_1lsb"])
    var min_motion_delta := int(classification["minimum_motion_changed_pixels_gt_1lsb"])
    var frames := {}
    var light_gate_ok := true
    var foreground_gate_ok := true

    for sample_key in SAMPLE_KEYS:
        frames[sample_key] = {}
        for context in CONTEXTS:
            var shaded: Image = captured[sample_key][context]["target_shaded"]
            var unshaded: Image = captured[sample_key][context]["target_unshaded"]
            var foreground := foreground_count(unshaded)
            var light_diff := masked_diff(shaded, unshaded)
            foreground_gate_ok = foreground_gate_ok and foreground >= min_foreground
            light_gate_ok = light_gate_ok and int(light_diff["changed_pixels_gt_1lsb"]) >= min_light_delta
            frames[sample_key][context] = {
                "foreground_pixels": foreground,
                "shaded_vs_unshaded": light_diff
            }

    var motion := {}
    var motion_gate_ok := true
    for sample_key in DEFORMED_KEYS:
        motion[sample_key] = {}
        for context in CONTEXTS:
            var deformed: Image = captured[sample_key][context]["target_shaded"]
            var neutral: Image = captured["160"][context]["target_shaded"]
            var diff := masked_diff(deformed, neutral)
            motion_gate_ok = motion_gate_ok and int(diff["changed_pixels_gt_1lsb"]) >= min_motion_delta
            motion[sample_key][context] = diff

    var renderer := {
        "godot_version": Engine.get_version_info(),
        "rendering_method": ProjectSettings.get_setting("rendering/renderer/rendering_method", "unknown"),
        "frame_size": [FRAME_SIZE.x, FRAME_SIZE.y]
    }

    var all_gates := foreground_gate_ok and light_gate_ok and motion_gate_ok
    var result := "PASS_CHARACTER_REVIEW006_CURRENT_TARGET_SHADED_MOTION_REFERENCE_PACK__DIRECTION_FRAME_PROVEN_SEPARATELY" if all_gates else "HOLD_CHARACTER_REVIEW006_CURRENT_TARGET_SHADED_MOTION_REFERENCE_PACK__RENDER_VISIBILITY_GATE_FAILED"
    var receipt := {
        "schema": "axm.character-review006-current-target-shaded-motion-reference-runtime/v0.3",
        "state": "PASS_DIAGNOSTIC",
        "result": result,
        "technical_art_direction_frame_gate": ta_gate,
        "frames": frames,
        "motion_vs_neutral": motion,
        "gates": {
            "foreground_gate": foreground_gate_ok,
            "ordinary_lighting_response_gate": light_gate_ok,
            "motion_visibility_gate": motion_gate_ok
        },
        "renderer": renderer,
        "truth_boundary": payload["truth_boundary"],
        "promotion_effect": "LOOKDEV_REFERENCE_PACK_ONLY__NO_FINAL_ART_OR_QA_ACCEPTANCE"
    }
    write_receipt(receipt)
    print(JSON.stringify(receipt, "  "))
    quit(0 if all_gates else 2)
