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
class UStaticMesh;
class UMaterialInterface;

UCLASS(Abstract)
class ASSIGNMENT1_API ALSPickupBase : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ALSPickupBase();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void OnBallOverlap(ASeedBall* Ball) override;

protected:
	/** The payload of the pickup. Children implement this. */
	virtual void OnCollected(ASeedBall* Ball) {}

	/** Pitch of the collect sound, 1 for its own pitch. Runs after OnCollected, so a child can follow a running count. */
	virtual float GetCollectPitch() const { return 1.f; }

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

	/** A looping effect on the model while it waits, such as sparks crackling off an energy orb. Goes with it. Optional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<UNiagaraSystem> IdleEffect;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects", meta = (ClampMin = "0"))
	float IdleEffectScale = 1.f;

	/** The model trembles up to this far, in cm, as if it can barely hold what's inside. 0 for still. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float ShakeAmount = 0.f;

	/** Lightning bolt meshes, pivot at one end, that crackle out of the model. Empty for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects|Lightning")
	TArray<TObjectPtr<UStaticMesh>> ArcMeshes;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects|Lightning")
	TObjectPtr<UMaterialInterface> ArcMaterial;

	/** How many arcs can show at once. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects|Lightning", meta = (ClampMin = "0"))
	int32 ArcCount = 0;

	/** Length of an arc in cm, from the model's centre outward. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects|Lightning", meta = (ClampMin = "0"))
	float ArcLength = 110.f;

	/** Average seconds an arc holds before it jumps somewhere new or blinks out. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects|Lightning", meta = (ClampMin = "0.01"))
	float ArcFlickerTime = 0.07f;

private:
	/** Gives every arc a new random direction, mesh and on/off state. */
	void RestrikeArcs();

	bool bCollected = false;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Arcs;

	float ArcTimeRemaining = 0.f;
};
