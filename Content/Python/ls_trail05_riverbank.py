"""Dress the landing-to-crossing stretch of Wildwood as a washed-out riverbank."""

import math

import unreal

from ls_generate_player_meshes import Mesh
from ls_generate_world_meshes import add_tube
from ls_material_helpers import blend, colour, combine, finish, fresh_material, library, node, number, output, texture
from ls_world_common import import_generated_mesh

FOLDER = "Parkour/Trail 05 Riverbank"
OLD_HINT = "Wither Blobs drain the colour from the world. Slam on them from above as Stone Shell."
ROOT_HINT = "Roll over the shallow root, then jump over the larger one."
STUMP = (17970.0, -856.0)
ROOT_BARK = "/Game/LastSeed/Materials/M_LS_RiverbankRoot"


def obsolete_obstacle(entry):
    return (
        entry["kind"] == "blob" and 16000 < entry["x"] < 18500 and -900 < entry["y"] < 900
        or entry["kind"] == "mushroom" and 16800 < entry["x"] < 17050 and 100 < entry["y"] < 350
    )


def root_mesh(surface, origin_z=None):
    mesh = Mesh()
    # Bury the inland ends and leave a landing between the two roots for the Life Notes.
    roots = (
        ((16400, -1450, -75, 109), (16482, -1160, -14, 96), (16560, -860, -5, 77),
         (16620, -560, -3, 67), (16660, -260, 0, 55), (16768, 28, -12, 38),
         (16890, 345, -19, 21), (16955, 448, -16, 2)),
        ((16482, -1160, -18, 63), (16614, -1308, -13, 49), (16804, -1440, -24, 20),
         (16900, -1505, -17, 2)),
        ((17445, -1210, -93, 134), (17368, -920, 6, 116), (17295, -625, 18, 105),
         (17282, -315, 21, 95), (17314, -37, 22, 85), (17372, 185, 17, 76),
         (17434, 422, 6, 53), (17502, 636, -12, 30), (17585, 782, -23, 2)),
        ((17368, -920, -7, 68), (17505, -797, -9, 55), (17642, -815, -14, 32),
         (17789, -925, -17, 2)),
        ((17434, 422, -8, 32), (17378, 595, -10, 22), (17356, 735, -21, 2)),
    )
    base = surface(*STUMP) if origin_z is None else origin_z
    seams = {}
    for root in roots:
        path = [(x - STUMP[0], y - STUMP[1], surface(x, y) + lift - base) for x, y, lift, _ in root]
        first = len(mesh.points)
        sides = 12
        add_tube(mesh, path, [r for _, _, _, r in root], sides)
        length = 0.0
        for row, point in enumerate(path):
            if row:
                length += math.dist(path[row - 1], point)
            ring = first + row * sides
            v = length / 430.0
            seams[ring] = v
            for side in range(sides):
                index = ring + side
                x, y, z = mesh.points[index]
                mesh.points[index] = (x, y, point[2] + (z - point[2]) * 0.58)
                mesh.uvs[index] = (side / sides, v)
    mesh.smooth_normals()
    # Duplicate the UV seam after smoothing so both sides keep the same normal.
    seam_vertices = {i: mesh.add_vertex(mesh.points[i], (1.0, v), mesh.normals[i])
                     for i, v in seams.items()}
    mesh.triangles = [
        tuple(seam_vertices.get(i, i) for i in face)
        if any(mesh.uvs[i][0] > 0.9 for i in face) else face
        for face in mesh.triangles
    ]
    return mesh


def build_root_bark():
    bark = fresh_material(ROOT_BARK.rsplit("/", 1)[-1])
    uv = node(bark, unreal.MaterialExpressionTextureCoordinate)
    trunk = "/Game/StyleHex_Studio/Free_Packs/FREE_Stylized_Forest_Sample/Textures/Trees/T_Tree_Trunk_Broadleaf_"
    grain = texture(bark, trunk + "BC", uv)
    # Wrap the noise around the root so the bark ridges meet across the UV seam.
    ridge_uv = unreal.CustomInput()
    ridge_uv.set_editor_property("input_name", "UV")
    ridges = node(bark, unreal.MaterialExpressionCustom, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                  inputs=[ridge_uv],
                  code="float angle = UV.x * 6.2831853; return float3(cos(angle) * 3, sin(angle) * 3, UV.y * 1.35);")
    assert library.connect_material_expressions(uv, "", ridges, "UV")
    weathering = node(bark, unreal.MaterialExpressionNoise, scale=1.0, levels=2,
                      noise_function=unreal.NoiseFunction.NOISEFUNCTION_SIMPLEX_TEX,
                      output_min=0.0, output_max=1.0, turbulence=False)
    assert library.connect_material_expressions(ridges, "", weathering, "")
    tint = blend(bark, colour(bark, 0.12, 0.105, 0.087), colour(bark, 0.43, 0.36, 0.28), weathering)
    output(bark, combine(bark, unreal.MaterialExpressionMultiply, grain, tint), unreal.MaterialProperty.MP_BASE_COLOR)
    normal = node(bark, unreal.MaterialExpressionTextureSample, texture=unreal.load_asset(trunk + "N"),
                  sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    library.connect_material_expressions(uv, "", normal, "UVs")
    output(bark, normal, unreal.MaterialProperty.MP_NORMAL)
    output(bark, number(bark, 0.92), unreal.MaterialProperty.MP_ROUGHNESS)
    return finish(bark)


def build():
    import build_level1_wildwood as wildwood
    from ls_blend_trail_banks import RIVERBANK, blend_source

    world = wildwood.require_map()
    actors = wildwood.actors.get_all_level_actors()
    ignored = []
    for actor in actors:
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = component.get_editor_property("static_mesh") if component else None
        if not isinstance(actor, unreal.LandscapeProxy) and not (mesh and mesh.get_name().startswith("SM_LS_WildwoodTrail_")):
            ignored.append(actor)

    def surface(x, y):
        hit = unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(x, y, 4000), unreal.Vector(x, y, -2000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored, unreal.DrawDebugTrace.NONE, True)
        assert hit, f"No ground beneath Trail 05 at {x}, {y}"
        return hit.to_tuple()[4].z

    def note_at(old, target):
        notes = [a for a in actors if isinstance(a, unreal.LifeNote)]
        for x, y in (old, target):
            for note in notes:
                p = note.get_actor_location()
                if abs(x - p.x) < 75 and abs(y - p.y) < 75:
                    return note
        raise RuntimeError(f"Missing Trail 05 Life Note near {old}")

    notes = [(note_at(old, target), target) for old, target in (
        ((17063, -466), (17191, -338)), ((17620, 108), (17924, 430)))]
    hint = next((a for a in actors if isinstance(a, unreal.TutorialTrigger)
                 and str(a.get_editor_property("message")) in (OLD_HINT, ROOT_HINT)), None)
    assert hint, "Missing Trail 05 tutorial trigger"
    old = []
    for actor in actors:
        if isinstance(actor, (unreal.WitherBlob, unreal.BounceMushroom)):
            p = actor.get_actor_location()
            kind = "blob" if isinstance(actor, unreal.WitherBlob) else "mushroom"
            if obsolete_obstacle({"kind": kind, "x": p.x, "y": p.y}):
                old.append(actor)
        elif str(actor.get_folder_path()) == "World/" + FOLDER:
            old.append(actor)

    asset = wildwood.import_trail_mesh(RIVERBANK, blend_source(RIVERBANK))
    root_asset = import_generated_mesh("SM_LS_Trail05Roots", root_mesh(surface), solid=True)
    bark = unreal.load_asset(ROOT_BARK) or build_root_bark()
    with unreal.ScopedEditorTransaction("Rework Trail 05 riverbank"):
        if old:
            assert wildwood.actors.destroy_actors(old)
        for note, (x, y) in notes:
            note.set_actor_location(unreal.Vector(x, y, surface(x, y) + 80), False, False)
        hint.set_editor_property("message", unreal.Text(ROOT_HINT))

        wildwood.collide(wildwood.mesh_actor(root_asset, *STUMP, surface(*STUMP), FOLDER,
                                            material=bark, label="Fallen Riverbank Tree and Roots"))

        # Keep the trees in the witch's restoration group while shifting the trunks out of the travel lane.
        for label, x, y in (("RiverCurseTree_4", 15920, -2100), ("RiverCurseTree_6", 18856, -575)):
            tree = next((a for a in actors if a.get_actor_label() == label), None)
            if tree:
                tree.set_actor_location(unreal.Vector(x, y, surface(x, y) - 12), False, False)

        for index, (x, y, length, width, height, yaw) in enumerate((
            (15850, -145, 245, 174, 139, 32), (16165, 160, 279, 191, 117, -19),
            (16493, 635, 374, 280, 166, 39), (17090, 1075, 236, 151, 98, -35),
            (18010, 1378, 350, 218, 143, 22), (18980, 1755, 306, 200, 155, -19),
            (19540, 1910, 288, 188, 106, 41),
        )):
            rock = wildwood.fit_box(wildwood.FLAT_ROCKS[index % len(wildwood.FLAT_ROCKS)], x, y,
                                    surface(x, y) + height * 0.55, yaw, length, width, height,
                                    FOLDER, "Partly Buried River Stone")
            wildwood.collide(rock)
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {"trail": asset, "note_locations": [str(note.get_actor_location()) for note, _ in notes]}
