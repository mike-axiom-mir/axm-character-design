extends SceneTree

const EVIDENCE_PATH := "res://generated/review006-accessor-sharing-adoption/result.json"
const CONTROL_PATH := "res://generated/review006-accessor-sharing-adoption/review006-control-duplicate-release-scale.glb"
const CANDIDATE_PATH := "res://generated/review006-accessor-sharing-adoption/review006-technical-art-shared-release-scale.glb"
const RECEIPT_PATH := "res://character-review006-exact-accessor-sharing-adoption-runtime-receipt.json"
const TOLERANCE := 1.0e-7

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

func fail(message: String, extra: Dictionary = {}) -> void:
    var receipt := {
        "schema": "axm.character-review006-exact-accessor-sharing-godot-receiver/v0.1",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    }
    for key in extra:
        receipt[key] = extra[key]
    write_receipt(receipt)
    push_error(message)
    quit(1)

func instantiate_glb(path: String) -> Node:
    var document := GLTFDocument.new()
    var state := GLTFState.new()
    var err := document.append_from_file(path, state)
    if err != OK:
        return null
    return document.generate_scene(state)

func find_animation_player(node: Node) -> AnimationPlayer:
    if node is AnimationPlayer:
        return node as AnimationPlayer
    for child in node.get_children():
        var found := find_animation_player(child)
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

func collect_meshes(node: Node, out: Array) -> void:
    if node is MeshInstance3D:
        out.append(node)
    for child in node.get_children():
        collect_meshes(child, out)

func scalar_delta(a: float, b: float) -> float:
    return absf(a - b)

func variant_delta(a: Variant, b: Variant) -> float:
    if typeof(a) != typeof(b):
        return INF
    if a is Vector3:
        var av: Vector3 = a
        var bv: Vector3 = b
        return maxf(absf(av.x - bv.x), maxf(absf(av.y - bv.y), absf(av.z - bv.z)))
    if a is Quaternion:
        var aq: Quaternion = a
        var bq: Quaternion = b
        return maxf(absf(aq.x - bq.x), maxf(absf(aq.y - bq.y), maxf(absf(aq.z - bq.z), absf(aq.w - bq.w))))
    if a is float or a is int:
        return absf(float(a) - float(b))
    return 0.0 if a == b else INF

func compare_animations(control: AnimationPlayer, candidate: AnimationPlayer) -> Dictionary:
    var control_clips := Array(control.get_animation_list())
    var candidate_clips := Array(candidate.get_animation_list())
    if control_clips != candidate_clips or control_clips.size() != 1:
        return {"state": "FAIL_CLIP_IDENTITY", "control": control_clips, "candidate": candidate_clips}
    var clip := String(control_clips[0])
    var a := control.get_animation(clip)
    var b := candidate.get_animation(clip)
    if a == null or b == null:
        return {"state": "FAIL_CLIP_MISSING", "clip": clip}
    if a.get_track_count() != b.get_track_count():
        return {"state": "FAIL_TRACK_COUNT", "control": a.get_track_count(), "candidate": b.get_track_count()}
    var max_key_delta := 0.0
    var max_time_delta := 0.0
    var total_keys := 0
    var tracks := []
    for track_index in range(a.get_track_count()):
        if String(a.track_get_path(track_index)) != String(b.track_get_path(track_index)):
            return {"state": "FAIL_TRACK_PATH", "track": track_index}
        if a.track_get_type(track_index) != b.track_get_type(track_index):
            return {"state": "FAIL_TRACK_TYPE", "track": track_index}
        if a.track_get_interpolation_type(track_index) != b.track_get_interpolation_type(track_index):
            return {"state": "FAIL_TRACK_INTERPOLATION", "track": track_index}
        var key_count := a.track_get_key_count(track_index)
        if key_count != b.track_get_key_count(track_index):
            return {"state": "FAIL_KEY_COUNT", "track": track_index}
        for key_index in range(key_count):
            max_time_delta = maxf(max_time_delta, absf(a.track_get_key_time(track_index, key_index) - b.track_get_key_time(track_index, key_index)))
            max_key_delta = maxf(max_key_delta, variant_delta(a.track_get_key_value(track_index, key_index), b.track_get_key_value(track_index, key_index)))
        total_keys += key_count
        tracks.append({
            "index": track_index,
            "path": String(a.track_get_path(track_index)),
            "type": int(a.track_get_type(track_index)),
            "interpolation": int(a.track_get_interpolation_type(track_index)),
            "keys": key_count
        })
    return {
        "state": "PASS",
        "clip": clip,
        "track_count": a.get_track_count(),
        "total_keys": total_keys,
        "maximum_key_value_component_delta": max_key_delta,
        "maximum_key_time_delta_s": max_time_delta,
        "tracks": tracks
    }

func compare_meshes(control_scene: Node, candidate_scene: Node) -> Dictionary:
    var control_meshes: Array = []
    var candidate_meshes: Array = []
    collect_meshes(control_scene, control_meshes)
    collect_meshes(candidate_scene, candidate_meshes)
    if control_meshes.size() != candidate_meshes.size() or control_meshes.size() != 1:
        return {"state": "FAIL_MESH_COUNT", "control": control_meshes.size(), "candidate": candidate_meshes.size()}
    var first: Mesh = control_meshes[0].mesh
    var second: Mesh = candidate_meshes[0].mesh
    if first.get_surface_count() != second.get_surface_count():
        return {"state": "FAIL_SURFACE_COUNT"}
    var max_position_delta := 0.0
    var max_normal_delta := 0.0
    var index_mismatches := 0
    var vertices := 0
    var indices := 0
    for surface in range(first.get_surface_count()):
        var a: Array = first.surface_get_arrays(surface)
        var b: Array = second.surface_get_arrays(surface)
        var av: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
        var bv: PackedVector3Array = b[Mesh.ARRAY_VERTEX]
        var an: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
        var bn: PackedVector3Array = b[Mesh.ARRAY_NORMAL]
        var ai: PackedInt32Array = a[Mesh.ARRAY_INDEX]
        var bi: PackedInt32Array = b[Mesh.ARRAY_INDEX]
        if av.size() != bv.size() or an.size() != bn.size() or ai.size() != bi.size():
            return {"state": "FAIL_ARRAY_COUNT", "surface": surface}
        for i in range(av.size()):
            max_position_delta = maxf(max_position_delta, variant_delta(av[i], bv[i]))
        for i in range(an.size()):
            max_normal_delta = maxf(max_normal_delta, variant_delta(an[i], bn[i]))
        for i in range(ai.size()):
            index_mismatches += int(ai[i] != bi[i])
        vertices += av.size()
        indices += ai.size()
    return {
        "state": "PASS",
        "vertices": vertices,
        "indices": indices,
        "maximum_position_component_delta": max_position_delta,
        "maximum_normal_component_delta": max_normal_delta,
        "index_mismatches": index_mismatches
    }

func skeleton_delta(control: Skeleton3D, candidate: Skeleton3D) -> Dictionary:
    if control.get_bone_count() != candidate.get_bone_count():
        return {"state": "FAIL_BONE_COUNT", "control": control.get_bone_count(), "candidate": candidate.get_bone_count()}
    var max_position_delta := 0.0
    var max_rotation_delta := 0.0
    var max_scale_delta := 0.0
    for bone in range(control.get_bone_count()):
        if control.get_bone_name(bone) != candidate.get_bone_name(bone):
            return {"state": "FAIL_BONE_NAME", "bone": bone}
        max_position_delta = maxf(max_position_delta, variant_delta(control.get_bone_pose_position(bone), candidate.get_bone_pose_position(bone)))
        max_rotation_delta = maxf(max_rotation_delta, variant_delta(control.get_bone_pose_rotation(bone), candidate.get_bone_pose_rotation(bone)))
        max_scale_delta = maxf(max_scale_delta, variant_delta(control.get_bone_pose_scale(bone), candidate.get_bone_pose_scale(bone)))
    return {
        "state": "PASS",
        "bone_count": control.get_bone_count(),
        "maximum_position_component_delta": max_position_delta,
        "maximum_rotation_component_delta": max_rotation_delta,
        "maximum_scale_component_delta": max_scale_delta
    }

func seek_player(player: AnimationPlayer, clip: String, time_s: float) -> void:
    player.play(clip)
    player.seek(time_s, true)
    player.advance(0.0)
    player.pause()

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    var evidence := read_json(EVIDENCE_PATH)
    if evidence.get("result") != "PASS_CHARACTER_REVIEW006_RUNTIME_EXACT_ACCESSOR_SHARING_ADOPTED_AT_TECHNICAL_ART_EXPORT_BOUNDARY_TO_CURRENT_UC":
        fail("missing or non-green Technical Art accessor-sharing evidence")
        return
    var control_scene := instantiate_glb(CONTROL_PATH)
    var candidate_scene := instantiate_glb(CANDIDATE_PATH)
    if control_scene == null or candidate_scene == null:
        fail("Godot failed to import control or candidate GLB")
        return
    get_root().add_child(control_scene)
    get_root().add_child(candidate_scene)

    var control_player := find_animation_player(control_scene)
    var candidate_player := find_animation_player(candidate_scene)
    var control_skeleton := find_skeleton(control_scene)
    var candidate_skeleton := find_skeleton(candidate_scene)
    if control_player == null or candidate_player == null or control_skeleton == null or candidate_skeleton == null:
        fail("Godot import did not expose expected AnimationPlayer/Skeleton3D")
        return

    var animation := compare_animations(control_player, candidate_player)
    if animation.get("state") != "PASS":
        fail("imported animation resources differ", {"animation": animation})
        return
    var mesh := compare_meshes(control_scene, candidate_scene)
    if mesh.get("state") != "PASS":
        fail("imported mesh resources differ", {"mesh": mesh})
        return

    var clip := String(animation["clip"])
    var imported_animation: Animation = control_player.get_animation(clip)
    var key_count := imported_animation.track_get_key_count(0)
    if key_count != 321:
        fail("bounded receiver expected 321 imported dense keys", {"key_count": key_count})
        return

    var max_pose_position_delta := 0.0
    var max_pose_rotation_delta := 0.0
    var max_pose_scale_delta := 0.0
    var compared_samples := 0
    for key_index in range(key_count):
        var time_s := imported_animation.track_get_key_time(0, key_index)
        seek_player(control_player, clip, time_s)
        seek_player(candidate_player, clip, time_s)
        var row := skeleton_delta(control_skeleton, candidate_skeleton)
        if row.get("state") != "PASS":
            fail("imported skeleton identity differs", {"sample": key_index, "row": row})
            return
        max_pose_position_delta = maxf(max_pose_position_delta, float(row["maximum_position_component_delta"]))
        max_pose_rotation_delta = maxf(max_pose_rotation_delta, float(row["maximum_rotation_component_delta"]))
        max_pose_scale_delta = maxf(max_pose_scale_delta, float(row["maximum_scale_component_delta"]))
        compared_samples += 1

    seek_player(control_player, clip, imported_animation.track_get_key_time(0, 160))
    seek_player(candidate_player, clip, imported_animation.track_get_key_time(0, 160))
    var before := skeleton_delta(control_skeleton, candidate_skeleton)
    if before.get("state") != "PASS" or float(before["maximum_scale_component_delta"]) > TOLERANCE:
        fail("negative-control baseline is not clean", {"before": before})
        return
    var negative_bone := 1 if candidate_skeleton.get_bone_count() > 1 else 0
    var scale := candidate_skeleton.get_bone_pose_scale(negative_bone)
    candidate_skeleton.set_bone_pose_scale(negative_bone, scale + Vector3(0.01, 0.0, 0.0))
    var negative := skeleton_delta(control_skeleton, candidate_skeleton)
    var negative_visible: bool = negative.get("state") == "PASS" and float(negative["maximum_scale_component_delta"]) >= 0.009

    var exact_under_bound: bool = (
        float(animation["maximum_key_value_component_delta"]) <= TOLERANCE
        and float(animation["maximum_key_time_delta_s"]) <= TOLERANCE
        and float(mesh["maximum_position_component_delta"]) <= TOLERANCE
        and float(mesh["maximum_normal_component_delta"]) <= TOLERANCE
        and int(mesh["index_mismatches"]) == 0
        and max_pose_position_delta <= TOLERANCE
        and max_pose_rotation_delta <= TOLERANCE
        and max_pose_scale_delta <= TOLERANCE
        and negative_visible
    )
    var receipt := {
        "schema": "axm.character-review006-exact-accessor-sharing-godot-receiver/v0.1",
        "state": "PASS_DIAGNOSTIC",
        "result": "PASS_CHARACTER_REVIEW006_TECHNICAL_ART_SHARED_ACCESSOR_GODOT_IMPORT_AND_DENSE_SKIN_POSE_EQUIVALENCE" if exact_under_bound else "HOLD_CHARACTER_REVIEW006_TECHNICAL_ART_SHARED_ACCESSOR_GODOT_EQUIVALENCE",
        "renderer": {
            "engine": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": "gl_compatibility",
            "adapter": RenderingServer.get_video_adapter_name()
        },
        "control_glb_sha256": evidence["control"]["sha256"],
        "candidate_glb_sha256": evidence["candidate"]["sha256"],
        "animation_resource_equivalence": animation,
        "mesh_resource_equivalence": mesh,
        "dense_skin_pose_equivalence": {
            "samples": compared_samples,
            "maximum_position_component_delta": max_pose_position_delta,
            "maximum_rotation_component_delta": max_pose_rotation_delta,
            "maximum_scale_component_delta": max_pose_scale_delta
        },
        "negative_control": {
            "mutation": "verifier-only +0.01 X scale on one imported candidate bone at neutral",
            "observed_maximum_scale_delta": negative.get("maximum_scale_component_delta", INF),
            "observer_sensitive": negative_visible
        },
        "truth_boundary": {
            "real_target_engine_import": "EVALUATED",
            "real_target_engine_dense_key_skin_pose_equivalence": "EVALUATED_321_KEYS",
            "rendered_frame_equivalence": "NOT_EVALUATED",
            "target_device_performance": "NOT_EVALUATED",
            "tangent_or_tangent_space": "NOT_EVALUATED",
            "art_or_visual_qa_acceptance": false,
            "universal_godot_rule": false,
            "uc_modified": false,
            "canon": false,
            "production_readiness": false
        }
    }
    write_receipt(receipt)
    quit(0)
