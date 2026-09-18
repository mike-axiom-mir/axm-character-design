extends SceneTree

const PAYLOAD_PATH := "res://generated/character_review006_target_host_winding_bridge_payload.json"
const RECEIPT_PATH := "res://character-review006-target-host-winding-bridge-runtime-receipt.json"
const FRAME_SIZE := Vector2i(900, 700)
const BACKGROUND := Color(0.055, 0.06, 0.07, 1.0)
const POSITION_CONTROL_MAX_XOR_FRACTION := 0.0005
const ADAPTED_SHADED_MAX_MEAN_DELTA := 0.002
const NATIVE_SHADED_MIN_MEAN_DELTA := 0.05

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
        "schema": "axm.character-review006-target-host-winding-bridge-runtime/v0.1",
        "state": "FAIL_INFRASTRUCTURE",
        "failure": message,
        "promotion_effect": "NONE"
    })
    push_error(message)
    quit(1)

func to_v3(raw: Array) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func make_material(unshaded: bool) -> StandardMaterial3D:
    var spec: Dictionary = payload["materials_fixture"]
    var c: Array = spec["albedo_srgb"]
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(float(c[0]), float(c[1]), float(c[2]), 1.0)
    mat.metallic = float(spec["metallic"])
    mat.roughness = float(spec["roughness"])
    mat.cull_mode = BaseMaterial3D.CULL_BACK
    if unshaded:
        mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    return mat

func sample_bounds() -> Dictionary:
    var raw_positions: Array = payload["neutral_reference"]["positions"]
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
    player.seek(float(payload["target"]["neutral_time_s"]), true)
    player.advance(0.0)
    player.pause()
    return {"state": "PASS"}

func build_reference_mesh(adapted: bool, invert_normals: bool = false) -> ArrayMesh:
    var ref: Dictionary = payload["neutral_reference"]
    var vertices := PackedVector3Array()
    var normals := PackedVector3Array()
    var indices := PackedInt32Array()
    for raw in ref["positions"]:
        vertices.append(to_v3(raw))
    for raw in ref["normals"]:
        var n := to_v3(raw).normalized()
        normals.append(-n if invert_normals else n)
    var key := "receiver_winding_candidate_faces" if adapted else "owner_faces"
    for raw_face in ref[key]:
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

func detached_mesh_from_imported(mesh_instance: MeshInstance3D) -> ArrayMesh:
    if mesh_instance.mesh == null or mesh_instance.mesh.get_surface_count() != 1:
        return null
    var source: Array = mesh_instance.mesh.surface_get_arrays(0)
    var vertices: PackedVector3Array = source[Mesh.ARRAY_VERTEX]
    var normals: PackedVector3Array = source[Mesh.ARRAY_NORMAL]
    var indices: PackedInt32Array = source[Mesh.ARRAY_INDEX]
    if vertices.is_empty() or normals.is_empty() or indices.is_empty():
        return null
    var arrays := []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = vertices.duplicate()
    arrays[Mesh.ARRAY_NORMAL] = normals.duplicate()
    arrays[Mesh.ARRAY_INDEX] = indices.duplicate()
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
    var mat := make_material(variant.ends_with("_unshaded"))

    if variant.begins_with("imported_"):
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
        var clone_mesh := detached_mesh_from_imported(imported_mesh)
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
        var adapted := variant.begins_with("adapted_") or variant.begins_with("adapted_inverted_")
        var inverted := variant.begins_with("adapted_inverted_")
        var owner := MeshInstance3D.new()
        owner.mesh = build_reference_mesh(adapted, inverted)
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
    var path := "res://character-review006-target-host-winding-%s-%s.png" % [context, variant]
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

func raw_import_audit() -> Dictionary:
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
    var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
    var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
    var ref: Dictionary = payload["neutral_reference"]
    if vertices.size() != ref["positions"].size() or normals.size() != ref["normals"].size():
        target_scene.queue_free()
        return {"state": "FAIL_TARGET_ARRAY_COUNT"}

    var max_position_component_delta := 0.0
    var max_normal_component_delta := 0.0
    for i in range(vertices.size()):
        var rp := to_v3(ref["positions"][i])
        var rn := to_v3(ref["normals"][i]).normalized()
        var p := vertices[i]
        var n := normals[i].normalized()
        max_position_component_delta = maxf(max_position_component_delta, maxf(absf(p.x-rp.x), maxf(absf(p.y-rp.y), absf(p.z-rp.z))))
        max_normal_component_delta = maxf(max_normal_component_delta, maxf(absf(n.x-rn.x), maxf(absf(n.y-rn.y), absf(n.z-rn.z))))

    var owner_flat := flat_indices(ref["owner_faces"])
    var reversed_flat := flat_indices(ref["receiver_winding_candidate_faces"])
    var owner_mismatches := mismatch_count(indices, owner_flat)
    var reversed_mismatches := mismatch_count(indices, reversed_flat)
    var exact_owner_triangles := 0
    var exact_reversed_triangles := 0
    var triangle_count := int(indices.size() / 3)
    for triangle_index in range(triangle_count):
        var base := triangle_index * 3
        if int(indices[base]) == int(owner_flat[base]) and int(indices[base+1]) == int(owner_flat[base+1]) and int(indices[base+2]) == int(owner_flat[base+2]):
            exact_owner_triangles += 1
        if int(indices[base]) == int(reversed_flat[base]) and int(indices[base+1]) == int(reversed_flat[base+1]) and int(indices[base+2]) == int(reversed_flat[base+2]):
            exact_reversed_triangles += 1

    var mutated := reversed_flat.duplicate()
    mutated[1] = owner_flat[1]
    mutated[2] = owner_flat[2]
    var mutated_mismatches := mismatch_count(indices, mutated)
    var xform := imported.global_transform
    var result := {
        "state": "PASS",
        "vertex_count": vertices.size(),
        "normal_count": normals.size(),
        "index_count": indices.size(),
        "triangle_count": triangle_count,
        "max_position_component_delta": max_position_component_delta,
        "max_normal_component_delta": max_normal_component_delta,
        "owner_order_mismatch_count": owner_mismatches,
        "reversed_winding_mismatch_count": reversed_mismatches,
        "exact_owner_triangles": exact_owner_triangles,
        "exact_reversed_triangles": exact_reversed_triangles,
        "mutated_candidate_mismatch_count": mutated_mismatches,
        "imported_global_transform": {
            "basis_determinant": xform.basis.determinant(),
            "origin": [xform.origin.x, xform.origin.y, xform.origin.z],
            "basis_x": [xform.basis.x.x, xform.basis.x.y, xform.basis.x.z],
            "basis_y": [xform.basis.y.x, xform.basis.y.y, xform.basis.y.z],
            "basis_z": [xform.basis.z.x, xform.basis.z.y, xform.basis.z.z]
        }
    }
    target_scene.queue_free()
    return result

func _initialize() -> void:
    payload = read_json(PAYLOAD_PATH)
    if payload.is_empty():
        fail("target-host winding payload missing")
        return
    if String(payload.get("schema", "")) != "axm.character-review006-target-host-winding-bridge-payload/v0.1":
        fail("target-host winding payload schema drift")
        return
    call_deferred("run_observer")

func run_observer() -> void:
    var audit := raw_import_audit()
    if audit.get("state") != "PASS":
        fail("raw import audit failed: %s" % JSON.stringify(audit))
        return

    var comparisons := {}
    var adapted_clean := true
    var native_still_divergent := true
    var negative_visible := true
    for context in payload["materials_fixture"]["contexts"]:
        var imported_shaded := await capture(context, "imported_shaded")
        var imported_unshaded := await capture(context, "imported_unshaded")
        var native_shaded := await capture(context, "native_shaded")
        var native_unshaded := await capture(context, "native_unshaded")
        var adapted_shaded := await capture(context, "adapted_shaded")
        var adapted_unshaded := await capture(context, "adapted_unshaded")
        var inverted_shaded := await capture(context, "adapted_inverted_shaded")
        for row in [imported_shaded, imported_unshaded, native_shaded, native_unshaded, adapted_shaded, adapted_unshaded, inverted_shaded]:
            if row.get("state") != "PASS":
                fail("render failed in %s: %s" % [context, JSON.stringify(row)])
                return

        var adapted_position := coverage_xor(imported_unshaded["image"], adapted_unshaded["image"])
        var native_position := coverage_xor(imported_unshaded["image"], native_unshaded["image"])
        var adapted_diff := masked_diff(imported_shaded["image"], adapted_shaded["image"], imported_unshaded["image"], adapted_unshaded["image"])
        var native_diff := masked_diff(imported_shaded["image"], native_shaded["image"], imported_unshaded["image"], native_unshaded["image"])
        var negative_diff := masked_diff(imported_shaded["image"], inverted_shaded["image"], imported_unshaded["image"], adapted_unshaded["image"])
        comparisons[context] = {
            "imported_to_adapted_position_control": adapted_position,
            "imported_to_native_position_control": native_position,
            "imported_to_adapted_shaded": adapted_diff,
            "imported_to_native_shaded": native_diff,
            "imported_to_adapted_inverted_negative": negative_diff,
        }
        adapted_clean = adapted_clean and float(adapted_position["frame_fraction"]) <= POSITION_CONTROL_MAX_XOR_FRACTION and float(adapted_diff["mean_abs_rgb_channel_delta"]) <= ADAPTED_SHADED_MAX_MEAN_DELTA
        native_still_divergent = native_still_divergent and float(native_diff["mean_abs_rgb_channel_delta"]) >= NATIVE_SHADED_MIN_MEAN_DELTA
        negative_visible = negative_visible and int(negative_diff["changed_pixels_gt_1lsb"]) > 0

    var exact_reversed := int(audit["triangle_count"]) == 360 and int(audit["owner_order_mismatch_count"]) == 720 and int(audit["reversed_winding_mismatch_count"]) == 0 and int(audit["exact_reversed_triangles"]) == 360
    var mutation_rejected := int(audit["mutated_candidate_mismatch_count"]) > 0
    var result := "PASS_CHARACTER_REVIEW006_GODOT_GLTF_TO_ARRAYMESH_WINDING_REFERENCE_BRIDGE__HOLD_DEFORMED_DIRECTION_FRAME" if exact_reversed and mutation_rejected and adapted_clean and native_still_divergent and negative_visible else "HOLD_CHARACTER_REVIEW006_TARGET_HOST_WINDING_BRIDGE_NOT_CLOSED"
    var receipt := {
        "schema": "axm.character-review006-target-host-winding-bridge-runtime/v0.1",
        "state": "PASS_DIAGNOSTIC",
        "result": result,
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "raw_import_audit": audit,
        "comparisons": comparisons,
        "gates": {
            "exact_per_triangle_reversed_winding_relation": exact_reversed,
            "mutated_candidate_rejected": mutation_rejected,
            "adapted_reference_neutral_receiver_clean": adapted_clean,
            "unadapted_reference_divergence_retained": native_still_divergent,
            "direction_frame_negative_visible": negative_visible,
        },
        "renderer": {
            "engine": "Godot",
            "version": Engine.get_version_info().get("string", "unknown"),
            "rendering_method": RenderingServer.get_current_rendering_method(),
            "adapter": RenderingServer.get_video_adapter_name(),
            "frame_size": [FRAME_SIZE.x, FRAME_SIZE.y]
        },
        "truth_boundary": {
            "neutral_receiver_winding_bridge": exact_reversed and adapted_clean,
            "universal_godot_rule": false,
            "source_topology_rewritten": false,
            "source_normals_rewritten": false,
            "uc_product_modified": false,
            "deformed_normals_or_tangents": false,
            "art_or_qa_acceptance": false,
            "canon": false,
            "production_ready": false
        }
    }
    write_receipt(receipt)
    print(JSON.stringify(receipt, "  "))
    quit(0 if result.begins_with("PASS_") else 2)
