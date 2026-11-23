// Last Seed - a platform that gives way after the ball lands on it.
//
// Purpose: on contact it shakes, then falls, then comes back after a delay.
// Design pattern: state machine. ECrumbleState lists each stage, and Tick runs the current one.
// Connections: ASeedBall calls OnBallHit through ILSInteractable. ASinkingPad is a child that only changes
// the default values.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "CrumblingPlatform.generated.h"

class UStaticMeshComponent;

UENUM()
enum class ECrumbleState : uint8
{
	Solid,		// Waiting for the ball.
	Shaking,	// Warning the player.
	Falling,	// Moving down.
	Waiting,	// At the bottom, or vanished, until the respawn delay ends.
	Returning	// Moving back up (only when bVanishAfterFall is off).
};

UCLASS()
class ASSIGNMENT1_API ACrumblingPlatform : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ACrumblingPlatform();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void OnBallHit(ASeedBall* Ball, FVector ImpactVelocity) override;

protected:
	/** Add a crack sound or dust here. Fires when the shaking starts. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Crumbling Platform|Effects")
	void PlayCrumbleEffect();

	/** Stays still while the mesh moves. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** The surface the ball stands on. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Seconds of shaking before it falls. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ShakeDuration = 0.8f;

	/** Shake size in cm. Horizontal only, because vertical shaking would launch the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ShakeAmplitude = 2.f;

	/** Fall speed in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float FallSpeed = 900.f;

	/** How far it falls in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float FallDistance = 1500.f;

	/** Seconds at the bottom before it comes back. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RespawnDelay = 3.f;

	/** On: disappears at the bottom and reappears in place. Off: stays visible and moves back up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bVanishAfterFall = true;

	/** Speed in cm/s when moving back up. Only used when Vanish After Fall is off. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float ReturnSpeed = 150.f;

private:
	void SetState(ECrumbleState NewState);
	void SetMeshPresent(bool bPresent);

	ECrumbleState State = ECrumbleState::Solid;
	// Counts down in the Shaking and Waiting states.
	float StateTimeRemaining = 0.f;
	// How far below its start the mesh currently is.
	float CurrentDrop = 0.f;
	// Where the level placed the mesh inside the actor. Shaking and falling move it from here, so a mesh lowered
	// to put its top at the actor's height doesn't snap back up and launch the ball.
	FVector MeshRestLocation = FVector::ZeroVector;
};
