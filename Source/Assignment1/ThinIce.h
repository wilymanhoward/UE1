// Last Seed - ice that only holds light forms.
//
// Purpose: breaks when a heavy form is on it, and freezes over again after a delay so the route can't be
// lost for good.
// Design pattern: data-driven. It compares mass and never asks "is this Stone?".
// Connections: child of ALSVolumeBase. Reads ASeedBall::GetCurrentFormData.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "ThinIce.generated.h"

class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API AThinIce : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AThinIce();

	virtual void Tick(float DeltaSeconds) override;

protected:
	/** Spawn the crack sound and ice shards here. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Thin Ice|Effects")
	void PlayBreakEffect();

	/** The solid surface, directly below the trigger box. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Forms at least this heavy break the ice. Default forms: Seed 20, Dandelion 5, Stone 80. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BreakMassKg = 50.f;

	/** Seconds until the ice re-forms. 0 means it stays broken. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestoreDelay = 5.f;

private:
	void Break();
	void Restore();

	FTimerHandle RestoreTimer;
	bool bBroken = false;
};
