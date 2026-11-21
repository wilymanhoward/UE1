"""Models the checkpoint: a hand-hewn wooden post with an arm, and an iron lantern hanging from it on a short chain.

Run with Maya's Python, outside Unreal:
  "C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe" Content/Python/maya_lantern_post.py
Writes Content/LastSeed/SourceMeshes/SM_LS_LanternPost.fbx, about 260 cm tall, with its origin at the foot of the post and the
lantern hanging 62 cm along +X. Three material slots: Wood, Iron and Glass (the panes, which ls_lantern_post.py lights up).
"""
import math
import os
import random

import maya.standalone

maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402 (needs the standalone session first)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "LastSeed", "SourceMeshes", "SM_LS_LanternPost.fbx")
LANTERN_X = 62.0
rng = random.Random(42)


def shader(name, rgb):
    material = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.setAttr(material + ".color", *rgb, type="double3")
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(material + ".outColor", group + ".surfaceShader")
    return group


SLOTS = {"Wood": shader("Wood", (0.32, 0.2, 0.11)), "Iron": shader("Iron", (0.08, 0.08, 0.09)),
         "Glass": shader("Glass", (1.0, 0.78, 0.4))}
parts = []


def keep(mesh, slot):
    cmds.sets(mesh, edit=True, forceElement=SLOTS[slot])
    parts.append(mesh)
    return mesh


def roughen(mesh, amount):
    """Nudges every vertex a little, so the wood reads as hand-cut rather than turned on a lathe."""
    for index in range(cmds.polyEvaluate(mesh, vertex=True)):
        cmds.move(rng.uniform(-amount, amount), 0, rng.uniform(-amount, amount), "{}.vtx[{}]".format(mesh, index),
                  relative=True)


# The post: an eight-sided timber, slightly narrower at the top, on a flared foot.
post = cmds.polyCylinder(radius=9, height=240, subdivisionsAxis=8, subdivisionsHeight=6, name="Post")[0]
cmds.move(0, 120, 0, post)
cmds.select("{}.vtx[{}:{}]".format(post, 48, 55))  # The top ring: 8 vertices per ring, 7 rings.
cmds.scale(0.85, 1, 0.85, relative=True, pivot=(0, 240, 0))
roughen(post, 0.8)
keep(post, "Wood")
foot = cmds.polyCone(radius=17, height=40, subdivisionsAxis=8, name="Foot")[0]
cmds.move(0, 20, 0, foot)  # Its base on the ground; the cone's tip is buried inside the post, so only its flare shows.
roughen(foot, 1.2)
keep(foot, "Wood")
cap = cmds.polyPyramid(sideLength=18, numberOfSides=4, name="Cap")[0]
cmds.rotate(0, 45, 0, cap)
cmds.move(0, 246, 0, cap)
keep(cap, "Wood")

# Iron bands round the post.
for y in (55, 205):
    band = cmds.polyTorus(radius=9.4, sectionRadius=1.1, subdivisionsAxis=16, subdivisionsHeight=6, name="Band")[0]
    cmds.move(0, y, 0, band)
    keep(band, "Iron")

# The arm reaching out, and a brace under it.
arm = cmds.polyCube(width=78, height=9, depth=9, name="Arm")[0]
cmds.move(34, 228, 0, arm)
roughen(arm, 0.6)
keep(arm, "Wood")
brace_length = math.hypot(32.0, 32.0)
brace = cmds.polyCube(width=brace_length, height=6, depth=6, name="Brace")[0]
cmds.rotate(0, 0, 45, brace)
cmds.move(20, 210, 0, brace)
keep(brace, "Wood")

# A hook and a short chain down to the lantern.
hook = cmds.polyTorus(radius=3.2, sectionRadius=0.7, subdivisionsAxis=12, subdivisionsHeight=6, name="Hook")[0]
cmds.rotate(90, 0, 0, hook)
cmds.move(LANTERN_X, 221, 0, hook)
keep(hook, "Iron")
for k, y in enumerate((216, 210, 204)):
    link = cmds.polyTorus(radius=2.4, sectionRadius=0.6, subdivisionsAxis=10, subdivisionsHeight=6, name="Link")[0]
    cmds.rotate(90, 90 * (k % 2), 0, link)
    cmds.move(LANTERN_X, y, 0, link)
    keep(link, "Iron")

# The lantern: a ring and pointed cap, four corner posts, glowing panes and a base plate.
ring = cmds.polyTorus(radius=2.8, sectionRadius=0.7, subdivisionsAxis=10, subdivisionsHeight=6, name="Ring")[0]
cmds.rotate(90, 0, 0, ring)
cmds.move(LANTERN_X, 199, 0, ring)
keep(ring, "Iron")
top = cmds.polyPyramid(sideLength=30, numberOfSides=4, name="LanternCap")[0]
cmds.rotate(0, 45, 0, top)
cmds.scale(1, 0.55, 1, top)
cmds.move(LANTERN_X, 191, 0, top)
keep(top, "Iron")
rim = cmds.polyCube(width=26, height=3, depth=26, name="Rim")[0]
cmds.move(LANTERN_X, 184, 0, rim)
keep(rim, "Iron")
for sx in (-1, 1):
    for sz in (-1, 1):
        corner = cmds.polyCube(width=2.6, height=34, depth=2.6, name="Corner")[0]
        cmds.move(LANTERN_X + sx * 11, 166, sz * 11, corner)
        keep(corner, "Iron")
glass = cmds.polyCube(width=20, height=32, depth=20, name="Panes")[0]
cmds.move(LANTERN_X, 166, 0, glass)
keep(glass, "Glass")
base = cmds.polyCube(width=26, height=4, depth=26, name="Base")[0]
cmds.move(LANTERN_X, 148, 0, base)
keep(base, "Iron")
finial = cmds.polyCone(radius=4, height=6, subdivisionsAxis=8, name="Finial")[0]
cmds.rotate(180, 0, 0, finial)
cmds.move(LANTERN_X, 143, 0, finial)
keep(finial, "Iron")

merged = cmds.polyUnite(parts, name="SM_LS_LanternPost", constructionHistory=False)[0]
cmds.polySoftEdge(merged, angle=35, constructionHistory=False)
cmds.xform(merged, pivots=(0, 0, 0), worldSpace=True)
low, high = cmds.exactWorldBoundingBox(merged)[1], cmds.exactWorldBoundingBox(merged)[4]
assert -1.0 < low < 1.0 and 245.0 < high < 260.0, (low, high)

cmds.loadPlugin("fbxmaya", quiet=True)
import maya.mel as mel  # noqa: E402
mel.eval("FBXExportSmoothingGroups -v true")  # Unreal reads hard and soft edges from these.
cmds.select(merged)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
cmds.file(os.path.normpath(OUT), force=True, options="v=0;", type="FBX export", exportSelected=True)
print("Wrote", os.path.normpath(OUT), "height", round(high - low, 1))
maya.standalone.uninitialize()
