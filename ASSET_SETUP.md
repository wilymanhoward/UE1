# Last Seed: Asset Setup

Everything you need to create or assign in the editor. Updated every phase.

## Phase 1

The game runs before you do any of this: the default game mode spawns a plain sphere ball with the default values. Do these steps when you want separate visuals and tuning for each form.

### 1. Physical materials
Create in `Content/Physics` (right-click > Physics > Physical Material):

| Asset | Friction | Friction Combine | Restitution |
|---|---|---|---|
| `PM_Seed` | 0.7 | default | 0.1 |
| `PM_Stone` | 1.5 | Override to **Max** | 0 |
| `PM_Dandelion` | 0.5 | default | 0.2 |

The **Max** setting is what gives Stone grip on ice: the higher of the two surfaces' friction values is used, so slippery ice can't cancel it out.

### 2. Materials
Create `M_Seed`, `M_Stone` and `M_Dandelion`. Solid gold, grey and white are enough for testing.

### 3. `BP_SeedBall`
1. Create a Blueprint with parent class `SeedBall` in `Content/Blueprints`.
2. In Class Defaults, expand **Tuning > Forms > Form Data**. For each of the 3 entries, assign **Mesh**, **Material** and **Physical Material**.
3. Custom meshes need simple sphere collision: in the Static Mesh editor use **Collision > Add Sphere Simplified Collision**. Otherwise the ball will not roll smoothly.
4. If your mesh's radius isn't 50 cm, set **Tuning > Movement > Ball Radius** to match.
5. Optional: implement the events **Play Form Switch Effect**, **Play Death Effect**, **Play Slam Start Effect** and **Play Slam Land Effect**.

### 4. `BP_LSGameMode`
1. Create a Blueprint with parent class `LSGameMode`.
2. Set **Default Pawn Class** to `BP_SeedBall`.
3. In **Project Settings > Maps & Modes**, set **Default GameMode** to `BP_LSGameMode`.

### 5. Test level
Create a Basic level `L_Test` with a large floor, some slopes, a few cubes and a Player Start. In **World Settings**, set **Kill Z** to about -1000 so falling off the floor triggers a respawn.

## Phase 2

Create these Blueprints in `Content/Blueprints`. Everything under **Effects** is optional.

| Blueprint | Parent class | Assign |
|---|---|---|
| `BP_LifeNote` | `LifeNote` | **Mesh** component's Static Mesh and material (a gold note). **Collect Effect**, **Collect Sound** |
| `BP_GoldenPetal` | `GoldenPetal` | **Mesh** component's Static Mesh and material. **Collect Effect**, **Collect Sound** |
| `BP_FormFlower_Stone` | `FormFlower` | **Mesh**. **Form To Unlock** = Stone. **Prompt Message** = `Stone Shell unlocked! Press 2 to transform.` |
| `BP_FormFlower_Dandelion` | `FormFlower` | **Mesh**. **Form To Unlock** = Dandelion. **Prompt Message** = `Dandelion unlocked! Press 3, then hold Space while falling to glide.` |
| `BP_CheckpointShrine` | `CheckpointShrine` | **Mesh**. **Glow** component's colour and intensity. **Activate Effect**, **Activate Sound**. Optional: the **Play Activate Effect** event, to swap to a glowing material |

The **Mesh** on pickups and shrines has no collision. For a shrine the ball should bump into, select its **Mesh** component and set **Collision Presets** to `BlockAll`. Keep its **Trigger** sphere larger than the mesh, or the ball won't reach it.

These two can be placed directly, with no Blueprint, from the **Place Actors** panel by searching their names. Set their values per instance in the level:
- **`KillVolume`:** place under gaps and scale to cover them.
- **`TutorialTrigger`:** scale to cover the area, then set **Message** and **Display Duration**.

## Phase 3

Every class here works as soon as it is placed from the **Place Actors** panel, using engine cubes and a cone. Blueprint children are only needed when you add your own art. Create them in `Content/Blueprints` and set values in **Class Defaults**.

| Blueprint | Parent class | Assign |
|---|---|---|
| `BP_CrackedWall` | `CrackedWall` | **Mesh** component's Static Mesh. **Debris Mesh**. Optional: **Play Break Effect** event |
| `BP_PressurePlate` | `PressurePlate` | **Mesh** component's Static Mesh and material |
| `BP_Gate` | `Gate` | **Door** component's Static Mesh. Optional: **Open Curve** (Float Curve asset) |
| `BP_IceBlock` | `PushableBlock` | **Mesh** component's Static Mesh and material. Under **Collision**, set **Phys Material Override** to `PM_Ice` |
| `BP_MovingPlatform` | `MovingPlatform` | **Mesh** component's Static Mesh |
| `BP_CrumblingPlatform` | `CrumblingPlatform` | **Mesh** component's Static Mesh. Optional: **Play Crumble Effect** event |
| `BP_SinkingPad` | `SinkingPad` | **Mesh** component's Static Mesh (a lily pad) |
| `BP_ThinIce` | `ThinIce` | **Mesh** component's Static Mesh and material. Optional: **Play Break Effect** event |
| `BP_WindVolume` | `WindVolume` | **Particles** component's Niagara system. Optional: **Play Wind Active Effect** event |
| `BP_SteamVent` | `SteamVent` | **Particles** component's Niagara system (steam) |
| `BP_WaterVolume` | `WaterVolume` | Add a **Plane** Static Mesh component with **No Collision** and a water material, at the top of the box |
| `BP_Thorns` | `HazardVolume` | **Mesh** component's Static Mesh. Optional: **Play Knockback Effect** event |

Create `PM_Ice` in `Content/Physics`: **Friction** 0.05 and **Friction Combine** set to **Min**, so ice stays slippery against normal floors. Assign it to icy floors too. Stone keeps its grip because `PM_Stone` uses **Max**, and Max takes priority over Min.

### Set these on each placed actor in the level
- **Gate:** add an entry to **Required Plates** and pick a plate with the eyedropper. Add two for the two-plate puzzle.
- **Wind Volume:** set **Wind Direction**. Use `(0, 0, 1)` for an updraft. For the fan puzzle, pick a plate in **Power Plate**.
- **Moving Platform:** select the placed actor, click a white spline point in the viewport and drag it. Alt+drag a point to add another. Turn on **Loop** for a closed route.
- **Scaling:** resize volumes with **Box Extent**, or by scaling the actor.

### Level design rules
- **Pressure plate:** set the plate's Z to 10 below the floor surface, so its top is level with the floor. A block can't slide up onto a raised plate.
- **Pushable block:** the default 150 kg is meant for `PM_Ice` floors. On a normal floor, set **Mass Kg** to about 52 or Stone will only nudge it.
- **Thin ice:** the actor's origin is 50 cm above the ice surface. Put a kill volume or water below it.
- **Water:** floating forms can't jump, so give every pool a gentle ramp out.
- **Sinking pad:** put the top of the pad level with the water surface.
- **Wind on Stone:** Stone's **Wind Response** is 0.05, so it crosses strong wind almost unaffected. Use this for bridges that Seed can't cross.
- **Updraft strength:** must beat gravity. The default of 1500 lifts Seed and Dandelion, but not Stone.

## Phase 4

Do these in order. Note counting and plant growth work without steps 1 to 3, but world colour needs them.

### 1. Material parameter collection
1. In `Content/Materials`, right-click and choose **Materials > Material Parameter Collection**. Name it `MPC_Restoration`.
2. Add these parameters with exactly these names:

| Type | Name | Default |
|---|---|---|
| Scalar | `Restoration` | 0 |
| Scalar | `LocalBloomRadius` | 0 |
| Vector | `LastNoteLocation` | 0, 0, 0, 0 |

### 2. Material function
Create `MF_WitherBlend` in `Content/Materials` (right-click, **Materials > Material Function**). Tick **Expose to Library**. Build this graph:

1. Add a **Function Input** named `Color` with **Input Type** set to **Function Input Vector 3**.
2. Add a **Collection Parameter** node for each of the three parameters, each with **Collection** set to `MPC_Restoration`.
3. Add a **Distance** node. Connect **Absolute World Position** to A. Pass `LastNoteLocation` through a **Component Mask** with only R, G and B ticked, then connect that to B. The parameter has four values and the position has three, so Distance gives an error without the mask.
4. Add a **Max** node with `LocalBloomRadius` in A and the constant `1` in B. This prevents dividing by zero.
5. Add a **Divide** node with Distance in A and Max in B.
6. Add a **OneMinus** after it, then a **Saturate**. This is the local bloom: 1 at the note, fading to 0 at the radius.
7. Add a second **Max** node with `Restoration` in A and the Saturate output in B.
8. Add a second **OneMinus** after it. This is the amount of grey.
9. Add a **Desaturation** node. Connect `Color` to its input, and the second OneMinus to **Fraction**.
10. Connect the Desaturation output to the **Output Result**, then save.

### 3. World materials
In every world material (ground, rocks, trees, plants):

1. Add the `MF_WitherBlend` node.
2. Connect what currently goes into **Base Color** to its `Color` input.
3. Connect its output to **Base Color**.

Leave `M_Seed`, `BP_LifeNote` and other glowing objects out of this, because they should stay colourful.

### 4. Level setup
1. Place a **Post Process Volume** and tick **Infinite Extent (Unbound)**.
2. Place an **Exponential Height Fog**, if the level doesn't have one.
3. Place one `RestorationDriver` from **Place Actors**. In **Details** set **Parameter Collection** to `MPC_Restoration`, and use the eyedroppers to pick **Post Process Volume** and **Height Fog**.
4. For World Partition levels such as `L_Test`: select the Post Process Volume and the fog, then untick **Is Spatially Loaded**. They must stay loaded, since the driver always is.
5. Once your world materials use `MF_WitherBlend`, set the driver's **Withered Saturation** to about 0.8. The default of 0.15 greys the whole screen, including the glowing seed and each note's local colour, and is only suitable for levels with no blended materials yet.

### 5. Plants
Create `BP_Flower` with parent `RestorableActor`, and assign the **Mesh** component's Static Mesh and material. Place copies, and set each one's **Restoration Threshold** and **Note Radius**. Use different thresholds so the world recovers in stages. For a plant the ball should bump into, set its **Mesh** component's **Collision Presets** to `BlockAll`.

## Phase 5

Both work as soon as they are placed, using an engine sphere and cube. Create Blueprint children when you add your own art.

| Blueprint | Parent class | Assign |
|---|---|---|
| `BP_WitherBlob` | `WitherBlob` | **Mesh** component's Static Mesh and a dark material. Optional: **Play Contact Effect** and **Play Death Effect** events |
| `BP_WitheringStorm` | `WitheringStorm` | **Mesh** component's material (dark and translucent). **Rumble Audio** component's **Sound** (looping). **Close Shake** |
| `BP_StormShake` | `CameraShakeBase` | **Root Shake Pattern** = Perlin Noise Camera Shake Pattern, with **Duration** of at least 1 s. Assign it to **Close Shake** |

`AStormTrigger` needs no Blueprint: place it from **Place Actors**.

### Set these on each placed actor in the level
- **Wither Blob:** under **Patrol Points**, click **+** for each point, then drag its diamond widget in the viewport. Leave the list empty for a guard that stays at its start.
- **Storm Trigger:** set **Storm** with the eyedropper, and scale it across the start of the climb.
- **Withering Storm:** scale the actor to resize it, so the mesh and the kill box stay matched. Place its top well below the player's starting height.

### Level design rules
- **Blobs:** they move in straight lines, so keep patrol routes free of walls. They stop at drops larger than **Max Drop Height**, so ledges are safe places.
- **Storm:** set **Max Rise Distance** so its top stops below the end of the climb. Phase 7 stops it when the level is complete.

## Phase 6

The game runs silently until sounds are assigned, and any sound can be left empty. Import `.wav` files by dragging them into `Content/Audio`.

### 1. Prepare the music files
Do this for each music stem:

1. Double-click the sound to open it.
2. Tick **Looping**.
3. Set **Virtualization Mode** to **Play When Silent**. Without this, a stem waiting at near-zero volume can restart when it fades in and fall out of time with the others.
4. Save.

All five stems must have exactly the same length and tempo, or they will drift apart as they loop. The finale track doesn't need either setting.

### 2. Music manager
Do this once in each level:

1. In **Place Actors**, search for `MusicManager` and drag it into the level.
2. With it selected, click **AdaptiveMusic** in the component list at the top of **Details**.
3. Under **Music > Stems**, click **+** five times and assign them in this order:

| Index | Stem | Starts when |
|---|---|---|
| 0 | Pads | Level start |
| 1 | Percussion | 25% restored |
| 2 | Bass | 50% restored |
| 3 | Melody | 75% restored |
| 4 | Strings | 100% restored |

4. Assign **Finale Track**.

### 3. Ball sounds
Open `BP_SeedBall`, click **Class Defaults**, and assign:

- **Audio:** **Jump Sound**, **Land Sound**, **Form Switch Sound** and **Death Sound**.
- **Tuning > Forms > Form Data:** a looping **Roll Sound** for each of the 3 forms. Tick **Looping** on each sound, as in step 1, but leave **Virtualization Mode** as it is.

### 4. World sounds
These go in the Blueprint children from Phases 3 and 5. Create the Blueprint first if you don't have it yet.

| Blueprint | Click | Assign |
|---|---|---|
| `BP_CrackedWall` | Class Defaults | **Break Sound** |
| `BP_WitherBlob` | Class Defaults | **Contact Sound** and **Death Sound** |
| `BP_WindVolume`, `BP_SteamVent` | **Wind Audio** component | **Sound** (looping) and **Attenuation Settings** |
| `BP_WitheringStorm` | **Rumble Audio** component | **Sound** (looping). Leave attenuation empty, as the code sets its volume by distance |

Life Note, Golden Petal, Form Flower and Shrine sounds were covered in Phase 2.

### 5. Attenuation for wind
Without attenuation, every wind volume is heard across the whole level.

1. In `Content/Audio`, right-click and choose **Audio > Sound Attenuation**. Name it `ATT_Wind`.
2. Open it. Set **Attenuation Shape** to **Sphere**, **Inner Radius** to about 500 and **Falloff Distance** to about 1500.
3. Save, and assign it to **Attenuation Settings** on **Wind Audio**.

Increase these for very large wind volumes, because the distance is measured from the centre of the volume.

## Input
No input assets are required. All input is built in `ALSPlayerController`.

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move | WASD | Left stick |
| Look | Mouse | Right stick |
| Jump / glide | Space | A / Cross |
| Slam | Left Ctrl or Left Mouse | B / Circle |
| Seed / Stone / Dandelion | 1 / 2 / 3 | D-pad Up / Left / Right |
| Cycle form | Q / E | LB / RB |
| Pause | Esc | Start / Options |

In Play In Editor, Esc stops the session instead of pausing. To test pausing, use a gamepad or run with **Play > Standalone Game**.
