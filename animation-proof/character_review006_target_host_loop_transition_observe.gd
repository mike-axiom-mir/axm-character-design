extends SceneTree

const CONTRACT_PATH := "res://character_review006_target_host_loop_transition_review_001.json"
const PAYLOAD_PATH := "res://generated/character_review006_current_motion_direction_frame_payload.json"
const GLB_PATH := "res://generated/character-review006-current-motion-target.glb"
const RECEIPT_PATH := "res://character-review006-target-host-loop-transition-runtime-receipt.json"
const EXPECTED_MATERIALS_HEAD := "c2ae66c75abac064b679f1597b7544d058dc3ad1"
const EXPECTED_TECHNICAL_ART_HEAD := "1c021d40d7d606f6fb2a29e69f9353640aa33f60"
const EXPECTED_SOURCE_ANIMATION_HEAD := "9519be55581c009fd800d175677d9b50ee6926e6"
const EXPECTED_RIGGING_HEAD := "fa16c44b1a488d43842470fc9f30c5fb5e98cab6"
const EXPECTED_GLB_SHA256 := "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
const EXACT_TRANSPORT_BAKE_FPS := 160.0
const EXPECTED_TRACK_COUNT := 6
const EXPECTED_KEY_COUNT := 321
const EXPECTED_DURATION_S := 2.0
const MIN_WRAP_COUNT := 3
const PRE_WRAP_POSITION_MIN_S := 1.75
const POST_WRAP_POSITION_MAX_S := 0.25
const EXACT_SEAM_ROTATION_TOLERANCE_DEG := 0.001
const EXACT_SEAM_SCALE_TOLERANCE := 0.00001
const OBSERVED_WRAP_ROTATION_TOLERANCE_DEG := 0.5
const OBSERVED_WRAP_SCALE_TOLERANCE := 0.005
const WALL_TIMEOUT_S := 8.0
const NEGATIVE_OFFSET_DEG := 0.25
const BONES := [
    "shoulder-L-distal",
    "shoulder-L-release-transport",
    "shoulder-R-distal",
    "shoulder-R-release-transport"
]

var receipt: Dictionary = {
    "schema": "axm.character-review006-target-host-loop-transition-runtime/v0.1",
    "state": "NOT_RUN",
    "result": "NOT_RUN",
    "promotion_effect": "NONE"
}

func read_json(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    return parsed as Dictionary if parsed is Dictionary else {}

func write_receipt() -> void:
    var file := FileAccess.open(RECEIPT_PATH, FileAccess.WRITE)
    if file != null:
        file.store_string(JSON.stringify(receipt, "  ") + "\n")
        file.close()

func fail(message: String, diagnostics: Dictionary = {}) -> void:
    receipt["state"] = "FAIL_TARGET_HOST_LOOP_TRANSITION_PROOF"
    receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_HOST_LOOP_TRANSITION"
    receipt["failure"] = message
    if not diagnostics.is_empty():
        receipt["diagnostics"] = diagnostics
    write_receipt()
    push_error(message)
    quit(1)

func sha256_file(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var ctx := HashingContext.new()
    ctx.start(HashingContext.HASH_SHA256)
    ctx.update(FileAccess.get_file_as_bytes(path))
    return ctx.finish().hex_encode()

func find_player(node: Node) -> AnimationPlayer:
    if node is AnimationPlayer:
        return node as AnimationPlayer
    for child in node.get_children():
        var found := find_player(child)
        if found != null:
            return found
    return null

func find_skeleton(node: Node) -> Skeleton3D:
    if node is Skeleton3D:
        return node as Skeleton3D
    for child in node.get_children():
        var found := find_skeleton(child)
        if found != null:
            return found
    return null

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

func rotation_error_deg(a: Quaternion, b: Quaternion) -> float:
    return rad_to_deg(a.normalized().angle_to(b.normalized()))

func scale_error(a: Vector3, b: Vector3) -> float:
    return maxf(absf(a.x - b.x), maxf(absf(a.y - b.y), absf(a.z - b.z)))

func capture_pose(skeleton: Skeleton3D, bone_indices: Dictionary) -> Dictionary:
    var result := {}
    for bone_name in BONES:
        var bone_index := int(bone_indices[bone_name])
        result[bone_name] = {
            "rotation": skeleton.get_bone_pose_rotation(bone_index).normalized(),
            "scale": skeleton.get_bone_pose_scale(bone_index)
        }
    return result

func pose_delta(a: Dictionary, b: Dictionary) -> Dictionary:
    var max_rotation := 0.0
    var max_scale := 0.0
    var worst_rotation_bone := ""
    var worst_scale_bone := ""
    for bone_name in BONES:
        var ar: Quaternion = a[bone_name]["rotation"] as Quaternion
        var br: Quaternion = b[bone_name]["rotation"] as Quaternion
        var ascale: Vector3 = a[bone_name]["scale"] as Vector3
        var bscale: Vector3 = b[bone_name]["scale"] as Vector3
        var re := rotation_error_deg(ar, br)
        var se := scale_error(ascale, bscale)
        if re > max_rotation:
            max_rotation = re
            worst_rotation_bone = bone_name
        if se > max_scale:
            max_scale = se
            worst_scale_bone = bone_name
    return {
        "max_rotation_error_deg": max_rotation,
        "max_scale_component_error": max_scale,
        "worst_rotation_bone": worst_rotation_bone,
        "worst_scale_bone": worst_scale_bone
    }

func validate_track_grid(animation: Animation) -> Array:
    var rows := []
    if animation.get_track_count() != EXPECTED_TRACK_COUNT:
        fail("target-host loop witness imported animation track-count drift", {"observed": animation.get_track_count()})
        return rows
    for track in range(animation.get_track_count()):
        var key_count := animation.track_get_key_count(track)
        var interpolation := animation.track_get_interpolation_type(track)
        var first_time := float(animation.track_get_key_time(track, 0)) if key_count > 0 else -1.0
        var last_time := float(animation.track_get_key_time(track, key_count - 1)) if key_count > 0 else -1.0
        var row := {
            "index": track,
            "path": String(animation.track_get_path(track)),
            "type": int(animation.track_get_type(track)),
            "interpolation": int(interpolation),
            "key_count": key_count,
            "first_time_s": first_time,
            "last_time_s": last_time
        }
        rows.append(row)
        if key_count != EXPECTED_KEY_COUNT:
            fail("target-host loop witness key-count drift", row)
            return rows
        if interpolation != Animation.INTERPOLATION_LINEAR:
            fail("target-host loop witness interpolation-mode drift", row)
            return rows
        if absf(first_time) > 0.000001 or absf(last_time - EXPECTED_DURATION_S) > 0.00001:
            fail("target-host loop witness key-time boundary drift", row)
            return rows
    return rows

func seek_pose(player: AnimationPlayer, time_s: float) -> void:
    player.seek(time_s, true)
    player.advance(0.0)

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    var contract := read_json(CONTRACT_PATH)
    var payload := read_json(PAYLOAD_PATH)
    if contract.get("schema") != "axm.character-review006-target-host-loop-transition/v0.1":
        fail("missing or invalid Animation loop-transition contract")
        return
    if contract.get("materials_parent_head") != EXPECTED_MATERIALS_HEAD or contract.get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD or contract.get("source_animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD or contract.get("rigging_head") != EXPECTED_RIGGING_HEAD:
        fail("Animation loop-transition lineage identity drift")
        return
    if contract.get("target_glb_sha256") != EXPECTED_GLB_SHA256 or sha256_file(GLB_PATH) != EXPECTED_GLB_SHA256:
        fail("Animation loop-transition target GLB identity drift")
        return
    if payload.get("schema") != "axm.character-review006-current-motion-direction-frame-payload/v0.1":
        fail("missing exact current-motion payload")
        return
    if payload["exact_identity"].get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD or payload["exact_identity"].get("animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD or payload["exact_identity"].get("rigging_head") != EXPECTED_RIGGING_HEAD or payload["exact_identity"].get("target_glb_sha256") != EXPECTED_GLB_SHA256:
        fail("loop-transition payload exact lineage identity drift")
        return

    var target := import_target()
    if target == null:
        return
    get_root().add_child(target)
    var player := find_player(target)
    var skeleton := find_skeleton(target)
    if player == null or skeleton == null:
        fail("target-host loop witness missing AnimationPlayer or Skeleton3D")
        return
    var clip := String(payload["target"]["clip_id"])
    if not player.has_animation(clip):
        fail("target-host loop witness missing exact clip", {"clip": clip, "available": Array(player.get_animation_list())})
        return
    var animation: Animation = player.get_animation(clip)
    if animation == null or absf(float(animation.length) - EXPECTED_DURATION_S) > 0.00001:
        fail("target-host loop witness duration drift")
        return
    var track_rows := validate_track_grid(animation)
    if receipt.get("state") == "FAIL_TARGET_HOST_LOOP_TRANSITION_PROOF":
        return

    var bone_indices := {}
    for bone_name in BONES:
        var bone_index := skeleton.find_bone(bone_name)
        if bone_index < 0:
            fail("target-host loop witness missing exact bone: " + bone_name)
            return
        bone_indices[bone_name] = bone_index

    player.play(clip)
    player.advance(0.0)
    player.pause()
    seek_pose(player, 0.0)
    var neutral_start := capture_pose(skeleton, bone_indices)
    seek_pose(player, EXPECTED_DURATION_S)
    var neutral_end := capture_pose(skeleton, bone_indices)
    var exact_seam := pose_delta(neutral_end, neutral_start)
    if float(exact_seam["max_rotation_error_deg"]) > EXACT_SEAM_ROTATION_TOLERANCE_DEG or float(exact_seam["max_scale_component_error"]) > EXACT_SEAM_SCALE_TOLERANCE:
        fail("exact imported loop seam does not close", exact_seam)
        return

    var mutated_start := neutral_start.duplicate(true)
    var source_rotation: Quaternion = neutral_start["shoulder-L-distal"]["rotation"] as Quaternion
    mutated_start["shoulder-L-distal"]["rotation"] = (source_rotation * Quaternion(Vector3.RIGHT, deg_to_rad(NEGATIVE_OFFSET_DEG))).normalized()
    var negative_delta := pose_delta(neutral_end, mutated_start)
    var negative_rejected := float(negative_delta["max_rotation_error_deg"]) > EXACT_SEAM_ROTATION_TOLERANCE_DEG
    if not negative_rejected:
        fail("loop seam negative control did not fail closed", negative_delta)
        return

    # Observer-only loop mode: this mutates only the imported in-memory Animation resource used by
    # this proof run. It does not rewrite the GLB, source clip, controller or production policy.
    var original_loop_mode := animation.loop_mode
    animation.loop_mode = Animation.LOOP_LINEAR
    player.stop()
    player.play(clip)
    player.seek(0.0, true)
    player.advance(0.0)

    var start_us := Time.get_ticks_usec()
    var last_us := start_us
    var previous_position := float(player.current_animation_position)
    var previous_pose := capture_pose(skeleton, bone_indices)
    var wrap_count := 0
    var frame_count := 0
    var min_frame_ms := 1.0e30
    var max_frame_ms := 0.0
    var sum_frame_ms := 0.0
    var max_pre_endpoint_rotation_error_deg := 0.0
    var max_post_endpoint_rotation_error_deg := 0.0
    var max_pre_endpoint_scale_error := 0.0
    var max_post_endpoint_scale_error := 0.0
    var max_cross_seam_rotation_jump_deg := 0.0
    var max_cross_seam_scale_jump := 0.0
    var wraps := []

    while wrap_count < MIN_WRAP_COUNT:
        await process_frame
        frame_count += 1
        var now_us := Time.get_ticks_usec()
        var frame_ms := float(now_us - last_us) / 1000.0
        last_us = now_us
        min_frame_ms = minf(min_frame_ms, frame_ms)
        max_frame_ms = maxf(max_frame_ms, frame_ms)
        sum_frame_ms += frame_ms
        var elapsed_s := float(now_us - start_us) / 1000000.0
        if elapsed_s > WALL_TIMEOUT_S:
            animation.loop_mode = original_loop_mode
            fail("target-host repeated loop witness timed out", {"wrap_count": wrap_count, "frame_count": frame_count, "elapsed_s": elapsed_s})
            return

        var position := float(player.current_animation_position)
        var current_pose := capture_pose(skeleton, bone_indices)
        if position + 0.000001 < previous_position:
            if previous_position < PRE_WRAP_POSITION_MIN_S or position > POST_WRAP_POSITION_MAX_S:
                animation.loop_mode = original_loop_mode
                fail("AnimationPlayer position reversal was not a bounded loop seam wrap", {"previous_position_s": previous_position, "position_s": position, "wrap_count": wrap_count})
                return
            var pre_delta := pose_delta(previous_pose, neutral_end)
            var post_delta := pose_delta(current_pose, neutral_start)
            var cross_delta := pose_delta(previous_pose, current_pose)
            max_pre_endpoint_rotation_error_deg = maxf(max_pre_endpoint_rotation_error_deg, float(pre_delta["max_rotation_error_deg"]))
            max_post_endpoint_rotation_error_deg = maxf(max_post_endpoint_rotation_error_deg, float(post_delta["max_rotation_error_deg"]))
            max_pre_endpoint_scale_error = maxf(max_pre_endpoint_scale_error, float(pre_delta["max_scale_component_error"]))
            max_post_endpoint_scale_error = maxf(max_post_endpoint_scale_error, float(post_delta["max_scale_component_error"]))
            max_cross_seam_rotation_jump_deg = maxf(max_cross_seam_rotation_jump_deg, float(cross_delta["max_rotation_error_deg"]))
            max_cross_seam_scale_jump = maxf(max_cross_seam_scale_jump, float(cross_delta["max_scale_component_error"]))
            wrap_count += 1
            wraps.append({
                "wrap_index": wrap_count,
                "pre_position_s": previous_position,
                "post_position_s": position,
                "pre_endpoint_rotation_error_deg": pre_delta["max_rotation_error_deg"],
                "post_endpoint_rotation_error_deg": post_delta["max_rotation_error_deg"],
                "pre_endpoint_scale_error": pre_delta["max_scale_component_error"],
                "post_endpoint_scale_error": post_delta["max_scale_component_error"],
                "cross_seam_rotation_jump_deg": cross_delta["max_rotation_error_deg"],
                "cross_seam_scale_jump": cross_delta["max_scale_component_error"]
            })
            if float(pre_delta["max_rotation_error_deg"]) > OBSERVED_WRAP_ROTATION_TOLERANCE_DEG or float(post_delta["max_rotation_error_deg"]) > OBSERVED_WRAP_ROTATION_TOLERANCE_DEG or float(pre_delta["max_scale_component_error"]) > OBSERVED_WRAP_SCALE_TOLERANCE or float(post_delta["max_scale_component_error"]) > OBSERVED_WRAP_SCALE_TOLERANCE:
                animation.loop_mode = original_loop_mode
                fail("observed repeated loop seam escaped bounded neutral endpoint neighborhood", wraps[-1])
                return
        previous_position = position
        previous_pose = current_pose

    var elapsed_total_s := float(Time.get_ticks_usec() - start_us) / 1000000.0
    player.stop()
    animation.loop_mode = original_loop_mode

    receipt["state"] = "PASS_DIAGNOSTIC"
    receipt["result"] = "PASS_CHARACTER_REVIEW006_TARGET_HOST_REPEATED_LOOP_SEAM_TRANSITION"
    receipt["identity"] = {
        "materials_parent_head": EXPECTED_MATERIALS_HEAD,
        "technical_art_head": EXPECTED_TECHNICAL_ART_HEAD,
        "source_animation_head": EXPECTED_SOURCE_ANIMATION_HEAD,
        "rigging_head": EXPECTED_RIGGING_HEAD,
        "target_glb_sha256": EXPECTED_GLB_SHA256,
        "clip_id": clip
    }
    receipt["imported_animation"] = {
        "duration_s": animation.length,
        "exact_transport_bake_fps": EXACT_TRANSPORT_BAKE_FPS,
        "track_count": animation.get_track_count(),
        "track_rows": track_rows
    }
    receipt["exact_loop_seam"] = {
        "start_time_s": 0.0,
        "end_time_s": EXPECTED_DURATION_S,
        "max_rotation_error_deg": exact_seam["max_rotation_error_deg"],
        "max_scale_component_error": exact_seam["max_scale_component_error"]
    }
    receipt["negative_control"] = {
        "kind": "VERIFIER_ONLY_NEUTRAL_ROTATION_OFFSET",
        "offset_deg": NEGATIVE_OFFSET_DEG,
        "mutated_max_rotation_error_deg": negative_delta["max_rotation_error_deg"],
        "expected_rejection": negative_rejected
    }
    receipt["repeated_animationplayer_loop"] = {
        "observer_only_loop_mode_override": "LOOP_LINEAR",
        "wrap_count": wrap_count,
        "frame_count": frame_count,
        "elapsed_s": elapsed_total_s,
        "frame_interval_ms_min": 0.0 if frame_count == 0 else min_frame_ms,
        "frame_interval_ms_mean": 0.0 if frame_count == 0 else sum_frame_ms / float(frame_count),
        "frame_interval_ms_max": max_frame_ms,
        "max_pre_endpoint_rotation_error_deg": max_pre_endpoint_rotation_error_deg,
        "max_post_endpoint_rotation_error_deg": max_post_endpoint_rotation_error_deg,
        "max_pre_endpoint_scale_error": max_pre_endpoint_scale_error,
        "max_post_endpoint_scale_error": max_post_endpoint_scale_error,
        "max_cross_seam_rotation_jump_deg": max_cross_seam_rotation_jump_deg,
        "max_cross_seam_scale_jump": max_cross_seam_scale_jump,
        "wraps": wraps
    }
    receipt["preserved_downstream_boundary"] = {
        "materials_result": "INCONCLUSIVE_CHARACTER_REVIEW006_TARGET_DIRECTION_FRAME_MIXED_RESPONSE",
        "deformed_normals_or_tangents": "NOT_EVALUATED"
    }
    receipt["truth_boundary"] = {
        "source_motion_changed": false,
        "rigging_or_skin_changed": false,
        "observer_only_loop_mode_override": true,
        "runtime_controller_or_state_machine": "NOT_EVALUATED",
        "physics_collision_input_gameplay": "NOT_EVALUATED",
        "complete_160hz_presentation_delivery": "NOT_CLAIMED",
        "target_device_performance": "NOT_EVALUATED",
        "art_direction_or_visual_qa_acceptance": false,
        "source_adoption_or_canon": false,
        "production_readiness": false
    }
    write_receipt()
    print(JSON.stringify(receipt, "  "))
    quit(0)
