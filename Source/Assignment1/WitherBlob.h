// Last Seed - the enemy of the Withering.
//
// Purpose: patrols between points, chases the ball when it comes close, and returns when it gets away.
// Touching it knocks the ball back and drains restoration. A Stone slam from above kills it.
// It moves with simple straight-line seeking, so it needs no navmesh.
// Design pattern: state machine. EBlobState lists the three behaviours, and Tick runs the current one.
// Connections: reads and knocks back ASeedBall. Drains URestorationSubsystem.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "WitherBlob.generated.h"

class ASeedBall;
class USphereComponent;
class UStaticMeshComponent;

UENUM()
enum class EBlobState : uint8
{
	Patrol,	// Moving between patrol points. Becomes Chase when the ball is inside ChaseRadius.
	Chase,	// Moving straight at the ball. Becomes Return when the ball is outside LoseRadius or dead.
	Return	// Going back to the patrol route. Becomes Patrol on arrival, or Chase if the ball comes close.
};

UCLASS()
class ASSIGNMENT1_API AWitherBlob : public APawn
{
	GENERATED_BODY()

public:
	AWitherBlob();

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

	/** Add a hit sound or dark splash here. Fires when the blob hurts the ball. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Wither Blob|Effects")
	void PlayContactEffect();

	/** Add a burst of particles here. Fires just before the blob is destroyed. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Wither Blob|Effects")
	void PlayDeathEffect();

	/** Detects the ball, and stops the blob at walls. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USphereComponent> Body;

	/** The visible blob. It has no collision of its own. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Route, relative to the blob. Drag the diamond widgets in the viewport. Empty means it guards its start point. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wither Blob", meta = (MakeEditWidget = "true"))
	TArray<FVector> PatrolPoints;

	/** Speed while patrolling, in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PatrolSpeed = 150.f;

	/** Speed while chasing, in cm/s. Keep it below rolling speed so the player can escape. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ChaseSpeed = 350.f;

	/** Speed while returning to its route, in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ReturnSpeed = 250.f;

	/** Starts chasing when the ball is within this many cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ChaseRadius = 800.f;

	/** Gives up when the ball is further than this. Keep it above Chase Radius, or the blob will flicker between states. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float LoseRadius = 1400.f;

	/** Counts as having reached a patrol point at this distance, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float ArrivalDistance = 30.f;

	/** Height of the blob's centre above the ground, in cm. Keep it above the Body radius so slopes don't block it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float HoverHeight = 70.f;

	/** Tallest step it can climb, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float MaxStepHeight = 100.f;

	/** Biggest drop it will move onto, in cm. Anything larger counts as a ledge, and it stops at the edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float MaxDropHeight = 300.f;

	/** Restoration lost on each hit (0 to 1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0", ClampMax = "1"))
	float RestorationDrain = 0.05f;

	/** Horizontal speed of the knockback, in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KnockbackSpeed = 800.f;

	/** Upward speed of the knockback, in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KnockbackUpSpeed = 400.f;

	/** Seconds after a hit before the blob can hurt the ball again. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ContactCooldown = 1.f;

	/** Downward speed in cm/s a slamming form needs to kill the blob. A normal Stone fall stays below this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float SlamKillSpeed = 1000.f;

private:
	void UpdateState(ASeedBall* Ball, float DeltaSeconds);
	bool IsBallWithin(const ASeedBall* Ball, float Radius) const;
	/** Moves toward Target on the ground. Returns true on arrival. */
	bool MoveToward(const FVector& Target, float Speed, float DeltaSeconds);
	void HandleBallContact(ASeedBall* Ball);

	EBlobState State = EBlobState::Patrol;
	TArray<FVector> WorldPatrolPoints;
	int32 PatrolIndex = 0;
	float ContactCooldownRemaining = 0.f;
};
