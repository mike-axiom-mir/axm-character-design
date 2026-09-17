extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_neutral_target_host_isolation_payload.json"
const RECEIPT_PATH := "res://character-review006-neutral-target-host-isolation-runtime-receipt.json"
const CONTEXTS := ["front", "three_quarter", "grazing"]
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.055, 0.06, 0.07, 1.0)
const POSITION_CONTROL_MAX_XOR_FRACTION := 0.0005

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
        "schema": "axm.character-review006-neutral-target-host-isolation-runtime/v0.1",
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

func build_owner_reference_mesh() -> ArrayMesh:
    var ref: Dictionary = payload["neutral_sample"]["reference"]
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var indices := PackedInt32Array()
    for raw in ref["positions"]:
        vertices.append(to_v3(raw))
    for raw in ref["pose_recomputed_normals"]:
        normals.append(to_v3(raw).normalized())
    for raw_face in ref["faces"]:
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

func sample_bounds() -> Dictionary:
    var raw_positions: Array = payload["neutral_sample"]["reference"]["positions"]
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

func configure_camera(camera: Camera3D, context: String) -> void:
    var b := sample_bounds()
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

func seek_neutral(target_scene: Node) -> Dictionary:
    var player := find_animation_player(target_scene)
    if player == null:
        return {"state": "FAIL_ANIMATION_PLAYER_MISSING"}
    var clip := String(payload["target"]["clip_id"])
    if not player.has_animation(clip):
        return {"state": "FAIL_CLIP_MISSING", "clips": Array(player.get_animation_list())}
    player.play(clip)
    player.seek(float(payload["neutral_sample"]["time_s"]), true)
    player.advance(0.0)
    player.pause()
    return {"state": "PASS"}

func detached_mesh_from_imported(mesh_instance: MeshInstance3D, invert_normals: bool) -> ArrayMesh:
    if mesh_instance.mesh == null or mesh_instance.mesh.get_surface_count() != 1:
        return null
    var source: Array = mesh_instance.mesh.surface_get_arrays(0)
    var source_vertices: PackedVector3Array = source[Mesh.ARRAY_VERTEX]
    var source_normals: PackedVector3Array = source[Mesh.ARRAY_NORMAL]
    var source_indices: PackedInt32Array = source[Mesh.ARRAY_INDEX]
    if source_vertices.is_empty() or source_normals.is_empty() or source_indices.is_empty():
        return null
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var indices := PackedInt32Array()
    for v in source_vertices:
        vertices.append(v)
    for n in source_normals:
        normals.append((-n if invert_normals else n).normalized())
    for i in source_indices:
        indices.append(i)
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = vertices
    arrays[Mesh.ARRAY_NORMAL] = normals
    arrays[Mesh.ARRAY_INDEX] = indices
    var mesh := ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    return mesh

func build_world(context: String, variant: String) -> Dictionary:
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

    if variant.begins_with("skinned_"):
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
        var target_mesh: MeshInstance3D = meshes[0]
        target_mesh.material_override = mat
        var seek := seek_neutral(target_scene)
        if seek.get("state") != "PASS":
            viewport.queue_free()
            return seek
    elif variant.begins_with("static_"):
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
        var imported_mesh: MeshInstance3D = meshes[0]
        var seek := seek_neutral(target_scene)
        if seek.get("state") != "PASS":
            viewport.queue_free()
            return seek
        var clone_mesh := detached_mesh_from_imported(imported_mesh, variant.begins_with("static_inverted_"))
        if clone_mesh == null:
            viewport.queue_free()
            return {"state": "FAIL_DETACHED_MESH"}
        var imported_global := imported_mesh.global_transform
        imported_mesh.visible = false
        var clone := MeshInstance3D.new()
        clone.mesh = clone_mesh
        clone.material_override = mat
        root3d.add_child(clone)
        clone.global_transform = imported_global
    else:
        var owner := MeshInstance3D.new()
        owner.mesh = build_owner_reference_mesh()
        owner.material_override = mat
        root3d.add_child(owner)

    var camera := Camera3D.new()
    configure_camera(camera, context)
    root3d.add_child(camera)
    camera.current = true
    return {"state": "PASS", "viewport": viewport}

func capture(context: String, variant: String) -> Dictionary:
    var built := build_world(context, variant)
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
    var path := "res://character-review006-neutral-isolation-%s-%s.png" % [context, variant]
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

func raw_import_audit() -> Dictionary:
    var target_scene := instantiate_target()
    if target_scene == null:
        return {"state": "FAIL_GLTF_IMPORT"}
    var meshes: Array = []
    collect_meshes(target_scene, meshes)
    if meshes.size() != 1:
        return {"state": "FAIL_TARGET_MESH_COUNT", "mesh_count": meshes.size()}
    var imported: MeshInstance3D = meshes[0]
    if imported.mesh == null or imported.mesh.get_surface_count() != 1:
        return {"state": "FAIL_TARGET_SURFACE_COUNT"}
    var arrays: Array = imported.mesh.surface_get_arrays(0)
    var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
    var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
    var ref: Dictionary = payload["neutral_sample"]["reference"]
    if vertices.size() != ref["positions"].size() or normals.size() != ref["pose_recomputed_normals"].size():
        return {
            "state": "FAIL_TARGET_ARRAY_COUNT",
            "vertices": vertices.size(),
            "reference_vertices": ref["positions"].size(),
            "normals": normals.size(),
            "reference_normals": ref["pose_recomputed_normals"].size()
        }
    var max_position_component_delta := 0.0
    var max_normal_component_delta := 0.0
    for i in range(vertices.size()):
        var rp := to_v3(ref["positions"][i])
        var rn := to_v3(ref["pose_recomputed_normals"][i]).normalized()
        var p := vertices[i]
        var n := normals[i].normalized()
        max_position_component_delta = maxf(
            max_position_component_delta,
            maxf(absf(p.x-rp.x), maxf(absf(p.y-rp.y), absf(p.z-rp.z))))
        max_normal_component_delta = maxf(
            max_normal_component_delta,
            maxf(absf(n.x-rn.x), maxf(absf(n.y-rn.y), absf(n.z-rn.z))))
    var expected_indices := PackedInt32Array()
    for face_raw in ref["faces"]:
        var face: Array = face_raw
        expected_indices.append(int(face[0]))
        expected_indices.append(int(face[1]))
        expected_indices.append(int(face[2]))
    var index_mismatch_count := 0
    if indices.size() != expected_indices.size():
        index_mismatch_count = maxi(indices.size(), expected_indices.size())
    else:
        for i in range(indices.size()):
            if indices[i] != expected_indices[i]:
                index_mismatch_count += 1
    return {
        "state": "PASS",
        "vertex_count": vertices.size(),
        "normal_count": normals.size(),
        "index_count": indices.size(),
        "max_position_component_delta": max_position_component_delta,
        "max_normal_component_delta": max_normal_component_delta,
        "index_mismatch_count": index_mismatch_count
    }

func _initialize() -> void:
    call_deferred("run_observer")

func run_observer() -> void:
    payload = read_json(PAYLOAD_PATH)
    if payload.get("schema") != "axm.character-review006-neutral-target-host-isolation-payload/v0.1":
        fail("missing or invalid neutral target-host isolation payload")
        return
    if payload["exact_identity"].get("technical_art_current_head") != "c007c327f2613989581192602338435b67b748d7":
        fail("current Technical Art identity drift")
        return
    if payload["exact_identity"].get("target_glb_sha256") != "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99":
        fail("current target GLB digest drift")
        return

    var raw_audit := raw_import_audit()
    if raw_audit.get("state") != "PASS":
        fail("raw imported surface audit failed: %s" % str(raw_audit))
        return

    var receipt := {
        "schema": "axm.character-review006-neutral-target-host-isolation-runtime/v0.1",
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
        "raw_import_audit": raw_audit,
        "comparisons": {},
        "position_control_clean_all_contexts": true,
        "static_closer_to_owner_all_contexts": true,
        "negative_control_visible_all_contexts": true,
        "truth_boundary": payload["truth_boundary"]
    }

    for context in CONTEXTS:
        var captures := {}
        for variant in [
            "skinned_unshaded",
            "static_unshaded",
            "owner_unshaded",
            "skinned_shaded",
            "static_shaded",
            "owner_shaded",
            "static_inverted_shaded"
        ]:
            var cap := await capture(context, variant)
            if cap.get("state") != "PASS":
                fail("capture failed: %s/%s -> %s" % [context, variant, str(cap)])
                return
            captures[variant] = cap

        var skinned_static_coverage := coverage_xor(captures["skinned_unshaded"]["image"], captures["static_unshaded"]["image"])
        var static_owner_coverage := coverage_xor(captures["static_unshaded"]["image"], captures["owner_unshaded"]["image"])
        if float(skinned_static_coverage["frame_fraction"]) > POSITION_CONTROL_MAX_XOR_FRACTION or float(static_owner_coverage["frame_fraction"]) > POSITION_CONTROL_MAX_XOR_FRACTION:
            receipt["position_control_clean_all_contexts"] = false

        var skinned_to_static := masked_diff(
            captures["skinned_shaded"]["image"], captures["static_shaded"]["image"],
            captures["skinned_unshaded"]["image"], captures["static_unshaded"]["image"])
        var static_to_owner := masked_diff(
            captures["static_shaded"]["image"], captures["owner_shaded"]["image"],
            captures["static_unshaded"]["image"], captures["owner_unshaded"]["image"])
        var skinned_to_owner := masked_diff(
            captures["skinned_shaded"]["image"], captures["owner_shaded"]["image"],
            captures["skinned_unshaded"]["image"], captures["owner_unshaded"]["image"])
        var inverted_to_static := masked_diff(
            captures["static_inverted_shaded"]["image"], captures["static_shaded"]["image"],
            captures["static_unshaded"]["image"], captures["static_unshaded"]["image"])

        var static_closer := float(static_to_owner["mean_abs_rgb_channel_delta"]) < float(skinned_to_owner["mean_abs_rgb_channel_delta"])
        if not static_closer:
            receipt["static_closer_to_owner_all_contexts"] = false
        if int(inverted_to_static["changed_pixels_gt_1lsb"]) <= 0:
            receipt["negative_control_visible_all_contexts"] = false

        receipt["comparisons"][context] = {
            "skinned_to_static_position_control": skinned_static_coverage,
            "static_to_owner_position_control": static_owner_coverage,
            "skinned_to_static_shaded": skinned_to_static,
            "static_to_owner_shaded": static_to_owner,
            "skinned_to_owner_shaded": skinned_to_owner,
            "inverted_to_static_negative": inverted_to_static,
            "static_closer_to_owner_than_skinned": static_closer
        }

    if not receipt["position_control_clean_all_contexts"]:
        receipt["result"] = "INCONCLUSIVE_CHARACTER_REVIEW006_NEUTRAL_ISOLATION__POSITION_CONTROL_MISMATCH"
    elif not receipt["negative_control_visible_all_contexts"]:
        receipt["result"] = "INCONCLUSIVE_CHARACTER_REVIEW006_NEUTRAL_ISOLATION__NORMAL_OBSERVER_INSENSITIVE"
    elif receipt["static_closer_to_owner_all_contexts"]:
        receipt["result"] = "DIAGNOSTIC_CHARACTER_REVIEW006_NEUTRAL_DIVERGENCE_IS_AFTER_RAW_IMPORTED_SURFACE_ARRAYS"
    else:
        receipt["result"] = "HOLD_CHARACTER_REVIEW006_NEUTRAL_DIVERGENCE_INCLUDES_STATIC_IMPORTED_SURFACE_OR_TRANSFORM_PATH"

    write_receipt(receipt)
    quit(0)
