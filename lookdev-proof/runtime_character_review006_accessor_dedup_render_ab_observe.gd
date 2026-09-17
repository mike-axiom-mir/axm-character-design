extends SceneTree

const BASELINE_PATH := "res://generated/runtime-accessor-dedup-render-ab/materials-baseline-payload.json"
const RUNTIME_RESULT_PATH := "res://generated/runtime-accessor-dedup-render-ab/runtime-result.json"
const CONTROL_PATH := "res://generated/runtime-accessor-dedup-render-ab/review006-control.glb"
const CANDIDATE_PATH := "res://generated/runtime-accessor-dedup-render-ab/review006-candidate.glb"
const RECEIPT_PATH := "res://runtime-character-review006-accessor-dedup-render-ab-receipt.json"
const SAMPLE_KEYS := ["80", "160", "240"]
const CONTEXTS := ["front", "three_quarter", "grazing"]
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.055, 0.06, 0.07, 1.0)
const CLIP_ID := "character-review006-bilateral-shoulder-articulation-review-loop-001"
const CONTROL_SHA256 := "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
const CANDIDATE_SHA256 := "2786a05578adbd1bacccd2c47305000bf7ead81a65580da896d46d9dd0666bcc"

var baseline: Dictionary = {}
var runtime_result: Dictionary = {}

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
        "schema": "axm.character-review006-runtime-accessor-dedup-render-ab/v0.1",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    })
    push_error(message)
    quit(1)

func to_v3(raw: Array) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func make_material(unshaded: bool) -> StandardMaterial3D:
    var spec: Dictionary = baseline["contract"]["material"]
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
    var b: Dictionary = baseline["samples"][sample_key]["camera_bounds"]
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

func instantiate_target(path: String) -> Node:
    var doc := GLTFDocument.new()
    var state := GLTFState.new()
    var err := doc.append_from_file(path, state)
    if err != OK:
        return null
    return doc.generate_scene(state)

func seek_target(target_scene: Node, sample_key: String) -> Dictionary:
    var player := find_animation_player(target_scene)
    if player == null:
        return {"state": "FAIL_ANIMATION_PLAYER_MISSING"}
    if not player.has_animation(CLIP_ID):
        return {"state": "FAIL_CLIP_MISSING", "clips": Array(player.get_animation_list())}
    player.play(CLIP_ID)
    player.seek(float(baseline["samples"][sample_key]["time_s"]), true)
    player.advance(0.0)
    player.pause()
    return {"state": "PASS"}

func build_world(sample_key: String, context: String, variant: String, unshaded: bool) -> Dictionary:
    var viewport := SubViewport.new()
    viewport.size = FRAME_SIZE
    viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
    viewport.transparent_bg = false
    viewport.world_3d = World3D.new()
    get_root().add_child(viewport)

    var root3d := Node3D.new()
    viewport.add_child(root3d)
    add_lighting(root3d)

    var path := CONTROL_PATH if variant == "control" else CANDIDATE_PATH
    var target_scene := instantiate_target(path)
    if target_scene == null:
        viewport.queue_free()
        return {"state": "FAIL_GLTF_IMPORT", "variant": variant}
    root3d.add_child(target_scene)

    var meshes: Array = []
    collect_meshes(target_scene, meshes)
    if meshes.size() != 1:
        viewport.queue_free()
        return {"state": "FAIL_TARGET_MESH_COUNT", "variant": variant, "mesh_count": meshes.size()}
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

func capture(sample_key: String, context: String, variant: String, unshaded: bool) -> Dictionary:
    var built := build_world(sample_key, context, variant, unshaded)
    if built.get("state") != "PASS":
        return built
    var viewport: SubViewport = built["viewport"]
    await process_frame
    await process_frame
    await RenderingServer.frame_post_draw
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        viewport.queue_free()
        return {"state": "FAIL_EMPTY_IMAGE", "variant": variant}
    var shade_label := "unshaded" if unshaded else "shaded"
    var path := "res://runtime-character-review006-accessor-dedup-render-ab-%s-%s-%s-%s.png" % [sample_key, context, variant, shade_label]
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
        "changed_fraction_raw": float(changed_raw) / float(total),
        "max_rgb_channel_delta": max_delta,
        "max_rgb_channel_delta_lsb": max_delta * 255.0,
        "mean_abs_rgb_channel_delta": sum_delta / float(total)
    }

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    baseline = read_json(BASELINE_PATH)
    runtime_result = read_json(RUNTIME_RESULT_PATH)
    if baseline.get("schema") != "axm.character-review006-current-target-shaded-motion-reference-payload/v0.3":
        fail("missing exact Materials baseline payload")
        return
    if baseline.get("exact_identity", {}).get("target_glb_sha256") != CONTROL_SHA256:
        fail("Materials baseline target identity drift")
        return
    if runtime_result.get("control", {}).get("glb_sha256") != CONTROL_SHA256:
        fail("Runtime control identity drift")
        return
    if runtime_result.get("candidate", {}).get("glb_sha256") != CANDIDATE_SHA256:
        fail("Runtime candidate identity drift")
        return
    if int(runtime_result.get("control", {}).get("glb_bytes", -1)) != 44032 or int(runtime_result.get("candidate", {}).get("glb_bytes", -1)) != 40064:
        fail("Runtime before/after byte budget drift")
        return

    var receipt := {
        "schema": "axm.character-review006-runtime-accessor-dedup-render-ab/v0.1",
        "state": "PASS_EVIDENCE",
        "renderer": {
            "engine": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": "gl_compatibility",
            "adapter": RenderingServer.get_video_adapter_name(),
            "frame_size": [FRAME_SIZE.x, FRAME_SIZE.y]
        },
        "identity": {
            "control_glb_sha256": CONTROL_SHA256,
            "candidate_glb_sha256": CANDIDATE_SHA256,
            "control_glb_bytes": 44032,
            "candidate_glb_bytes": 40064,
            "materials_baseline_head": "57da8ac7456c4b90bd79efa9292c969a4ecb01ac",
            "technical_art_adoption_head": "a8e2759e72e15a63e50f2cddecf1b407bbfd4224"
        },
        "comparisons": {},
        "summary": {
            "pair_count": 0,
            "unshaded_changed_pixels_raw_total": 0,
            "unshaded_changed_pixels_gt_1lsb_total": 0,
            "shaded_changed_pixels_raw_total": 0,
            "shaded_changed_pixels_gt_1lsb_total": 0,
            "maximum_unshaded_rgb_channel_delta_lsb": 0.0,
            "maximum_shaded_rgb_channel_delta_lsb": 0.0,
            "observer_lighting_sensitive_pair_count": 0
        },
        "truth_boundary": {
            "exact_retained_key_render_ab": true,
            "continuous_playback": false,
            "full_body": false,
            "production_tangents_or_tangent_space": false,
            "target_device_cpu_gpu_fps_vram": false,
            "art_direction_final_acceptance": false,
            "visual_qa_final_acceptance": false,
            "technical_art_adoption_authority": false,
            "canon": false,
            "production_ready": false
        }
    }

    for sample_key in SAMPLE_KEYS:
        receipt["comparisons"][sample_key] = {}
        for context in CONTEXTS:
            var control_unshaded := await capture(sample_key, context, "control", true)
            var candidate_unshaded := await capture(sample_key, context, "candidate", true)
            var control_shaded := await capture(sample_key, context, "control", false)
            var candidate_shaded := await capture(sample_key, context, "candidate", false)
            for cap in [control_unshaded, candidate_unshaded, control_shaded, candidate_shaded]:
                if cap.get("state") != "PASS":
                    fail("capture failed for %s/%s: %s" % [sample_key, context, JSON.stringify(cap)])
                    return

            var unshaded_delta := image_diff(control_unshaded["image"], candidate_unshaded["image"])
            var shaded_delta := image_diff(control_shaded["image"], candidate_shaded["image"])
            var control_lighting := image_diff(control_shaded["image"], control_unshaded["image"])
            if unshaded_delta.get("state") != "PASS" or shaded_delta.get("state") != "PASS" or control_lighting.get("state") != "PASS":
                fail("image-diff dimension mismatch")
                return

            receipt["summary"]["pair_count"] += 1
            receipt["summary"]["unshaded_changed_pixels_raw_total"] += int(unshaded_delta["changed_pixels_raw"])
            receipt["summary"]["unshaded_changed_pixels_gt_1lsb_total"] += int(unshaded_delta["changed_pixels_gt_1lsb"])
            receipt["summary"]["shaded_changed_pixels_raw_total"] += int(shaded_delta["changed_pixels_raw"])
            receipt["summary"]["shaded_changed_pixels_gt_1lsb_total"] += int(shaded_delta["changed_pixels_gt_1lsb"])
            receipt["summary"]["maximum_unshaded_rgb_channel_delta_lsb"] = maxf(float(receipt["summary"]["maximum_unshaded_rgb_channel_delta_lsb"]), float(unshaded_delta["max_rgb_channel_delta_lsb"]))
            receipt["summary"]["maximum_shaded_rgb_channel_delta_lsb"] = maxf(float(receipt["summary"]["maximum_shaded_rgb_channel_delta_lsb"]), float(shaded_delta["max_rgb_channel_delta_lsb"]))
            if int(control_lighting["changed_pixels_gt_1lsb"]) >= 100:
                receipt["summary"]["observer_lighting_sensitive_pair_count"] += 1

            receipt["comparisons"][sample_key][context] = {
                "time_s": baseline["samples"][sample_key]["time_s"],
                "angle_deg": baseline["samples"][sample_key]["angle_deg"],
                "control_to_candidate_unshaded": unshaded_delta,
                "control_to_candidate_shaded": shaded_delta,
                "control_shaded_to_unshaded_observer_sensitivity": control_lighting
            }

    var observer_sensitive := int(receipt["summary"]["observer_lighting_sensitive_pair_count"]) == 9
    var unshaded_exact := int(receipt["summary"]["unshaded_changed_pixels_raw_total"]) == 0
    var shaded_exact := int(receipt["summary"]["shaded_changed_pixels_raw_total"]) == 0
    if not observer_sensitive:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_ACCESSOR_DEDUP_RENDER_AB__OBSERVER_LIGHTING_SENSITIVITY_NOT_PROVEN"
        receipt["visual_tradeoff"] = "INCONCLUSIVE_OBSERVER_SENSITIVITY"
    elif not unshaded_exact:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_ACCESSOR_DEDUP_RENDER_AB__UNSHADED_RECEIVER_DELTA"
        receipt["visual_tradeoff"] = "UNSHADED_DELTA_REQUIRES_ART_QA_REVIEW"
    elif shaded_exact:
        receipt["result"] = "PASS_CHARACTER_REVIEW006_ACCESSOR_DEDUP_EXACT_FROZEN_BASELINE_RENDER_BYTE_IDENTITY__HOLD_CONTINUOUS_FULL_BODY_TANGENT_TARGET_DEVICE_ADOPTION"
        receipt["visual_tradeoff"] = "NONE_OBSERVED_9_UNSHADED_AND_9_SHADED_CONTROL_CANDIDATE_PAIRS_BYTE_IDENTICAL"
    else:
        receipt["result"] = "MEASURED_CHARACTER_REVIEW006_ACCESSOR_DEDUP_SHADED_RENDER_DELTA__HOLD_ART_QA"
        receipt["visual_tradeoff"] = "SHADED_DELTA_MEASURED_EXACTLY__ART_QA_REVIEW_REQUIRED"

    receipt["promotion_effect"] = "RUNTIME_EVIDENCE_ONLY__NO_AUTOMATIC_ART_QA_TECHNICAL_ART_OR_CANON_ADOPTION"
    write_receipt(receipt)
    print(JSON.stringify(receipt, "  "))
    quit(0)
