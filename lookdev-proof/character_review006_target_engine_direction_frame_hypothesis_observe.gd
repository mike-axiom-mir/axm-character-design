extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_target_engine_direction_frame_hypothesis_payload.json"
const RECEIPT_PATH := "res://character-review006-target-engine-direction-frame-hypothesis-runtime-receipt.json"
const SAMPLE_KEYS := ["80", "160", "240"]
const DEFORMED_KEYS := ["80", "240"]
const CONTEXTS := ["front", "three_quarter", "grazing"]
const HYPOTHESES := ["linear_gradient", "inverse_transpose", "pose_recomputed", "frozen_neutral"]
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.035, 0.04, 0.05, 1.0)
const POSITION_CONTROL_MAX_XOR_FRACTION := 0.0005
const NEUTRAL_NORMAL_MAX_MEAN_DELTA := 0.002
const COHERENT_HYPOTHESIS_MAX_MEAN_DELTA := 0.002
const MIN_NONRIG_SEPARATION_RATIO := 100.0

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
        "schema": "axm.character-review006-target-engine-direction-frame-hypothesis-runtime/v0.1",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    })
    push_error(message)
    quit(1)

func to_v3(raw: Array) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func make_position_material() -> StandardMaterial3D:
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.8, 0.8, 0.8, 1.0)
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.cull_mode = BaseMaterial3D.CULL_BACK
    return mat

func make_normal_material() -> ShaderMaterial:
    var shader := Shader.new()
    shader.code = """
shader_type spatial;
render_mode unshaded;

void fragment() {
    vec3 n = normalize(NORMAL);
    ALBEDO = n * 0.5 + vec3(0.5);
}
"""
    var mat := ShaderMaterial.new()
    mat.shader = shader
    return mat

func build_reference_mesh(sample_key: String, normal_mode: String, invert_normals: bool = false) -> ArrayMesh:
    var ref: Dictionary = payload["samples"][sample_key]["reference"]
    var raw_positions: Array = ref["positions"]
    var raw_normals: Array = ref["normals"][normal_mode]
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var indices := PackedInt32Array()
    for raw in raw_positions:
        vertices.append(to_v3(raw))
    for raw in raw_normals:
        var n := to_v3(raw).normalized()
        normals.append(-n if invert_normals else n)
    for raw_face in ref["receiver_winding_faces"]:
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
    return {"center": (mn + mx) * 0.5, "extent": mx - mn}

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

func configure_environment(root3d: Node3D) -> void:
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = BACKGROUND
    var world_env := WorldEnvironment.new()
    world_env.environment = env
    root3d.add_child(world_env)

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
        return {"state": "FAIL_CLIP_MISSING", "clips": Array(player.get_animation_list()), "wanted": clip}
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
    configure_environment(root3d)
    var normal_probe := not variant.ends_with("_position")
    var material: Material = make_normal_material() if normal_probe else make_position_material()
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
            mesh_instance.material_override = material
        var seek := seek_target(target_scene, sample_key)
        if seek.get("state") != "PASS":
            viewport.queue_free()
            return seek
    else:
        var normal_mode := "linear_gradient"
        if variant.begins_with("inverse_transpose_"):
            normal_mode = "inverse_transpose"
        elif variant.begins_with("pose_recomputed_"):
            normal_mode = "pose_recomputed"
        elif variant.begins_with("frozen_neutral_"):
            normal_mode = "frozen_neutral"
        var invert_normals := variant.begins_with("inverted_linear_")
        var instance := MeshInstance3D.new()
        instance.mesh = build_reference_mesh(sample_key, normal_mode, invert_normals)
        instance.material_override = material
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
    var path := "res://character-review006-target-engine-direction-frame-%s-%s-%s.png" % [sample_key, context, variant]
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

func interior_diff(a: Image, b: Image, mask_a: Image, mask_b: Image) -> Dictionary:
    var changed_gt_1lsb := 0
    var max_delta := 0.0
    var sum_delta := 0.0
    var masked_pixels := 0
    for y in range(a.get_height()):
        for x in range(a.get_width()):
            if not (is_foreground(mask_a.get_pixel(x, y)) and is_foreground(mask_b.get_pixel(x, y))):
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

func choose_winner(rows: Dictionary) -> Dictionary:
    var ordered: Array = []
    for name in HYPOTHESES:
        ordered.append({"name": name, "mean": float(rows[name]["mean_abs_rgb_channel_delta"])})
    ordered.sort_custom(func(a, b): return float(a["mean"]) < float(b["mean"]))
    var best: Dictionary = ordered[0]
    var second: Dictionary = ordered[1]
    var margin := float(second["mean"]) - float(best["mean"])
    # The retained normal probe is encoded through an 8-bit render target. The
    # two Rigging-derived hypotheses differ by less than one display LSB in
    # source-vector space, so an arbitrary per-view absolute winner margin
    # would erase a repeatable ordering. Keep the classifier fail-closed on
    # ties, require the selected hypothesis to be independently close, and let
    # the run-level gate require the same signed relation in every deformed
    # view plus a large separation from non-rig controls.
    var coherent := margin > 0.0 and float(best["mean"]) <= COHERENT_HYPOTHESIS_MAX_MEAN_DELTA
    return {
        "winner": String(best["name"]) if coherent else "unresolved",
        "best_mean_abs_rgb_channel_delta": float(best["mean"]),
        "second_best_mean_abs_rgb_channel_delta": float(second["mean"]),
        "winner_margin": margin,
        "coherent_under_bound": coherent
    }

func _initialize() -> void:
    payload = read_json(PAYLOAD_PATH)
    if payload.get("schema") != "axm.character-review006-target-engine-direction-frame-hypothesis/v0.1":
        fail("missing or invalid target-engine direction-frame hypothesis payload")
        return
    call_deferred("run_observer")

func run_observer() -> void:
    var receipt := {
        "schema": "axm.character-review006-target-engine-direction-frame-hypothesis-runtime/v0.1",
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
        "comparisons": {},
        "position_control_clean_all_contexts": true,
        "neutral_gate": true,
        "inverted_negative_visible_all_deformed_contexts": true,
        "deformed_winner_counts": {
            "linear_gradient": 0,
            "inverse_transpose": 0,
            "pose_recomputed": 0,
            "frozen_neutral": 0,
            "unresolved": 0
        },
        "deformed_comparison_count": 0,
        "linear_beats_inverse_count": 0,
        "minimum_linear_to_nonrig_separation_ratio": INF,
        "maximum_linear_mean_abs_rgb_channel_delta": 0.0,
        "truth_boundary": payload["truth_boundary"]
    }
    for sample_key in SAMPLE_KEYS:
        receipt["comparisons"][sample_key] = {}
        for context in CONTEXTS:
            var captures := {}
            for variant in [
                "target_position",
                "linear_gradient_position",
                "target_normal",
                "linear_gradient_normal",
                "inverse_transpose_normal",
                "pose_recomputed_normal",
                "frozen_neutral_normal",
                "inverted_linear_normal"
            ]:
                var cap := await capture(sample_key, context, variant)
                if cap.get("state") != "PASS":
                    fail("capture failed: %s/%s/%s -> %s" % [sample_key, context, variant, str(cap)])
                    return
                captures[variant] = cap
            var coverage := coverage_xor(captures["target_position"]["image"], captures["linear_gradient_position"]["image"])
            if float(coverage["frame_fraction"]) > POSITION_CONTROL_MAX_XOR_FRACTION:
                receipt["position_control_clean_all_contexts"] = false
            var diffs := {}
            for hypothesis in HYPOTHESES:
                var variant := "%s_normal" % hypothesis
                diffs[hypothesis] = interior_diff(
                    captures["target_normal"]["image"],
                    captures[variant]["image"],
                    captures["target_position"]["image"],
                    captures["linear_gradient_position"]["image"]
                )
            var inverted := interior_diff(
                captures["target_normal"]["image"],
                captures["inverted_linear_normal"]["image"],
                captures["target_position"]["image"],
                captures["linear_gradient_position"]["image"]
            )
            if sample_key in DEFORMED_KEYS and int(inverted["changed_pixels_gt_1lsb"]) <= 0:
                receipt["inverted_negative_visible_all_deformed_contexts"] = false
            var winner := choose_winner(diffs)
            if sample_key in DEFORMED_KEYS:
                receipt["deformed_comparison_count"] += 1
                var winner_name := String(winner["winner"])
                receipt["deformed_winner_counts"][winner_name] = int(receipt["deformed_winner_counts"][winner_name]) + 1
                var linear_mean := float(diffs["linear_gradient"]["mean_abs_rgb_channel_delta"])
                var inverse_mean := float(diffs["inverse_transpose"]["mean_abs_rgb_channel_delta"])
                var nonrig_best := minf(
                    float(diffs["pose_recomputed"]["mean_abs_rgb_channel_delta"]),
                    float(diffs["frozen_neutral"]["mean_abs_rgb_channel_delta"])
                )
                if linear_mean < inverse_mean:
                    receipt["linear_beats_inverse_count"] += 1
                receipt["minimum_linear_to_nonrig_separation_ratio"] = minf(
                    float(receipt["minimum_linear_to_nonrig_separation_ratio"]),
                    nonrig_best / maxf(linear_mean, 1e-15)
                )
                receipt["maximum_linear_mean_abs_rgb_channel_delta"] = maxf(
                    float(receipt["maximum_linear_mean_abs_rgb_channel_delta"]),
                    linear_mean
                )
            if sample_key == "160":
                receipt["neutral_gate"] = bool(receipt["neutral_gate"]) and float(diffs["linear_gradient"]["mean_abs_rgb_channel_delta"]) <= NEUTRAL_NORMAL_MAX_MEAN_DELTA
            receipt["comparisons"][sample_key][context] = {
                "angle_deg": payload["samples"][sample_key]["angle_deg"],
                "time_s": payload["samples"][sample_key]["time_s"],
                "position_control": coverage,
                "normal_buffer_diffs": diffs,
                "inverted_linear_negative": inverted,
                "winner": winner
            }
    var total := int(receipt["deformed_comparison_count"])
    var counts: Dictionary = receipt["deformed_winner_counts"]
    if not bool(receipt["position_control_clean_all_contexts"]):
        receipt["result"] = "INCONCLUSIVE_CHARACTER_REVIEW006_TARGET_ENGINE_DIRECTION_FRAME__POSITION_CONTROL_MISMATCH"
    elif not bool(receipt["neutral_gate"]):
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_ENGINE_DIRECTION_FRAME__NEUTRAL_NORMAL_BUFFER_GATE_NOT_CLOSED"
    elif not bool(receipt["inverted_negative_visible_all_deformed_contexts"]):
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_ENGINE_DIRECTION_FRAME__OBSERVER_SENSITIVITY_NOT_PROVEN"
    elif (
        int(counts["linear_gradient"]) == total
        and int(receipt["linear_beats_inverse_count"]) == total
        and float(receipt["minimum_linear_to_nonrig_separation_ratio"]) >= MIN_NONRIG_SEPARATION_RATIO
        and float(receipt["maximum_linear_mean_abs_rgb_channel_delta"]) <= COHERENT_HYPOTHESIS_MAX_MEAN_DELTA
    ):
        receipt["result"] = "PASS_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_CONSISTENTLY_NEARER_RIGGING_LINEAR_GRADIENT_REFERENCE__INVERSE_TRANSPOSE_SEPARATION_SUB_LSB"
    elif int(counts["inverse_transpose"]) == total:
        receipt["result"] = "PASS_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_CONSISTENT_WITH_RIGGING_INVERSE_TRANSPOSE_HYPOTHESIS"
    elif int(counts["pose_recomputed"]) == total:
        receipt["result"] = "PASS_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_CONSISTENT_WITH_POSE_RECOMPUTED_HYPOTHESIS"
    elif int(counts["frozen_neutral"]) == total:
        receipt["result"] = "FAIL_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_CONSISTENT_WITH_FROZEN_NEUTRAL_CONTROL"
    else:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_MIXED_OR_UNRESOLVED_HYPOTHESES"
    write_receipt(receipt)
    quit(0)
