extends SceneTree

const CONTRACT_PATH := "res://character_review006_target_host_playback_review_001.json"
const PAYLOAD_PATH := "res://generated/character_review006_current_motion_direction_frame_payload.json"
const GLB_PATH := "res://generated/character-review006-current-motion-target.glb"
const RECEIPT_PATH := "res://character-review006-target-host-playback-runtime-receipt.json"
const EXPECTED_MATERIALS_HEAD := "c2ae66c75abac064b679f1597b7544d058dc3ad1"
const EXPECTED_TECHNICAL_ART_HEAD := "1c021d40d7d606f6fb2a29e69f9353640aa33f60"
const EXPECTED_SOURCE_ANIMATION_HEAD := "9519be55581c009fd800d175677d9b50ee6926e6"
const EXPECTED_RIGGING_HEAD := "fa16c44b1a488d43842470fc9f30c5fb5e98cab6"
const EXPECTED_GLB_SHA256 := "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
const EXPECTED_TRACK_COUNT := 6
const EXPECTED_KEY_COUNT := 321
const EXPECTED_INTERVAL_COUNT := 320
const EXPECTED_DURATION_S := 2.0
const ROTATION_TOLERANCE_DEG := 0.001
const SCALE_TOLERANCE := 0.00001
const WALL_CLOCK_TIMEOUT_S := 4.0
const NEGATIVE_OFFSET_DEG := 0.25
const BONES := [
    "shoulder-L-distal",
    "shoulder-L-release-transport",
    "shoulder-R-distal",
    "shoulder-R-release-transport"
]

var contract: Dictionary = {}
var payload: Dictionary = {}
var receipt: Dictionary = {
    "schema": "axm.character-review006-target-host-playback-runtime/v0.1",
    "state": "NOT_RUN",
    "result": "NOT_RUN",
    "promotion_effect": "NONE"
}

func read_json(path: String) -> Dictionary:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    file.close()
    return parsed as Dictionary if parsed is Dictionary else {}

func write_receipt() -> void:
    var file := FileAccess.open(RECEIPT_PATH, FileAccess.WRITE)
    if file != null:
        file.store_string(JSON.stringify(receipt, "  ") + "\n")
        file.close()

func fail(message: String) -> void:
    receipt["state"] = "FAIL_TARGET_HOST_PLAYBACK_PROOF"
    receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_HOST_PLAYBACK"
    receipt["failure"] = message
    write_receipt()
    push_error(message)
    quit(1)

func sha256_file(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var bytes := FileAccess.get_file_as_bytes(path)
    var ctx := HashingContext.new()
    ctx.start(HashingContext.HASH_SHA256)
    ctx.update(bytes)
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
    var generated = document.generate_scene(state)
    if generated == null or not (generated is Node3D):
        fail("GLTFDocument generate_scene returned no Node3D")
        return null
    return generated as Node3D

func track_binding(animation: Animation) -> Dictionary:
    var bindings := {}
    var paths := []
    for bone_name in BONES:
        bindings[bone_name] = {"rotation": -1, "scale": -1}
    for track in range(animation.get_track_count()):
        var path_text := String(animation.track_get_path(track))
        var track_type := animation.track_get_type(track)
        paths.append({"index": track, "path": path_text, "type": int(track_type), "key_count": animation.track_get_key_count(track)})
        for bone_name in BONES:
            if path_text.find(bone_name) < 0:
                continue
            if track_type == Animation.TYPE_ROTATION_3D:
                bindings[bone_name]["rotation"] = track
            elif track_type == Animation.TYPE_SCALE_3D:
                bindings[bone_name]["scale"] = track
    return {"bindings": bindings, "paths": paths}

func validate_track_grid(animation: Animation, binding_info: Dictionary) -> void:
    if animation.get_track_count() != EXPECTED_TRACK_COUNT:
        fail("target-host imported animation track-count drift: " + str(animation.get_track_count()))
        return
    for row in binding_info["paths"]:
        var track := int(row["index"])
        if animation.track_get_key_count(track) != EXPECTED_KEY_COUNT:
            fail("target-host imported animation key-count drift on track %d: %d" % [track, animation.track_get_key_count(track)])
            return
        if absf(float(animation.track_get_key_time(track, 0))) > 0.000001:
            fail("target-host first key is not neutral time zero")
            return
        if absf(float(animation.track_get_key_time(track, EXPECTED_KEY_COUNT - 1)) - EXPECTED_DURATION_S) > 0.00001:
            fail("target-host final key time drift")
            return
        for index in range(1, EXPECTED_KEY_COUNT):
            if float(animation.track_get_key_time(track, index)) <= float(animation.track_get_key_time(track, index - 1)):
                fail("target-host imported key times are not strictly increasing")
                return
    for bone_name in BONES:
        var binding: Dictionary = binding_info["bindings"][bone_name]
        if int(binding["rotation"]) < 0:
            fail("missing target-host rotation track for " + bone_name)
            return
    if int(binding_info["bindings"]["shoulder-L-release-transport"]["scale"]) < 0:
        fail("missing target-host scale track for left release helper")
        return
    if int(binding_info["bindings"]["shoulder-R-release-transport"]["scale"]) < 0:
        fail("missing target-host scale track for right release helper")
        return
    if int(binding_info["bindings"]["shoulder-L-distal"]["scale"]) >= 0 or int(binding_info["bindings"]["shoulder-R-distal"]["scale"]) >= 0:
        fail("unexpected distal scale track appeared in target-host import")
        return

func key_quaternion(animation: Animation, track: int, index: int) -> Quaternion:
    var raw = animation.track_get_key_value(track, index)
    if raw is Quaternion:
        return (raw as Quaternion).normalized()
    fail("rotation track key is not Quaternion")
    return Quaternion.IDENTITY

func key_scale(animation: Animation, track: int, index: int) -> Vector3:
    var raw = animation.track_get_key_value(track, index)
    if raw is Vector3:
        return raw as Vector3
    fail("scale track key is not Vector3")
    return Vector3.ONE

func expected_rotation_between(animation: Animation, track: int, index: int, alpha: float) -> Quaternion:
    var a := key_quaternion(animation, track, index)
    var b := key_quaternion(animation, track, index + 1)
    return a.slerp(b, alpha).normalized()

func expected_scale_between(animation: Animation, track: int, index: int, alpha: float) -> Vector3:
    return key_scale(animation, track, index).lerp(key_scale(animation, track, index + 1), alpha)

func rotation_error_deg(a: Quaternion, b: Quaternion) -> float:
    return rad_to_deg(a.normalized().angle_to(b.normalized()))

func scale_error(a: Vector3, b: Vector3) -> float:
    return maxf(absf(a.x - b.x), maxf(absf(a.y - b.y), absf(a.z - b.z)))

func observed_pose(skeleton: Skeleton3D, bone_indices: Dictionary, bone_name: String) -> Dictionary:
    var bone := int(bone_indices[bone_name])
    return {
        "rotation": skeleton.get_bone_pose_rotation(bone).normalized(),
        "scale": skeleton.get_bone_pose_scale(bone)
    }

func compare_interval_pose(animation: Animation, skeleton: Skeleton3D, bone_indices: Dictionary, binding_info: Dictionary, interval_index: int, alpha: float) -> Dictionary:
    var max_rotation_error_deg := 0.0
    var max_scale_error := 0.0
    var per_bone := {}
    for bone_name in BONES:
        var binding: Dictionary = binding_info["bindings"][bone_name]
        var observed := observed_pose(skeleton, bone_indices, bone_name)
        var expected_rotation := expected_rotation_between(animation, int(binding["rotation"]), interval_index, alpha)
        var r_error := rotation_error_deg(observed["rotation"], expected_rotation)
        max_rotation_error_deg = maxf(max_rotation_error_deg, r_error)
        var s_error := 0.0
        if int(binding["scale"]) >= 0:
            var expected_scale := expected_scale_between(animation, int(binding["scale"]), interval_index, alpha)
            s_error = scale_error(observed["scale"], expected_scale)
            max_scale_error = maxf(max_scale_error, s_error)
        else:
            s_error = scale_error(observed["scale"], Vector3.ONE)
            max_scale_error = maxf(max_scale_error, s_error)
        per_bone[bone_name] = {"rotation_error_deg": r_error, "scale_component_error": s_error}
    return {
        "max_rotation_error_deg": max_rotation_error_deg,
        "max_scale_component_error": max_scale_error,
        "per_bone": per_bone
    }

func interval_for_time(animation: Animation, reference_track: int, time_s: float) -> Dictionary:
    if time_s <= float(animation.track_get_key_time(reference_track, 0)):
        return {"index": 0, "alpha": 0.0}
    if time_s >= float(animation.track_get_key_time(reference_track, EXPECTED_KEY_COUNT - 1)):
        return {"index": EXPECTED_KEY_COUNT - 2, "alpha": 1.0}
    var guess := clampi(int(floor(time_s * 160.0 + 0.000001)), 0, EXPECTED_KEY_COUNT - 2)
    while guess > 0 and time_s < float(animation.track_get_key_time(reference_track, guess)):
        guess -= 1
    while guess < EXPECTED_KEY_COUNT - 2 and time_s > float(animation.track_get_key_time(reference_track, guess + 1)):
        guess += 1
    var t0 := float(animation.track_get_key_time(reference_track, guess))
    var t1 := float(animation.track_get_key_time(reference_track, guess + 1))
    var alpha := clampf((time_s - t0) / maxf(t1 - t0, 0.000000001), 0.0, 1.0)
    return {"index": guess, "alpha": alpha}

func endpoint_snapshot(player: AnimationPlayer, clip: String, skeleton: Skeleton3D, bone_indices: Dictionary, time_s: float) -> Dictionary:
    player.play(clip)
    player.seek(time_s, true)
    player.advance(0.0)
    var out := {}
    for bone_name in BONES:
        var pose := observed_pose(skeleton, bone_indices, bone_name)
        var q: Quaternion = pose["rotation"]
        var s: Vector3 = pose["scale"]
        out[bone_name] = {"rotation": [q.x, q.y, q.z, q.w], "scale": [s.x, s.y, s.z]}
    player.stop()
    return out

func endpoint_residual(a: Dictionary, b: Dictionary) -> Dictionary:
    var max_rotation_error_deg := 0.0
    var max_scale_error := 0.0
    for bone_name in BONES:
        var ar: Array = a[bone_name]["rotation"]
        var br: Array = b[bone_name]["rotation"]
        var aq := Quaternion(float(ar[0]), float(ar[1]), float(ar[2]), float(ar[3]))
        var bq := Quaternion(float(br[0]), float(br[1]), float(br[2]), float(br[3]))
        max_rotation_error_deg = maxf(max_rotation_error_deg, rotation_error_deg(aq, bq))
        var ascale: Array = a[bone_name]["scale"]
        var bscale: Array = b[bone_name]["scale"]
        max_scale_error = maxf(max_scale_error, maxf(absf(float(ascale[0]) - float(bscale[0])), maxf(absf(float(ascale[1]) - float(bscale[1])), absf(float(ascale[2]) - float(bscale[2])))))
    return {"max_rotation_error_deg": max_rotation_error_deg, "max_scale_component_error": max_scale_error}

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    contract = read_json(CONTRACT_PATH)
    payload = read_json(PAYLOAD_PATH)
    if contract.get("schema") != "axm.character-review006-target-host-playback/v0.1":
        fail("missing or invalid Animation target-host contract")
        return
    if contract.get("materials_parent_head") != EXPECTED_MATERIALS_HEAD:
        fail("Materials parent identity drift")
        return
    if contract.get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD:
        fail("Technical Art identity drift")
        return
    if contract.get("source_animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD:
        fail("source Animation identity drift")
        return
    if contract.get("rigging_head") != EXPECTED_RIGGING_HEAD:
        fail("Rigging identity drift")
        return
    if contract.get("target_glb_sha256") != EXPECTED_GLB_SHA256:
        fail("target GLB contract identity drift")
        return
    if payload.get("schema") != "axm.character-review006-current-motion-direction-frame-payload/v0.1":
        fail("missing exact current-motion payload")
        return
    if payload["exact_identity"].get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD:
        fail("payload Technical Art identity drift")
        return
    if payload["exact_identity"].get("animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD:
        fail("payload source Animation identity drift")
        return
    if payload["exact_identity"].get("rigging_head") != EXPECTED_RIGGING_HEAD:
        fail("payload Rigging identity drift")
        return
    if payload["exact_identity"].get("target_glb_sha256") != EXPECTED_GLB_SHA256:
        fail("payload target GLB identity drift")
        return
    if sha256_file(GLB_PATH) != EXPECTED_GLB_SHA256:
        fail("target GLB bytes do not match exact Technical Art receiver")
        return

    var target := import_target()
    if target == null:
        return
    get_root().add_child(target)
    var player := find_player(target)
    var skeleton := find_skeleton(target)
    if player == null:
        fail("target-host import exposes no AnimationPlayer")
        return
    if skeleton == null:
        fail("target-host import exposes no Skeleton3D")
        return
    var clip := String(payload["target"]["clip_id"])
    if not player.has_animation(clip):
        fail("target-host AnimationPlayer missing exact source clip: " + clip)
        return
    var animation: Animation = player.get_animation(clip)
    if animation == null:
        fail("target-host could not retrieve exact source clip")
        return
    if absf(float(animation.length) - EXPECTED_DURATION_S) > 0.00001:
        fail("target-host clip duration drift: " + str(animation.length))
        return

    var binding_info := track_binding(animation)
    validate_track_grid(animation, binding_info)
    var bone_indices := {}
    for bone_name in BONES:
        var bone := skeleton.find_bone(bone_name)
        if bone < 0:
            fail("target-host Skeleton3D missing exact bone: " + bone_name)
            return
        bone_indices[bone_name] = bone

    var midpoint_max_rotation_error_deg := 0.0
    var midpoint_max_scale_error := 0.0
    var midpoint_worst := {}
    player.play(clip)
    for interval_index in range(EXPECTED_INTERVAL_COUNT):
        var reference_track := int(binding_info["bindings"]["shoulder-L-distal"]["rotation"])
        var t0 := float(animation.track_get_key_time(reference_track, interval_index))
        var t1 := float(animation.track_get_key_time(reference_track, interval_index + 1))
        var midpoint := (t0 + t1) * 0.5
        player.seek(midpoint, true)
        player.advance(0.0)
        var comparison := compare_interval_pose(animation, skeleton, bone_indices, binding_info, interval_index, 0.5)
        var r_error := float(comparison["max_rotation_error_deg"])
        var s_error := float(comparison["max_scale_component_error"])
        if r_error > midpoint_max_rotation_error_deg or s_error > midpoint_max_scale_error:
            midpoint_worst = {"interval_index": interval_index, "time_s": midpoint, "rotation_error_deg": r_error, "scale_component_error": s_error}
        midpoint_max_rotation_error_deg = maxf(midpoint_max_rotation_error_deg, r_error)
        midpoint_max_scale_error = maxf(midpoint_max_scale_error, s_error)
    player.stop()
    if midpoint_max_rotation_error_deg > ROTATION_TOLERANCE_DEG:
        fail("target-host midpoint rotation interpolation drift: " + str(midpoint_max_rotation_error_deg))
        return
    if midpoint_max_scale_error > SCALE_TOLERANCE:
        fail("target-host midpoint scale interpolation drift: " + str(midpoint_max_scale_error))
        return

    var neutral_start := endpoint_snapshot(player, clip, skeleton, bone_indices, 0.0)
    var neutral_end := endpoint_snapshot(player, clip, skeleton, bone_indices, EXPECTED_DURATION_S)
    var closure := endpoint_residual(neutral_start, neutral_end)
    if float(closure["max_rotation_error_deg"]) > ROTATION_TOLERANCE_DEG or float(closure["max_scale_component_error"]) > SCALE_TOLERANCE:
        fail("target-host neutral endpoint closure drift: " + str(closure))
        return

    var negative_interval := 80
    var negative_reference_track := int(binding_info["bindings"]["shoulder-L-distal"]["rotation"])
    var negative_t0 := float(animation.track_get_key_time(negative_reference_track, negative_interval))
    var negative_t1 := float(animation.track_get_key_time(negative_reference_track, negative_interval + 1))
    var negative_midpoint := (negative_t0 + negative_t1) * 0.5
    player.play(clip)
    player.seek(negative_midpoint, true)
    player.advance(0.0)
    var negative_observed := observed_pose(skeleton, bone_indices, "shoulder-L-distal")
    var clean_expected := expected_rotation_between(animation, negative_reference_track, negative_interval, 0.5)
    var mutation := Quaternion(Vector3(1.0, 0.0, 0.0), deg_to_rad(NEGATIVE_OFFSET_DEG)) * clean_expected
    var clean_error := rotation_error_deg(negative_observed["rotation"], clean_expected)
    var mutated_error := rotation_error_deg(negative_observed["rotation"], mutation)
    player.stop()
    var negative_rejected := clean_error <= ROTATION_TOLERANCE_DEG and mutated_error > ROTATION_TOLERANCE_DEG
    if not negative_rejected:
        fail("verifier-only rotation negative control did not fail closed")
        return

    var wall_frame_count := 0
    var wall_monotonic_violations := 0
    var wall_max_rotation_error_deg := 0.0
    var wall_max_scale_error := 0.0
    var wall_min_dt_ms := INF
    var wall_max_dt_ms := 0.0
    var wall_sum_dt_ms := 0.0
    var wall_dt_count := 0
    var previous_position := -1.0
    var previous_ticks := -1
    var highest_position := 0.0
    var reference_track := int(binding_info["bindings"]["shoulder-L-distal"]["rotation"])
    player.play(clip)
    var wall_start := Time.get_ticks_usec()
    while true:
        await process_frame
        var now := Time.get_ticks_usec()
        var elapsed_s := float(now - wall_start) / 1000000.0
        if elapsed_s > WALL_CLOCK_TIMEOUT_S:
            fail("capture-free wall-clock AnimationPlayer proof exceeded timeout")
            return
        var position_s := float(player.current_animation_position)
        highest_position = maxf(highest_position, position_s)
        if previous_position >= 0.0 and position_s + 0.000001 < previous_position:
            wall_monotonic_violations += 1
        if previous_ticks >= 0:
            var dt_ms := float(now - previous_ticks) / 1000.0
            wall_min_dt_ms = minf(wall_min_dt_ms, dt_ms)
            wall_max_dt_ms = maxf(wall_max_dt_ms, dt_ms)
            wall_sum_dt_ms += dt_ms
            wall_dt_count += 1
        previous_ticks = now
        previous_position = position_s
        wall_frame_count += 1
        var interval := interval_for_time(animation, reference_track, position_s)
        var comparison := compare_interval_pose(animation, skeleton, bone_indices, binding_info, int(interval["index"]), float(interval["alpha"]))
        wall_max_rotation_error_deg = maxf(wall_max_rotation_error_deg, float(comparison["max_rotation_error_deg"]))
        wall_max_scale_error = maxf(wall_max_scale_error, float(comparison["max_scale_component_error"]))
        if not player.is_playing():
            break
    var wall_elapsed_s := float(Time.get_ticks_usec() - wall_start) / 1000000.0
    if wall_frame_count <= 0:
        fail("wall-clock playback produced no process frames")
        return
    if wall_monotonic_violations != 0:
        fail("wall-clock AnimationPlayer position reversed")
        return
    if highest_position < EXPECTED_DURATION_S - 0.03:
        fail("wall-clock AnimationPlayer did not reach clip end: " + str(highest_position))
        return
    if wall_max_rotation_error_deg > ROTATION_TOLERANCE_DEG:
        fail("wall-clock applied rotation diverged from imported LINEAR track interpolation")
        return
    if wall_max_scale_error > SCALE_TOLERANCE:
        fail("wall-clock applied scale diverged from imported LINEAR track interpolation")
        return

    receipt = {
        "schema": "axm.character-review006-target-host-playback-runtime/v0.1",
        "state": "PASS_DIAGNOSTIC",
        "result": "PASS_CHARACTER_REVIEW006_TARGET_HOST_ANIMATIONPLAYER_INTERPOLATION_AND_PLAYBACK_TRACE",
        "promotion_effect": "NONE",
        "engine": {
            "name": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": "gl_compatibility",
            "adapter": RenderingServer.get_video_adapter_name()
        },
        "identity": {
            "materials_parent_head": EXPECTED_MATERIALS_HEAD,
            "technical_art_head": EXPECTED_TECHNICAL_ART_HEAD,
            "source_animation_head": EXPECTED_SOURCE_ANIMATION_HEAD,
            "rigging_head": EXPECTED_RIGGING_HEAD,
            "target_glb_sha256": EXPECTED_GLB_SHA256,
            "clip_id": clip
        },
        "imported_animation": {
            "duration_s": animation.length,
            "track_count": animation.get_track_count(),
            "track_paths": binding_info["paths"],
            "transport_key_count_per_track": EXPECTED_KEY_COUNT,
            "interpolation_contract": "glTF LINEAR channels imported by target host"
        },
        "midpoint_interpolation": {
            "intervals_checked": EXPECTED_INTERVAL_COUNT,
            "diagnostic_sample_density_hz": 320,
            "maximum_rotation_error_deg": midpoint_max_rotation_error_deg,
            "maximum_scale_component_error": midpoint_max_scale_error,
            "worst_observation": midpoint_worst,
            "rotation_tolerance_deg": ROTATION_TOLERANCE_DEG,
            "scale_component_tolerance": SCALE_TOLERANCE
        },
        "endpoint_closure": closure,
        "negative_control": {
            "kind": "VERIFIER_ONLY_EXPECTED_ROTATION_OFFSET",
            "interval_index": negative_interval,
            "time_s": negative_midpoint,
            "offset_deg": NEGATIVE_OFFSET_DEG,
            "clean_error_deg": clean_error,
            "mutated_error_deg": mutated_error,
            "expected_rejection": negative_rejected
        },
        "wall_clock_playback": {
            "capture_free": true,
            "wall_elapsed_s": wall_elapsed_s,
            "process_frames": wall_frame_count,
            "highest_animation_position_s": highest_position,
            "position_monotonic_violations": wall_monotonic_violations,
            "maximum_rotation_error_deg": wall_max_rotation_error_deg,
            "maximum_scale_component_error": wall_max_scale_error,
            "minimum_process_interval_ms": wall_min_dt_ms if wall_dt_count > 0 else null,
            "maximum_process_interval_ms": wall_max_dt_ms if wall_dt_count > 0 else null,
            "mean_process_interval_ms": wall_sum_dt_ms / float(wall_dt_count) if wall_dt_count > 0 else null,
            "meaning": "Proof-host wall-clock characterization only; no complete 160 Hz display/scheduler or target-device claim."
        },
        "preserved_downstream_boundary": {
            "materials_result": contract["known_downstream_boundary"]["materials_current_motion_result"],
            "materials_artifact_id": contract["known_downstream_boundary"]["materials_direction_frame_artifact_id"],
            "meaning": contract["known_downstream_boundary"]["meaning"]
        },
        "truth_boundary": contract["truth_boundary"]
    }
    write_receipt()
    quit(0)
