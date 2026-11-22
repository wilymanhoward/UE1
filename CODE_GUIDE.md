# Last Seed: Code Guide

The player is the last glowing seed of a dead Heart Tree. This guide explains each class and suggests how to present the code in the video. It is updated every phase.

## Classes

### `SeedFormTypes.h`: form data
- `ESeedForm`: Seed, Stone, Dandelion.
- `FSeedFormData`: every value that makes a form different (rolling and upright meshes, glow, mass, damping, torque, jump, wind response, gravity scale, and the ability flags).
- **Pattern:** data-driven design. Slam and glide check `bCanSlam` and `bCanGlide`, not "is this Stone?".

### `ASeedBall`: the player pawn
| Function | What it does |
|---|---|
| `Tick` | Runs the per-frame steps in a readable order, and does nothing while dead |
| `UpdateGrounded` / `CheckForGround` | Sphere sweep down using the ball's own collision channel, rejecting steep surfaces |
| `TryConsumeJump` | Jumps only when the buffer window and the coyote window are both open |
| `ApplyMovement` | Camera-relative torque on the ground, reduced direct force in the air |
| `ApplyGravityScale` | Adds only the difference from normal gravity, as there is no per-body gravity scale to set |
| `ApplyGlide` | While falling with jump held: small lift and a clamped fall speed |
| `SlamPressed` | Strong downward impulse in the air, for forms with `bCanSlam` |
| `TrySwitchForm` | The state transition: guards, `OnExitForm`, `OnEnterForm`, effect hook, delegate |
| `ApplyFormData` | Applies a form's mass, damping and friction to the physics body. The sphere itself never changes, so a switch can't lose velocity |
| `ApplyFormVisuals` | Shows the form's rolling and upright meshes, light colour and particles. None of them have collision |
| `UpdateFormSwitch` | The switch transition (0.35 s): the old form squashes and shrinks while the light swells, then `ApplyFormVisuals` swaps the meshes and the new form pops in past full size and settles. Stone also shakes the camera by `SwitchShake` |
| `SpawnSwitchBurst` | A burst of the pack's `NS_Sparkling` in the new form's `SwitchColor`, `SwitchBurstRadius` wide. The effect only has a spawn rate, so the burst is that rate stopped after 0.12 s |
| `Die` / `Respawn` | Freeze and hide, then teleport to the checkpoint with velocity zeroed |
| `UpdateRollAudio` | Sets the roll loop's volume and pitch from speed as a fraction of the form's top speed |
| `UpdateTrail` | Always, on the ground or in the air, sets the `TrailParticles` sparkle rate from a fifth when still to full at the form's top speed (up to `TrailRate`, 50 a second in Wildwood) and tints them with the form's `GlowColor`. Each sparkle lives 0.6 to 1 s, so the trail fades just behind the ball. `TrailEffect` is the pack's `NS_Sparkling`, assigned by `Content/Python/ls_seed_trail.py` |

**Patterns:** state (small and data-driven) and observer (`OnFormChanged`, `OnDied`, `OnRespawned`).

### `ALSPlayerController`: input
- `CreateInputObjects` builds all actions and the mapping context with `NewObject`, so no input assets are needed.
- `BindInputActions` connects actions to small handlers that forward to the ball.
- `OpenMenu` and `CloseMenu` are the one place that switches input mode, the mouse cursor, the pause state and the HUD.
- `PlayStory` plays a sequence or text cards with gameplay input off, then runs a callback.
- `ShowPrompt` is the single route for player messages, and goes to the HUD.
- `ApplyVolumeSettings` sends the saved volumes to the sound classes through a sound mix.
- Test commands: `LSUnlockAllForms`, `LSKillBall`, `LSDeleteSave`, `LSDrainRestoration <amount>`, and `LSCompleteLevel`.
- **Pattern:** command-style forwarding. The controller knows the keys, the ball knows the behaviour.

### `ULSGameInstance` and `ULSSaveGame`: persistent data
The game instance stores `UnlockedForms`, a `FLSLevelRecord` of best scores per level, and the volumes. It survives level changes, so Level 2 keeps forms unlocked in Level 1. `bRestoredArrival` is the one unsaved flag: Emberwood's energy burst sets it, so the level it opens starts healed. `RecordLevelResult` keeps the best of each value, `SaveProgress` copies everything into a `ULSSaveGame` and writes it to disk, and `Init` loads it at startup. **Pattern:** memento (the save object is a plain snapshot).

### `ALSGameMode`: level rules
| Function | What it does |
|---|---|
| `Tick` | Adds to the level timer. It doesn't tick while paused, so menus and text cards don't count |
| `InitGame` | Reads and clears `ULSGameInstance::bRestoredArrival` before any actor's `BeginPlay`, so `IsRestoredArrival` is true only in the level the burst opened |
| `RestartPlayer` | Listens to the new ball's `OnDied` to count deaths. On a restored arrival, puts Seed just before the level's goal, facing back down the trail |
| `BuildResult` | Fills in `FLSLevelResult`, including each star condition and the star count |
| `CompleteLevel` | Saves the result, fires `OnLevelCompleted`, plays the ending, then opens the results. A goal with `bEnergyFinale` plays its shots with the `Gameplay` transition, then `ALevelGoal::PlayEnergyBurst` |
| `ContinueAfterResults` | Opens the next level, or plays the credits and returns to the menu after the last level |

**Pattern:** observer (`OnLevelCompleted`).

### `ALevelGoal` and `AStoryTrigger`: placed flow actors
`ALevelGoal` ends the level, and holds the settings that differ per level, such as par time and next level, because all levels share one game mode Blueprint. `AStoryTrigger` calls `PlayStory` once, when entered or at the start of the level, except on a restored arrival.

Emberwood's goal sets `bEnergyFinale`:
- It opens only once every energy (the level's Life Notes) is collected; earlier, it shows `MissingEnergyMessage` with the count.
- After the `TravelShots` (the witch), `PlayEnergyBurst` holds Seed still and `Tick` runs the charge for `ChargeTime` (3 s): Seed shakes harder and harder (`ChargeShake`, squared), lifts a little, its glow light swells, and `ChargeShellMaterial` on a sphere grows round it to `ChargeShellSize`, pulsing faster.
- Then the burst: `BurstEffect` at `BurstScale`, `BurstSound`, Seed hidden, and a white camera fade. `ContinueAfterResults` sets `ULSGameInstance::bRestoredArrival` and opens `NextLevel` (Wildwood).
- In that Wildwood, `URestorationSubsystem::RestoreFully` removes the notes and sets restoration to 1 on the first tick, the opening is skipped, the white fade clears, and a prompt says Wildwood is whole again. The goal there no longer ends the level.

### UI widgets
Each is a C++ base class with `meta = (BindWidget)` properties, and the layout lives in a Blueprint child. A missing or misnamed widget is a compile error in the Widget Blueprint, not a crash in play.
- `ULSHUDWidget`: form, notes, petals, timer, restoration bar and a fading prompt. **Pattern:** observer.
- `ULSMainMenuWidget`: Play, Level Select with Level 2 locked, Controls and Quit.
- `ULSPauseMenuWidget`: Resume, Restart, Controls, volume sliders and Main Menu.
- `ULSResultsWidget`: stars, stats and which conditions were met.
- `ULSStoryCardWidget`: one card at a time, then `OnFinished`.
- `ULSControlsWidget`: one controls list, placed inside both menus.

### `ULSIntroWidget`: the painted opening cutscene
Plays a list of `FLSIntroShot`s: each a full-screen picture (fitted by a `UScaleBox`, so it fills any screen shape without stretching) that slowly zooms and pans, fading in over the one before, sometimes from a white flash, with an optional caption. `NativeTick` works out the current shot from the elapsed time. The music is a UI sound, so it plays while the game is paused behind the cutscene, and the last second fades the widget out to show the level. It builds its widgets in code in `NativeOnInitialized`, so it has no Widget Blueprint. `AStoryTrigger` plays it when `IntroShots` is set, through `ALSPlayerController::PlayIntro`, which shares `BeginStory` with the story cards and ends the same way. The shots (timings, camera moves, captions) are in `Content/Python/ls_intro_shots.py`, and the recorded soundtrack is `MUS_LS_Intro_Recordings.wav`. See `AUDIO_CREDITS.md` for sources. **Pattern:** observer (`OnFinished`).

A shot can also carry a `MotionMaterial`, a UI material that animates the painting itself through its `ShotTime` parameter (the witch frames use this for drifting curse light), and a `SeedMatch`, the seed's place and size in the last frame. `ELSIntroTransition` says how the cutscene enters and leaves:
| Transition | Used by | How it ends |
|---|---|---|
| `Opening` | The intro | The last frame's seed lines up with the real ball, then the camera is released |
| `Gameplay` | The riverbank ambush | Fades back to the live camera |
| `Travel` | The Witch Exile | Holds black, so the next level can load behind it |
| `Arrival` | The Emberwood landing | Starts from black and lines the painted seed up with the ball, like `Opening` |

### The witch cutscenes
The intro shows the witch cursing the forest. She comes back twice more, using the same `ULSIntroWidget`.

**1. The riverbank ambush (Trail 05).** `ls_witch_ambush.py` places an `AStoryTrigger` called `RiverbankWitchAmbush` on the far bank of the river. It has two painted shots, `WitchReveal` ("The Heart Tree's last seed… I'll crush you myself.") and `WitchScream`, and plays Kristen's recorded lines from `SFX_LS_RiverAmbush`.
- `bWaitForLanding`: entering the box only starts a 0.05 s timer, `CheckLanding`, which waits until the ball is grounded and not still rising. The Dandelion glides in over the river, so without this the cutscene would cut in mid-air.
- `RevealTargetOffset`: before the first painting, the camera turns for 1.5 s to look at the spot where the witch stands, behind black bars, so the player sees where the scene is.

**2. The river curse.** When the ambush ends, its callback calls `StartRising` on `AfterCutsceneCurse`, an `AWitheringStorm` that `ls_river_curse.py` sets up as `RiverbankCurse`. It reuses the chase path (`ChasePoints`), with these settings:
- `bShockwaveAttacks`: `TickShockwave` sends a thin curved wave from ahead of the ball down the path every 6 to 8 seconds, so the player has to jump it. `ShockwaveBend` curves the wave into a crescent, and each wave picks a different one of three heights from the last, so the jump timing changes.
- Sweeping: the wave's box is stretched by the distance it moved that frame, so a fast wave can't pass through the ball between frames.
- `ShockwaveMinLaunchDistance`: no wave is launched while the ball is too close to its start point.
- `CurseTrees`: trees the wave passes are switched to their dead trunk (`ARestorableActor::SetCursed`), so the player sees the curse spread. On respawn every tree comes back, and the curse starts again from the trigger, because a ball that dies here never keeps a checkpoint inside the chase.
- The script gets the path's heights by tracing down to the trail, so a low wave never goes under a slope. It also swaps the foliage trees beside the river for single `ARestorableActor`s, because instanced trees can't wither one at a time.

**3. The Witch Exile (end of Wildwood).** `ls_witch_exile.py` turns Wildwood's `ALevelGoal` into the planting spot:
- `bRequireJump`: the goal only completes when Seed lands from a jump inside it (`ASeedBall::JustLandedFromJump`). It ticks to check this, because landing creates no new overlap event. A `TutorialTrigger` just before it says "Take Seed form, then jump into the dirt to plant yourself."
- `TravelShots`: `PlantingSoil`, `WitchNotYet` ("Not yet.") and `WitchBanishment` ("By ash and flame… I cast you out!"), with the voiced track `SFX_LS_ExilePlantingVoiced`. `ALSGameMode::CompleteLevel` saves the result first, then plays these with the `Travel` transition instead of opening the results screen, and `ContinueAfterResults` opens `NextLevel`.

**4. The Emberwood arrival.** Level 2 is now built by `ls_emberwood.py` (below), whose `arrival` places the player start and the `ExileEmberwood` shot in the lava pack's basin. Before that, this script built the start of the plain `L_Level2`, still in the project but no longer opened: a lava plane with an `AKillVolume` just under its surface, basalt shelves to roll across (hidden cylinders for collision, the same idea as point 32), charred trees, orange lights, a darker fog and the fire ambience. An `AStoryTrigger` with `bPlayOnStart` and `bArrivalCutscene` plays one shot, `ExileEmberwood`, whose `SeedMatch` lines the painted seed up with the real ball as the player takes control.

**5. The Emberwood confrontation.** `ls_emberwood.py` puts the witch's `TravelShots` on Emberwood's goal: three frames from `SourceIntro/EmberwoodWitch`, reimported on every run. They are placeholders copied from the earlier scenes, so new paintings dropped in under the same names replace them. Then the energy burst (see `ALevelGoal`) takes Seed home.

Every frame and sound is imported by the scripts from `Content/LastSeed/SourceIntro/RiverAmbush`, `SourceIntro/WitchExile` and `SourceSounds`, so a rerun rebuilds the same scene. **Patterns:** observer (the `OnFinished` callback starts the curse), data-driven (one widget and one trigger class tell all four scenes).

### `ILSInteractable`: the interaction contract
`OnBallOverlap(Ball)` and `OnBallHit(Ball, ImpactVelocity)`, both defaulting to no action. `ASeedBall::HandleBeginOverlap` and `HandleHit` cast whatever they touched to this interface and call it. **Pattern:** interface / polymorphism. The ball never casts to a pickup or a volume, so new world objects don't change the ball.

### `ALSPickupBase`, `ALifeNote`, `AGoldenPetal`, `AFormFlower`: pickups
`ALSPickupBase` handles bob and spin, the collect-once guard, effects and `Destroy`. Children implement only `OnCollected`:
- `ALifeNote`: reports to `URestorationSubsystem`. It overrides `GetCollectPitch`, so each note chimes one step higher on a major scale than the one before.
- `AGoldenPetal`: adds to the count in `ALSGameMode`.
- `AFormFlower`: unlocks a form, saves, and shows a prompt.

**Pattern:** template method. The base class fixes the order of the steps, and children fill in one step.

### `ACheckpointShrine`: respawn points
On first touch it sets the ball's checkpoint, locks in the current restoration, and lights the lantern. Over `LightFadeTime` (1.2 s) `Tick` eases the glow light and the glass material's `Lit` from 0 up to full, then turns ticking off again. The effect and the match-and-fire sound (`ls_lantern_sound.py`) play at the lantern. It then ignores further touches. The actor sits on the trail's centre line, where the ball respawns. Only its mesh, a wooden post with a hanging lantern (`maya_lantern_post.py`), stands at the trail's edge. `ls_lantern_post.py` places the post and widens the trigger sphere across the trail, so rolling past anywhere lights it. Checkpoints last for the current run only, because collected notes aren't saved.

### `ALSVolumeBase`, `AKillVolume`, `ATutorialTrigger`: volumes
`ALSVolumeBase` creates the invisible overlap box. `AKillVolume` calls `Die`. `ATutorialTrigger` shows its message once.

### `ATiltingLog`: mass balance
Each tick it adds up mass times distance from the pivot for every simulating body in `Trigger`. It compares that with `CounterweightKgCm` and turns the log, with `Damping` and a limit of `MaxTiltDegrees`. It moves itself instead of simulating physics, so it can't fling or jam the ball. Stone tips it quickly and Seed slowly, and a counterweight above Seed's best makes a log only Stone can tip.

### `ACrackedWall`: breakable wall
`OnBallHit` checks for Stone, then for a slam or an impact speed of at least `BreakSpeed`. `Break` hides the mesh and any `RubbleActors`, removes their collision, and spawns physics debris with a set lifespan. It is the first user of the `ImpactVelocity` value that `ASeedBall` saves before each impact.

### `APressurePlate`: weight sensor
`GetMassOnPlate` adds up the mass of every simulating body in the trigger. `Tick` compares it with `RequiredMassKg` and broadcasts `OnPlatePressed` or `OnPlateReleased` when the answer changes. `OnBallOverlap` shows the "Too light!" prompt. **Pattern:** observer.

### `ALever`: a floor lever held by a pushed block
A standalone actor (no pressure plate). `GetMassAgainst` adds up the mass of every simulating body in `PushZone`, just in front of the plinth's front end, skipping pawns, so the player's ball never counts and only something pushed there (the block) holds it. `Tick` broadcasts `OnLeverOn` or `OnLeverOff` when that crosses `RequiredMassKg`, and swings `ArmPivot` (with the `Rod` and `Grip` on it) between `OffPitch` and `OnPitch`. `AGate` takes levers in `RequiredLevers`, alongside its plates. Its meshes and painted wood, iron and leather textures come from `Content/Python/ls_generate_lever.py`; `build_level1_wildwood.lever_assets` imports them and builds the materials. **Pattern:** observer.

### `AGate`: door with a timeline
`BeginPlay` builds the timeline from `OpenCurve`, or from `CreateDefaultCurve` when none is assigned, and subscribes to every plate. `RefreshGate` plays forward only if all plates are pressed, and otherwise reverses. **Pattern:** observer.

### `APushableBlock`: heavy physics body
Contains almost no code, because mass and friction produce the behaviour. `FellOutOfWorld` returns it to its start so a puzzle can't become impossible.

### `AMovingPlatform`: spline path
`Tick` advances a distance along the spline, handles ping-pong or loop at the ends, and moves the kinematic mesh. Two spline points are the simple A-to-B case, so there is one path system and not two.

### `ACrumblingPlatform` and `ASinkingPad`: delayed collapse
An `ECrumbleState` state machine: Solid, Shaking, Falling, Waiting, Returning. `ASinkingPad` only changes default values in its constructor. **Pattern:** state machine.

### `UCollapsingStoneComponent`: gorge pillars
Each of the first gorge's four stone caps owns this component and references its supporting rocks. Leaving the cap's sensor starts a three-second timer. The complete pillar then tumbles downward, loses collision, and stays hidden. `ASeedBall::OnRespawned` cancels pending timers and restores each visited pillar's original transforms, visibility, and collision. The component ticks only during the falling animation; waiting safely on a cap does not start its countdown.

### `AThinIce`: mass-limited surface
`Tick` breaks the ice when the ball inside weighs at least `BreakMassKg`. A timer restores it. **Pattern:** data-driven.

### `AWindVolume` and `ASteamVent`: directional force
`IsWindActive` combines the optional power plate and the pulse timer. `Tick` switches the particles when that changes, then pushes the ball by `Strength * WindResponse`. `ASteamVent` only changes defaults. **Pattern:** data-driven.

### `AWaterVolume`: buoyancy and drag
Each frame it adds drag against the velocity, plus upward buoyancy that grows with depth if the form has `bBuoyancyEnabled`. **Pattern:** data-driven.

### `AHazardVolume`: thorns
`Tick` kills a ball that is fragile or lighter than `SurviveMassKg`, and otherwise calls `Knockback`. **Pattern:** data-driven.

### `URestorationSubsystem`: the rules of restoration
| Function | What it does |
|---|---|
| `OnWorldBeginPlay` | Counts every `ALifeNote` in the level |
| `ReportNoteCollected` | Adds a note, tells listeners where it was, and recalculates. All notes always means 1.0 |
| `DrainRestoration` | Lowers the value, never below the locked amount, and records the loss as `DrainPenalty` |
| `LockInRestoration` | Called by shrines. The current value becomes the minimum |
| `BroadcastNewMilestones` | Fires each of the 25, 50, 75 and 100 percent events once |

**Patterns:** subsystem and observer.

### `ARestorationDriver`: what the player sees
`Tick` moves `DisplayedRestoration` smoothly toward the real value. `ApplyVisuals` writes it to the material parameter collection, the post-process volume and the fog. `HandleNoteCollected` sets `LastNoteLocation` and restarts the local bloom radius. If `M_LS_WitherPost` exists, `BeginPlay` adds it to the volume and saturation goes through that material, which leaves the player in full colour. If not, the volume's own saturation is used. **Pattern:** observer. At full restoration the volume's own saturation, contrast and gain, read at `BeginPlay`, come back exactly, so the healed Wildwood looks as the pack's map was graded.

**The witch's storm.** `GetStorm` is 1 while the world is withered and fades to 0 by 75% restoration, and everything stormy follows it, so collecting notes calms the sky as it brings the colour back. With `bStormGrade` on (set by `Content/Python/ls_storm.py`, which also raises Wildwood's sky light from 2.0 to 6.0 and the volume's exposure bias from 2.0 to 2.8, so the healed forest is bright even under the canopy; the storm scales both back down), `BeginPlay` reads the level's own exposure, vignette, grain, fringe, fog colour and the `Sun` and `SkyLight` brightness, and the storm fades each one from its storm value back to that. At full storm the picture is a little darker, harsher, cold, grainy and fringed at the edges, the sun and sky light are dimmed, and the fog and clouds are near black. `Strike` fires every `LightningIntervalMin`–`LightningIntervalMax` seconds with up to `MaxBoltsPerStrike` bolts (`LightningBolt` plus copies made at `BeginPlay`), now and then a close one (`CloseStrikeChance`). Its thunder is delayed by the distance over the speed of sound, and louder and sharper when close. Each flash brightens the sky light so the strike lights the land. The sun is not flashed, because a sudden change in its brightness makes the volumetric clouds re-render as blocky noise. Every thunder still playing is kept in `ThunderAudios`, so all of them fade when the storm clears. The Wildwood pack's `NS_Rain` (its 200 m spawn square scaled to a quarter across) follows the camera while the storm is above 0.35. `StormWindEffect` can add swirling leaves the same way; Wildwood leaves it empty. **Pattern:** observer.

### `ARestorableActor`: plants that grow back
Hidden at the start. It starts growing when restoration reaches its threshold or a note is collected nearby. `Tick` scales it with a bounce curve, and only runs while growing. An optional `WitheredMesh` (a dead trunk, say) stands in its place until then and shrinks away as it grows, which is how Level 1's dead trees come back to life. Trees also wait a random `MaxStartDelay` (so a stand rises in a wave), sway by `ShakeDegrees` while growing, fading as they settle, and play `GrowSound` when they start (spaced at least 0.35 s apart across all trees, so many at once don't turn into noise). The sound uses recorded leaves and a robin call credited in `AUDIO_CREDITS.md`. **Pattern:** observer.

### `AWitherBlob`: the enemy
| Function | What it does |
|---|---|
| `UpdateState` | The state machine: Patrol, Chase, Return, with the rule for leaving each state |
| `MoveToward` | Straight-line seek. A line trace finds the ground, stops the blob at ledges, and a sweep stops it at walls |
| `HandleBallContact` | A slam from above kills the blob. Otherwise it drains restoration and knocks the ball back |

**Pattern:** state machine.

### `AWitheringStorm` and `AStormTrigger`: the chase
`AStormTrigger` calls `StartRising`, which subscribes to the ball's events. `Tick` raises the box, updates the rumble and camera shake, and kills a ball inside. `HandleNoteCollected` pushes it down, `HandleCheckpointSet` saves a safe height, and `HandleBallRespawned` restores it. **Pattern:** observer.

When `ChasePoints` is set, the storm chases along that path instead of rising: `Progress` is how far along it the storm is, and `SetProgress` places and turns it there. It stays hidden until the trigger fires. Notes push it back along the path. A ball that dies before reaching a checkpoint in the chase respawns behind the trigger, so the chase is called off and starts again when the ball passes the trigger. The old purple chase to the Heart Tree has been removed. In Wildwood the class now drives the witch's river curse, started by the riverbank ambush (see "The witch cutscenes").

### `ABounceMushroom`: a giant mushroom that bounces the ball
`OnBallHit` launches a ball that lands on the cap (more than `BounceAboveHeight` above the base) upward at `LaunchSpeed` through `ASeedBall::Knockback`, keeping most of its sideways speed, and plays `BounceSound` at a slightly random pitch. `Tick` squashes the cap and lets it spring back for 0.8 s. Its meshes and textures come from `Content/Python/ls_generate_mushroom.py`. In Level 1, two notes float above mushrooms where only a bounce reaches them. **Pattern:** interface (`ILSInteractable`).

### `AGhostRacer` and `ULSGhostSave`: legacy replay, disabled
The white best-run replay ball has been removed from the level. The builder removes legacy replay actors instead of spawning them, so gameplay no longer records or displays a ghost. The C++ classes and existing `Ghost_<level>` save files remain for compatibility; normal progression and best times are unaffected.

### `UAdaptiveMusicComponent` and `AMusicManager`: music that grows back
`AMusicManager` is a placeable actor that stays loaded and holds the component. `BeginPlay` starts every stem together at near-zero volume and fades in stem 0. `HandleMilestoneReached` fades in the next stem at each restoration milestone. `PlayFinale` fades out the stems and fades in the finale when the level completes. **Pattern:** observer.

The five stems and the finale are made by `Content/Python/ls_generate_music.py`: 45.7 s loops at 84 BPM in D major (pads, then drums, bass, flute melody, and strings with birdsong), so every layer lines up. It also makes the bounce, note chime and storm rumble sounds.

### Sound effects
Looping sounds use a `UAudioComponent`, so an attenuation can be assigned: `RollAudio` on the ball, `WindAudio` on wind volumes, and `RumbleAudio` on the storm. One-shot sounds call `UGameplayStatics::PlaySoundAtLocation`, which does nothing when the sound is empty, so every sound is optional. The roll sound lives in `FSeedFormData`, so each form sounds different with no form check in the code.

### Shared helpers
- `ALSVolumeBase::GetBallInside` returns the living ball in the box, for children that act every frame.
- `ASeedBall::AddExternalAcceleration` and `Knockback` are how the world pushes the ball.
- `LSDefaultMeshes.h` supplies engine meshes, so actors are visible as soon as they are placed.

### `Content/Python/build_greybox.py`: the level builder
An editor script, so it isn't part of the game. Helpers such as `floor`, `ramp` and `note` keep each zone function readable, and the spacing comes from the ball's real speed and jump height. Every actor gets a tag, so a rerun replaces only its own work. `dress_mesh` reads a mesh's bounds to scale it to a target height and rest it on the ground.

### `Content/Python/ls_asset_inventory.py`: what the Fab packs contain
An editor script that writes every mesh, material, Niagara system and cloud asset to a CSV, with its size and a category guessed from its name. The world scripts choose assets from this list, which is why they can scale scenery correctly. It only reads.

### `Content/Python/ls_generate_player_meshes.py`: the player's models
A standalone script using only the standard library. It builds each model from maths and writes it as an OBJ file. The Seed's ridges come from the angle around the ball. Stone's plates are Voronoi cells: each point belongs to its nearest random centre, and the cracks are where two centres are almost equally near. The Dandelion is many thin stalks with small tufts, spread evenly with a Fibonacci spiral. `check_mesh` stops the script if any part would stick out past the 50 cm ball.

### `Content/Python/ls_import_player_assets.py`: the player's art
An editor script that imports the OBJ files, builds the materials node by node, creates the physical materials and fills in `BP_SeedBall`'s form data. Rerunning it rebuilds each asset in place. The materials need no textures, because the UVs carry masks: on the Stone, U says how much of a crack a point is, and the material turns that into glowing gold.

### `Content/Python/build_world_level1.py` and `ls_world_common.py`: the forest
The level script decides what goes where, and `ls_world_common.py` knows how to place it, so Level 2 can share it. The tables at the top of the script hold the whole layout: `BENDS`, `INSERTS`, `HILLS` and the rest. `ls_curved_route.py` turns a greybox position into (s, d), the distance along the winding road and the distance to its right. Because distance along the road never changes, a jump measures the same after bending. `road_height` and `terrain_height` give one height for any point, and the road mesh, terrain and trees all use them, which is why everything sits on the hills. `shaped_land` averages the hillsides over the nearby road, as using only the nearest point would make a cliff wherever a different stretch of road becomes nearest. `check_layout` stops the build if a table edit makes a slope too steep, puts a bend on a puzzle, or runs the road into itself. Each greybox actor keeps its original place in an `LS_Origin` tag, so a rerun bends from the straight line again. `ls_generate_world_meshes.py` builds what the Fab packs lack: the giant tree, music note, gate ring and floating island. `Scatter` groups transforms by mesh into one instanced component each, with a cull distance per ring. `jittered_grid` with a fixed seed gives a forest that looks random but rebuilds identically. `ls_material_helpers.py` holds the small node-building functions the material scripts share.

### `Content/Python/ls_emberwood.py`: Level 2, Emberwood
Level 2 is `/Game/LastSeed/Maps/L_Level2_Emberwood`, a copy of the lava pack's `references` map (the pack's own map is never changed). Wildwood's goal, the main menu's Level 2 button and `ls_witch_exile.DESTINATION` all point at it. Seed lands in the pack's lava basin, where all ground is safe, with the painted arrival shot. The route then leaves the basin's east shore (world y 7500), where shore rocks hide the drop to lower open lava that kills. A second kill volume lies under the whole map, below the pack's deep lava pit. The route's numbers are in its own frame, and `to_world` turns them onto the map, running along world +Y.

It builds three sections from the pack in `Content/Lava` (all under `World/Emberwood/`, which a rerun clears):
1. **Ember Steps.** Basalt stones over the lava, like the arrival's (shelf mesh for looks, a hidden flat cylinder to land on), then four `ACrumblingPlatform`s dressed as the pack's dark slab. Lantern checkpoint on the big stone.
2. **Updraft Chasm.** Three `AWindVolume` updrafts from lava vents, marked by the pack's sparks and an orange light, with two rest stones. Too far to jump, so Dandelion rides them; an energy hangs in each column.
3. **Ruined Keep.** The pack's floor tiles, walls, arches and columns, standing on a basalt foundation. Seed rolls on a hidden flat slab, because the tiles' rocky tops trap a ball. Stone Shell pushes Wildwood's crate onto an `ALever` (it ignores the ball itself), which raises a portcullis (`AGate` sliding up). The goal with `bEnergyFinale` is beyond it.

Sixteen energy orbs are `BP_LifeNote`s with a sphere and `M_LS_EnergyOrb`; the HUD calls them Energy when the level's goal has `bEnergyFinale`. Scenery: lava cliffs, lava falls with splashes, glowing lava floes, burning trees, ember bushes and the pack's lava ambience.

### `Content/Python/ls_wildwood_plan.py` and `build_level1_wildwood.py`: Level 1 in the Wildwood forest
`L_Level1_Wildwood` is a copy of the Wildwood pack's demo map. The plan script runs outside Unreal (it needs numpy) and works out a 900 m trail through the pack's own landscape: a smooth curve through the control points in `ROUTE`, picked to keep to the gentler slopes. The trail is a dirt ribbon that hugs the ground, never more than `FILL_CAP` (2 m) above it, with level stretches only where `FLATS` needs them. It is a mesh laid on the landscape, never cut into it, because this engine version's landscape import scrambles the Wildwood landscape. All parkour is props: rock stacks, logs, a moving rock and crumbling rocks over the three water crossings in `CROSSINGS`, a rock tower to glide from, and rock stairs (`find_climbs`, `rock_stairs`) wherever the ground climbs more steeply than 15 degrees. The build script's `fit_rock` keeps each rock close to its own proportions, since a stretched boulder reads as a spike. Every parkour rock and log collides as its own mesh (`collide`): the boulders as their exact triangles, the logs and stacked rocks as a hull wrapped round the mesh, so the ball meets the shape the player sees. `trail01_extras` adds easy rock and log hops along trail piece 01, marked `extra` so the `extras` stage can add them to a level that is already open without touching anything else. Rocks and logs placed by hand in the editor are kept in `ls_hand_placed.json` (the `protect` stage records them and turns on collision for copies made in the editor, which come with it off; the `hand` stage puts them back after a full rebuild). Run `protect` after editing them by hand, and don't rebuild the level without running it first. `Content/Python/ls_widen_trail.py` moves the hidden side walls up to 2 m further out on open stretches, easing to no change near anything that spans the trail wall to wall and near kill volumes, and moves each wall's ends so neighbouring walls stay joined; run it again after a full rebuild. `ASeedBall::ApplyTrailEdgeResistance` starts its soft push 60 cm before a wall. The plan also places every pickup, puzzle and hidden wall, and picks the trees near the trail that become regrowing trees. The build script applies the plan in the editor, one stage per call. The far forest has no actors to swap: its leaf material multiplies the leaves' opacity by `Restoration` from `MPC_Restoration` against each tree's random value, so a little more of the forest leafs out with every note. `fun_extras` in the plan adds the bouncy mushrooms, the two raised notes, and the Withering's chase, marked `extra: "fun"`. The `fun` stage adds them to the open level, together with the music and the note chime.

### `Content/Python/ls_generate_ui.py` and `build_ui.py`: the screens
Every screen's logic is in C++ (`ULSMainMenuWidget`, `ULSPauseMenuWidget`, `ULSControlsWidget`, `ULSHUDWidget`, `ULSStoryCardWidget`, `ULSResultsWidget`). Its layout is a Widget Blueprint of the same name in `/Game/UI` (`WBP_MainMenu` and so on) whose widget names match the C++ `BindWidget` properties. They share one look: dark moss panels with a thin gold edge, cream text, gold for the main button of each screen. `ls_generate_ui.py` paints the icons (notes, petals, timer, stars, the three forms) and the leaf divider, and `build_ui.py` imports them, makes `L_MainMenu` (an empty level run by `BP_LSGameMode_Menu`, which shows the main menu and spawns no ball) and points the player controller at every screen. The packaged game starts on `L_MainMenu`.

### Dev cheats
`bEnableDevCheats` on `ALSPlayerController` adds F1, F2 and F3 to the mapping context. F3 collects real notes through `OnBallOverlap`, so the count and stars stay correct. In editor builds only, F10 (`HandleDevGoToFinale`) puts the ball on the ground just before the planting goal, to test the Witch Exile without playing the whole level.

## How to explain this in my video
Each rubric area, with what to show and where it is.

### Complexity
| Show | Where |
|---|---|
| Forms as a data-driven state pattern | `FSeedFormData`, then `ASeedBall::TrySwitchForm` |
| An interface in place of casting | `ILSInteractable`, `ASeedBall::HandleBeginOverlap` |
| A world subsystem holding the rules | `URestorationSubsystem` |
| Delegates, with several listeners on one event | `OnMilestoneReached`, used by plants and music |
| An AI state machine | `AWitherBlob::UpdateState` |
| Physics | `ASeedBall::ApplyMovement`, and point 11 below on why the block needs no push code |

### Engagement
| Show | Where |
|---|---|
| Stars and their conditions | `ALSGameMode::BuildResult`, then the results screen |
| Hidden Golden Petals | `AGoldenPetal`, and a petal found in play |
| The witch's river curse | `AWitheringStorm::TickShockwave`, then jumping the waves on the riverbank |
| Bouncy mushrooms and raised notes | `ABounceMushroom::OnBallHit`, then bouncing up to a note |
| Notes that play a rising tune | `ALifeNote::GetCollectPitch` |
| No replay ball | Verify no `AGhostRacer` actors exist during the intro and gameplay, including when a legacy ghost save exists |

### Clarity
| Show | Where |
|---|---|
| Tutorial triggers | `ATutorialTrigger`, and a prompt fading on the HUD |
| The HUD | `ULSHUDWidget`, and how `BindWidget` links C++ to the layout |
| The controls menu | `ULSControlsWidget`, a single list used by both menus |

### Music
| Show | Where |
|---|---|
| Adaptive stems | `UAdaptiveMusicComponent::BeginPlay` and `HandleMilestoneReached`, then collect notes in play so the layers are heard |
| Why stems stay in sync | Point 22 below |
| The finale | `PlayFinale`, listening to `OnLevelCompleted` |

### Storyline
| Show | Where |
|---|---|
| Story triggers | `AStoryTrigger`, then `ALSPlayerController::PlayStory` |
| Endings and credits | `ALevelGoal`, then `ALSGameMode::CompleteLevel` and `ContinueAfterResults` |
| The witch's ambush and curse | `AStoryTrigger::CheckLanding`, then `AfterCutsceneCurse` starting the shockwaves |
| The Witch Exile into Emberwood | `ALevelGoal::bRequireJump` and `TravelShots`, then the `Arrival` shot in `L_Level2` |
| Facing the witch, and the energy burst home | `ALevelGoal::bEnergyFinale` and `PlayEnergyBurst`, then `ALSGameMode::IsRestoredArrival` and `URestorationSubsystem::RestoreFully` in Wildwood |
| The story told through the world | `ARestorationDriver` and `ARestorableActor`, colour returning as notes are collected |

## Points worth explaining
1. **The camera does not spin with the ball.** The spring arm uses absolute rotation and control rotation.
2. **Why `bAccelChange = true`.** Rolling and jumping stay independent of mass, so mass can drive plates and blocks while handling is tuned separately. Friction still depends on the physical material.
3. **The torque axis.** `Up x MoveDirection` makes the top of the ball move toward the input direction.
4. **Coyote time and jump buffering.** Two countdown timers forgive a jump pressed slightly late or slightly early.
5. **The velocity save in `ApplyFormData`.** `SetStaticMesh` recreates the physics body, which would stop the ball mid-air without this.
6. **The zero-delay timer guard in `Die`.** `SetTimer` with a rate of 0 cancels the timer, so the ball would never respawn.
7. **`PreImpactVelocity`.** Hit events fire after physics has resolved the collision, so the ball's speed at that moment is already reduced. It is saved each Tick to get the true impact speed.
8. **The `bCollected` guard.** `Destroy` doesn't remove the actor immediately, so the guard prevents collecting twice.
9. **Why pickups have no overlap code of their own.** The ball is the only class listening for overlaps, which keeps the logic in one place.
10. **Why plates, ice and hazards check every frame.** Switching form changes mass and abilities with no new overlap event. An overlap-only plate would miss Stone transforming while already on it.
11. **Why the block needs no push code.** A rolling ball pushes with the smaller of its grip (friction x weight) and its rolling force (0.4 x mass x radius x `TorqueStrength`). On ice, Seed has almost no grip, while `PM_Stone` keeps Stone's grip high, so only Stone moves the block.
12. **How the ball rides a platform.** Moving a kinematic body without teleporting gives it a real velocity in the physics engine, and friction carries the ball.
13. **Forms are never named in hazard, ice or wind code.** They compare `MassKg`, `bFragile`, `WindResponse` and `bBuoyancyEnabled`, so tuning a form changes how the whole world treats it. `ACrackedWall` is the one exception: the brief says only Stone breaks it.
14. **Why the wind pulse has no timer.** `Fmod(time, on + off) < on` works out the current state from world time, so there is no state to keep in sync.
15. **Why rules and visuals are two classes.** A subsystem can't hold editor-assigned assets or level references, and it should only contain rules. The driver is a replaceable view of the same data.
16. **Why restoration is recalculated from the note count.** Adding 0.05 twenty times can miss exactly 1.0 through rounding, and a milestone could be skipped. `Collected / Total - DrainPenalty` can't drift.
17. **How one asset recolours the whole world.** A material parameter collection is shared by every material that reads it, so one value change updates them all with no list of objects.
18. **`bIsSpatiallyLoaded = false`.** World Partition only loads actors near the player. Without this, distant notes wouldn't exist when they are counted, and the total would be wrong.
19. **Why two radii on the blob.** With `ChaseRadius` smaller than `LoseRadius`, a ball near the limit can't make the blob flip between states every frame.
20. **Why the blob's collision blocks only level geometry.** It overlaps the ball, so the ball's physics isn't disturbed and the code decides what contact means, but it still stops at walls.
21. **`RespawnClearance`.** Without it, a checkpoint reached with the storm just below would kill the player again on every respawn.
22. **Why all stems start at the beginning.** A stem started at its milestone would begin from its first beat, out of time with the others. Starting them together and only changing volume keeps them in sync, which is why they need **Play When Silent**.
23. **Why the stems use the fade and not the volume multiplier.** The final volume is the multiplier times the fade level. If the multiplier were set near zero, fading "up to 1" would still be near silent, so the multiplier stays at 1.
24. **`AirFallSpeed`.** By the frame the ball counts as grounded, physics may already have stopped it, so the landing volume uses the speed from the last frame in the air. `Respawn` clears it so a fatal fall doesn't play a landing at the checkpoint.
25. **Why menus use Game and UI input.** UI-only input would stop the Pause key reaching the controller, so it couldn't close the pause menu. Gameplay keys are still safe, because Enhanced Input ignores them while paused unless an action sets `bTriggerWhenPaused`.
26. **Why text cards pause the game but cutscenes don't.** A sequence can't play while paused, so a cutscene removes the input context and stops the timer. Text cards simply pause, which also freezes the blobs and storm.
27. **Why results are saved before the ending plays.** A player who quits during the ending has still finished the level.
28. **Why the first best time needs a check.** A new record's time starts at 0, so `Min` would keep 0 forever. The first finish copies the time across.
29. **Why the visuals are separate from the physics sphere.** A bumpy mesh on the physics body would make the ball bounce on its own bumps, and swapping meshes would rebuild the body and lose its speed. A hidden perfect sphere does the physics, so all three forms roll the same way, and the art can change freely.
30. **How the sprout stays upright on a rolling ball.** `UprightVisual` uses absolute rotation, so it ignores the ball's spin. The mesh is modelled around the ball's centre with no offset, so there is no position for the spin to swing around.
30a. **Why a switch changes physics at once but the look over 0.35 s.** `TrySwitchForm` applies mass, grip and abilities on the key press, so a switch to Stone mid-jump is heavy straight away. Only the meshes, light and camera follow `UpdateFormSwitch`, which runs before `Tick`'s death check, so a switch interrupted by dying still finishes and the ball respawns at full size. Each form's burst, sound and shake come from its `FSeedFormData`, filled in by `Content/Python/ls_form_switch.py`, which also cuts the three switch sounds from CC0 recordings credited in `AUDIO_CREDITS.md`.
31. **How the player stays in colour in a grey world.** Post-process saturation greys every pixel, including the player. Instead, the ball's meshes write stencil value 1, and `M_LS_WitherPost` greys only the pixels without it. Custom depth keeps a marked object's depth even when something stands in front of it, so the material also checks that the marked object is the nearest thing at that pixel. Without that check, everything in front of the lava stayed in colour. This needs `r.CustomDepth=3` in `DefaultEngine.ini`, which turns on the stencil.
32. **Why the cubes are hidden and not deleted.** A flat cube is perfect collision for a rolling ball, and a Fab mesh's rough collision would make it bounce. Hidden components still collide, so art and physics can each be what they are best at.
33. **Why instancing matters.** The forest has about 5,700 objects. One instanced component draws all copies of a mesh together, and its cull distance drops distant ones, which keeps a laptop GPU near 60 fps.
34. **Why the invisible walls ignore the camera channel.** The spring arm pulls in when it hits something on that channel, so a wall that blocked it would make the view jump whenever the ball rolled beside an edge.
35. **Why the road is one mesh instead of rotated cubes.** Rotated cubes would leave a small step at every joint on a curve. A strip following the curve has none, and it uses its exact triangles as collision.
36. **Why blocks have their own physical material.** Stone's grip is so strong that pushing a block also presses it into the ground, and that friction also fights the ball's spin, which jammed it. `PM_Block`'s lower friction leaves enough push to move it at a fair pace. Seed can push it too, but only Stone or a block can hold a plate down.
38. **Why the block runs in a log chute.** A block pushed against a wall could never be pulled back, which would leave the gate shut for good. The chute runs straight down the middle of the tunnel with the road open on both sides, and a log at its end stops the block on the plate. The block also has its Z rotation locked, because a turning block wedged itself across the chute.
39. **How the rock pile breaks.** The hidden `ACrackedWall` cube is still what the ball hits. The boulders are plain scenery listed in its `RubbleActors`, which it hides as it breaks. The cave shell is solid, which keeps the camera inside the tunnel.
41. **Why the cavern is one fenced walkway.** The first version was a loop of pads behind hidden walls, and players couldn't tell where to go or why the ball stopped. Now it is one straight line to the exit with no walls at its edges, and any form can tip the logs. A fall into the water just restarts from the checkpoint just before the cavern.
42. **Why the sun shaft fades at its edges.** A cone would show hard lines in the air, so the material's Fresnel term dims the faces seen edge-on. It is additive and has no shadows, which keeps it cheap. The real light comes from one spotlight.
40. **How a zone gets its own look.** `zone_grade` adds a post-process component under a box, so the change applies only while the camera is inside it and fades at the edges. A box can't bend, so Rootwood Hollow uses three.
43. **Why the marsh's mist is sheets and not fog volumes.** Local Fog Volumes only start 20 m from the camera, which leaves the air around the ball clear. Three thin translucent sheets of drifting noise sit just above the water instead. The mesh's U sets how thick the mist is at each point, and Depth Fade softens the line where a sheet meets a root.
44. **How one material draws a blob's body, goo and eyes.** `build_blob` stores the part in each vertex's U (0 body, 0.5 goo, 1 eye), and `M_LS_Blob` turns that into dark skin, a purple glow or a white glow. It needs only one material slot and no textures. The eyes are fixed to look back down the road, because `AWitherBlob` doesn't turn as it moves.
45. **Why the water is a generated mesh.** The road bends under the swamp, and overlapping planes would double up their transparency. `build_swamp_water` makes one sheet from a grid, keeping only the squares near the swamp's low ground, so it can't spill into the cavern or the thorn pits.
46. **Why only the cliffs are solid scenery.** `mesh_actor` turns collision off, because rough rocks by the road would make a rolling ball bounce. `solid_cliffs` turns it back on for every `Cliff_07`, using the simple collision shapes the Fab mesh already has, so the Fab asset itself never changes.
47. **How the lava works.** It needs no new gameplay class. The pit already had an `AKillVolume`, whose top now sits just under the lava's surface, and the imported `M_Lava_01` material only has to look dangerous. `river_shape` describes the river as a middle and a width at each distance from the road, and both the terrain's channel and `build_lava`'s strip are built from it, so the two always fit. The lava is wider than the channel and the banks hide its edges, so the shore is simply where the ground meets the surface. Stencil 1 keeps it in colour in the grey world, so it reads as danger at once.
37. **Why the world starts at saturation 0.** `RestorationDriver` starts Level 1 fully black and white, so `WitheredSaturation` must be 0. A higher value keeps too much of the sunset's colour and the effect stops reading. Only things the player must find have stencil 1 and keep their colour.

## Suggested explanation order
1. `SeedFormTypes.h`: what a form is.
2. `ALSPlayerController::CreateInputObjects`: input built in code.
3. `ASeedBall::Tick`: a readable overview of each frame.
4. Rolling, then the jump timers.
5. `TrySwitchForm`, `ApplyFormData` and `ApplyFormVisuals`: the state pattern, with physics and art kept apart.
6. Slam and glide: abilities driven by data flags.
7. `Die`, `Respawn` and the delegates: the observer pattern.
8. `ILSInteractable` and `ASeedBall::HandleBeginOverlap`: the interface.
9. `ALSPickupBase::OnBallOverlap`, then the three short `OnCollected` versions: the template method.
10. `ACheckpointShrine`, then `ULSGameInstance::SaveProgress`: checkpoints and saving.
11. `ACrackedWall::OnBallHit`: the interface in use, with a real impact speed.
12. `APressurePlate::Tick`, then `AGate::RefreshGate`: the observer pattern, where a gate waits for its plates.
13. `AHazardVolume::Tick`, `AWindVolume::Tick` and `AWaterVolume::Tick`: one form data struct driving three different systems.
14. `ACrumblingPlatform::Tick`: a state machine, then `ASinkingPad`'s constructor as the same logic with new values.
15. `ALifeNote::OnCollected`, then `URestorationSubsystem::ReportNoteCollected`: one pickup updating the whole game.
16. `ARestorationDriver::ApplyVisuals`, then the `MF_WitherBlend` material function: how a number becomes colour.
17. `ARestorableActor`: another listener, and the bounce curve.
18. `AWitherBlob::UpdateState`: the enum state machine, then `HandleBallContact` for the slam check.
19. `AWitheringStorm`: three events from two classes driving one chase, then `TickShockwave` for the witch's river curse.
20. `UAdaptiveMusicComponent`: the same milestone event that grows plants brings in the music.
21. `ASeedBall::UpdateRollAudio`: form data choosing the sound, and speed shaping it.
22. `ALSGameMode::CompleteLevel`, then `BuildResult`: the level-complete flow and the star rules.
23. `ALSPlayerController::OpenMenu` and `PlayStory`: input modes, pausing and story.
24. The witch cutscenes: `AStoryTrigger` waiting for the landing, `ELSIntroTransition`, and `ALevelGoal::TravelShots` carrying the seed to Emberwood.
25. `ULSHUDWidget`: `BindWidget`, and a display that only listens.
26. `ULSGameInstance::RecordLevelResult`, then `ULSMainMenuWidget`: how saved data unlocks Level 2.
