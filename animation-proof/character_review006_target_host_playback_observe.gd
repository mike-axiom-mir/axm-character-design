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
const INTERPOLATION_ROTATION_TOLERANCE_DEG := 0.001
const INTERPOLATION_SCALE_TOLERANCE := 0.00001
const WALL_ENDPOINT_TOLERANCE_DEG := 0.05
const MIN_WALL_DISTAL_EXCURSION_DEG := 20.0
const WALL_SYMMETRY_TOLERANCE_DEG := 0.25
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
    "schema": "axm.character-review006-target-host-playback-runtime/v0.3",
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
    receipt["state"] = "FAIL_TARGET_HOST_PLAYBACK_PROOF"
    receipt["result"] = "HOLD_CHARACTER_REVIEW006_TARGET_HOST_PLAYBACK"
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
    var generated = document.generate_scene(state)
    if generated == null or not (generated is Node3D):
        fail("GLTFDocument generate_scene returned no Node3D")
        return null
    return generated as Node3D

func track_type_name(track_type: int) -> String:
    match track_type:
        Animation.TYPE_ROTATION_3D:
            return "TYPE_ROTATION_3D"
        Animation.TYPE_SCALE_3D:
            return "TYPE_SCALE_3D"
        Animation.TYPE_POSITION_3D:
            return "TYPE_POSITION_3D"
        _:
            return "TYPE_%d" % int(track_type)

func interpolation_name(interpolation: int) -> String:
    match interpolation:
        Animation.INTERPOLATION_NEAREST:
            return "NEAREST"
        Animation.INTERPOLATION_LINEAR:
            return "LINEAR"
        Animation.INTERPOLATION_CUBIC:
            return "CUBIC"
        Animation.INTERPOLATION_LINEAR_ANGLE:
            return "LINEAR_ANGLE"
        Animation.INTERPOLATION_CUBIC_ANGLE:
            return "CUBIC_ANGLE"
        _:
            return "UNKNOWN_%d" % int(interpolation)

func track_binding(animation: Animation) -> Dictionary:
    var bindings := {}
    var paths := []
    for bone_name in BONES:
        bindings[bone_name] = {"rotation": -1, "scale": -1}
    for track in range(animation.get_track_count()):
        var path_text := String(animation.track_get_path(track))
        var track_type := animation.track_get_type(track)
        var key_count := animation.track_get_key_count(track)
        var first_time = float(animation.track_get_key_time(track, 0)) if key_count > 0 else null
        var last_time = float(animation.track_get_key_time(track, key_count - 1)) if key_count > 0 else null
        paths.append({
            "index": track,
            "path": path_text,
            "type": int(track_type),
            "type_name": track_type_name(track_type),
            "interpolation": int(animation.track_get_interpolation_type(track)),
            "interpolation_name": interpolation_name(animation.track_get_interpolation_type(track)),
            "key_count": key_count,
            "first_time_s": first_time,
            "last_time_s": last_time
        })
        for bone_name in BONES:
            if path_text.find(bone_name) < 0:
                continue
            if track_type == Animation.TYPE_ROTATION_3D:
                bindings[bone_name]["rotation"] = track
            elif track_type == Animation.TYPE_SCALE_3D:
                bindings[bone_name]["scale"] = track
    return {"bindings": bindings, "paths": paths}

func validate_track_grid(animation: Animation, info: Dictionary) -> bool:
    if animation.get_track_count() != EXPECTED_TRACK_COUNT:
        fail("target-host imported animation track-count drift", {"observed": animation.get_track_count(), "tracks": info["paths"]})
        return false
    for row in info["paths"]:
        var track := int(row["index"])
        if animation.track_get_key_count(track) != EXPECTED_KEY_COUNT:
            fail("target-host imported animation key-count drift", {"track": row, "all_tracks": info["paths"]})
            return false
        if animation.track_get_interpolation_type(track) != Animation.INTERPOLATION_LINEAR:
            fail("target-host imported animation interpolation-mode drift", {"track": row, "all_tracks": info["paths"]})
            return false
        if absf(float(animation.track_get_key_time(track, 0))) > 0.000001:
            fail("target-host first key is not time zero", row)
            return false
        if absf(float(animation.track_get_key_time(track, EXPECTED_KEY_COUNT - 1)) - EXPECTED_DURATION_S) > 0.00001:
            fail("target-host final key time drift", row)
            return false
        for index in range(1, EXPECTED_KEY_COUNT):
            if float(animation.track_get_key_time(track, index)) <= float(animation.track_get_key_time(track, index - 1)):
                fail("target-host imported key times are not strictly increasing", {"track": row, "index": index})
                return false
    for bone_name in BONES:
        if int(info["bindings"][bone_name]["rotation"]) < 0:
            fail("missing target-host rotation track for " + bone_name, {"bindings": info["bindings"], "tracks": info["paths"]})
            return false
    if int(info["bindings"]["shoulder-L-release-transport"]["scale"]) < 0 or int(info["bindings"]["shoulder-R-release-transport"]["scale"]) < 0:
        fail("missing target-host release-helper scale tracks", {"bindings": info["bindings"], "tracks": info["paths"]})
        return false
    if int(info["bindings"]["shoulder-L-distal"]["scale"]) >= 0 or int(info["bindings"]["shoulder-R-distal"]["scale"]) >= 0:
        fail("unexpected distal scale track appeared", {"bindings": info["bindings"], "tracks": info["paths"]})
        return false
    return true

func key_quaternion(animation: Animation, track: int, index: int) -> Quaternion:
    var raw = animation.track_get_key_value(track, index)
    if raw is Quaternion:
        return (raw as Quaternion).normalized()
    fail("rotation track key is not Quaternion", {"track": track, "index": index})
    return Quaternion.IDENTITY

func key_scale(animation: Animation, track: int, index: int) -> Vector3:
    var raw = animation.track_get_key_value(track, index)
    if raw is Vector3:
        return raw as Vector3
    fail("scale track key is not Vector3", {"track": track, "index": index})
    return Vector3.ONE

func rotation_error_deg(a: Quaternion, b: Quaternion) -> float:
    return rad_to_deg(a.normalized().angle_to(b.normalized()))

func scale_error(a: Vector3, b: Vector3) -> float:
    return maxf(absf(a.x - b.x), maxf(absf(a.y - b.y), absf(a.z - b.z)))

func observed_rotation(skeleton: Skeleton3D, bone_indices: Dictionary, bone_name: String) -> Quaternion:
    return skeleton.get_bone_pose_rotation(int(bone_indices[bone_name])).normalized()

func observed_scale(skeleton: Skeleton3D, bone_indices: Dictionary, bone_name: String) -> Vector3:
    return skeleton.get_bone_pose_scale(int(bone_indices[bone_name]))

func apply_pose_time(player: AnimationPlayer, time_s: float) -> void:
    player.seek(time_s, true)
    player.advance(0.0)

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    contract = read_json(CONTRACT_PATH)
    payload = read_json(PAYLOAD_PATH)
    if contract.get("schema") != "axm.character-review006-target-host-playback/v0.1":
        fail("missing or invalid Animation target-host contract")
        return
    if contract.get("materials_parent_head") != EXPECTED_MATERIALS_HEAD or contract.get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD or contract.get("source_animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD or contract.get("rigging_head") != EXPECTED_RIGGING_HEAD:
        fail("Animation target-host lineage identity drift")
        return
    if contract.get("target_glb_sha256") != EXPECTED_GLB_SHA256 or sha256_file(GLB_PATH) != EXPECTED_GLB_SHA256:
        fail("target GLB identity drift")
        return
    if payload.get("schema") != "axm.character-review006-current-motion-direction-frame-payload/v0.1":
        fail("missing exact current-motion payload")
        return
    if payload["exact_identity"].get("technical_art_head") != EXPECTED_TECHNICAL_ART_HEAD or payload["exact_identity"].get("animation_head") != EXPECTED_SOURCE_ANIMATION_HEAD or payload["exact_identity"].get("rigging_head") != EXPECTED_RIGGING_HEAD or payload["exact_identity"].get("target_glb_sha256") != EXPECTED_GLB_SHA256:
        fail("payload exact lineage identity drift")
        return

    var target := import_target()
    if target == null:
        return
    get_root().add_child(target)
    var player := find_player(target)
    var skeleton := find_skeleton(target)
    if player == null or skeleton == null:
        fail("target-host import missing AnimationPlayer or Skeleton3D")
        return
    var clip := String(payload["target"]["clip_id"])
    if not player.has_animation(clip):
        fail("target-host AnimationPlayer missing exact clip", {"clip": clip, "available": Array(player.get_animation_list())})
        return
    var animation: Animation = player.get_animation(clip)
    if animation == null or absf(float(animation.length) - EXPECTED_DURATION_S) > 0.00001:
        fail("target-host clip duration drift")
        return

    var info := track_binding(animation)
    if not validate_track_grid(animation, info):
        return
    # Establish the exact imported clip as AnimationPlayer's active animation before any seek probe.
    player.play(clip)
    player.advance(0.0)
    player.pause()
    var bone_indices := {}
    for bone_name in BONES:
        var bone := skeleton.find_bone(bone_name)
        if bone < 0:
            fail("target-host Skeleton3D missing exact bone: " + bone_name)
            return
        bone_indices[bone_name] = bone

    # v0.3 target-host method: verify LINEAR semantics through the actual AnimationPlayer-applied
    # Skeleton3D pose, not by comparing imported Animation resource keys to pose-space values or
    # trusting typed resource interpolation helpers as a proxy for application. The exact clip,
    # rig, transport GLB and tolerances are unchanged.
    var midpoint_max_rotation_error_deg := 0.0
    var midpoint_max_scale_error := 0.0
    var midpoint_worst := {}
    for interval_index in range(EXPECTED_INTERVAL_COUNT):
        var timing_track := int(info["bindings"]["shoulder-L-distal"]["rotation"])
        var t0 := float(animation.track_get_key_time(timing_track, interval_index))
        var t1 := float(animation.track_get_key_time(timing_track, interval_index + 1))
        var midpoint := (t0 + t1) * 0.5
        if t0 < -0.000001 or t1 > EXPECTED_DURATION_S + 0.000001 or midpoint <= t0 or midpoint >= t1:
            fail("target-host midpoint timing escaped validated interval", {"interval_index": interval_index, "t0": t0, "t1": t1, "midpoint": midpoint})
            return

        apply_pose_time(player, t0)
        var endpoint0 := {}
        for bone_name in BONES:
            endpoint0[bone_name] = {
                "rotation": observed_rotation(skeleton, bone_indices, bone_name),
                "scale": observed_scale(skeleton, bone_indices, bone_name)
            }
        apply_pose_time(player, t1)
        var endpoint1 := {}
        for bone_name in BONES:
            endpoint1[bone_name] = {
                "rotation": observed_rotation(skeleton, bone_indices, bone_name),
                "scale": observed_scale(skeleton, bone_indices, bone_name)
            }
        apply_pose_time(player, midpoint)
        for bone_name in BONES:
            var binding: Dictionary = info["bindings"][bone_name]
            var host_rotation := observed_rotation(skeleton, bone_indices, bone_name)
            var expected_rotation: Quaternion = (endpoint0[bone_name]["rotation"] as Quaternion).slerp(endpoint1[bone_name]["rotation"] as Quaternion, 0.5).normalized()
            var r_error := rotation_error_deg(host_rotation, expected_rotation)
            var s_error := 0.0
            if int(binding["scale"]) >= 0:
                var host_scale := observed_scale(skeleton, bone_indices, bone_name)
                var expected_scale: Vector3 = (endpoint0[bone_name]["scale"] as Vector3).lerp(endpoint1[bone_name]["scale"] as Vector3, 0.5)
                s_error = scale_error(host_scale, expected_scale)
            if r_error > midpoint_max_rotation_error_deg or s_error > midpoint_max_scale_error:
                midpoint_worst = {
                    "interval_index": interval_index,
                    "bone": bone_name,
                    "time_s": midpoint,
                    "rotation_error_deg": r_error,
                    "scale_component_error": s_error
                }
            midpoint_max_rotation_error_deg = maxf(midpoint_max_rotation_error_deg, r_error)
            midpoint_max_scale_error = maxf(midpoint_max_scale_error, s_error)
    if midpoint_max_rotation_error_deg > INTERPOLATION_ROTATION_TOLERANCE_DEG or midpoint_max_scale_error > INTERPOLATION_SCALE_TOLERANCE:
        fail("target-host AnimationPlayer pose-space LINEAR interpolation drift", {
            "rotation_error_deg": midpoint_max_rotation_error_deg,
            "scale_error": midpoint_max_scale_error,
            "worst": midpoint_worst,
            "tracks": info["paths"]
        })
        return

    var negative_interval := 80
    var timing_track := int(info["bindings"]["shoulder-L-distal"]["rotation"])
    var nt0 := float(animation.track_get_key_time(timing_track, negative_interval))
    var nt1 := float(animation.track_get_key_time(timing_track, negative_interval + 1))
    var negative_midpoint := (nt0 + nt1) * 0.5
    apply_pose_time(player, nt0)
    var negative_q0 := observed_rotation(skeleton, bone_indices, "shoulder-L-distal")
    apply_pose_time(player, nt1)
    var negative_q1 := observed_rotation(skeleton, bone_indices, "shoulder-L-distal")
    var clean_expected := negative_q0.slerp(negative_q1, 0.5).normalized()
    apply_pose_time(player, negative_midpoint)
    var host_expected := observed_rotation(skeleton, bone_indices, "shoulder-L-distal")
    var mutated_expected := (Quaternion(Vector3(1.0, 0.0, 0.0), deg_to_rad(NEGATIVE_OFFSET_DEG)) * clean_expected).normalized()
    var clean_error := rotation_error_deg(host_expected, clean_expected)
    var mutated_error := rotation_error_deg(host_expected, mutated_expected)
    var negative_rejected := clean_error <= INTERPOLATION_ROTATION_TOLERANCE_DEG and mutated_error > INTERPOLATION_ROTATION_TOLERANCE_DEG
    if not negative_rejected:
        fail("verifier-only pose-space interpolation negative control did not fail closed", {"clean_error_deg": clean_error, "mutated_error_deg": mutated_error})
        return

    # Reset explicitly to the authored neutral before wall-clock observation; midpoint probing
    # must not leak its final seek state into the wall-clock baseline.
    apply_pose_time(player, 0.0)
    await process_frame
    var neutral_left := observed_rotation(skeleton, bone_indices, "shoulder-L-distal")
    var neutral_right := observed_rotation(skeleton, bone_indices, "shoulder-R-distal")
    var max_left_excursion_deg := 0.0
    var max_right_excursion_deg := 0.0
    var max_bilateral_excursion_delta_deg := 0.0
    var wall_frame_count := 0
    var wall_position_reversals := 0
    var highest_position_s := 0.0
    var previous_position_s := -1.0
    var previous_ticks := -1
    var wall_min_dt_ms := INF
    var wall_max_dt_ms := 0.0
    var wall_sum_dt_ms := 0.0
    var wall_dt_count := 0

    player.stop()
    player.play(clip)
    var wall_start := Time.get_ticks_usec()
    while true:
        await process_frame
        var now := Time.get_ticks_usec()
        var elapsed_s := float(now - wall_start) / 1000000.0
        if elapsed_s > WALL_CLOCK_TIMEOUT_S:
            fail("capture-free wall-clock AnimationPlayer proof exceeded timeout", {"elapsed_s": elapsed_s, "frames": wall_frame_count})
            return
        var still_playing := player.is_playing()
        var position_s := float(player.current_animation_position)
        highest_position_s = maxf(highest_position_s, position_s)
        if still_playing and previous_position_s >= 0.0 and position_s + 0.000001 < previous_position_s:
            wall_position_reversals += 1
        if previous_ticks >= 0:
            var dt_ms := float(now - previous_ticks) / 1000.0
            wall_min_dt_ms = minf(wall_min_dt_ms, dt_ms)
            wall_max_dt_ms = maxf(wall_max_dt_ms, dt_ms)
            wall_sum_dt_ms += dt_ms
            wall_dt_count += 1
        previous_ticks = now
        if still_playing:
            previous_position_s = position_s
        wall_frame_count += 1
        var left_excursion := rotation_error_deg(observed_rotation(skeleton, bone_indices, "shoulder-L-distal"), neutral_left)
        var right_excursion := rotation_error_deg(observed_rotation(skeleton, bone_indices, "shoulder-R-distal"), neutral_right)
        max_left_excursion_deg = maxf(max_left_excursion_deg, left_excursion)
        max_right_excursion_deg = maxf(max_right_excursion_deg, right_excursion)
        max_bilateral_excursion_delta_deg = maxf(max_bilateral_excursion_delta_deg, absf(left_excursion - right_excursion))
        if not still_playing:
            break

    var wall_elapsed_s := float(Time.get_ticks_usec() - wall_start) / 1000000.0
    var final_left := observed_rotation(skeleton, bone_indices, "shoulder-L-distal")
    var final_right := observed_rotation(skeleton, bone_indices, "shoulder-R-distal")
    var final_left_residual_deg := rotation_error_deg(final_left, neutral_left)
    var final_right_residual_deg := rotation_error_deg(final_right, neutral_right)
    if wall_position_reversals != 0:
        fail("wall-clock AnimationPlayer position reversed", {"reversals": wall_position_reversals})
        return
    if highest_position_s < EXPECTED_DURATION_S - 0.03:
        fail("wall-clock AnimationPlayer did not reach clip end", {"highest_position_s": highest_position_s})
        return
    if max_left_excursion_deg < MIN_WALL_DISTAL_EXCURSION_DEG or max_right_excursion_deg < MIN_WALL_DISTAL_EXCURSION_DEG:
        fail("wall-clock AnimationPlayer did not apply meaningful distal shoulder motion", {"left_max_deg": max_left_excursion_deg, "right_max_deg": max_right_excursion_deg})
        return
    if max_bilateral_excursion_delta_deg > WALL_SYMMETRY_TOLERANCE_DEG:
        fail("wall-clock bilateral shoulder excursion symmetry drift", {"max_delta_deg": max_bilateral_excursion_delta_deg})
        return
    if final_left_residual_deg > WALL_ENDPOINT_TOLERANCE_DEG or final_right_residual_deg > WALL_ENDPOINT_TOLERANCE_DEG:
        fail("wall-clock shoulder loop did not close to neutral", {"left_residual_deg": final_left_residual_deg, "right_residual_deg": final_right_residual_deg})
        return

    receipt = {
        "schema": "axm.character-review006-target-host-playback-runtime/v0.3",
        "state": "PASS_DIAGNOSTIC",
        "result": "PASS_CHARACTER_REVIEW006_TARGET_HOST_ANIMATIONPLAYER_INTERPOLATION_AND_PLAYBACK_TRACE",
        "promotion_effect": "NONE",
        "repair_trace": {
            "prior_run_id": 35217194776,
            "prior_artifact_id": 10494834190,
            "prior_failure": "ambiguous resource-helper interpolation receipt reported up to 29.9999160766602 deg rotation error and 1.0 scale error, with a later invalid/default observation at time_s=-1.0",
            "diagnosis": "v0.3 removes the ambiguous imported-resource interpolation helper from the acceptance path and checks midpoint LINEAR behavior through actual AnimationPlayer-applied Skeleton3D pose space; track-grid failures now stop immediately instead of allowing a later receipt overwrite",
            "source_motion_or_tolerance_changed_to_force_pass": false
        },
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
            "track_paths": info["paths"],
            "transport_key_count_per_track": EXPECTED_KEY_COUNT,
            "interpolation_contract": "glTF LINEAR channels imported by target host"
        },
        "midpoint_interpolation": {
            "intervals_checked": EXPECTED_INTERVAL_COUNT,
            "intervals_checked_per_track": EXPECTED_INTERVAL_COUNT,
            "rotation_tracks_checked": 4,
            "scale_tracks_checked": 2,
            "observation_space": "AnimationPlayer-applied Skeleton3D pose space",
            "diagnostic_sample_density_hz": 320,
            "maximum_rotation_error_deg": midpoint_max_rotation_error_deg,
            "maximum_scale_component_error": midpoint_max_scale_error,
            "worst_observation": midpoint_worst,
            "rotation_tolerance_deg": INTERPOLATION_ROTATION_TOLERANCE_DEG,
            "scale_component_tolerance": INTERPOLATION_SCALE_TOLERANCE
        },
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
            "highest_animation_position_s": highest_position_s,
            "position_monotonic_violations": wall_position_reversals,
            "left_distal_max_excursion_deg": max_left_excursion_deg,
            "right_distal_max_excursion_deg": max_right_excursion_deg,
            "maximum_bilateral_excursion_delta_deg": max_bilateral_excursion_delta_deg,
            "left_endpoint_residual_deg": final_left_residual_deg,
            "right_endpoint_residual_deg": final_right_residual_deg,
            "minimum_process_interval_ms": wall_min_dt_ms if wall_dt_count > 0 else null,
            "maximum_process_interval_ms": wall_max_dt_ms if wall_dt_count > 0 else null,
            "mean_process_interval_ms": wall_sum_dt_ms / float(wall_dt_count) if wall_dt_count > 0 else null,
            "meaning": "Actual Skeleton3D pose movement under capture-free AnimationPlayer.play(); proof-host characterization only, not complete 160 Hz display/scheduler or target-device certification."
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
