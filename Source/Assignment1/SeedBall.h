// Last Seed - the player's ball.
//
// Purpose: the physics-driven pawn. It rolls, jumps, glides, slams, changes form, dies and respawns.
// Design patterns:
//   - State pattern (small, data-driven): TrySwitchForm runs OnExitForm then OnEnterForm, and the
//     active state's behaviour comes from its FSeedFormData entry.
//   - Observer pattern: OnFormChanged, OnDied and OnRespawned let UI and audio react without the ball
//     knowing they exist.
// Connections: ALSPlayerController calls the input functions below. ULSGameInstance says which forms are
// unlocked. Everything the ball touches is told through ILSInteractable. Hazards, water and wind (Phase 3)
// read GetCurrentFormData().

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "SeedFormTypes.h"
#include "SeedBall.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnSeedFormChanged, ESeedForm, OldForm, ESeedForm, NewForm);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSeedDied);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSeedRespawned);

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

	/** True from the start of a slam until the ball lands. Cracked walls and blobs check this later. */
	UFUNCTION(BlueprintPure, Category = "Seed|State")
	bool IsSlamming() const { return bIsSlamming; }

	UFUNCTION(BlueprintPure, Category = "Seed|State")
	bool IsDead() const { return bIsDead; }

	// --- Death and checkpoints ---

	/** Plays the death effect, disables control and schedules a respawn. Does nothing if already dead. */
	UFUNCTION(BlueprintCallable, Category = "Seed|Death")
	void Die();

	/** Sets where the next respawn happens. Called by ACheckpointShrine in Phase 2. */
	UFUNCTION(BlueprintCallable, Category = "Seed|Death")
	void SetCheckpoint(const FVector& Location) { CheckpointLocation = Location; }

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

	/** Keeps the camera behind the ball, with lag and wall collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USpringArmComponent> SpringArm;

	/** The player's view. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UCameraComponent> Camera;

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

private:
	// The per-frame steps, called in order by Tick.
	void UpdateGrounded();
	void UpdateTimers(float DeltaSeconds);
	void TryConsumeJump(const FSeedFormData& Data);
	void ApplyMovement(const FSeedFormData& Data);
	void ApplyGravityScale(const FSeedFormData& Data);
	void ApplyGlide(const FSeedFormData& Data);

	bool CheckForGround() const;
	bool IsFormUnlocked(ESeedForm Form) const;

	// The form state transition.
	void OnExitForm(ESeedForm OldForm);
	void OnEnterForm(ESeedForm NewForm);
	void ApplyFormData(const FSeedFormData& Data);

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

	ESeedForm CurrentForm = ESeedForm::Seed;
	FVector2D MoveInput = FVector2D::ZeroVector;
	FVector CheckpointLocation = FVector::ZeroVector;
	FTimerHandle RespawnTimer;

	bool bIsGrounded = false;
	bool bJumpHeld = false;
	bool bIsSlamming = false;
	bool bIsDead = false;

	// Countdown timers in seconds. Each is "active" while above zero.
	float CoyoteTimeRemaining = 0.f;
	float JumpBufferRemaining = 0.f;
	float JumpLockoutRemaining = 0.f;
	float FormCooldownRemaining = 0.f;
};
