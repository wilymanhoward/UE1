// Last Seed - shared behaviour of everything the ball can collect.
//
// Purpose: bobbing, spinning, the collect-once rule, effects and removal. Children supply only their payload.
// Design pattern: template method. OnBallOverlap fixes the order of the steps, and children fill in the
// OnCollected step.
// Connections: ASeedBall triggers collection through ILSInteractable. Children are ALifeNote, AGoldenPetal
// and AFormFlower.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "LSPickupBase.generated.h"

class UNiagaraSystem;
class USoundBase;
class USphereComponent;
class UStaticMeshComponent;

UCLASS(Abstract)
class ASSIGNMENT1_API ALSPickupBase : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ALSPickupBase();

	virtual void Tick(float DeltaSeconds) override;
	virtual void OnBallOverlap(ASeedBall* Ball) override;

protected:
	/** The payload of the pickup. Children implement this. */
	virtual void OnCollected(ASeedBall* Ball) {}

	/** Overlap area that detects the ball. Change its radius to make the pickup easier or harder to touch. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USphereComponent> Trigger;

	/** The visible model. It moves separately so the trigger stays still while it bobs. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Particle effect spawned on collection. Optional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<UNiagaraSystem> CollectEffect;

	/** Sound played on collection. Optional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<USoundBase> CollectSound;

	/** How far the mesh moves up and down, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BobHeight = 15.f;

	/** Bob speed in radians per second. About 6.3 is one full cycle each second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BobSpeed = 2.f;

	/** Spin speed in degrees per second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float SpinSpeed = 90.f;

private:
	bool bCollected = false;
};
