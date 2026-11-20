"""Dress the landing-to-crossing stretch of Wildwood as a washed-out riverbank."""

import unreal

from ls_generate_player_meshes import Mesh
from ls_generate_world_meshes import add_tube
from ls_world_common import import_generated_mesh

FOLDER = "Parkour/Trail 05 Riverbank"
OLD_HINT = "Wither Blobs drain the colour from the world. Slam on them from above as Stone Shell."
ROOT_HINT = "Roll over the shallow root, then jump over the larger one."
STUMP = (17970.0, -856.0)


def obsolete_obstacle(entry):
    return (
        entry["kind"] == "blob" and 16000 < entry["x"] < 18500 and -900 < entry["y"] < 900
        or entry["kind"] == "mushroom" and 16800 < entry["x"] < 17050 and 100 < entry["y"] < 350
    )


def root_mesh(surface):
    mesh = Mesh()
    # Each entry gives the root centre relative to the ground and its horizontal radius.
    roots = (
        ((17882, -795, 106, 177), (18152, -895, 124, 163), (18404, -965, 139, 128),
         (18629, -1053, 140, 100), (18811, -1120, 132, 81), (18833, -1130, 117, 1)),
        ((18404, -965, 139, 62), (18462, -1160, 161, 40), (18522, -1280, 144, 23),
         (18578, -1340, 131, 1)),
        ((STUMP[0], STUMP[1], 95, 166), (17575, -885, 20, 149), (17212, -845, -20, 123),
         (16864, -655, -26, 105), (16637, -440, -25, 90), (16424, -237, -32, 65),
         (16251, -84, -34, 46), (16183, 15, -55, 1)),
        ((STUMP[0], STUMP[1], 114, 180), (18113, -564, 57, 150), (18067, -284, 38, 138),
         (17844, -112, 33, 124), (17603, 90, 31, 115), (17370, 318, 21, 99),
         (17154, 507, -15, 72), (17017, 692, -33, 1)),
        ((17212, -845, -20, 78), (17070, -987, -19, 47), (16908, -1030, -30, 1)),
        ((16424, -237, -22, 49), (16395, -108, -10, 35), (16288, 20, -21, 18), (16245, 88, -32, 1)),
        ((17370, 318, 21, 67), (17263, 301, -3, 53), (17103, 351, -20, 31), (17012, 439, -31, 1)),
    )
    base = surface(*STUMP)
    for root in roots:
        path = [(x - STUMP[0], y - STUMP[1], surface(x, y) + lift - base) for x, y, lift, _ in root]
        rings = len(mesh.points)
        sides = 12
        add_tube(mesh, path, [r for _, _, _, r in root], sides)
        for index in range(rings, len(mesh.points)):
            x, y, z = mesh.points[index]
            centre = path[(index - rings) // sides][2]
            mesh.points[index] = (x, y, centre + (z - centre) * 0.58)
    mesh.smooth_normals()
    return mesh


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
    with unreal.ScopedEditorTransaction("Rework Trail 05 riverbank"):
        if old:
            assert wildwood.actors.destroy_actors(old)
        for note, (x, y) in notes:
            note.set_actor_location(unreal.Vector(x, y, surface(x, y) + 80), False, False)
        hint.set_editor_property("message", unreal.Text(ROOT_HINT))

        wildwood.collide(wildwood.mesh_actor(root_asset, *STUMP, surface(*STUMP), FOLDER,
                                            material=wildwood.material("M_LS_Bark"), label="Fallen Riverbank Tree and Roots"))

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
