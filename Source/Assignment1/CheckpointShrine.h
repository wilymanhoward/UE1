// Last Seed - a respawn point that lights up when the ball reaches it.
//
// Purpose: sets the ball's respawn location, turns on its glow and locks in restoration. It works only once.
// Design pattern: none. It is a plain implementer of the ILSInteractable interface.
// Connections: touched by ASeedBall through ILSInteractable. Calls ASeedBall::SetCheckpoint and
// URestorationSubsystem::LockInRestoration.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "CheckpointShrine.generated.h"

class UNiagaraSystem;
class UPointLightComponent;
class USoundBase;
class USphereComponent;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ACheckpointShrine : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ACheckpointShrine();

	virtual void OnBallOverlap(ASeedBall* Ball) override;
	virtual void Tick(float DeltaSeconds) override;

	/** True once the ball has reached this shrine. */
	bool IsActivated() const { return bActivated; }

protected:
	/** Change the mesh material here to make the shrine itself glow. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Checkpoint")
	void PlayActivateEffect();

	/** Overlap area that activates the shrine. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USphereComponent> Trigger;

	/** The visible shrine. It has no collision until you enable it on the Blueprint child. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Glow light, off until the shrine is activated. Set its colour and brightness here. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UPointLightComponent> Glow;

	/** Particle effect spawned on activation. Optional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<UNiagaraSystem> ActivateEffect;

	/** Sound played on activation. Optional. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<USoundBase> ActivateSound;

	/** How far above the shrine the ball respawns, in cm, so it doesn't appear inside the floor. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RespawnHeight = 100.f;

	/** Seconds the lantern takes to brighten from dark to full once lit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float LightFadeTime = 1.2f;

private:
	bool bActivated = false;

	/** The light's brightness as placed, which the fade-in rises to. */
	float FullIntensity = 0.f;

	/** How far the fade-in has got, 0 to 1. */
	float LightAlpha = 0.f;
};
