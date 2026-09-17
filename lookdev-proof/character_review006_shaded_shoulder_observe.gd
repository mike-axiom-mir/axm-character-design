extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_shaded_shoulder_payload.json"
const RECEIPT_PATH := "res://character-review006-shaded-shoulder-runtime-receipt.json"
const MODES := ["frozen_neutral_control", "pose_recomputed_candidate", "inverted_pose_negative"]
const POSES := ["-40", "0", "36", "37"]
const SAFE_DEFORMED_POSES := ["-40", "36"]
const CONTEXTS := ["front", "three_quarter", "grazing"]

var payload: Dictionary = {}

func read_json(path: String) -> Dictionary:
    var f := FileAccess.open(path, FileAccess.READ)
    if f == null:
        return {}
    var text := f.get_as_text()
    f.close()
    var parsed = JSON.parse_string(text)
    return parsed as Dictionary if parsed is Dictionary else {}

func write_receipt(data: Dictionary) -> void:
    var f := FileAccess.open(RECEIPT_PATH, FileAccess.WRITE)
    if f != null:
        f.store_string(JSON.stringify(data, "  ") + "\n")
        f.close()

func fail(message: String) -> void:
    write_receipt({
        "schema": "axm.character-review006-shaded-shoulder-runtime/v0.1",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    })
    push_error(message)
    quit(1)

func to_v3(raw: Array) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func build_mesh(side_data: Dictionary, pose_key: String, mode: String) -> ArrayMesh:
    var pose: Dictionary = side_data["poses"][pose_key]
    var raw_positions: Array = pose["positions"]
    var raw_normals: Array
    if mode == "frozen_neutral_control":
        raw_normals = side_data["neutral_smooth_normals"]
    else:
        raw_normals = pose["pose_recomputed_normals"]
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    for i in range(raw_positions.size()):
        vertices.append(to_v3(raw_positions[i]))
        var n := to_v3(raw_normals[i]).normalized()
        if mode == "inverted_pose_negative":
            n = -n
        normals.append(n)
    var indices := PackedInt32Array()
    for raw_face in side_data["faces"]:
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

func make_review_material() -> StandardMaterial3D:
    var spec: Dictionary = payload["review_contract"]["material"]
    var c: Array = spec["albedo_srgb"]
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(float(c[0]), float(c[1]), float(c[2]), 1.0)
    mat.metallic = float(spec["metallic"])
    mat.roughness = float(spec["roughness"])
    mat.cull_mode = BaseMaterial3D.CULL_BACK
    return mat

func pose_bounds(pose_key: String) -> Dictionary:
    var mn := Vector3(INF, INF, INF)
    var mx := Vector3(-INF, -INF, -INF)
    for side in ["L", "R"]:
        var raw_positions: Array = payload["sides"][side]["poses"][pose_key]["positions"]
        for raw in raw_positions:
            var p := to_v3(raw)
            mn.x = minf(mn.x, p.x)
            mn.y = minf(mn.y, p.y)
            mn.z = minf(mn.z, p.z)
            mx.x = maxf(mx.x, p.x)
            mx.y = maxf(mx.y, p.y)
            mx.z = maxf(mx.z, p.z)
    return {"min": mn, "max": mx, "center": (mn + mx) * 0.5, "extent": mx - mn}

func configure_camera(camera: Camera3D, pose_key: String, context: String) -> void:
    var b := pose_bounds(pose_key)
    var center: Vector3 = b["center"]
    var extent: Vector3 = b["extent"]
    var radius := maxf(0.22, maxf(extent.x, maxf(extent.y, extent.z)))
    var d := radius * 3.2
    if context == "front":
        camera.position = center + Vector3(0.0, d, radius * 0.12)
    elif context == "three_quarter":
        camera.position = center + Vector3(d * 0.58, d * 0.82, radius * 0.28)
    else:
        camera.position = center + Vector3(d * 0.96, d * 0.30, radius * 0.18)
    camera.fov = 34.0
    camera.near = 0.01
    camera.far = 20.0
    camera.look_at(center, Vector3.UP)

func build_world(pose_key: String, context: String, mode: String) -> SubViewport:
    var viewport := SubViewport.new()
    viewport.size = Vector2i(900, 700)
    viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
    viewport.transparent_bg = false
    viewport.world_3d = World3D.new()
    get_root().add_child(viewport)

    var root3d := Node3D.new()
    viewport.add_child(root3d)

    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color(0.055, 0.06, 0.07, 1.0)
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

    var mat := make_review_material()
    for side in ["L", "R"]:
        var instance := MeshInstance3D.new()
        instance.mesh = build_mesh(payload["sides"][side], pose_key, mode)
        instance.material_override = mat
        root3d.add_child(instance)

    var camera := Camera3D.new()
    configure_camera(camera, pose_key, context)
    root3d.add_child(camera)
    camera.current = true
    return viewport

func capture(pose_key: String, context: String, mode: String) -> Dictionary:
    var viewport := build_world(pose_key, context, mode)
    await process_frame
    await process_frame
    await RenderingServer.frame_post_draw
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        viewport.queue_free()
        return {"state": "FAIL_EMPTY_IMAGE"}
    var path := "res://character-review006-shaded-%s-%s-%s.png" % [pose_key.replace("-", "m"), context, mode]
    var err := image.save_png(path)
    viewport.queue_free()
    await process_frame
    return {"state": "PASS" if err == OK else "FAIL_SAVE", "image": image, "path": path}

func image_diff(a: Image, b: Image) -> Dictionary:
    if a.get_width() != b.get_width() or a.get_height() != b.get_height():
        return {"state": "FAIL_DIMENSIONS"}
    var changed_raw := 0
    var changed_gt_1lsb := 0
    var max_delta := 0.0
    var sum_delta := 0.0
    var total := a.get_width() * a.get_height()
    for y in range(a.get_height()):
        for x in range(a.get_width()):
            var ca := a.get_pixel(x, y)
            var cb := b.get_pixel(x, y)
            var dr := absf(ca.r - cb.r)
            var dg := absf(ca.g - cb.g)
            var db := absf(ca.b - cb.b)
            var d := maxf(dr, maxf(dg, db))
            if d > 0.0:
                changed_raw += 1
            if d > (1.0 / 255.0 + 0.0000001):
                changed_gt_1lsb += 1
            max_delta = maxf(max_delta, d)
            sum_delta += (dr + dg + db) / 3.0
    return {
        "state": "PASS",
        "total_pixels": total,
        "changed_pixels_raw": changed_raw,
        "changed_pixels_gt_1lsb": changed_gt_1lsb,
        "changed_fraction_gt_1lsb": float(changed_gt_1lsb) / float(total),
        "max_rgb_channel_delta": max_delta,
        "mean_abs_rgb_channel_delta": sum_delta / float(total)
    }

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    payload = read_json(PAYLOAD_PATH)
    if payload.get("schema") != "axm.character-review006-shaded-shoulder-payload/v0.1":
        fail("missing or invalid shaded shoulder payload")
        return
    if payload.get("rigging_parent_head") != "efa48c344f1b8c9e70c4c5dfdbf4a3031dacd777":
        fail("Rigging parent identity drift")
        return
    if payload["receiver"].get("source_positions_or_faces_changed") != false:
        fail("Materials receiver must not rewrite source positions/faces")
        return
    if int(payload["sides"]["L"]["poses"]["37"]["nonadjacent_intersection_pair_count"]) <= 0 or int(payload["sides"]["R"]["poses"]["37"]["nonadjacent_intersection_pair_count"]) <= 0:
        fail("+37 structural failure witness missing")
        return

    var receipt := {
        "schema": "axm.character-review006-shaded-shoulder-runtime/v0.1",
        "state": "PASS",
        "renderer": {
            "engine": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": "gl_compatibility",
            "adapter": RenderingServer.get_video_adapter_name()
        },
        "payload_sha256": payload["payload_sha256"],
        "comparisons": {},
        "neutral_control_exact_all_contexts": true,
        "safe_pose_recomputed_normals_visible_all_contexts": true,
        "negative_control_visible_all_contexts": true,
        "outside_envelope_witness_rendered_only": true,
        "truth_boundary": payload["truth_boundary"]
    }

    for pose_key in POSES:
        receipt["comparisons"][pose_key] = {}
        for context in CONTEXTS:
            var captures := {}
            for mode in MODES:
                var cap := await capture(pose_key, context, mode)
                if cap.get("state") != "PASS":
                    fail("capture failed: %s/%s/%s" % [pose_key, context, mode])
                    return
                captures[mode] = cap
            var frozen_to_candidate := image_diff(captures["frozen_neutral_control"]["image"], captures["pose_recomputed_candidate"]["image"])
            var candidate_to_negative := image_diff(captures["pose_recomputed_candidate"]["image"], captures["inverted_pose_negative"]["image"])
            receipt["comparisons"][pose_key][context] = {
                "frozen_to_pose_recomputed": frozen_to_candidate,
                "candidate_to_inverted_negative": candidate_to_negative
            }
            if pose_key == "0" and int(frozen_to_candidate["changed_pixels_raw"]) != 0:
                receipt["neutral_control_exact_all_contexts"] = false
            if pose_key in SAFE_DEFORMED_POSES and int(frozen_to_candidate["changed_pixels_gt_1lsb"]) <= 0:
                receipt["safe_pose_recomputed_normals_visible_all_contexts"] = false
            if int(candidate_to_negative["changed_pixels_gt_1lsb"]) <= 0:
                receipt["negative_control_visible_all_contexts"] = false

    if not receipt["neutral_control_exact_all_contexts"]:
        receipt["state"] = "FAIL_NEUTRAL_NORMAL_IDENTITY"
    elif not receipt["safe_pose_recomputed_normals_visible_all_contexts"]:
        receipt["state"] = "FAIL_RECOMPUTED_NORMAL_NOT_RENDERER_VISIBLE"
    elif not receipt["negative_control_visible_all_contexts"]:
        receipt["state"] = "FAIL_NEGATIVE_CONTROL_NOT_VISIBLE"
    else:
        receipt["result"] = "PASS_CHARACTER_REVIEW006_POSE_RECOMPUTED_SMOOTH_NORMAL_TARGET_HOST_DIAGNOSTIC"
    write_receipt(receipt)
    quit(0 if receipt["state"] == "PASS" else 1)
