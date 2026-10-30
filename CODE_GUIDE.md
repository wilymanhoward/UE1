# Last Seed: Code Guide

The player is the last glowing seed of a dead Heart Tree. This guide explains each class and suggests how to present the code in the video. It is updated every phase.

## Classes

### `SeedFormTypes.h`: form data
- `ESeedForm`: Seed, Stone, Dandelion.
- `FSeedFormData`: every value that makes a form different (mesh, mass, damping, torque, jump, wind response, gravity scale, and the ability flags).
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
| `ApplyFormData` | Applies a form to the physics body, saving velocity because a mesh swap would lose it |
| `Die` / `Respawn` | Freeze and hide, then teleport to the checkpoint with velocity zeroed |

**Patterns:** state (small and data-driven) and observer (`OnFormChanged`, `OnDied`, `OnRespawned`).

### `ALSPlayerController`: input
- `CreateInputObjects` builds all actions and the mapping context with `NewObject`, so no input assets are needed.
- `BindInputActions` connects actions to small handlers that forward to the ball.
- `HandleTogglePause` is a placeholder until the Phase 7 pause menu.
- Test commands: `LSUnlockAllForms`, `LSKillBall`.
- **Pattern:** command-style forwarding. The controller knows the keys, the ball knows the behaviour.

- `ShowPrompt` is the single route for player messages. It shows debug text until the Phase 7 HUD exists.
- Extra test commands: `LSDeleteSave`, and `LSDrainRestoration <amount>`.
- `ShowRestorationStatus` displays the note count until the Phase 7 HUD exists.

### `ULSGameInstance` and `ULSSaveGame`: persistent data
The game instance stores `UnlockedForms` and the last shrine reached. It survives level changes, so Level 2 keeps forms unlocked in Level 1. `SaveProgress` copies those values into a `ULSSaveGame` and writes it to disk, and `Init` loads them at startup. **Pattern:** memento (the save object is a plain snapshot).

### `ALSGameMode`: level rules
Sets the default pawn and controller, and counts Golden Petals. Phase 7 adds the rest.

### `ILSInteractable`: the interaction contract
`OnBallOverlap(Ball)` and `OnBallHit(Ball, ImpactVelocity)`, both defaulting to no action. `ASeedBall::HandleBeginOverlap` and `HandleHit` cast whatever they touched to this interface and call it. **Pattern:** interface / polymorphism. The ball never casts to a pickup or a volume, so new world objects don't change the ball.

### `ALSPickupBase`, `ALifeNote`, `AGoldenPetal`, `AFormFlower`: pickups
`ALSPickupBase` handles bob and spin, the collect-once guard, effects and `Destroy`. Children implement only `OnCollected`:
- `ALifeNote`: reports to `URestorationSubsystem`.
- `AGoldenPetal`: adds to the count in `ALSGameMode`.
- `AFormFlower`: unlocks a form, saves, and shows a prompt.

**Pattern:** template method. The base class fixes the order of the steps, and children fill in one step.

### `ACheckpointShrine`: respawn points
On first touch it sets the ball's checkpoint, records and saves it, locks in the current restoration, turns on the glow and plays effects. It then ignores further touches.

### `ALSVolumeBase`, `AKillVolume`, `ATutorialTrigger`: volumes
`ALSVolumeBase` creates the invisible overlap box. `AKillVolume` calls `Die`. `ATutorialTrigger` shows its message once.

### `ACrackedWall`: breakable wall
`OnBallHit` checks for Stone, then for a slam or an impact speed of at least `BreakSpeed`. `Break` hides the mesh, removes its collision, and spawns physics debris with a set lifespan. It is the first user of the `ImpactVelocity` value that `ASeedBall` saves before each impact.

### `APressurePlate`: weight sensor
`GetMassOnPlate` adds up the mass of every simulating body in the trigger. `Tick` compares it with `RequiredMassKg` and broadcasts `OnPlatePressed` or `OnPlateReleased` when the answer changes. `OnBallOverlap` shows the "Too light!" prompt. **Pattern:** observer.

### `AGate`: door with a timeline
`BeginPlay` builds the timeline from `OpenCurve`, or from `CreateDefaultCurve` when none is assigned, and subscribes to every plate. `RefreshGate` plays forward only if all plates are pressed, and otherwise reverses. **Pattern:** observer.

### `APushableBlock`: heavy physics body
Contains almost no code, because mass and friction produce the behaviour. `FellOutOfWorld` returns it to its start so a puzzle can't become impossible.

### `AMovingPlatform`: spline path
`Tick` advances a distance along the spline, handles ping-pong or loop at the ends, and moves the kinematic mesh. Two spline points are the simple A-to-B case, so there is one path system and not two.

### `ACrumblingPlatform` and `ASinkingPad`: delayed collapse
An `ECrumbleState` state machine: Solid, Shaking, Falling, Waiting, Returning. `ASinkingPad` only changes default values in its constructor. **Pattern:** state machine.

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
`Tick` moves `DisplayedRestoration` smoothly toward the real value. `ApplyVisuals` writes it to the material parameter collection, the post-process volume and the fog. `HandleNoteCollected` sets `LastNoteLocation` and restarts the local bloom radius. **Pattern:** observer.

### `ARestorableActor`: plants that grow back
Hidden at the start. It starts growing when restoration reaches its threshold or a note is collected nearby. `Tick` scales it with a bounce curve, and only runs while growing. **Pattern:** observer.

### Shared helpers
- `ALSVolumeBase::GetBallInside` returns the living ball in the box, for children that act every frame.
- `ASeedBall::AddExternalAcceleration` and `AddVelocityChange` are how the world pushes the ball.
- `LSDefaultMeshes.h` supplies engine meshes, so actors are visible as soon as they are placed.

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

## Suggested explanation order
1. `SeedFormTypes.h`: what a form is.
2. `ALSPlayerController::CreateInputObjects`: input built in code.
3. `ASeedBall::Tick`: a readable overview of each frame.
4. Rolling, then the jump timers.
5. `TrySwitchForm` and `ApplyFormData`: the state pattern.
6. Slam and glide: abilities driven by data flags.
7. `Die`, `Respawn` and the delegates: the observer pattern.
8. `ILSInteractable` and `ASeedBall::HandleBeginOverlap`: the interface.
9. `ALSPickupBase::OnBallOverlap`, then the three short `OnCollected` versions: the template method.
10. `ACheckpointShrine`, then `ULSGameInstance::SaveProgress`: checkpoints and saving.
11. `ACrackedWall::OnBallHit`: the interface in use, with a real impact speed.
12. `APressurePlate::Tick`, then `AGate::RefreshGate`: the observer pattern solving the two-plate puzzle.
13. `AHazardVolume::Tick`, `AWindVolume::Tick` and `AWaterVolume::Tick`: one form data struct driving three different systems.
14. `ACrumblingPlatform::Tick`: a state machine, then `ASinkingPad`'s constructor as the same logic with new values.
15. `ALifeNote::OnCollected`, then `URestorationSubsystem::ReportNoteCollected`: one pickup updating the whole game.
16. `ARestorationDriver::ApplyVisuals`, then the `MF_WitherBlend` material function: how a number becomes colour.
17. `ARestorableActor`: another listener, and the bounce curve.
