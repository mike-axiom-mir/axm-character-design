extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_current_motion_host_equivalent_direction_frame_payload.json"
const RECEIPT_PATH := "res://character-review006-current-motion-host-equivalent-direction-frame-runtime-receipt.json"
const SAMPLE_KEYS := ["80", "160", "240"]
const DEFORMED_KEYS := ["80", "240"]
const CONTEXTS := ["front", "three_quarter", "grazing"]
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.055, 0.06, 0.07, 1.0)
const POSITION_CONTROL_MAX_XOR_FRACTION := 0.0005
const NEUTRAL_ADAPTED_MAX_MEAN_DELTA := 0.002

var payload: Dictionary = {}

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
        "schema": "axm.character-review006-current-motion-host-equivalent-direction-frame-runtime/v0.2",
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

func build_reference_mesh(sample_key: String, normal_mode: String, adapted: bool, invert_normals: bool = false) -> ArrayMesh:
    var ref: Dictionary = payload["samples"][sample_key]["reference"]
    var raw_positions: Array = ref["positions"]
    var raw_normals: Array = ref["pose_recomputed_normals"] if normal_mode == "pose" else ref["frozen_neutral_normals"]
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var indices := PackedInt32Array()
    for raw in raw_positions:
        vertices.append(to_v3(raw))
    for raw in raw_normals:
        var n := to_v3(raw).normalized()
        normals.append(-n if invert_normals else n)
    var face_key := "receiver_winding_faces" if adapted else "owner_faces"
    for raw_face in ref[face_key]:
        var face: Array = raw_face
        indices.append(int(face[0]))
        indices.append(int(face[1]))
        indices.append(int(face[2]))
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = vertices
    arrays[Mesh.ARRAY_NORMAL] = normals
    arrays[Mesh.ARRAY_INDEX] = indices
    var mesh := ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    return mesh

func sample_bounds(sample_key: String) -> Dictionary:
    var raw_positions: Array = payload["samples"][sample_key]["reference"]["positions"]
    var mn := Vector3(INF, INF, INF)
    var mx := Vector3(-INF, -INF, -INF)
    for raw in raw_positions:
        var p := to_v3(raw)
        mn.x = minf(mn.x, p.x)
        mn.y = minf(mn.y, p.y)
        mn.z = minf(mn.z, p.z)
        mx.x = maxf(mx.x, p.x)
        mx.y = maxf(mx.y, p.y)
        mx.z = maxf(mx.z, p.z)
    return {"min": mn, "max": mx, "center": (mn + mx) * 0.5, "extent": mx - mn}

func configure_camera(camera: Camera3D, sample_key: String, context: String) -> void:
    var b := sample_bounds(sample_key)
    var center: Vector3 = b["center"]
    var extent: Vector3 = b["extent"]
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

func build_world(sample_key: String, context: String, variant: String) -> Dictionary:
    var viewport := SubViewport.new()
    viewport.size = FRAME_SIZE
    viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
    viewport.transparent_bg = false
    viewport.world_3d = World3D.new()
    get_root().add_child(viewport)
    var root3d := Node3D.new()
    viewport.add_child(root3d)
    add_lighting(root3d)
    var unshaded := variant.ends_with("_unshaded")
    var mat := make_material(unshaded)
    if variant.begins_with("target_"):
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
        for mesh_instance in meshes:
            mesh_instance.material_override = mat
        var seek := seek_target(target_scene, sample_key)
        if seek.get("state") != "PASS":
            viewport.queue_free()
            return seek
    else:
        var normal_mode := "frozen" if variant.begins_with("frozen_") else "pose"
        var adapted := not variant.begins_with("pose_native_")
        var inverted := variant.begins_with("pose_adapted_inverted_")
        var instance := MeshInstance3D.new()
        instance.mesh = build_reference_mesh(sample_key, normal_mode, adapted, inverted)
        instance.material_override = mat
        root3d.add_child(instance)
    var camera := Camera3D.new()
    configure_camera(camera, sample_key, context)
    root3d.add_child(camera)
    camera.current = true
    return {"state": "PASS", "viewport": viewport}

func capture(sample_key: String, context: String, variant: String) -> Dictionary:
    var built := build_world(sample_key, context, variant)
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
    var path := "res://character-review006-current-motion-host-equivalent-%s-%s-%s.png" % [sample_key, context, variant]
    var err := image.save_png(path)
    viewport.queue_free()
    await process_frame
    return {"state": "PASS" if err == OK else "FAIL_SAVE", "image": image, "path": path}

func is_foreground(c: Color) -> bool:
    return maxf(absf(c.r - BACKGROUND.r), maxf(absf(c.g - BACKGROUND.g), absf(c.b - BACKGROUND.b))) > 0.08

func coverage_xor(a: Image, b: Image) -> Dictionary:
    var xor_pixels := 0
    var union_pixels := 0
    var total := a.get_width() * a.get_height()
    for y in range(a.get_height()):
        for x in range(a.get_width()):
            var fa := is_foreground(a.get_pixel(x, y))
            var fb := is_foreground(b.get_pixel(x, y))
            if fa or fb:
                union_pixels += 1
            if fa != fb:
                xor_pixels += 1
    return {
        "xor_pixels": xor_pixels,
        "union_foreground_pixels": union_pixels,
        "frame_fraction": float(xor_pixels) / float(total),
        "union_fraction": float(xor_pixels) / float(maxi(1, union_pixels))
    }

func masked_diff(a: Image, b: Image, mask_a: Image, mask_b: Image) -> Dictionary:
    var changed_gt_1lsb := 0
    var max_delta := 0.0
    var sum_delta := 0.0
    var masked_pixels := 0
    for y in range(a.get_height()):
        for x in range(a.get_width()):
            if not (is_foreground(mask_a.get_pixel(x, y)) or is_foreground(mask_b.get_pixel(x, y))):
                continue
            masked_pixels += 1
            var ca := a.get_pixel(x, y)
            var cb := b.get_pixel(x, y)
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

func flat_indices(raw_faces: Array) -> Array:
    var result: Array = []
    for raw_face in raw_faces:
        var face: Array = raw_face
        result.append(int(face[0]))
        result.append(int(face[1]))
        result.append(int(face[2]))
    return result

func mismatch_count(actual: PackedInt32Array, expected: Array) -> int:
    if actual.size() != expected.size():
        return maxi(actual.size(), expected.size())
    var count := 0
    for i in range(actual.size()):
        if int(actual[i]) != int(expected[i]):
            count += 1
    return count

func raw_neutral_import_audit() -> Dictionary:
    var target_scene := instantiate_target()
    if target_scene == null:
        return {"state": "FAIL_GLTF_IMPORT"}
    get_root().add_child(target_scene)
    var meshes: Array = []
    collect_meshes(target_scene, meshes)
    if meshes.size() != 1:
        target_scene.queue_free()
        return {"state": "FAIL_TARGET_MESH_COUNT", "mesh_count": meshes.size()}
    var imported: MeshInstance3D = meshes[0]
    if imported.mesh == null or imported.mesh.get_surface_count() != 1:
        target_scene.queue_free()
        return {"state": "FAIL_TARGET_SURFACE_COUNT"}
    var arrays: Array = imported.mesh.surface_get_arrays(0)
    var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
    var ref: Dictionary = payload["samples"]["160"]["reference"]
    var owner_flat := flat_indices(ref["owner_faces"])
    var adapted_flat := flat_indices(ref["receiver_winding_faces"])
    var result := {
        "state": "PASS",
        "index_count": indices.size(),
        "triangle_count": int(indices.size() / 3),
        "owner_order_mismatch_count": mismatch_count(indices, owner_flat),
        "receiver_winding_mismatch_count": mismatch_count(indices, adapted_flat),
        "imported_global_transform_basis_determinant": imported.global_transform.basis.determinant()
    }
    target_scene.queue_free()
    return result

func _initialize() -> void:
    payload = read_json(PAYLOAD_PATH)
    if payload.get("schema") != "axm.character-review006-current-motion-host-equivalent-direction-frame-payload/v0.2":
        fail("missing or invalid host-equivalent direction-frame payload")
        return
    if payload["exact_identity"].get("technical_art_bridge_head") != "a61f96d2cf8c33b153d17810ad18ca48074b81d2":
        fail("Technical Art bridge identity drift")
        return
    call_deferred("run_observer")

func run_observer() -> void:
    var audit := raw_neutral_import_audit()
    if audit.get("state") != "PASS":
        fail("neutral import audit failed: %s" % JSON.stringify(audit))
        return
    var exact_bridge := int(audit["triangle_count"]) == 360 and int(audit["owner_order_mismatch_count"]) == 720 and int(audit["receiver_winding_mismatch_count"]) == 0
    var receipt := {
        "schema": "axm.character-review006-current-motion-host-equivalent-direction-frame-runtime/v0.2",
        "state": "PASS_DIAGNOSTIC",
        "renderer": {
            "engine": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": "gl_compatibility",
            "adapter": RenderingServer.get_video_adapter_name(),
            "frame_size": [FRAME_SIZE.x, FRAME_SIZE.y]
        },
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "raw_neutral_import_audit": audit,
        "comparisons": {},
        "position_control_clean_all_contexts": true,
        "neutral_host_equivalent_gate": exact_bridge,
        "native_history_control_visible_all_neutral_contexts": true,
        "inverted_negative_visible_all_contexts": true,
        "deformed_pose_closer_to_recomputed_count": 0,
        "deformed_pose_closer_to_frozen_count": 0,
        "deformed_comparison_count": 0,
        "truth_boundary": payload["truth_boundary"]
    }
    for sample_key in SAMPLE_KEYS:
        receipt["comparisons"][sample_key] = {}
        for context in CONTEXTS:
            var captures := {}
            for variant in [
                "target_unshaded",
                "pose_adapted_unshaded",
                "target_shaded",
                "pose_adapted_shaded",
                "frozen_adapted_shaded",
                "pose_native_shaded",
                "pose_adapted_inverted_shaded"
            ]:
                var cap := await capture(sample_key, context, variant)
                if cap.get("state") != "PASS":
                    fail("capture failed: %s/%s/%s -> %s" % [sample_key, context, variant, str(cap)])
                    return
                captures[variant] = cap
            var coverage := coverage_xor(captures["target_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            if float(coverage["frame_fraction"]) > POSITION_CONTROL_MAX_XOR_FRACTION:
                receipt["position_control_clean_all_contexts"] = false
            var target_to_pose := masked_diff(captures["target_shaded"]["image"], captures["pose_adapted_shaded"]["image"], captures["target_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            var target_to_frozen := masked_diff(captures["target_shaded"]["image"], captures["frozen_adapted_shaded"]["image"], captures["target_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            var pose_to_frozen := masked_diff(captures["pose_adapted_shaded"]["image"], captures["frozen_adapted_shaded"]["image"], captures["pose_adapted_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            var target_to_native := masked_diff(captures["target_shaded"]["image"], captures["pose_native_shaded"]["image"], captures["target_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            var target_to_inverted := masked_diff(captures["target_shaded"]["image"], captures["pose_adapted_inverted_shaded"]["image"], captures["target_unshaded"]["image"], captures["pose_adapted_unshaded"]["image"])
            if sample_key == "160":
                receipt["neutral_host_equivalent_gate"] = bool(receipt["neutral_host_equivalent_gate"]) and float(coverage["frame_fraction"]) <= POSITION_CONTROL_MAX_XOR_FRACTION and float(target_to_pose["mean_abs_rgb_channel_delta"]) <= NEUTRAL_ADAPTED_MAX_MEAN_DELTA
                receipt["native_history_control_visible_all_neutral_contexts"] = bool(receipt["native_history_control_visible_all_neutral_contexts"]) and float(target_to_native["mean_abs_rgb_channel_delta"]) >= 0.05
            receipt["inverted_negative_visible_all_contexts"] = bool(receipt["inverted_negative_visible_all_contexts"]) and int(target_to_inverted["changed_pixels_gt_1lsb"]) > 0
            var relation := "equal_or_unresolved"
            if float(target_to_pose["mean_abs_rgb_channel_delta"]) < float(target_to_frozen["mean_abs_rgb_channel_delta"]):
                relation = "target_closer_to_pose_recomputed"
            elif float(target_to_frozen["mean_abs_rgb_channel_delta"]) < float(target_to_pose["mean_abs_rgb_channel_delta"]):
                relation = "target_closer_to_frozen_neutral"
            if sample_key in DEFORMED_KEYS:
                receipt["deformed_comparison_count"] += 1
                if relation == "target_closer_to_pose_recomputed":
                    receipt["deformed_pose_closer_to_recomputed_count"] += 1
                elif relation == "target_closer_to_frozen_neutral":
                    receipt["deformed_pose_closer_to_frozen_count"] += 1
            receipt["comparisons"][sample_key][context] = {
                "angle_deg": payload["samples"][sample_key]["angle_deg"],
                "time_s": payload["samples"][sample_key]["time_s"],
                "position_control": coverage,
                "target_to_pose_recomputed_host_equivalent": target_to_pose,
                "target_to_frozen_neutral_host_equivalent": target_to_frozen,
                "pose_recomputed_to_frozen_neutral_host_equivalent": pose_to_frozen,
                "target_to_native_owner_order_history_control": target_to_native,
                "target_to_inverted_normal_negative": target_to_inverted,
                "relation": relation
            }
    if not exact_bridge:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_HOST_EQUIVALENT_BRIDGE_DRIFT"
    elif not receipt["position_control_clean_all_contexts"]:
        receipt["result"] = "INCONCLUSIVE_CHARACTER_REVIEW006_HOST_EQUIVALENT_DIRECTION_FRAME__POSITION_CONTROL_MISMATCH"
    elif not receipt["neutral_host_equivalent_gate"]:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_HOST_EQUIVALENT_DIRECTION_FRAME__NEUTRAL_GATE_NOT_CLOSED"
    elif not receipt["inverted_negative_visible_all_contexts"]:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_HOST_EQUIVALENT_DIRECTION_FRAME__OBSERVER_SENSITIVITY_NOT_PROVEN"
    elif int(receipt["deformed_pose_closer_to_recomputed_count"]) == int(receipt["deformed_comparison_count"]):
        receipt["result"] = "PASS_CHARACTER_REVIEW006_TARGET_DIRECTION_FRAME_CLOSER_TO_HOST_EQUIVALENT_POSE_RECOMPUTED_REFERENCE"
    elif int(receipt["deformed_pose_closer_to_frozen_count"]) == int(receipt["deformed_comparison_count"]):
        receipt["result"] = "FAIL_CHARACTER_REVIEW006_TARGET_DIRECTION_FRAME_CLOSER_TO_HOST_EQUIVALENT_FROZEN_NEUTRAL_CONTROL"
    else:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_DIRECTION_FRAME_MIXED_HOST_EQUIVALENT_RESPONSE"
    write_receipt(receipt)
    quit(0)
