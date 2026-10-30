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
