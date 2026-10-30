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
- Extra test command: `LSDeleteSave`.

### `ULSGameInstance` and `ULSSaveGame`: persistent data
The game instance stores `UnlockedForms` and the last shrine reached. It survives level changes, so Level 2 keeps forms unlocked in Level 1. `SaveProgress` copies those values into a `ULSSaveGame` and writes it to disk, and `Init` loads them at startup. **Pattern:** memento (the save object is a plain snapshot).

### `ALSGameMode`: level rules
Sets the default pawn and controller, and counts Golden Petals. Phase 7 adds the rest.

### `ILSInteractable`: the interaction contract
`OnBallOverlap(Ball)` and `OnBallHit(Ball, ImpactVelocity)`, both defaulting to no action. `ASeedBall::HandleBeginOverlap` and `HandleHit` cast whatever they touched to this interface and call it. **Pattern:** interface / polymorphism. The ball never casts to a pickup or a volume, so new world objects don't change the ball.

### `ALSPickupBase`, `ALifeNote`, `AGoldenPetal`, `AFormFlower`: pickups
`ALSPickupBase` handles bob and spin, the collect-once guard, effects and `Destroy`. Children implement only `OnCollected`:
- `ALifeNote`: logs for now, and reports to the restoration subsystem in Phase 4.
- `AGoldenPetal`: adds to the count in `ALSGameMode`.
- `AFormFlower`: unlocks a form, saves, and shows a prompt.

**Pattern:** template method. The base class fixes the order of the steps, and children fill in one step.

### `ACheckpointShrine`: respawn points
On first touch it sets the ball's checkpoint, records and saves it, turns on the glow and plays effects. It then ignores further touches.

### `ALSVolumeBase`, `AKillVolume`, `ATutorialTrigger`: volumes
`ALSVolumeBase` creates the invisible overlap box. `AKillVolume` calls `Die`. `ATutorialTrigger` shows its message once.

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
