// Last Seed - the player's ball.
//
// Purpose: the physics-driven pawn. It rolls, jumps, glides, slams, changes form, dies and respawns.
// Design patterns:
//   - State pattern (small, data-driven): TrySwitchForm runs OnExitForm then OnEnterForm, and the
//     active state's behaviour comes from its FSeedFormData entry.
//   - Observer pattern: OnFormChanged, OnDied and OnRespawned let UI and audio react without the ball
//     knowing they exist.
// Connections: ALSPlayerController calls the input functions below. ULSGameInstance says which forms are
// unlocked. Everything the ball touches is told through ILSInteractable. Hazards, water and wind read
// GetCurrentFormData() and push the ball through AddExternalAcceleration and Knockback. It plays its own
// sounds, including a rolling loop chosen by the active form's data. What the player sees is separate from
// the physics: the sphere is hidden once a form has a mesh, and the visual meshes have no collision.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "SeedFormTypes.h"
#include "SeedBall.generated.h"

class UAudioComponent;
class UCameraComponent;
class UNiagaraComponent;
class UPointLightComponent;
class USoundBase;
class USpringArmComponent;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnSeedFormChanged, ESeedForm, OldForm, ESeedForm, NewForm);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSeedDied);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSeedRespawned);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSeedCheckpointSet, FVector, Location);

UCLASS()
class ASSIGNMENT1_API ASeedBall : public APawn
{
	GENERATED_BODY()

public:
	ASeedBall();

	virtual void Tick(float DeltaSeconds) override;

	/** The world's KillZ destroys actors by default. The player respawns instead. */
	virtual void FellOutOfWorld(const UDamageType& DamageType) override;

	// --- Input commands, called by ALSPlayerController ---

	/** X = right, Y = forward, relative to the camera. */
	void SetMoveInput(const FVector2D& Input);
	void JumpPressed();
	void JumpReleased();
	void SlamPressed();
	/** Moves to the next unlocked form. Direction is +1 or -1. */
	void CycleForm(int32 Direction);

	// --- Forms ---

	/** Switches form unless it is locked, already active, on cooldown, or the ball is dead. Returns true on success. */
	UFUNCTION(BlueprintCallable, Category = "Seed|Form")
	bool TrySwitchForm(ESeedForm NewForm);

	UFUNCTION(BlueprintPure, Category = "Seed|Form")
	ESeedForm GetCurrentForm() const { return CurrentForm; }

	/** Data of the active form. Returns struct defaults if that form was removed from the FormData map. */
	UFUNCTION(BlueprintPure, Category = "Seed|Form")
	const FSeedFormData& GetCurrentFormData() const;

	// --- State queries ---

	UFUNCTION(BlueprintPure, Category = "Seed|State")
	bool IsGrounded() const { return bIsGrounded; }

	/** True until landing after a successful jump input. */
	bool IsInJump() const { return bJumpInProgress; }

	/** True from the start of a slam until the ball lands. Cracked walls and blobs check this later. */
	UFUNCTION(BlueprintPure, Category = "Seed|State")
	bool IsSlamming() const { return bIsSlamming; }

	UFUNCTION(BlueprintPure, Category = "Seed|State")
	bool IsDead() const { return bIsDead; }

	// --- Death and checkpoints ---

	/** Plays the death effect, disables control and schedules a respawn. Does nothing if already dead. */
	UFUNCTION(BlueprintCallable, Category = "Seed|Death")
	void Die();

	/** Sets where the next respawn happens. Called by ACheckpointShrine. */
	UFUNCTION(BlueprintCallable, Category = "Seed|Death")
	void SetCheckpoint(const FVector& Location);

	/** Moves the ball straight to Location and stops it. Used by the dev cheats. */
	void TeleportBall(const FVector& Location);

	// --- Forces from the world, called by wind, water and hazards ---

	/** Adds acceleration in cm/s^2 for this frame. Mass does not affect it, so callers scale it by form data. */
	void AddExternalAcceleration(const FVector& Acceleration);

	/** Replaces the ball's velocity, so a knockback is the same size whatever speed the ball had. Speeds are in cm/s. */
	void Knockback(const FVector& Direction, float HorizontalSpeed, float UpSpeed);

	// --- Observer events ---

	/** Fires after a form switch has been applied. */
	UPROPERTY(BlueprintAssignable, Category = "Seed|Events")
	FOnSeedFormChanged OnFormChanged;

	/** Fires the moment the ball dies. */
	UPROPERTY(BlueprintAssignable, Category = "Seed|Events")
	FOnSeedDied OnDied;

	/** Fires once the ball is back at its checkpoint. */
	UPROPERTY(BlueprintAssignable, Category = "Seed|Events")
	FOnSeedRespawned OnRespawned;

	/** Fires when a new checkpoint is set, with its location. */
	UPROPERTY(BlueprintAssignable, Category = "Seed|Events")
	FOnSeedCheckpointSet OnCheckpointSet;

protected:
	virtual void BeginPlay() override;

	// --- Effect hooks, implemented in the Blueprint child ---

	/** Spawn form-switch particles and sound here. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Seed|Effects")
	void PlayFormSwitchEffect(ESeedForm OldForm, ESeedForm NewForm);

	/** Spawn death particles and sound here. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Seed|Effects")
	void PlayDeathEffect();

	/** Fires when a slam starts in the air. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Seed|Effects")
	void PlaySlamStartEffect();

	/** Fires when a slam reaches the ground. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Seed|Effects")
	void PlaySlamLandEffect();

	// --- Components ---

	/** Root and physics body. Rolling, jumping and form data all act on this component. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> BallMesh;

	/** Shows the active form's Mesh. It turns with the physics body, so it looks like it is rolling. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> RollingVisual;

	/** Shows the active form's UprightMesh. It follows the ball's position but not its rotation. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> UprightVisual;

	/** Lights the ground around the ball with the active form's colour. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> GlowLight;

	/** Plays the active form's GlowEffect. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UNiagaraComponent> GlowParticles;

	/** Keeps the camera behind the ball, with lag and wall collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USpringArmComponent> SpringArm;

	/** The player's view. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UCameraComponent> Camera;

	/** Plays the active form's Roll Sound. Assign an attenuation here if you want one. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UAudioComponent> RollAudio;

	// --- Sounds ---

	/** Plays on every jump. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	TObjectPtr<USoundBase> JumpSound;

	/** Plays on landing. Harder landings are louder. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	TObjectPtr<USoundBase> LandSound;

	/** Plays on every form switch. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	TObjectPtr<USoundBase> FormSwitchSound;

	/** Plays when the ball dies. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	TObjectPtr<USoundBase> DeathSound;

	// --- Forms ---

	/** Data for each form. The constructor fills in defaults; edit them on the Blueprint child. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Forms")
	TMap<ESeedForm, FSeedFormData> FormData;

	/** The form the ball starts in. It does not need to be unlocked. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Forms")
	ESeedForm InitialForm = ESeedForm::Seed;

	/** Minimum seconds between form switches. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Forms", meta = (ClampMin = "0"))
	float FormSwitchCooldown = 0.3f;

	// --- Movement ---

	/** Collision radius in cm. The engine sphere is 50. Update this if you scale the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Movement", meta = (ClampMin = "1"))
	float BallRadius = 50.f;

	/** Airborne acceleration as a fraction of the acceleration the form gets when rolling. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Movement", meta = (ClampMin = "0", ClampMax = "1"))
	float AirControlFraction = 0.25f;

	// --- Jump ---

	/** How far below the ball, in cm, still counts as touching the ground. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Jump", meta = (ClampMin = "0"))
	float GroundCheckDistance = 6.f;

	/** Steepest surface that counts as ground, as a normal Z value. 1 is flat, 0.5 is a 60 degree slope. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Jump", meta = (ClampMin = "0", ClampMax = "1"))
	float MinGroundNormalZ = 0.5f;

	/** Seconds after leaving the ground that a jump still works. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Jump", meta = (ClampMin = "0"))
	float CoyoteTime = 0.1f;

	/** Seconds a jump press is remembered before landing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Jump", meta = (ClampMin = "0"))
	float JumpBufferTime = 0.1f;

	/** Seconds after a jump when ground is ignored, so a quick second press can't double jump. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Jump", meta = (ClampMin = "0"))
	float JumpLockoutTime = 0.15f;

	// --- Form abilities ---

	/** Downward speed in cm/s added by a ground slam. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Abilities", meta = (ClampMin = "0"))
	float SlamImpulse = 1800.f;

	/** Fastest fall speed in cm/s while gliding. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Abilities", meta = (ClampMin = "0"))
	float GlideMaxFallSpeed = 150.f;

	/** Upward acceleration in cm/s^2 while gliding. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Abilities", meta = (ClampMin = "0"))
	float GlideLiftAcceleration = 300.f;

	// --- Death ---

	/** Seconds between dying and respawning. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Death", meta = (ClampMin = "0"))
	float RespawnDelay = 1.f;

	// --- Audio ---

	/** Roll sound pitch when the ball is almost still. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Audio", meta = (ClampMin = "0.4", ClampMax = "2"))
	float RollMinPitch = 0.8f;

	/** Roll sound pitch at the form's top rolling speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Audio", meta = (ClampMin = "0.4", ClampMax = "2"))
	float RollMaxPitch = 1.3f;

	/** How quickly the roll volume changes. Higher is faster. Low values smooth out small bumps. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Audio", meta = (ClampMin = "0.1"))
	float RollFadeSpeed = 8.f;

	/** Falling speed in cm/s below which a landing makes no sound. This keeps small bumps quiet. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Audio", meta = (ClampMin = "0"))
	float LandMinSpeed = 200.f;

	/** Falling speed in cm/s at which the landing sound reaches full volume. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Audio", meta = (ClampMin = "1"))
	float LandFullVolumeSpeed = 1000.f;

private:
	// The per-frame steps, called in order by Tick.
	void UpdateGrounded(const FSeedFormData& Data);
	void UpdateTimers(float DeltaSeconds);
	void TryConsumeJump(const FSeedFormData& Data);
	void ApplyMovement(const FSeedFormData& Data);
	void ApplyTrailEdgeResistance();
	void ApplyGravityScale(const FSeedFormData& Data);
	void ApplyGlide(const FSeedFormData& Data);
	void UpdateRollAudio(const FSeedFormData& Data, float DeltaSeconds);

	bool CheckForGround() const;
	float GetMaxRollSpeed(const FSeedFormData& Data) const;
	bool IsFormUnlocked(ESeedForm Form) const;

	// The form state transition.
	void OnExitForm(ESeedForm OldForm);
	void OnEnterForm(ESeedForm NewForm);
	void ApplyFormData(const FSeedFormData& Data);
	void ApplyFormVisuals(const FSeedFormData& Data);

	void Respawn();

	// Physics events, forwarded to ILSInteractable. UFUNCTION is required to bind them with AddDynamic.
	UFUNCTION()
	void HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void HandleHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		FVector NormalImpulse, const FHitResult& Hit);

	// Velocity saved each Tick. By the time a hit event fires, physics has already changed the real velocity.
	FVector PreImpactVelocity = FVector::ZeroVector;

	// Falling speed on the last frame in the air. By the time the ball counts as grounded, it may have stopped.
	float AirFallSpeed = 0.f;
	float RollVolume = 0.f;

	ESeedForm CurrentForm = ESeedForm::Seed;
	FVector2D MoveInput = FVector2D::ZeroVector;
	FVector CheckpointLocation = FVector::ZeroVector;
	FTimerHandle RespawnTimer;

	bool bIsGrounded = false;
	bool bJumpInProgress = false;
	bool bJumpHeld = false;
	bool bIsSlamming = false;
	bool bIsDead = false;

	// Countdown timers in seconds. Each is "active" while above zero.
	float CoyoteTimeRemaining = 0.f;
	float JumpBufferRemaining = 0.f;
	float JumpLockoutRemaining = 0.f;
	float FormCooldownRemaining = 0.f;
};
