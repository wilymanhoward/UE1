// Last Seed - thorns and spikes.
//
// Purpose: kills fragile or light forms on touch, and knocks heavy forms back.
// Design pattern: data-driven. The result comes from bFragile and MassKg, and never from "is this Stone?".
// Connections: child of ALSVolumeBase. Reads ASeedBall::GetCurrentFormData, then calls Die or Knockback.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "HazardVolume.generated.h"

class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API AHazardVolume : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AHazardVolume();

	virtual void Tick(float DeltaSeconds) override;

protected:
	/** Add a clang sound or sparks here. Fires when a heavy form is knocked back. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Hazard|Effects")
	void PlayKnockbackEffect();

	/** The visible thorns. It has no collision, so only the box decides what gets hurt. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Forms at least this heavy survive, unless they are fragile. Default forms: Seed 20, Stone 80. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float SurviveMassKg = 50.f;

	/** Horizontal speed in cm/s of a knockback. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KnockbackSpeed = 700.f;

	/** Upward speed in cm/s of a knockback. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KnockbackUpSpeed = 350.f;

	/** Minimum seconds between knockbacks, so one bounce can't apply several frames in a row. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KnockbackCooldown = 0.4f;

private:
	void Knockback(ASeedBall* Ball);

	double NextKnockbackTime = 0.0;
};
